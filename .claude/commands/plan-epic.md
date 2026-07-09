Plan an epic: read every ticket in the group together and produce a high-level plan that
ties the work into one cohesive narrative.  The output is a reference document that
`/plan-feature` will specialise from when a dev picks up a single ticket.

Input: a list of GitHub issue numbers that form the epic, optionally preceded by a slug
(short kebab-case name for the epic).  Examples:
  /plan-epic 17879 17880 17881
  /plan-epic completed-cases-q2 17879 17880 17881

Input: $ARGUMENTS

---

## 1. Parse input
- Pull every numeric token out of the args; treat those as GitHub issue numbers.
- If a non-numeric token appears, treat it as the epic slug.  If none does, derive a slug
  from the first ticket title and confirm it with the developer before writing files.
- If fewer than two ticket numbers are supplied, ask the developer if they really mean
  an epic or whether `/plan-feature` is the right command.

## 2. Fetch every ticket
Run `gh issue view <num> --json number,title,body,labels,milestone,state,comments` for
each ticket, in parallel.  Cache the bodies and comments in memory for the rest of the
command — do not re-fetch.  Comments often refine the ACs and carry additional design
images.

If any ticket is closed, flag it and ask whether to include it (it may already be done,
or may be a parent issue with the epic description).

### Download and read every ticket image
Ticket bodies and comments routinely embed screenshots, mockups,
and design specs as images.  These are first-class context — for any design ticket you
must be able to **reproduce the new or changed design**, which is impossible from alt
text alone.  Do not skip them, and do not assume a ticket has none until you have checked
the raw body.

1. Extract every image URL from each fetched ticket.  Check both Markdown (`![alt](url)`)
   and HTML (`<img src="url">`) forms.  GitHub stores attachments at URLs like:
   - `https://github.com/user-attachments/assets/<uuid>`
   - `https://github.com/<org>/<repo>/assets/<id>`
   - `https://user-images.githubusercontent.com/...`
2. Get a token once with `gh auth token` (private-repo attachments 404 without it).
3. Download each image with curl, following redirects (`-L`) and sending the token.
   Create the per-ticket dir first; preserve the URL's file extension, defaulting to
   `.png` when there is none:
   ```bash
   mkdir -p /tmp/ticket-images/<num>
   curl -sSL -H "Authorization: token $(gh auth token)" \
     -o /tmp/ticket-images/<num>/<n>.<ext> "<url>"
   ```
4. Read every downloaded file with the Read tool so the design is actually in context.
   In §9 per-feature briefs, note which figure informs which AC or design change.
5. If a download fails (403/404, empty/HTML body instead of an image), say so explicitly
   rather than silently planning without the design context.

## 3. Read project context
- `CLAUDE.md` (project conventions, multi-tenancy notes, what-not-to-do list).
- The user's memory (`MEMORY.md`) for any recent corrections about workflow.
- Any existing `tasks/plans/epic-*.md` files — if one already covers some of these
  tickets, stop and ask whether to update the existing plan instead of writing a new one.

## 4. Cross-read the tickets
Before writing anything, identify what spans the epic — this is the whole point of the
high-level plan.  Look for:

- **Shared entities or tables** that more than one ticket touches.
- **Status workflow changes** — if multiple tickets mention statuses, list the full
  resulting state machine, not each ticket's slice.
- **New or changed settings / configuration** — multi-council concerns, council-specific
  flags, fee structures.
- **External integrations** affected (Stripe, Pay360, EPC, SES, Cognito).
- **Notification triggers** introduced or modified.
- **Dependencies between tickets** — does ticket B assume work from ticket A is done?
  Order matters for the implementation roadmap.
- **Patterns that should be decided once** so individual feature plans don't reinvent
  them — naming conventions for new services, form types, table classes.

If you need to skim the codebase to understand existing patterns these tickets plug into,
spawn a foreground general-purpose agent and ask for a structured summary — do not pull
raw search output into the main context.

## 5. Write the epic plan
Save to `tasks/plans/epic-<slug>.md`.  Use this structure (it is deliberately tighter
than a feature plan — the detail lives in `/plan-feature` outputs):

