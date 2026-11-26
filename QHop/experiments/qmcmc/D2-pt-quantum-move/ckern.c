// D2 kernels: single-spin Metropolis, parallel tempering (+ optional Houdayer), Chebyshev statevector
// propagation for the QeMCMC proposal, and the decohered (dephased every dt) proposal walk.
// Spin convention as qmc.py: state index a, bit i of a = spin i, bit 0 -> s=+1, bit 1 -> s=-1.
// E(s) = -sum_{i<j} J_ij s_i s_j - sum_i h_i s_i, local field F_i = sum_j J_ij s_j + h_i, dE(flip i) = 2 s_i F_i.
// Build: gcc -O3 -march=native -fopenmp -shared -fPIC ckern.c -o libckern.so -lm
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

static inline uint64_t rotl(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }
static inline uint64_t nxt(uint64_t *s) {  // xoshiro256**
    uint64_t r = rotl(s[1] * 5, 7) * 9, t = s[1] << 17;
    s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3]; s[2] ^= t; s[3] = rotl(s[3], 45);
    return r;
}
static inline double u01(uint64_t *s) { return (nxt(s) >> 11) * (1.0 / 9007199254740992.0); }
static inline int rint_n(uint64_t *s, int n) { return (int)(u01(s) * n); }

static inline void do_flip(int n, const double *J, int8_t *s, double *F, int i) {
    s[i] = -s[i];
    double d = 2.0 * s[i];
    const double *Ji = J + (long)i * n;
    for (int j = 0; j < n; j++) F[j] += Ji[j] * d;
}

// one Metropolis sweep (n random-site attempts) on one configuration; returns accepted count
static inline int sweep1(int n, const double *J, double beta, int8_t *s, double *F, double *E, double *q,
                         const int8_t *sgs, uint64_t *rng) {
    int acc = 0;
    for (int k = 0; k < n; k++) {
        int i = rint_n(rng, n);
        double dE = 2.0 * s[i] * F[i];
        if (dE <= 0 || u01(rng) < exp(-beta * dE)) {
            do_flip(n, J, s, F, i);
            *E += dE; *q += 2.0 * s[i] * sgs[i] / n; acc++;
        }
    }
    return acc;
}

// single-spin Metropolis for nflips attempts; record E and q every rec_every attempts
long metro_run(int n, const double *J, double beta, long nflips, int rec_every, int8_t *s, double *F,
               double *E, double *q, const int8_t *sgs, uint64_t *rng, double *outE, double *outQ) {
    long nrec = 0;
    for (long k = 0; k < nflips; k++) {
        int i = rint_n(rng, n);
        double dE = 2.0 * s[i] * F[i];
        if (dE <= 0 || u01(rng) < exp(-beta * dE)) {
            do_flip(n, J, s, F, i);
            *E += dE; *q += 2.0 * s[i] * sgs[i] / n;
        }
        if ((k + 1) % rec_every == 0) { outE[nrec] = *E; outQ[nrec] = *q; nrec++; }
    }
    return nrec;
}

static void swap_rows(int n, int8_t *S, double *F, double *E, double *Q, int a, int b) {
    int8_t tb[64]; double tf[64]; double t;
    memcpy(tb, S + (long)a * n, n); memcpy(S + (long)a * n, S + (long)b * n, n); memcpy(S + (long)b * n, tb, n);
    memcpy(tf, F + (long)a * n, n * 8); memcpy(F + (long)a * n, F + (long)b * n, n * 8); memcpy(F + (long)b * n, tf, n * 8);
    t = E[a]; E[a] = E[b]; E[b] = t; t = Q[a]; Q[a] = Q[b]; Q[b] = t;
}

static void recompute(int n, const double *J, const double *h, const int8_t *s, double *F, double *E, double *q,
                      const int8_t *sgs) {
    double e = 0, qq = 0;
    for (int i = 0; i < n; i++) {
        double f = h[i];
        for (int j = 0; j < n; j++) f += J[(long)i * n + j] * s[j];
        F[i] = f;
    }
    for (int i = 0; i < n; i++) { e += -0.5 * s[i] * (F[i] - h[i]) - h[i] * s[i]; qq += s[i] * sgs[i]; }
    *E = e; *q = qq / n;
}

void recompute_row(int n, const double *J, const double *h, const int8_t *s, double *F, double *E, double *q,
                   const int8_t *sgs) { recompute(n, J, h, s, F, E, q, sgs); }

