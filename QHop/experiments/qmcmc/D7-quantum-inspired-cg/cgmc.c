// D7 quantum-inspired coarse-grained QeMCMC: C kernels for honest wall-clock comparison.
// Single thread, scalar C, -O3. All moves keep cached local fields l_i = h_i + sum_j J_ij s_j.
// Energy E(s) = -sum_{i<j} J_ij s_i s_j - sum_i h_i s_i ; target pi ~ exp(-beta E).
//
// Methods (chain_run):
//   0  single-spin Metropolis, one move = one sequential sweep over all n sites
//   1  CG block heat-bath (exact Gibbs on the group, 2^k enumeration), no accept step needed
//   2  CG quantum proposal: |psi> = exp(-i H_g t)|x0>, H_g = (1-gam)*alpha*E_g + gam*sum X,
//      exact statevector via Chebyshev/Bessel expansion (machine precision), sample x', MH accept
//   3  CG decohered control: same generator, Z-dephased every dt = t/round(t/0.25) (sample per slice)
// Group modes: 0 random consecutive block (start uniform, wrap), 1 random k-subset,
//              2 fixed precomputed partition, part chosen uniformly. All state independent -> symmetric.
// pt_run: parallel tempering with Metropolis sweeps, optional Houdayer cluster move (2 sets).
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

typedef struct { uint64_t s[4]; } rng_t;
static inline uint64_t rotl(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }
static uint64_t splitmix(uint64_t *x) {
    uint64_t z = (*x += 0x9E3779B97F4A7C15ULL);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}
static void rng_seed(rng_t *r, uint64_t seed) { for (int i = 0; i < 4; i++) r->s[i] = splitmix(&seed); }
static inline uint64_t rnext(rng_t *r) {
    uint64_t *s = r->s, res = rotl(s[1] * 5, 7) * 9, t = s[1] << 17;
    s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3]; s[2] ^= t; s[3] = rotl(s[3], 45);
    return res;
}
static inline double u01(rng_t *r) { return (rnext(r) >> 11) * (1.0 / 9007199254740992.0); }
static inline int randint(rng_t *r, int n) { return (int)(u01(r) * n); }
static double cputime(void) {
    struct timespec t; clock_gettime(CLOCK_THREAD_CPUTIME_ID, &t); return t.tv_sec + 1e-9 * t.tv_nsec;
}

typedef struct {
    int n; const int *rp, *ci; const double *cv, *h, *Jd;
    int *s; double *l; double E; int ham; const int *sref;
} sys_t;

static void sys_init(sys_t *y) {
    int n = y->n; double E = 0; int ham = 0;
    for (int i = 0; i < n; i++) {
        double f = y->h[i];
        for (int p = y->rp[i]; p < y->rp[i + 1]; p++) f += y->cv[p] * y->s[y->ci[p]];
        y->l[i] = f;
    }
    for (int i = 0; i < n; i++) {
        E += -0.5 * y->s[i] * (y->l[i] - y->h[i]) - y->h[i] * y->s[i];
        ham += (y->s[i] != y->sref[i]);
    }
    y->E = E; y->ham = ham;
}
static inline void flip(sys_t *y, int i) {
    y->s[i] = -y->s[i];
    double d = 2.0 * y->s[i];
    for (int p = y->rp[i]; p < y->rp[i + 1]; p++) y->l[y->ci[p]] += d * y->cv[p];
    y->ham += (y->s[i] != y->sref[i]) ? 1 : -1;
}
static void metro_sweep(sys_t *y, double beta, rng_t *r, long *acc) {
    for (int i = 0; i < y->n; i++) {
        double dE = 2.0 * y->s[i] * y->l[i];
        if (dE <= 0 || u01(r) < exp(-beta * dE)) { y->E += dE; flip(y, i); (*acc)++; }
    }
}