```markdown
# Epic: <human-readable name>

**Slug:** <slug>
**Tickets:** #N1, #N2, #N3 (count)
**Author:** Claude (Opus)
**Date:** <YYYY-MM-DD>
**Status:** Draft | Approved | In progress | Complete

## 1. Why this epic exists
2–3 paragraphs.  What is the business problem these tickets jointly solve?  Who asked
for it?  What is the user-visible outcome?  Pull from the ticket bodies — do not invent.

## 2. Tickets in this epic
| ID | Ticket | Title | State | One-line summary |
|----|--------|-------|-------|------------------|
| F1 | #17879 | Completed cases status logic | open | … |
| F2 | #17880 | … | open | … |

The `ID` column (F1, F2, …) is referenced from the rest of the plan and from
per-feature plans.

## 3. Cross-cutting decisions
Decisions that span multiple tickets and must be made once for the whole epic.
Each subsequent `/plan-feature` invocation must respect these.  Examples:

- Entity / class naming for the new domain concept introduced by F1+F3
- Whether status changes are emitted as Symfony events or handled inline
- Form type reuse vs duplication across F2 and F4
- Multi-council config flag(s) that gate the whole epic

If you don't know the answer, list it in §8 Open Questions — do not guess.

## 4. Shared data model changes
Tables, columns, entities that more than one ticket touches.  Put migrations and Table
class updates here so individual feature plans inherit them instead of redefining.

| Table | Change | Introduced by | Consumed by |
|-------|--------|---------------|-------------|
| `licence_application` | new `completed_at` column | F1 | F3, F4 |

## 5. Status / workflow changes
If statuses or workflows change, write the **full resulting** state machine here, not
each ticket's slice.  Use a table or diagram.  Note which transitions are new.

## 6. Multi-council considerations
- Is the epic universal, or behind a council-specific flag?  Which councils opt in for v1?
- Any council with non-standard config that needs extra verification (Birmingham, Slough
  are flagged in CLAUDE.md)?
- Settings or fee-structure assumptions worth listing.

## 7. Implementation order
Propose an order for the tickets.  Identify any that must precede others (e.g. F1
introduces a column F3 reads).  Flag the ones that can be picked up independently.

## 8. Open questions (epic-wide)
- [ ] Q1: …
- [ ] Q2: …

Once answered, fold the answer into the relevant section above and tick the box.

## 9. Per-feature briefs
For each ticket, write a short brief (½–1 page) that gives a dev enough context to start
`/plan-feature <number>` without re-reading the whole epic.

### F1 — #17879 — <title>
- **What it delivers:** 2–3 sentences from the ticket
- **Acceptance criteria (verbatim from issue):**
  - AC-F1.1 …
  - AC-F1.2 …
- **Likely files / areas affected:** rough guess from a codebase skim
- **Depends on:** other tickets in the epic (or "none")
- **Multi-council notes:** if relevant
- **Conventions to follow:** point to specific existing patterns (e.g. "mirror
  `src/BusinessLogic/Renewals/RenewalCaseProcess` for the new completed-cases process")
- **Out of scope (for this ticket):** anything the ticket explicitly defers or that
  another ticket in this epic covers
```

## 6. Ground rules while drafting
- Every ticket from the input must appear in §2 and have a brief in §9.
- Every AC in a §9 brief must be quoted **verbatim** from the GitHub issue — do not
  paraphrase, do not merge similar bullets, do not invent.
- Do not design implementation detail in this plan — that is `/plan-feature`'s job.
  Per-ticket briefs should answer "what and why" and point at "where", not "how".
- Multi-tenancy: never assume one-council behaviour applies to all.  If a ticket only
  mentions one council, flag it.
- If two tickets contradict each other (e.g. one assumes a status exists that another
  is renaming), surface the conflict in §8 — do not paper over it.

## 7. Present the plan
- Print the path to the new plan file.
- Quote §8 Open Questions in chat so the developer can answer inline.
- Ask: *"Epic plan ready for review.  Please answer the open questions and approve, or
  request changes."*

## 8. Rules
- Do **not** edit any file outside `tasks/plans/`.
- Do **not** invoke `/plan-feature` or `/implement-feature` from this command — planning
  the epic stops here.
- Do **not** mark `Status: Approved` yourself.  The developer does that.