// Houdayer cluster move between configs A and B at equal beta (rejection-free); returns cluster size
static int houdayer(int n, const double *J, const double *h, int8_t *A, int8_t *B, double *FA, double *FB,
                    double *EA, double *EB, double *qA, double *qB, const int8_t *sgs, const int *nbr,
                    const int *deg, int maxdeg, uint64_t *rng) {
    int diff[64], nd = 0, inq[64], queue[64];
    for (int i = 0; i < n; i++) if (A[i] != B[i]) diff[nd++] = i;
    if (nd == 0 || nd == n) return 0;
    memset(inq, 0, sizeof(inq));
    int head = 0, tail = 0, i0 = diff[rint_n(rng, nd)];
    queue[tail++] = i0; inq[i0] = 1;
    while (head < tail) {
        int i = queue[head++];
        for (int k = 0; k < deg[i]; k++) {
            int j = nbr[i * maxdeg + k];
            if (!inq[j] && A[j] != B[j]) { inq[j] = 1; queue[tail++] = j; }
        }
    }
    for (int k = 0; k < tail; k++) { int i = queue[k]; do_flip(n, J, A, FA, i); do_flip(n, J, B, FB, i); }
    recompute(n, J, h, A, FA, EA, qA, sgs); recompute(n, J, h, B, FB, EB, qB, sgs);
    return tail;
}

// PT: ncopy independent ladders of R slots each; config c = copy*R + r sits at betas[r].
// Each sweep: Metropolis sweep of every config, optional Houdayer between copies 0/1 at each slot,
// then replica-exchange on alternating even/odd pairs within each copy. Records copy-0 slot `target`.
void pt_run(int n, int R, int ncopy, const double *J, const double *h, const double *betas, int8_t *S, double *F,
            double *E, double *Q, const int8_t *sgs, long nsweeps, uint64_t *rng, long *parity, double *sw_acc,
            double *sw_try, int target, double *outE, double *outQ, int hou, const int *nbr, const int *deg,
            int maxdeg, double *hstat) {
    for (long sw = 0; sw < nsweeps; sw++) {
        for (int c = 0; c < ncopy * R; c++)
            sweep1(n, J, betas[c % R], S + (long)c * n, F + (long)c * n, E + c, Q + c, sgs, rng);
        if (hou && ncopy == 2) {
            for (int r = 0; r < R; r++) {
                int a = r, b = R + r;
                int cs = houdayer(n, J, h, S + (long)a * n, S + (long)b * n, F + (long)a * n, F + (long)b * n,
                                  E + a, E + b, Q + a, Q + b, sgs, nbr, deg, maxdeg, rng);
                hstat[0] += 1; hstat[1] += cs;
            }
        }
        for (int cp = 0; cp < ncopy; cp++) {
            for (int r = (int)(*parity % 2); r < R - 1; r += 2) {
                int a = cp * R + r, b = cp * R + r + 1;
                double x = (betas[r + 1] - betas[r]) * (E[b] - E[a]);
                sw_try[r] += 1;
                if (x >= 0 || u01(rng) < exp(x)) { swap_rows(n, S, F, E, Q, a, b); sw_acc[r] += 1; }
            }
        }
        (*parity)++;
        if (outE) { outE[sw] = E[target]; outQ[sw] = Q[target]; }
    }
}