// ---------------------------------------------------------------- Bessel J_0..J_M(x) (Miller)
static void bessel_array(double x, int M, double *J, double *work) {
    if (x < 1e-14) { J[0] = 1; for (int m = 1; m <= M; m++) J[m] = 0; return; }
    int mx = M > (int)x ? M : (int)x;
    int N = mx + 30 + (int)sqrt(40.0 * mx); if (N & 1) N++;
    double jp1 = 0.0, j = 1e-280, sum = 0.0;
    // work[m] holds unnormalised J_m for m<=M
    for (int m = N; m >= 1; m--) {
        double jm1 = (2.0 * m / x) * j - jp1;
        if (m <= M) work[m] = j;
        if (m % 2 == 0) sum += 2.0 * j;
        jp1 = j; j = jm1;
        if (fabs(j) > 1e250) {
            j *= 1e-250; jp1 *= 1e-250; sum *= 1e-250;
            for (int q = m; q <= M; q++) work[q] *= 1e-250;
        }
    }
    sum += j; // J_0 term
    work[0] = j;
    for (int m = 0; m <= M; m++) J[m] = work[m] / sum;
}

// ---------------------------------------------------------------- group machinery
typedef struct {
    int kmax; int *g; double *Jg, *heff, *Eg, *f; int *x;
    double *v0, *v1, *v2, *re, *im, *bes, *bw; int *perm;
    long cheb_terms;
} gws_t;

static gws_t *gws_new(int n, int kmax) {
    gws_t *w = calloc(1, sizeof(gws_t)); int D = 1 << kmax;
    w->kmax = kmax; w->g = malloc(sizeof(int) * kmax); w->Jg = malloc(sizeof(double) * kmax * kmax);
    w->heff = malloc(sizeof(double) * kmax); w->f = malloc(sizeof(double) * kmax); w->x = malloc(sizeof(int) * kmax);
    w->Eg = malloc(sizeof(double) * D); w->v0 = malloc(sizeof(double) * D); w->v1 = malloc(sizeof(double) * D);
    w->v2 = malloc(sizeof(double) * D); w->re = malloc(sizeof(double) * D); w->im = malloc(sizeof(double) * D);
    w->bes = malloc(sizeof(double) * 4096); w->bw = malloc(sizeof(double) * 4096);
    w->perm = malloc(sizeof(int) * n); for (int i = 0; i < n; i++) w->perm[i] = i;
    return w;
}
static void gws_free(gws_t *w) {
    free(w->g); free(w->Jg); free(w->heff); free(w->f); free(w->x); free(w->Eg); free(w->v0); free(w->v1);
    free(w->v2); free(w->re); free(w->im); free(w->bes); free(w->bw); free(w->perm); free(w);
}

static int choose_group(int mode, int k, int n, const int *parts, const int *poff, int nparts, gws_t *w, rng_t *r) {
    if (mode == 0) { int st = randint(r, n); for (int a = 0; a < k; a++) w->g[a] = (st + a) % n; return k; }
    if (mode == 1) {
        for (int a = 0; a < k; a++) {
            int b = a + randint(r, n - a); int t = w->perm[a]; w->perm[a] = w->perm[b]; w->perm[b] = t;
            w->g[a] = w->perm[a];
        }
        return k;
    }
    int p = randint(r, nparts); int kk = poff[p + 1] - poff[p];
    for (int a = 0; a < kk; a++) w->g[a] = parts[poff[p] + a];
    return kk;
}

// fills Jg, heff, Eg[2^k] (bit a = 1 <-> spin g[a] = -1); returns index of current config
static int group_energies(sys_t *y, gws_t *w, int k) {
    int n = y->n; double *Jg = w->Jg;
    for (int a = 0; a < k; a++) for (int b = 0; b < k; b++) Jg[a * k + b] = (a == b) ? 0.0 : y->Jd[(long)w->g[a] * n + w->g[b]];
    int x0 = 0;
    for (int a = 0; a < k; a++) {
        double hf = y->l[w->g[a]];
        for (int b = 0; b < k; b++) hf -= Jg[a * k + b] * y->s[w->g[b]];
        w->heff[a] = hf;
        if (y->s[w->g[a]] < 0) x0 |= (1 << a);
    }
    double E = 0;
    for (int a = 0; a < k; a++) {
        w->x[a] = 1; double fa = w->heff[a];
        for (int b = 0; b < k; b++) fa += Jg[a * k + b];
        w->f[a] = fa; E -= w->heff[a];
        for (int b = a + 1; b < k; b++) E -= Jg[a * k + b];
    }
    int D = 1 << k; int gray = 0; w->Eg[0] = E;
    for (int i = 1; i < D; i++) {
        int a = __builtin_ctz(i);
        E += 2.0 * w->x[a] * w->f[a];
        w->x[a] = -w->x[a];
        double d = 2.0 * w->x[a]; const double *Ja = Jg + a * k;
        for (int b = 0; b < k; b++) w->f[b] += d * Ja[b];
        gray ^= (1 << a);
        w->Eg[gray] = E;
    }
    return x0;
}

