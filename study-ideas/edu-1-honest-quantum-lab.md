# Edu Idea 1 — Honest Quantum Lab: can students learn to catch a false quantum claim by running real ones?

**Tag: QUANTUM · edu · effort: low-medium · QC: optional (replays stored hardware runs; live runs optional)**

## Pitch
Students meet quantum computing through hype. The repo holds something rare: real hardware runs where the quantum
claim *passed* (CHSH 2.73, GHZ ⟨XX⟩+⟨ZZ⟩ ≈ 1.96, tick-clock 0.39 > 0.296) next to runs where it *looked* quantum
and was not (single-basis witness saturated by a classical mixture, diagonal observables with exact classical
twins, PMD lost to a 1-bit model). Package them as an interactive lab built on the quantum-artificial-life
visualisation: every exercise asks "is this quantum?", the student picks a classical twin to try to fake it, and
the page shows whether the fake succeeds. Measure learning gain with pre/post tests in a real course.

**Paper strength score: 68/100** — a real user (students, teachers), the defensible "first interactive quantum
artificial-life visualisation", and Quantum Week's education track (QSEEC) is a natural home; docked because an
education paper needs a classroom study (ethics, N students) and the docent's course access.

## How it becomes a study
**Research question:** Does hands-on falsification (trying to fake a quantum result with a classical twin) improve
students' ability to judge quantum-advantage claims more than a lecture on the same material?

**Hypothesis:** Students using the lab score higher on a "claim-judging" post-test (classify 10 published-style
claims as supported / overclaimed) than a lecture-only group.

**Method:** Six exercises from stored runs (three true passes, three caught overclaims). Each has a "fake it"
button with 2–3 classical twins. Two groups in the docent's course (lab vs lecture), same pre/post test.

**Baseline:** lecture + slides covering identical content.

**Metrics:** pre/post gain on claim-judging test; time-on-task; fraction of fakes students try before conceding.

**Novel contribution:** an education tool whose content is a genuine record of claims made and caught, with a
measured effect on claim literacy.

## THE VISUALIZATION
Two organisms collide on a real-chip lattice; beside them a "fake it" panel. The student picks a classical twin;
the witness needle either stays above the bound (quantum stands) or the fake matches it (claim falls).

## Connection to what already exists
- `artificial-life/web/` interactive visualisation (prior-art check: first interactive quantum-alife viz).
- Failure catalogue: `THESIS/QuantumEvolutionFrontier/` (nine failure modes, history-and-roadmap).
- Hardware records: QuantumPhantoms RUNLOG, PJ2.4 ghz2 run on ibm_marrakesh.

## Bull case / Bear case / Likely outcome / Value if null
**Bull:** clear learning gain, adoption by the docent's course and others, QSEEC paper plus a reusable public tool.
**Bear:** small N, one course, teacher effect; reviewers want a validated instrument.
**Likely:** a moderate gain, strongest on "diagonal observable" and "single-basis witness" traps.
**Value if null:** the tool and the open run archive still stand as a teaching resource.

## Thesis — IEEE short paper (6–8 pp, double-column)
**Central question:** does falsifying real quantum claims teach claim literacy?
**Single defended claim:** lab students improve X points more than lecture students on claim judging.
**Target venue:** IEEE QCE 2027 / QSEEC education track.
**Compelling-study likelihood: 68/100.**

Needs: docent's course for the classroom arm; ethics approval for the student study.
