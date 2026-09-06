// VENDORED from `framework/grover_min.py` — do not edit by hand; regenerate +
// re-run `tools/parity_check.py`. This is the browser mirror of the Python source
// of truth. It MUST reproduce the Python integer/float logic byte-for-byte; the
// build-time parity assert (TargetedDos D-parity discipline) fails on any drift.
//
// BigInt is used for the size functions so 2**n / factorial(n) stay exact even if
// the sweep is widened past the Number safe-integer range (~n>18). The float math
// (sqrt/floor) uses IEEE-754 doubles, identical to Python's math on the n<=14 vector.

const C_DH = 1.3;

/** Feasible search-space size |S|: 2**n (subset) or n! (ordering). Returns BigInt. */
export function searchSpaceSize(n, kind) {
  if (kind === "subset") {
    return 1n << BigInt(n);
  }
  if (kind === "ordering") {
    let f = 1n;
    for (let i = 2n; i <= BigInt(n); i++) f *= i;
    return f;
  }
  throw new Error(`unknown kind '${kind}'; expected 'subset' or 'ordering'`);
}

/** Optimal Grover iteration count: floor((pi/4)*sqrt(N/max(M,1))), max(k,1) for
 * M>=1, 0 for M<=0. One iteration == one oracle call. Returns a Number integer. */
export function groverIterations(N, M) {
  const m = typeof M === "bigint" ? Number(M) : M;
  if (m <= 0) return 0;
  const n = typeof N === "bigint" ? Number(N) : N;
  const k = Math.floor((Math.PI / 4) * Math.sqrt(n / m));
  return Math.max(k, 1);
}

/** Dürr–Høyer expected minimum-finding queries: c_dh * sqrt(N). Float. */
export function durrHoyerExpectedQueries(N, cDh = C_DH) {
  const n = typeof N === "bigint" ? Number(N) : N;
  return cDh * Math.sqrt(n);
}

/** Single entry point mirroring framework.grover_min.expected_queries. */
export function expectedQueries(n, kind, marked = 1, mode = "min") {
  const N = searchSpaceSize(n, kind);
  if (mode === "search") return groverIterations(N, marked);
  if (mode === "min") return durrHoyerExpectedQueries(N);
  throw new Error(`unknown mode '${mode}'; expected 'search' or 'min'`);
}