static int sample_prob(const double *p, int D, double tot, rng_t *r) {
    double u = u01(r) * tot, c = 0;
    for (int i = 0; i < D; i++) { c += p[i]; if (u < c) return i; }
    return D - 1;
}

// psi = exp(-i H t)|x0>, H = diag(d) + gam*sum X (d already scaled). Probabilities into w->re.
static void evolve_basis(gws_t *w, int k, const double *d, double gam, double t, int x0) {
    int D = 1 << k;
    double dmin = d[0], dmax = d[0];
    for (int i = 1; i < D; i++) { if (d[i] < dmin) dmin = d[i]; if (d[i] > dmax) dmax = d[i]; }
    double lo = dmin - gam * k, hi = dmax + gam * k;
    double c = 0.5 * (lo + hi), rr = 0.5 * (hi - lo) * 1.0001 + 1e-12;
    double X = rr * t;
    int M = (int)(X + 6.0 * cbrt(X) + 25);
    if (M > 4000) M = 4000;
    bessel_array(X, M, w->bes, w->bw);
    double *T0 = w->v0, *T1 = w->v1, *T2 = w->v2, *re = w->re, *im = w->im;
    double gs = gam / rr;
    memset(T0, 0, sizeof(double) * D); T0[x0] = 1.0;
    for (int i = 0; i < D; i++) { re[i] = 0; im[i] = 0; }
    re[x0] = w->bes[0];
    // T1 = Hn T0
    for (int i = 0; i < D; i++) {
        double acc = (d[i] - c) / rr * T0[i];
        for (int a = 0; a < k; a++) acc += gs * T0[i ^ (1 << a)];
        T1[i] = acc;
    }
    { double cf = -2.0 * w->bes[1]; for (int i = 0; i < D; i++) im[i] += cf * T1[i]; }
    for (int m = 2; m <= M; m++) {
        for (int i = 0; i < D; i++) {
            double acc = (d[i] - c) / rr * T1[i];
            for (int a = 0; a < k; a++) acc += gs * T1[i ^ (1 << a)];
            T2[i] = 2.0 * acc - T0[i];
        }
        double cf = 2.0 * w->bes[m];
        switch (m & 3) {
            case 0: for (int i = 0; i < D; i++) re[i] += cf * T2[i]; break;
            case 1: for (int i = 0; i < D; i++) im[i] -= cf * T2[i]; break;
            case 2: for (int i = 0; i < D; i++) re[i] -= cf * T2[i]; break;
            default: for (int i = 0; i < D; i++) im[i] += cf * T2[i]; break;
        }
        double *tmp = T0; T0 = T1; T1 = T2; T2 = tmp;
    }
    w->cheb_terms += M;
    for (int i = 0; i < D; i++) re[i] = re[i] * re[i] + im[i] * im[i];
}

static double group_alpha(gws_t *w, int k) {
    double s2 = 0;
    for (int a = 0; a < k; a++) { s2 += w->heff[a] * w->heff[a]; for (int b = a + 1; b < k; b++) s2 += w->Jg[a * k + b] * w->Jg[a * k + b]; }
    return s2 > 0 ? sqrt((double)k) / sqrt(s2) : 1.0;
}

static void apply_group(sys_t *y, gws_t *w, int k, int x0, int x1) {
    int diff = x0 ^ x1;
    y->E += w->Eg[x1] - w->Eg[x0];
    for (int a = 0; a < k; a++) if (diff & (1 << a)) flip(y, w->g[a]);
}