// Chebyshev propagation psi_t = exp(-i H t)|s>, H = w*(Ht) + c, Ht = diag(dtil) + gw * sum_i X_i (scaled to [-1,1]).
// coef[t*K + k] = (2-delta_k0) J_k(w t) * sign; real part from even k (sign +,-,+..), imag part from odd k.
// Output outP[t*dim + a] = |<a|psi_t>|^2 (global phase irrelevant). work: 3*dim + 2*nt*dim doubles.
void cheb_evolve(int n, const double *dtil, double gw, long s, int K, int nt, const double *coef, double *outP,
                 double *work) {
    long dim = 1L << n;
    double *v0 = work, *v1 = work + dim, *v2 = work + 2 * dim, *re = work + 3 * dim, *im = re + (long)nt * dim;
    memset(v0, 0, dim * 8); memset(re, 0, (long)nt * dim * 8); memset(im, 0, (long)nt * dim * 8);
    v0[s] = 1.0;
    for (int t = 0; t < nt; t++) re[(long)t * dim + s] += coef[(long)t * K + 0];
    // v1 = Ht v0
    memset(v1, 0, dim * 8);
    v1[s] = dtil[s];
    for (int i = 0; i < n; i++) v1[s ^ (1L << i)] += gw;
    for (int t = 0; t < nt; t++) {
        double c = coef[(long)t * K + 1]; double *imt = im + (long)t * dim;
        for (long a = 0; a < dim; a++) imt[a] += c * v1[a];
    }
    for (int k = 2; k < K; k++) {
        double *dstb = (k % 2 == 0) ? re : im;
        // v2 = sum_i X_i v1 by blocked bit flips (vectorisable), then fuse recursion + accumulation
        memset(v2, 0, dim * 8);
        for (int i = 0; i < n; i++) {
            long h = 1L << i;
            for (long base = 0; base < dim; base += 2 * h) {
                double *lo = v2 + base, *hi = v2 + base + h; const double *vl = v1 + base, *vh = v1 + base + h;
                for (long j = 0; j < h; j++) { lo[j] += vh[j]; hi[j] += vl[j]; }
            }
        }
        for (long a = 0; a < dim; a++) v2[a] = 2.0 * (dtil[a] * v1[a] + gw * v2[a]) - v0[a];
        for (int t = 0; t < nt; t++) {
            double c = coef[(long)t * K + k]; double *dst = dstb + (long)t * dim;
            for (long a = 0; a < dim; a++) dst[a] += c * v2[a];
        }
        double *tmp = v0; v0 = v1; v1 = v2; v2 = tmp;
    }
#pragma omp parallel for schedule(static)
    for (long a = 0; a < dim; a++)
        for (int t = 0; t < nt; t++) {
            double r = re[(long)t * dim + a], m = im[(long)t * dim + a];
            outP[(long)t * dim + a] = r * r + m * m;
        }
}

// Decohered proposal walk: nsub substeps; each substep samples s -> s ^ mask[m] with probability
// |<s^mask[m]| exp(-i H dt) |s>|^2, computed by Chebyshev on the Hamming ball (masks with popcount <= rad).
// adjacency (CSR) between ball masks via single bit flips (edges leaving the ball truncated).
// coef: K signed coefficients for w*dt. Returns final state; *leak accumulates (1 - ball norm).
long dec_walk(int nb, const long *masks, const int *aptr, const int *aidx, const double *Eall, long s0,
              double ascale, double cshift, double winv, double gw, int K, const double *coef, int nsub,
              uint64_t *rng, double *work, double *leak) {
    double *v0 = work, *v1 = work + nb, *v2 = work + 2 * nb, *re = work + 3 * nb, *im = work + 4 * nb,
           *dt = work + 5 * nb;
    long s = s0;
    for (int st = 0; st < nsub; st++) {
        for (int m = 0; m < nb; m++) { dt[m] = (ascale * Eall[s ^ masks[m]] - cshift) * winv; v0[m] = 0; re[m] = 0; im[m] = 0; }
        v0[0] = 1.0; re[0] = coef[0];
        for (int m = 0; m < nb; m++) {
            double acc = 0;
            for (int e = aptr[m]; e < aptr[m + 1]; e++) acc += v0[aidx[e]];
            v1[m] = dt[m] * v0[m] + gw * acc; im[m] += coef[1] * v1[m];
        }
        for (int k = 2; k < K; k++) {
            double *dst = (k % 2 == 0) ? re : im; double c = coef[k];
            for (int m = 0; m < nb; m++) {
                double acc = 0;
                for (int e = aptr[m]; e < aptr[m + 1]; e++) acc += v1[aidx[e]];
                double y = 2.0 * (dt[m] * v1[m] + gw * acc) - v0[m];
                v2[m] = y; dst[m] += c * y;
            }
            double *tmp = v0; v0 = v1; v1 = v2; v2 = tmp;
        }
        double tot = 0;
        for (int m = 0; m < nb; m++) { v2[m] = re[m] * re[m] + im[m] * im[m]; tot += v2[m]; }
        *leak += 1.0 - tot;
        double u = u01(rng) * tot, cum = 0; int pick = nb - 1;
        for (int m = 0; m < nb; m++) { cum += v2[m]; if (u < cum) { pick = m; break; } }
        s ^= masks[pick];
    }
    return s;
}
