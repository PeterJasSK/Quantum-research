/* E2 claim 3(a): classical basin-difference mask library + local vs Metropolis / tuned PT, CPU-time comparison.
   Ising E = -1/2 sum_ij J_ij s_i s_j - sum_i h_i s_i, CSR neighbour lists. Single thread.
   Build: gcc -O3 -march=native -fPIC -shared -o libe2mc.so e2mc.c -lm */
#include <math.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

typedef struct { int n; const int *off; const int *nb; const double *J; const double *h; } G;

static uint64_t rs[4];
static inline uint64_t rotl(const uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }
static inline uint64_t nxt(void) {
    const uint64_t r = rotl(rs[1] * 5, 7) * 9, t = rs[1] << 17;
    rs[2] ^= rs[0]; rs[3] ^= rs[1]; rs[1] ^= rs[2]; rs[0] ^= rs[3]; rs[2] ^= t; rs[3] = rotl(rs[3], 45);
    return r;
}
static inline double U(void) { return (nxt() >> 11) * 0x1.0p-53; }
static inline int RI(int m) { return (int)((nxt() >> 33) % (uint64_t)m); }
void seed_rng(uint64_t s) {
    for (int i = 0; i < 4; i++) { s += 0x9e3779b97f4a7c15ULL; uint64_t z = s; z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL; rs[i] = z ^ (z >> 31); }
}
static double cpu(void) { struct timespec t; clock_gettime(CLOCK_THREAD_CPUTIME_ID, &t); return t.tv_sec + 1e-9 * t.tv_nsec; }

static void fields(const G *g, const int8_t *s, double *f) {
    for (int i = 0; i < g->n; i++) { double a = g->h[i];
        for (int k = g->off[i]; k < g->off[i + 1]; k++) a += g->J[k] * s[g->nb[k]];
        f[i] = a; }
}
static double energy(const G *g, const int8_t *s, const double *f) {
    double e = 0; for (int i = 0; i < g->n; i++) e -= 0.5 * s[i] * (f[i] + g->h[i]); return e;
}
static inline void flip(const G *g, int8_t *s, double *f, int i) {
    s[i] = -s[i]; double d = 2.0 * s[i];
    for (int k = g->off[i]; k < g->off[i + 1]; k++) f[g->nb[k]] += d * g->J[k];
}
static inline void metro_sweep(const G *g, int8_t *s, double *f, double beta, double *E) {
    for (int t = 0; t < g->n; t++) { int i = RI(g->n); double dE = 2.0 * s[i] * f[i];
        if (dE <= 0 || U() < exp(-beta * dE)) { flip(g, s, f, i); *E += dE; } }
}
static inline double qref(const int8_t *s, const int8_t *ref, int n) {
    int a = 0; for (int i = 0; i < n; i++) a += s[i] * ref[i]; return fabs((double)a) / n;
}
/* mask move: flip set m (len lm) sequentially, accumulate dE, Metropolis accept, revert on reject */
static inline void mask_move(const G *g, int8_t *s, double *f, double beta, double *E, const int *m, int lm) {
    double dE = 0;
    for (int a = 0; a < lm; a++) { int i = m[a]; dE += 2.0 * s[i] * f[i]; flip(g, s, f, i); }
    if (dE <= 0 || U() < exp(-beta * dE)) { *E += dE; return; }
    for (int a = lm - 1; a >= 0; a--) flip(g, s, f, m[a]);
}

/* steepest single-spin descent to a local minimum (in place) */
void greedy_min(int n, const int *off, const int *nb, const double *J, const double *h, int8_t *s) {
    G g = {n, off, nb, J, h}; double *f = malloc(n * sizeof(double)); fields(&g, s, f);
    for (;;) { int bi = -1; double bd = -1e-12;
        for (int i = 0; i < n; i++) { double d = 2.0 * s[i] * f[i]; if (d < bd) { bd = d; bi = i; } }
        if (bi < 0) break; flip(&g, s, f, bi); }
    free(f);
}
void random_state(int n, int8_t *s) { for (int i = 0; i < n; i++) s[i] = (nxt() >> 63) ? 1 : -1; }

