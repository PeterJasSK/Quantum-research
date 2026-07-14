# Feature Plan — EPIC 12: Header navigation refactor (8888.sk panel-scroll nav, solid background)

**Status:** Complete (2026-07-14) — developer accepted both §6 recommended defaults as-is.
**Owning plan:** None — standalone assignment (#12), same pattern as EPIC 11: a raw prompt, not a
build-plan story or GitHub issue.
**Interpretation of the prompt:** the current `Header.tsx` nav ("doesn't look good") gets rebuilt
**from the ground up**, borrowing 8888.sk's actual interaction model — its dropdown/mobile panels
animate open by sliding down from above (translate-Y, not a fade/scale) — but with **fully opaque,
solid-color panel backgrounds** instead of 8888.sk's translucent/blurred ones, so nav content is
never see-through against the page behind it. Source verbatim prompt:

> "i want to refactyore the navigation in header it doesnt look good it is not look good i want it
> fully refactored based on 8888.sk with its js where the pannels scrolls from up down and it needs
> to have solid background be fully visibla. Make it from ground up."

> **No automated tests** (project directive, [[qrng-eaas-plan-workflow]]). Verification is manual:
> `npm run build`/`tsc --noEmit`/`npm run lint`, then eyeball the open/close animation and contrast
> in the browser across all three themes and mobile/desktop widths.

---

## 1. Research — what 8888.sk actually does

Fetched `https://www.8888.sk/`'s shipped bundle (`assets/index-Cld4lQHw.js`) directly, since the
rendered DOM carries no readable structure. Relevant behavior:

- **Header shell:** `fixed left-0 right-0 top-6` (shrinks to `top-4` after scroll), a floating
  rounded pill bar, **not** full-width — `bg-white/80 backdrop-blur-sm` idle → `bg-white/95
  backdrop-blur-md` once scrolled, with a shadow that deepens on scroll.
- **Desktop dropdown items:** `absolute top-full left-0 w-64 pt-2`, panel body is
  `bg-white rounded-xl shadow-xl border` — opens via opacity/scale (`opacity-0 scale-95 invisible`
  → `opacity-100 scale-100 visible`), on hover or click.
- **Mobile full-screen panel — the "scrolls from up down" behavior:** `fixed inset-0 z-[60]
  bg-white/95 backdrop-blur-xl`, closed state is `opacity-0 -translate-y-full pointer-events-none`,
  open state is `opacity-100 translate-y-0`, `transition-all duration-500 ease-in-out`. It literally
  slides the whole panel down from off-screen-above into place, covering the full viewport. Each nav
  link inside staggers in (`animate-in slide-in-from-bottom fade-in`, `animationDelay: index*50ms`).

**What we take vs. leave:** take the translate-Y slide-down mechanic and the full-bleed overlay
panel shape (both desktop dropdown and mobile menu become "panels that drop down," not fades). We
**do not** copy the translucency (`/80`, `/95`, `backdrop-blur-*`) — the prompt explicitly asks for
solid, fully-visible backgrounds, so every panel uses an opaque `--color-bg`/`--color-surface`
token instead of an alpha-suffixed one.

---

## 2. Current state (`qrng-eaas/web/components/Header.tsx`)

- Desktop nav (`Header.tsx:65-77`) is a flat, always-visible `flex gap-6` link row — no dropdown,
  no grouping, no panel of any kind.
- Mobile menu (`Header.tsx:93-107`) is already a `fixed inset-0` full-screen overlay, but it has
  **no enter/exit transition at all** — it's a bare `{menuOpen && (...)}` conditional mount/unmount
  (instant show/hide), and its background is translucent (`bg-bg-deep/95 backdrop-blur`).
- Header bar itself (`Header.tsx:44`) is `sticky top-0` full-width with `bg-bg-deep/80
  backdrop-blur` — translucent, not solid.
- 5-tap easter-egg gesture (`lib/theme.ts` `useSecretTap`), `ThemeToggle`, `HealthBadge` are
  existing infra from EPIC 11 — kept as-is, just re-hosted in the new markup.

---

## 3. Acceptance criteria

| AC | Requirement | Met by |
|----|-------------|--------|
| AC-1 | Nav "fully refactored... from ground up" | `Header.tsx` rewritten: new `NavLink`/`NavChild` types and `DesktopNavItem` component (`Header.tsx:11-67`), new mobile panel markup with per-link `children` support (`Header.tsx:137-167`), new header shell class (`Header.tsx:94`) — not a patch of the prior implementation. |
| AC-2 | "based on 8888.sk with its js where the pannels scrolls from up down" | Mobile menu now always mounted and toggles `-translate-y-full ↔ translate-y-0`, `opacity-0 ↔ opacity-100`, `transition-all duration-500 ease-in-out` (`Header.tsx:137-143`), replacing the prior instant `{menuOpen && (...)}` mount/unmount. Desktop nav items become dropdown-capable via `DesktopNavItem` (`Header.tsx:23-67`): a panel anchored `top-full`, sliding `-translate-y-2 ↔ translate-y-0` + opacity on hover/click (`Header.tsx:47-51`). |
| AC-3 | "solid background be fully visibla" | Header bar uses solid `bg-bg-deep` with no alpha suffix or blur (`Header.tsx:94`); desktop dropdown panel uses solid `bg-surface` (`Header.tsx:52`); mobile overlay uses solid `bg-bg-deep` (`Header.tsx:139`). None of the three panels use an alpha-suffixed background or `backdrop-blur` (verified via grep — the only remaining `backdrop-blur`/alpha-background hit in the file is the pre-existing, out-of-scope quantum-unlock toast, `Header.tsx:175`, not one of the three panels this AC covers). |

---

## 4. Scope

### In scope
- `Header.tsx`: full rewrite of desktop nav (add a data-driven `NAV_LINKS` structure supporting
  optional dropdown children, matching 8888.sk's grouping idea) and mobile nav (real slide-down
  transition, solid background).
- Header bar background: switch from translucent+blur to solid theme token.
- Preserve unchanged: `ThemeToggle`, `HealthBadge`, the 5-tap quantum easter egg, all existing
  routes/links (no new pages).

### Out of scope
- No new nav destinations/content — same links as today (`/`, `/#pipeline`, `/#api`, `/dice`,
  `/demo`), just restructured presentation. If a dropdown grouping is introduced, it's purely
  visual sub-grouping of the existing five links, not new IA.
- No backend/API changes.
- No automated tests, per [[qrng-eaas-plan-workflow]].
- Copying 8888.sk's floating-pill/scroll-shrink header *shape* is optional polish, not required —
  the prompt's two hard requirements are the slide-down animation and solid backgrounds; the sticky
  full-width bar can stay as today's layout if the developer prefers less visual churn (flag as an
  open question, §6).

