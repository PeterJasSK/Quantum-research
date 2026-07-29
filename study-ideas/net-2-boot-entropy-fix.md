# Idea 2 — Boot-Entropy Fix: Q-EaaS Cures Weak Keys on Headless Devices

## Pitch
A device at first boot has almost no entropy and generates weak or duplicate keys (real, documented:
Heninger et al. 2012 found thousands of hosts sharing factory-default keys). The device pulls a
signed entropy issue from your Q-EaaS API and its keys recover full min-entropy. Measure the state
before and after across N cold boots. Does not claim quantum magic — it fixes *seeding*, which
genuinely fails in the field. The API + provenance receipts + CNL lab hardware become one deployable
story with the lowest reviewer risk of all the ideas.

**Paper strength score: 84/100** — the highest. Real cited problem, sharp question, hard measurable
metrics (not "looks random"), direct link to your API and hardware. The defense against the hype
critique is built in.

## How it becomes a study

**Research question:** Does distributing quantum entropy via API reduce the key-failure rate on
devices with low entropy at boot?

**Hypothesis:** A headless device at cold boot generates keys with low min-entropy; a single entropy
issue from Q-EaaS restores it to full value.

**Method:** Reproduce the Heninger et al. 2012 failure at small scale (Raspberry Pi / VM / network
box with a drained entropy pool). Measure keys across N cold boots, then inject a seed from the API
and measure again.

**Baseline:** The same device with no intervention; and a device using its normal local CSPRNG.

**Metrics:**
- Min-entropy of generated keys (bits)
- Count of duplicate / colliding keys across N cold boots
- Time-to-sufficient-entropy (seconds from boot to healthy pool)
- GCD attack on RSA moduli (the exact method from Heninger — shared factors = broken keys)
- Statistical quality of the seeded output (bias, NIST subset) as a sanity check
- Overhead / latency of the API entropy pull

**Novel contribution:** A quantified measurement that centralized quantum entropy with *verifiable
provenance* (a signed receipt) fixes a specific class of failure — and no one has measured this with
*auditable provenance* before.

**Target venues:** ACM IoT S&P, IEEE Euro S&P (workshop), ACSAC, WiSec.

**Main weakness:** A reviewer will object "a $2 hardware TRNG is enough." You must argue why a
*central, verifiable* source (audit trail, compliance, no trusted local hardware required) is a
different class of solution.

## High-level 5 steps to the goal
1. Set up a headless target device with a drained/starved entropy pool (Raspberry Pi or VM).
2. Reproduce the weak-key failure: generate keys across N cold boots, run the GCD attack, record min-entropy.
3. Integrate the Q-EaaS entropy pull into the boot seeding path (pull a signed issue, seed local RNG).
4. Re-run the N-cold-boot experiment with the entropy injection; measure key recovery.
5. Analyze before/after, quantify failure reduction, and argue the verifiable-provenance angle.

## Hardware

This idea WANTS real hardware — it is the one study that gets stronger the more physical it is.

### Minimalist setup (cheapest that still counts)
- 3–5 Raspberry Pi (or any cheap SBC / OpenWrt router) — the headless victims that boot with weak entropy.
- 1 server/workstation — runs the Q-EaaS API.
- 1 basic switch — connects devices to the API.
- 1 switched PDU, or just manual power access, so you can force real cold boots.

### Maximalist setup (impressive)
- A fleet of 20–50 identical headless boxes (SBCs, or diskless VMs on real blades) = a believable
  "deployment," enough to show duplicate-key collisions across the fleet, not just within one device.
- Automated power control (managed PDU) to script hundreds of cold boots overnight.
- A mix of device classes (SBC, SOHO router, IoT module) to show the failure generalizes.
- Q-EaaS on a proper server with the live quantum-job pipeline feeding it, shown on a provenance dashboard.
- An out-of-band serial console to each device to capture entropy state from the very first millisecond of boot.

### How to connect it physically
- Every device → access switch → same LAN as the Q-EaaS API server.
- Device power → managed PDU (scriptable on/off) so a script can cold-boot the whole fleet in a loop.
- Optional serial/UART console from each device → console server, to log kernel entropy state at boot.
- Air-gap the bench from the internet so the ONLY entropy the device can reach is the one you control.

### What you actually do with it
1. Drain the entropy pool (fresh image, no saved seed file, no RTC, disable hardware RNG).
2. Cold-boot the device N times; each boot, immediately generate SSH/TLS/RSA keys and save them.
3. Run the GCD attack across all collected keys — shared factors = broken keys = your failure metric.
4. Flip on the Q-EaaS boot-seed hook; repeat the N cold boots.
5. Compare: min-entropy, duplicate-key count, GCD-breakable count, time-to-healthy-pool, before vs after.

### Can it be done fully virtually?
**Weakly.** You can drain entropy in a VM and script boots, but a hypervisor leaks host entropy into
the guest (virtio-rng, host jitter), so the "starved device" is not honestly starved. You can force it
with kernel flags, but a reviewer will ask whether the failure is real or an artifact of your VM config.

### Credibility impact of going virtual
**Severe.** This paper's entire authority comes from reproducing a real-world field failure (Heninger
et al. observed it on real deployed devices). A VM-only version invites the exact critique "your weak
entropy is a simulation artifact." Real cheap SBCs cost almost nothing and remove that objection
completely. Do this one on iron.