// returns 1 if state changed
static int group_move(int method, sys_t *y, gws_t *w, int k, double beta, rng_t *r) {
    int D = 1 << k;
    int x0 = group_energies(y, w, k);
    if (method == 1) {
        double Emin = w->Eg[0];
        for (int i = 1; i < D; i++) if (w->Eg[i] < Emin) Emin = w->Eg[i];
        double tot = 0;
        for (int i = 0; i < D; i++) { double p = exp(-beta * (w->Eg[i] - Emin)); w->re[i] = p; tot += p; }
        int x1 = sample_prob(w->re, D, tot, r);
        if (x1 != x0) { apply_group(y, w, k, x0, x1); return 1; }
        return 0;
    }
    double gam = 0.25 + 0.35 * u01(r), t = 2.0 + 18.0 * u01(r);
    double al = group_alpha(w, k);
    double *d = w->f; // need a D-sized buffer: reuse v2? v2 used by Chebyshev; allocate scaled diag in bw? use im? -> use dedicated
    (void)d;
    static double *dbuf = NULL; static int dcap = 0;
    if (dcap < D) { free(dbuf); dbuf = malloc(sizeof(double) * D); dcap = D; }
    for (int i = 0; i < D; i++) dbuf[i] = (1.0 - gam) * al * w->Eg[i];
    int x1;
    if (method == 2) {
        evolve_basis(w, k, dbuf, gam, t, x0);
        double tot = 0; for (int i = 0; i < D; i++) tot += w->re[i];
        x1 = sample_prob(w->re, D, tot, r);
    } else {
        int ns = (int)lround(t / 0.25); if (ns < 1) ns = 1;
        double dt = t / ns; x1 = x0;
        for (int q = 0; q < ns; q++) {
            evolve_basis(w, k, dbuf, gam, dt, x1);
            double tot = 0; for (int i = 0; i < D; i++) tot += w->re[i];
            x1 = sample_prob(w->re, D, tot, r);
        }
    }
    if (x1 == x0) return 0;
    double dE = w->Eg[x1] - w->Eg[x0];
    if (dE <= 0 || u01(r) < exp(-beta * dE)) { apply_group(y, w, k, x0, x1); return 1; }
    return 0;
}

// stats: [0]=accepted/changed moves, [1]=moves, [2]=cpu seconds, [3]=mean chebyshev terms per evolve call,
//        [4]=sum of hamming size of accepted group changes
int chain_run(int method, int gmode, int k, int n, const int *rp, const int *ci, const double *cv,
              const double *Jd, const double *h, double beta, int *s, const int *sref,
              const int *parts, const int *poff, int nparts, int moves_per_rec, int max_rec,
              double tlimit, uint64_t seed, double *recE, int *recH, double *recT, double *stats) {
    rng_t r; rng_seed(&r, seed);
    double *l = malloc(sizeof(double) * n);
    sys_t y = {n, rp, ci, cv, h, Jd, s, l, 0, 0, sref};
    sys_init(&y);
    int kmax = k; if (gmode == 2) for (int p = 0; p < nparts; p++) if (poff[p + 1] - poff[p] > kmax) kmax = poff[p + 1] - poff[p];
    gws_t *w = (method > 0) ? gws_new(n, kmax) : NULL;
    long acc = 0, moves = 0; double flips = 0; long ncalls = 0;
    double t0 = cputime(); int nrec = 0;
    while (nrec < max_rec) {
        for (int q = 0; q < moves_per_rec; q++) {
            if (method == 0) metro_sweep(&y, beta, &r, &acc);
            else {
                int kk = choose_group(gmode, k, n, parts, poff, nparts, w, &r);
                int hold = y.ham; (void)hold;
                long ct = w->cheb_terms;
                int ch = group_move(method, &y, w, kk, beta, &r);
                if (w->cheb_terms != ct) ncalls++;
                acc += ch;
            }
            moves++;
        }
        double tn = cputime() - t0;
        recE[nrec] = y.E; recH[nrec] = y.ham; recT[nrec] = tn; nrec++;
        if (tn > tlimit) break;
    }
    stats[0] = (double)acc; stats[1] = (double)moves; stats[2] = cputime() - t0;
    stats[3] = (w && ncalls) ? (double)w->cheb_terms / ncalls : 0.0; stats[4] = flips;
    if (w) gws_free(w);
    free(l);
    return nrec;
}

// test hook: evolve a given diagonal for given gamma,t from basis x0, output probabilities
void test_evolve(int k, const double *d, double gam, double t, int x0, double *out) {
    gws_t *w = gws_new(1, k);
    evolve_basis(w, k, d, gam, t, x0);
    memcpy(out, w->re, sizeof(double) * (1 << k));
    gws_free(w);
}
void test_bessel(double x, int M, double *out) {
    double *wk = malloc(sizeof(double) * (M + 1)); bessel_array(x, M, out, wk); free(wk);
}

