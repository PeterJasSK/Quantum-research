Draft a detailed implementation plan for one ticket inside an approved epic plan.
The output is the contract `/implement-feature` will execute against.

> **No tests (project directive).** Do **not** plan, design, or describe automated tests of any
> kind in the plan — no test files, no test suites, no "Test impact" or "Testing approach"
> sections, no per-AC test mapping. Plan production code + manual verification only. If a section
> below asks for tests, skip it.

Input: a GitHub issue number, optionally followed by the path to the owning epic plan
if it can't be auto-discovered.  Examples:
  /plan-feature 17879
  /plan-feature 17879 tasks/plans/epic-completed-cases-q2.md

Input: $ARGUMENTS

---

## 1. Parse input and locate the epic
- Pull the ticket number from the args.  If missing, ask and stop.
- If an epic path is supplied, use it.  Otherwise scan `tasks/plans/epic-*.md` for a
  row in the §2 ticket table that contains this number.
- If no epic plan is found, ask the developer: do they want `/plan-epic` first, or are
  they planning a standalone feature?  If standalone, proceed without an epic — but
  flag in the plan that there is no epic context.
- If the epic plan's Status is not `Approved`, warn but continue.  The developer may
  be iterating on both at once.

## 2. Required reading
Read these in order, in full:

1. `CLAUDE.md` — project conventions
2. The user's `MEMORY.md` — recent corrections you must not repeat
3. The owning epic plan (if any) — especially §3 (cross-cutting decisions), §4 (shared
   data model), §5 (statuses), §6 (multi-council), §9 (this ticket's brief)
4. The GitHub issue itself: `gh issue view <num> --json title,body,labels,milestone,comments`
   — read comments too, they often refine the ACs
5. `tasks/plans/_plan-template.md` — the template you will fill in

If the ticket references PRs or other issues, fetch those as well (`gh pr view`,
`gh issue view`) — they often carry the real spec.

### Download and read every ticket image
The issue body and its comments routinely embed screenshots, mockups, and design specs
as images.  These are first-class context — for any design ticket you must be able to
**reproduce the new or changed design**, which is impossible from alt text alone.  Do
not skip them, and do not assume the ticket has none until you have checked the raw body
and comments.

1. Extract every image URL from the fetched body **and comments**.  Check both Markdown
   (`![alt](url)`) and HTML (`<img src="url">`) forms.  GitHub stores attachments at URLs
   like:
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
   Reference the relevant figures from §2 (ACs) and §6 (File Plan) so the implementer
   knows which screen each change reproduces.
5. If a download fails (403/404, empty/HTML body instead of an image), say so explicitly
   rather than silently planning without the design context.

## 3. Survey the codebase
Spawn a foreground general-purpose agent to do the read-heavy work — keep raw search
output out of the main context.  Brief it to return a structured summary covering:

- Existing code the feature must integrate with (controllers, services, processes,
  table classes, form types, templates)
- Patterns the feature should mirror (find the closest existing analogue)
- Doctrine entities and migrations that will need changes
- Multi-tenancy touch points — which councils already use the affected code path
- Tests that already cover the affected behaviour, so the plan knows which tests
  may break mechanically when the feature lands

Review the summary.  If anything is still unclear about scope or integration, ask the
developer before drafting — do not guess.

## 4. Draft the plan
Fill **every** section of `tasks/plans/_plan-template.md`.  Save to
`tasks/plans/feature-<num>-<slug>.md` where `<slug>` is a short kebab-case form of the
ticket title.

Rules while drafting:

- **Verbatim ACs.**  Copy every acceptance criterion from the issue into §2.  Do not
  paraphrase.  Each gets an ID (AC-1, AC-2, …) so tasks and tests can reference it.
- **Concrete file paths.**  Every file change in §6 names the actual path.  No
  placeholders, no `…etc`.
- **Respect the epic.**  If the epic plan made a cross-cutting decision (naming,
  status names, settings keys), the feature plan adopts it without restating the
  reasoning.  If the epic forgot to decide something this ticket needs, raise it in §11
  Open Questions and propose an answer.
- **Stay in scope.**  If the ticket text or the epic's §9 brief defers something, list
  it in §3 Out of Scope.  Do not slip later-epic work into this plan.
- **No tests.**  Do not add a "Test impact" or "Testing approach" section, do not list
  test files in the File Plan, and do not map ACs to tests.  Verification is manual only —
  describe how to exercise the feature by hand (e.g. `/docs`, `curl`, running the app).
- **Strict types and PSR-12.**  The plan's File Plan should reflect strict_types and
  full type hints everywhere; do not let an implementer infer it.
- **No raw SQL.**  All DB access through Doctrine DBAL or table classes — call this
  out in §6 if the implementer will be tempted otherwise.
- **No business logic in templates or controllers.**  If a section reads like it puts
  logic in a controller or Twig, restructure it.

## 5. Ask questions once
- Collect every ambiguity in §11.  Produce the full list at once — do not iterate.
- For each question, propose a default answer if you have a reasonable guess; mark it
  clearly as a proposal.

## 6. Present the plan
- Print the path to the new plan file.
- Quote §11 Open Questions in chat for the developer to answer.
- Ask: *"Plan ready for review.  Please answer the open questions and approve, or
  request changes."*

## 7. Rules
- Do **not** edit any file outside `tasks/plans/`.
- Do **not** start implementation from this command.
- Do **not** mark `Status: Approved` yourself.  The developer does that, then runs
  `/implement-feature`.
- Do **not** invent acceptance criteria.  If the ticket is underspecified, ask.

## 8. After approval
Once the developer approves the plan, tell them:

> Plan approved.  Run `/implement-feature tasks/plans/feature-<num>-<slug>.md` to start
> the implementation.
