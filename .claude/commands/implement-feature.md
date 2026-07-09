Execute an approved feature plan.  Reads the plan, runs a foreground exploration agent,
implements layer-by-layer in the main context, and does a sanity-check review against the
plan before handing back.

> **No tests (project directive).** Do **not** write, create, or run automated tests of any
> kind — no test files, no test suites, no test commands.  Verify the work manually (run the
> app, hit `/docs`, `curl` the endpoints) as the plan's verification section describes.

Input: path to a plan file under `tasks/plans/`.  Example:
  /implement-feature tasks/plans/feature-17879-completed-cases.md

Input: $ARGUMENTS

---

## 1. Pre-flight
- Parse the plan path.  If missing, ask and stop.
- Read the plan in full.
- Verify the plan's `Status:` line says `Approved`.  If it says `Draft`, stop and tell
  the developer to approve it first (or to re-run `/plan-feature` to revise).
- Verify every section is populated — no `{placeholders}`, no empty tables.  If anything
  is empty, stop and ask the developer to fill it.
- Verify every checkbox in §11 Open Questions is ticked.  If any is open, stop.
- Read `CLAUDE.md` and the user's `MEMORY.md` if not already in context.
- Read the owning epic plan (path is in the feature plan header) — you need the
  cross-cutting decisions from §3 and the shared data-model state from §4 to keep
  this ticket consistent with the epic.

## 2. Branch check
- Run `git status` and `git branch --show-current`.
- The expected branch is `feature-<ticket-number>` (per `CLAUDE.md`).  If the current
  branch does not match, ask the developer whether to create/switch — do not switch
  silently.
- If the working tree has unrelated changes, ask before proceeding.

## 3. Foreground exploration agent
Spawn a foreground general-purpose agent to:

- Open every file listed in the plan's §6 File Plan and read its current state.
- Trace the call chains for any class/method the plan will modify.
- Identify any consumers the plan may have missed (callers of methods being changed,
  templates that include templates being changed, fixtures that reference renamed
  fields).
- Return a structured summary: integration points, surprises, anything that contradicts
  the plan.

Review the summary.  If it contradicts the plan in any meaningful way, **stop** and
report back — do not silently deviate.  Either the plan needs revision or the surprise
needs to be raised with the developer.

## 4. Implement, layer by layer
Work through the §6 File Plan in dependency order — typically:

1. Database / Doctrine entities / migrations / Table classes
2. Domain code (`src/BusinessLogic/`, `src/Services/`, `src/DataSource/`, `src/Provider/`)
3. Forms (`src/Form/`)
4. Controllers (`src/Controller/`)
5. Twig templates (`templates/`)
6. Frontend assets (`assets/` — Stimulus controllers, Sass)
7. Console commands / fixtures (`src/Command/`)

After each layer:

- Match patterns already in the codebase.  Do not introduce a new style if an existing
  one fits — the plan should have pointed at the analogue to mirror.
- Strict types everywhere (`declare(strict_types=1);`).  Type-hint every parameter and
  return type.  No untyped properties.
- No raw SQL — use Doctrine DBAL query builder or table classes (per `CLAUDE.md`).
- Controllers stay thin: validate, call a service, return a response.  If you find
  yourself writing logic in a controller or template, stop and refactor into a service.
- Multi-tenancy: never assume one-council behaviour applies to all.  Read settings
  through the configured channels; do not hardcode council-specific behaviour.

Run `./ops cs` against the touched files at the end of each layer (not the full suite),
and fix every issue inline before moving to the next layer.

If something surfaces that the plan did not anticipate (a hidden caller, a misaligned
status enum, an existing migration in the way), **stop and report**.  Do not invent
scope.  The plan is the contract.

## 5. Verify manually (no tests)
Do **not** write or run automated tests.  Verify the feature by exercising it by hand as the
plan's verification section describes — run the app, open `/docs`, `curl` each endpoint for the
happy path and the edge cases, and confirm each AC in §2 holds against the running code.

Leave any pre-existing tests untouched.  If a legacy test would break as a mechanical
consequence of this change, note it in the hand-back report but do not update or run it (unless
the plan explicitly says otherwise).

## 6. Sanity-check review
A simple pass before handing back.  Re-read the plan's §2 Acceptance Criteria table and
verify each row, in order:

- Does the file named in the "Covered by" column actually exist?
- Does the AC actually hold in that file?  Read it and confirm.  If you can't point at
  the specific line(s), the AC is not covered.
- Tick each AC in the plan file with file:line evidence (`src/.../Foo.php:42`).

Then sweep the diff for the usual easy mistakes:

- Any new `?->` on values an external API can legitimately return as null-vs-string-vs-object?
- Any controller method doing real work instead of delegating?
- Any logic in a Twig template?
- Any raw SQL?
- Any missing `declare(strict_types=1);` at the top of a new PHP file?
- Any new dependency in `composer.json` (per `CLAUDE.md`, do not add without discussion —
  if you did, stop and surface it)?
- Does the change respect the epic's cross-cutting decisions (names, status enums,
  setting keys)?

If anything fails the sanity check, fix it inline.  If a fix is non-trivial, surface
it to the developer before changing course.

Run `./ops cs` one final time across all touched files.

## 7. Update the plan
- Set the plan's `Status:` to `Complete`.
- Make sure §2 has file:line evidence in every "Covered by" cell.
- Fill §13 Post-Implementation: short notes on what was built and any follow-ups the
  developer should know about.

## 8. Hand back
Produce a final report covering:

- One-paragraph summary of what was built
- Bullet list of files created or modified
- AC coverage table (verbatim from the updated plan §2)
- Anything noteworthy: deviations from the plan, things deferred, council-specific
  concerns the developer should verify
- Branch name and a one-line suggested commit message in the project format
  (`#<num> <summary>`, per `CLAUDE.md`)

Then say:

> Implemented and manually verified per the plan's verification section.  No automated tests
> were written or run (project directive).

## 9. Rules
- Do not start implementation if pre-flight fails — fix the plan or branch first.
- Do not write or run automated tests of any kind (project directive).  Verify manually.
- Do not invent scope.  Anything not in the plan stops the work and gets surfaced.
- Do not add Co-Authored-By lines to any commits (per `MEMORY.md`).
- Do not write to `tasks/plans/` except to update the plan you are executing.