---

## 5. File plan

| File | Change |
|------|--------|
| `qrng-eaas/web/components/Header.tsx` | **Rewrite.** New `NAV_LINKS` shape (flat, unless dropdown grouping is approved per §6 Q1); mobile panel gets real CSS transition classes (`transition-all duration-500 ease-in-out`, translate-Y toggle) instead of conditional mount; header bar and all panels switch to solid `--color-bg-deep`/`--color-surface` tokens, dropping every `/NN` alpha suffix and `backdrop-blur*` utility. Keep `ThemeToggle`, `HealthBadge`, `useSecretTap` wiring as-is. |
| `qrng-eaas/web/app/globals.css` | **Edit only if needed.** No new tokens expected — solid backgrounds reuse existing `--color-bg-deep`/`--color-surface`; touch only if the panel needs a shade not already defined. |

---

## 6. Open questions — RESOLVED (developer, 2026-07-14)

Both answered by accepting the recommended default, verbatim.

**Q1 — Does "fully refactored" include adding dropdown grouping to the desktop nav (mirroring
8888.sk's `group/menu` submenu), or just the animation + solid-background fix on the existing flat
link list?**
**Resolved: keep the flat link list** (only 5 items today, no natural grouping) but build the
component so a link can optionally carry `children` and get the slide-down panel mechanic — don't
invent new groupings for links that don't need one yet.

**Q2 — Keep today's full-width `sticky top-0` header bar, or adopt 8888.sk's floating rounded pill
(`fixed`, inset margin, shrinks on scroll)?**
**Resolved: keep full-width `sticky`** (matches the rest of the site's layout, avoids extra scroll-
listener complexity); apply only the two required changes (solid background, slide-down panels) —
no floating-pill treatment.

---

## 7. Step-by-step (manual — no automated tests)

1. Rewrite `Header.tsx` per §5; run `npm run build && npx tsc --noEmit && npm run lint`.
2. Desktop: confirm no dropdown panel is visible until hover/click, and it slides down from the
   header edge (not an instant pop or a fade-only transition).
3. Mobile: open the menu, confirm the panel visibly translates down into place over ~500ms and
   fully occludes page content beneath it (no bleed-through); close and confirm it slides back up.
4. Confirm solid backgrounds read correctly in all three themes (`light`/`dark`/`quantum`) — no
   alpha transparency or blur remaining on header/dropdown/mobile-panel surfaces.
5. Re-confirm the 5-tap quantum easter egg and `ThemeToggle` still work unchanged.

---

## 8. Post-implementation

`Header.tsx` was rewritten: `NAV_LINKS` gained an optional `children` field (typed via new
`NavLink`/`NavChild` types), a `DesktopNavItem` component renders either a plain link or, when
`children` is present, a hover/click-toggled dropdown panel that slides down from `top-full`
(`-translate-y-2 → translate-y-0` + opacity, `duration-300`). The mobile panel is now always
mounted and toggles `-translate-y-full ↔ translate-y-0` / `opacity-0 ↔ opacity-100` over
`duration-500 ease-in-out` instead of conditionally mounting; it also renders any per-link
`children` indented beneath their parent. Header bar and both panels switched from alpha-suffixed
`/NN` backgrounds + `backdrop-blur` to solid `bg-bg-deep` / `bg-surface` theme tokens. `HealthBadge`,
`ThemeToggle`, and the 5-tap `useSecretTap` quantum-unlock wiring were re-hosted unchanged.
`npm run build`, `npx tsc --noEmit`, and `npm run lint` all pass clean.

**Deferred/not done:** the plan's step-by-step §7 items 2-5 (in-browser eyeballing of the
animation, contrast, and theme behavior) were **not** performed in this pass — the developer
declined browser-based verification via `chromium-cli`/Playwright during this session. The
static checks (build/typecheck/lint) pass, and the JSX/class logic was manually re-read against
each AC, but the actual rendered animation timing, occlusion, and per-theme contrast have not
been eyeballed in a running browser. Recommend the developer run `npm run dev` and step through
§7 items 2-5 before considering this epic fully closed.

**No new NAV_LINKS entries carry `children` yet** (per §6 Q1) — the dropdown code path exists but
is currently untriggered by real data; first link that needs grouping should just add a
`children` array to test it live.
