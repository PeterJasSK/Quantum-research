# Field 5: AI-Assisted Oncolytic Virus Selectivity
### 11. Screening microRNA-detargeting cassettes for tumor-selective viral replication

## Setup
Take a real tumor type + matched healthy tissue from public expression data
(TCGA/GTEx), identify which microRNAs are abundant in the healthy tissue but
depleted in the tumor. Generate thousands of candidate multi-site
microRNA-detargeting cassette sequences (inserted into a viral gene's UTR)
using a genomic model, fine-tuned or paired with a differential-expression
scoring model trained on the real TCGA/GTEx data. Rank candidates by
predicted selectivity margin — how strongly each cassette should silence the
viral gene in healthy tissue while staying active in tumor cells. Perun's
GPU fleet runs the large-scale parallel scoring/generation pass; this is
explicitly a computational triage step, not a finished therapeutic.

## Bull case
This targets a genuinely combinatorial, data-driven sub-problem (which
microRNA target sites, how many, in what arrangement) that's a good fit for
large-scale parallel screening — turning a slow trial-and-error design
process into a fast computational shortlist. Real, usable expression data
exists (TCGA/GTEx) to ground the scoring, so this isn't speculative pattern
matching — it's tied to real biology from the start.

## Bear case
Design was never really the field's bottleneck — expert-designed
microRNA-detargeting cassettes already exist and work reasonably well; it's
unproven whether an AI-generated cassette meaningfully beats one a domain
expert already designed by hand. Evo-style models weren't trained to predict
differential expression between specific tissues, so without a properly
fine-tuned scoring layer, outputs are just plausible-looking sequences, not
ones actually optimized for this task. Wet-lab and animal validation remain
the real bottleneck regardless of how good the computational screen is — a
better shortlist doesn't shorten the years of testing behind it, and a wrong
computational prediction reaching further validation is a real risk, not
just wasted compute.

## Likely outcome
Most probable: the computational screen produces a shortlist statistically
comparable in predicted selectivity to hand-designed baselines, with a few
outlier candidates worth flagging for actual wet-lab testing — a modest
triage speedup rather than a discovered breakthrough cassette.

## Value if null
Good. Even if no candidate beats the hand-designed baseline, a validated,
reproducible computational screening pipeline against real expression data
is a reusable tool for future tumor types — and an honest "no candidate
outperformed the expert baseline in silico" result is still useful,
since it tells the field whether this kind of large-scale sequence search is
worth wet-lab time at all before committing resources to it.