/* method: 0 metro, 1 mask-mix (pmask), sweeps of n moves. records E and |q| per sweep until cpu budget */
int run_single(int n, const int *off, const int *nb, const double *J, const double *h, double beta, int8_t *s,
               const int *moff, const int *midx, int L, double pmask, double budget, const int8_t *ref,
               double *rE, double *rq, int maxrec, double *cpu_used, double *acc_mask) {
    G g = {n, off, nb, J, h}; double *f = malloc(n * sizeof(double)); fields(&g, s, f); double E = energy(&g, s, f);
    double t0 = cpu(); int r = 0; long na = 0, nm = 0;
    while (r < maxrec) {
        if (pmask <= 0) metro_sweep(&g, s, f, beta, &E);
        else for (int t = 0; t < n; t++) {
            if (U() < pmask) { int j = RI(L); double E0 = E; mask_move(&g, s, f, beta, &E, midx + moff[j], moff[j + 1] - moff[j]);
                nm++; if (E != E0) na++; }
            else { int i = RI(n); double dE = 2.0 * s[i] * f[i]; if (dE <= 0 || U() < exp(-beta * dE)) { flip(&g, s, f, i); E += dE; } }
        }
        if ((r & 255) == 255) { fields(&g, s, f); E = energy(&g, s, f); }
        rE[r] = E; rq[r] = qref(s, ref, n); r++;
        if ((r & 15) == 0 && cpu() - t0 > budget) break;
    }
    *cpu_used = cpu() - t0; *acc_mask = nm ? (double)na / nm : 0; free(f); return r;
}

/* PT: R replicas (betas ascending, last = target), each sweep: per replica n moves (metro or mask-mix), then swaps.
   records target replica. S is R*n states in/out. */
int run_pt(int n, const int *off, const int *nb, const double *J, const double *h, int R, const double *betas, int8_t *S,
           const int *moff, const int *midx, int L, double pmask, double budget, const int8_t *ref,
           double *rE, double *rq, int maxrec, double *cpu_used, double *swap_rate) {
    G g = {n, off, nb, J, h}; double *F = malloc((size_t)R * n * sizeof(double)); double *E = malloc(R * sizeof(double));
    int *perm = malloc(R * sizeof(int)); long nsw = 0, nacc = 0;
    for (int k = 0; k < R; k++) { perm[k] = k; fields(&g, S + k * n, F + k * n); E[k] = energy(&g, S + k * n, F + k * n); }
    double t0 = cpu(); int r = 0;
    while (r < maxrec) {
        for (int k = 0; k < R; k++) { int p = perm[k]; int8_t *s = S + p * n; double *f = F + p * n; double b = betas[k];
            if (pmask <= 0) metro_sweep(&g, s, f, b, &E[p]);
            else for (int t = 0; t < n; t++) {
                if (U() < pmask) { int j = RI(L); mask_move(&g, s, f, b, &E[p], midx + moff[j], moff[j + 1] - moff[j]); }
                else { int i = RI(n); double dE = 2.0 * s[i] * f[i]; if (dE <= 0 || U() < exp(-b * dE)) { flip(&g, s, f, i); E[p] += dE; } }
            }
        }
        for (int k = 0; k + 1 < R; k++) { int a = perm[k], c = perm[k + 1];
            double x = (betas[k + 1] - betas[k]) * (E[c] - E[a]); nsw++;
            if (x >= 0 || U() < exp(x)) { perm[k] = c; perm[k + 1] = a; nacc++; } }
        if ((r & 255) == 255) for (int k = 0; k < R; k++) { fields(&g, S + k * n, F + k * n); E[k] = energy(&g, S + k * n, F + k * n); }
        int p = perm[R - 1]; rE[r] = E[p]; rq[r] = qref(S + p * n, ref, n); r++;
        if ((r & 7) == 0 && cpu() - t0 > budget) break;
    }
    /* return target state in slot R-1 order-agnostic: copy perm order */
    int8_t *tmp = malloc((size_t)R * n); for (int k = 0; k < R; k++) memcpy(tmp + k * n, S + perm[k] * n, n);
    memcpy(S, tmp, (size_t)R * n); free(tmp);
    *cpu_used = cpu() - t0; *swap_rate = nsw ? (double)nacc / nsw : 0; free(F); free(E); free(perm); return r;
}