// ---------------------------------------------------------------- parallel tempering (+ Houdayer)
// S: nsets*R*n spins (storage); betas ascending length R; temps at index >= houd_from get Houdayer (nsets==2).
// records E and hamming of set-0 configuration sitting at temperature index tgt after every sweep.
int pt_run(int n, const int *rp, const int *ci, const double *cv, const double *h, int R, const double *betas,
           int *S, int nsets, int houd_from, int tgt, const int *sref, int max_rec, double tlimit, uint64_t seed,
           double *recE, int *recH, double *recT, double *swap_rate, double *stats) {
    rng_t r; rng_seed(&r, seed);
    int NR = nsets * R;
    sys_t *ys = malloc(sizeof(sys_t) * NR); double *L = malloc(sizeof(double) * NR * n);
    for (int q = 0; q < NR; q++) {
        sys_t y = {n, rp, ci, cv, h, NULL, S + (long)q * n, L + (long)q * n, 0, 0, sref};
        ys[q] = y; sys_init(&ys[q]);
    }
    int *perm = malloc(sizeof(int) * NR); // perm[set*R + temp] = storage index
    for (int q = 0; q < NR; q++) perm[q] = q;
    long *sacc = calloc(R, sizeof(long)), *stry = calloc(R, sizeof(long));
    int *stack = malloc(sizeof(int) * n); char *inc = calloc(n, 1); int *neg = malloc(sizeof(int) * n);
    long acc = 0, sweeps = 0, hmoves = 0; double hsize = 0;
    double t0 = cputime(); int nrec = 0;
    while (nrec < max_rec) {
        for (int st = 0; st < nsets; st++)
            for (int tq = 0; tq < R; tq++) metro_sweep(&ys[perm[st * R + tq]], betas[tq], &r, &acc);
        for (int st = 0; st < nsets; st++)
            for (int tq = (int)(sweeps & 1); tq < R - 1; tq += 2) {
                sys_t *a = &ys[perm[st * R + tq]], *b = &ys[perm[st * R + tq + 1]];
                double x = (betas[tq + 1] - betas[tq]) * (b->E - a->E);
                if (st == 0) stry[tq]++;
                if (x >= 0 || u01(&r) < exp(x)) {
                    int tmp = perm[st * R + tq]; perm[st * R + tq] = perm[st * R + tq + 1]; perm[st * R + tq + 1] = tmp;
                    if (st == 0) sacc[tq]++;
                }
            }
        if (nsets == 2) {
            for (int tq = houd_from; tq < R; tq++) {
                sys_t *A = &ys[perm[tq]], *B = &ys[perm[R + tq]];
                int nn = 0;
                for (int i = 0; i < n; i++) if (A->s[i] != B->s[i]) neg[nn++] = i;
                if (nn == 0 || nn == n) continue;
                int seedsite = neg[randint(&r, nn)];
                int sp = 0, csz = 0; stack[sp++] = seedsite; inc[seedsite] = 1;
                // collect cluster into neg[] reuse as list (overwrite from 0)
                int *clu = neg;
                while (sp) {
                    int i = stack[--sp]; clu[csz++] = i;
                    for (int p = rp[i]; p < rp[i + 1]; p++) {
                        int j = ci[p];
                        if (!inc[j] && A->s[j] != B->s[j]) { inc[j] = 1; stack[sp++] = j; }
                    }
                }
                for (int c = 0; c < csz; c++) {
                    int i = clu[c]; inc[i] = 0;
                    double dA = 2.0 * A->s[i] * A->l[i]; A->E += dA; flip(A, i);
                    double dB = 2.0 * B->s[i] * B->l[i]; B->E += dB; flip(B, i);
                }
                hmoves++; hsize += csz;
            }
        }
        sweeps++;
        sys_t *ty = &ys[perm[tgt]];
        double tn = cputime() - t0;
        recE[nrec] = ty->E; recH[nrec] = ty->ham; recT[nrec] = tn; nrec++;
        if (tn > tlimit) break;
    }
    for (int tq = 0; tq < R - 1; tq++) swap_rate[tq] = stry[tq] ? (double)sacc[tq] / stry[tq] : 0.0;
    stats[0] = (double)acc; stats[1] = (double)sweeps; stats[2] = cputime() - t0;
    stats[3] = hmoves ? hsize / hmoves : 0.0;
    // copy back storage in temperature order is not needed; S holds storage states
    free(ys); free(L); free(perm); free(sacc); free(stry); free(stack); free(inc); free(neg);
    return nrec;
}
