# PQC Idea 1 — Patient-Data Quantum Clock: how much of today's hospital traffic will be readable when a quantum computer arrives?

**Tag: NON-QUANTUM (quantum-threat) · pqc · effort: medium · QC: no**

## Pitch
Health data stays sensitive for a lifetime, so it is the textbook "harvest now, decrypt later" target. Existing
scans measure PQC *adoption* (a 2026 internet-wide study, a 2026 UK sector study, Forescout's vendor report:
~31 % of exposed healthcare systems even speak TLS 1.3). None turns adoption into the number a hospital board
needs: *for each data class, the year its intercepted traffic becomes readable*, using Mosca's inequality with
health-data shelf lives. We scan Slovak and Central-European hospital, lab, PACS-portal and e-health endpoints,
record the key exchange actually negotiated (classical / hybrid ML-KEM), and publish a per-sector "quantum clock".

**Paper strength score: 70/100** — real users (hospitals, national CERTs, the EU PQC roadmap with its 2030
high-risk deadline), a measured not modelled number, and a regional dataset no one has; docked because scanning
studies exist and the quantum-arrival year is an assumption that must be swept, not asserted.

## How it becomes a study
**Research question:** What fraction of CEE healthcare traffic is already exposed to harvest-now-decrypt-later, and
by which year does each data class become readable under a swept Q-day?

**Hypothesis:** Most healthcare endpoints negotiate classical-only key exchange, so for lifelong data (genomics,
imaging, records) the exposure window is already open for every plausible Q-day.

**Method:** Passive, polite TLS handshake scans (no exploitation) of public healthcare endpoints listed in national
registries; record TLS version, offered/negotiated groups (X25519MLKEM768 etc.), certificate algorithm. Map each
endpoint to a data class and shelf life x; migration time y from published roadmaps; sweep Q-day z. Exposure if
x + y > z.

**Baseline:** the same scan on banks and government (sectors with known migration programmes) and the UK sector
study's numbers.

**Metrics:** % endpoints with hybrid PQC key exchange; % TLS 1.3; per-class exposure year; share of lifelong-data
traffic exposed at z = 2030 / 2035 / 2040.

**Novel contribution:** The first per-data-class quantum-exposure clock for healthcare, on a CEE dataset, turning
adoption counts into a deadline a hospital can act on.

## Connection to what already exists
- Network measurement skills: `DNSPoisonRace/`, `TargetedDosColisionsAndRNGAngle/`.
- Healthcare framing: `study-ideas/siemens/` (pivot away from security there; here security IS the healthcare value).
- No overlap with any built study: nothing in the repo scans PQC deployment.

## Bull case / Bear case / Likely outcome / Value if null
**Bull:** a striking regional number, picked up by the national CERT and health ministry; grant-friendly (EU PQC
roadmap, health security).
**Bear:** a scan paper is "just measurement"; ethics review needed for scanning hospitals; Q-day assumption
attacked by reviewers.
**Likely:** low hybrid adoption in healthcare vs banks, clear exposure for lifelong data under every z swept.
**Value if null:** if healthcare has already migrated, that is good news with a citable number and a method other
countries can reuse.

## Thesis — IEEE short paper (6–8 pp, double-column)
**Central question:** when does today's intercepted patient traffic become readable?
**Single defended claim:** X % of CEE healthcare endpoints negotiate classical-only key exchange, exposing lifelong
data for every Q-day ≥ 2030.
**Target venue:** IEEE QCE 2027 (Quantum-safe security track), or a security measurement venue.
**Compelling-study likelihood: 70/100.**

Citation check needed: arXiv 2606.16473 (internet PQC readiness 2026), 2608.02147 (UK sectors), Forescout
healthcare report, Mosca's inequality original, EU coordinated PQC roadmap (2025). Ethics: scanning policy and
responsible disclosure must be set before any scan.
