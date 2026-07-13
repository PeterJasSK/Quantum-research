# Feature Plan — EPIC 11: Design refactor (8888.sk design language, light/dark mode, quantum easter egg)

**Status:** Complete (2026-07-13) — implemented per §6, verified via `npm run build`/`tsc --noEmit`/
`npm run lint` (all pass with zero errors); manual in-browser verification (§6 steps 2-8) was not
run per developer instruction this session — see §13.
**Owning plan:** None. This is a **standalone assignment** (#11), not a line item in
`qrng-eaas/claude/QRNG_EaaS_BUILD_PLAN.md` — EPICs 0-10 are already Complete and this ticket was
handed over as a raw prompt, not a build-plan story or GitHub issue.
**Interpretation of "assignment 11":** a full visual design refactor of the `qrng-eaas/web/`
Next.js app, scoped entirely to presentation (CSS tokens, typography, component markup/classes,
theming infrastructure) — **no backend, API, or content changes**. Source verbatim prompt:

> "I want to refactor the design i want you to copy design lenguage from sight
> https://www.8888.sk/, I want it to be highly mobile friendly have light and dark mode and be
> professionally looking any additional context needed about the design should be derived from the
> sight. I want to change the color schemes to be copied but want one special color scheme this
> original one as a special version of the sight that will be able to switch as easter egg of sort
> but will not be default."

> **No automated tests in this plan.** Per the project directive: production code + manual
> verification only — no test files, no "Testing approach" section, no AC-to-test mapping.
> Verification is manual (§6): load the app in a real/emulated mobile viewport and desktop, toggle
> light/dark, trigger the easter egg, and visually confirm against the reference site's design
> tokens captured below.

---

## 1. Context & goal

**Reference site research (`https://www.8888.sk/`, a Košice accounting-services SPA).** The
rendered page is a client-side React/Vite app; its shipped stylesheet
(`/assets/index-B6O2L7gx.css`, fetched and inspected directly since the rendered DOM carries no
useful text) yields the actual design tokens in use — this is the "design language" the prompt asks
to copy, not the accounting content:

- **Palette:** deep navy family for headings/dark surfaces — `#052e44` (darkest), `#0a2540`,
  `#084666` (mid navy) — paired with a single mint/emerald **accent** `#12eaa6`, used at systematic
  alpha steps (`1a/26/33/40/4d/66/80/99/b3/e6` hex-alpha suffixes = a tint/shade ramp, not ad-hoc
  opacities). Neutrals: `#f8fafc`, `#ecfdf5` (mint-tinted near-white), `#e2e8f0`, `#9ca3af`.
  Incidental colors (`#f97316` orange, `#2563eb` blue, `#fca5a5` light red) read as semantic
  accent/warning/info/error chips, not brand colors.
- **Typography:** `Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif` for
  everything; `"JetBrains Mono", "Fira Code", monospace` for numeric/code figures. Tight negative
  tracking on large headings (`letter-spacing:-.05em`/`-.025em`), wide positive tracking on small
  uppercase labels (`.1em`–`.3em`) — the classic SaaS "eyebrow label + tight display heading"
  pairing.
- **Shape & elevation:** generous, large corner radii (`.75rem`–`3rem`, including a `2.6rem`
  bespoke value on a hero panel), `rounded-full` pills for buttons/badges, and **soft, low-opacity,
  navy-tinted shadows** (`box-shadow:0 8px 32px #0846660d`) rather than heavy dark drop-shadows.
  `backdrop-filter:blur(20px)` glass panels appear over the navy gradients.
- **Gradients:** navy→navy (`linear-gradient(135deg,#084666,#052e44)`) for dark hero/section
  backgrounds, and navy→mint (`linear-gradient(135deg,#084666,#12eaa6)`) as a diagonal accent
  treatment.
- **Layout:** standard content widths up to `max-w-7xl` (80rem/1280px), Tailwind-driven responsive
  utilities, viewport meta present — a conventional mobile-first SaaS layout.
- **Mode:** the reference site itself ships **light-mode only** — no `prefers-color-scheme` or
  dark-mode CSS was found in its stylesheet. The prompt's dark-mode requirement is therefore **our
  own extension** of this palette (§4 Decision 2), not something copied verbatim.

**Current app state (`qrng-eaas/web/`, surveyed in full — see file-by-file references throughout).**
The whole visual identity lives in exactly one file, `app/globals.css`, as a Tailwind v4 CSS-first
`@theme` block: deep-space neon palette (`--color-bg-deep:#01040b`, `--color-bg:#060c1f`,
`--color-text:#e3f6ff`, `--color-heading:#7ad9ff`, `--color-accent:#4dcfff`,
`--color-primary:#00aaff`, `--color-primary-hover:#0077cc`, `--color-border:rgba(0,170,255,.35)`),
one font (`Orbitron`, `app/layout.tsx:2,7-11`), and three custom utilities consumed everywhere —
`.glow` (13 call sites), `.pill` (8 call sites), `.panel` (16 call sites) — plus zero hardcoded
hex values in any `.tsx` file (everything reads the theme tokens). This was a **deliberate design
choice**, not an accident: the EPIC 5 plan
(`feature-epic5-web-app.md:93,101,120,230-231,340,355`) explicitly built this neon/Orbitron look to
*"reproduce the look of the old Django project"* as Tailwind v4 tokens, and called it AC-7,
manually verified. **This plan preserves that work in full as the hidden "quantum" theme (§4
Decision 3) — nothing about it is deleted, only demoted from default.**

There is currently **zero theming infrastructure**: no `next-themes` or equivalent in
`package.json`, no `localStorage`/`data-theme`/`prefers-color-scheme`/`ThemeProvider` anywhere in
`app/` or `components/`. Light/dark/quantum switching must be built from scratch (§4 Decision 1).

Mobile responsiveness today is minimal and uneven: only `sm:`/`md:` breakpoints exist (no `lg:`/
`xl:` anywhere), confined to the header nav collapse, the homepage hero CTA row, the homepage `h1`,
and the pipeline diagram's flex-direction flip. The six largest static content sections
(`ApiUsage`, `CryptoFraming`, `NetworkingUseCases`, `WhatIsQrng`, `VerifyReceipt`'s static parts)
have **no responsive classes at all** — acceptable on a single `max-w-3xl` column at most sizes, but
untuned for tablet and for the code blocks in `ApiUsage`/`KemHandshakeDemo`, which have no
horizontal-scroll guard. Touch targets are already mostly 44px (`h-11`/`min-h-11`) on primary
buttons, inconsistently applied to header links/badges.

`HealthBadge.tsx:16-21` and `VerifyReceipt.tsx` (an `amber-600` fallback pill) are the **only** two
places that bypass the theme-token system, hardcoding raw Tailwind palette classes
(`emerald-500/300/400`, `amber-500/300/400`, `white/10`, `white/5`) for status colors — these need
semantic tokens so status colors adapt correctly across all three themes (§4 Decision 4).

`public/` holds one real brand asset (`logo.png`, used in `Header.tsx:30` + `layout.tsx` metadata
icon) plus five unused Next.js/Vercel starter SVGs (`file.svg`, `globe.svg`, `next.svg`,
`vercel.svg`, `window.svg` — zero grep hits anywhere in `app/`/`components/`).

---

## 2. Acceptance criteria

No ticket exists, so these ACs are derived directly from the verbatim prompt (quoted per-AC) —
not paraphrased assumptions. "Met by" is left blank; this section is the implementation contract.

| AC | Source (verbatim prompt intent) | Met by |
|----|----------------------------------|--------------|
| **AC-1** | "copy design language from sight https://www.8888.sk/ ... any additional context needed about the design should be derived from the sight" | `app/globals.css:3-21` (light `@theme` block: navy `#052e44`/`#0a2540`(as `--color-bg`)/`#084666` + mint `#12eaa6`), `app/layout.tsx:2,15-18` (Inter + JetBrains Mono via `next/font/google`), `app/globals.css:109-123` (large radii `1.5rem`, soft navy-tinted shadow, `blur(20px)` glass panels in light/dark). |
| **AC-2** | "I want it to be highly mobile friendly" | Responsive scale added across `WhatIsQrng.tsx`, `CryptoFraming.tsx`, `NetworkingUseCases.tsx`, `ApiUsage.tsx`, `VerifyReceipt.tsx` (all `sm:` breakpoints on type/spacing/padding); `ApiUsage.tsx:234`/`KemHandshakeDemo.tsx:179,199,269` `<pre>` blocks already had `overflow-x-auto` (confirmed, no gap); touch targets already ≥44px (`h-11`/`h-14`/`min-h-11`) and unchanged; `Header.tsx` mobile menu retains `h-11 w-11` button + adds `<ThemeToggle/>` at `Header.tsx:105`; `app/page.tsx` hero CTAs now `w-full sm:w-auto` stacking. |
| **AC-3** | "havge light and dark mode" | `components/ThemeProvider.tsx` (`next-themes`, `themes=["light","dark","quantum"]`, `defaultTheme="system"`, `enableSystem`, `storageKey="qeaas-theme"`); `components/ThemeToggle.tsx` sun/moon segments call `setTheme()`; `app/layout.tsx:44` `suppressHydrationWarning` on `<html>` + `next-themes`' pre-paint script avoids flash; `localStorage` persistence via `storageKey`. |
| **AC-4** | "be proffesionnaly looking" | `app/globals.css:99-123` (light/dark shadow/elevation overrides for `.pill`/`.panel`); `Header.tsx`/`Footer.tsx` restyled with new tokens/spacing; `HealthBadge.tsx:16-21`, `VerifyReceipt.tsx:87,102`, `DicePlayer.tsx:110`, `KemHandshakeDemo.tsx:160,262` converted to `--color-warning`/`--color-success` tokens (expanded scope, see §13); `public/file.svg,globe.svg,next.svg,vercel.svg,window.svg` deleted; logo is now a theme-aware inline "Q" mark + text wordmark (`Header.tsx:54-62`) reading theme CSS vars, replacing the raster `<Image>` in the header (favicon/metadata `logo.png` usage in `layout.tsx:29` untouched). |
| **AC-5** | "I want to chnge the color shemes to be copied" | `app/globals.css:3-21` (light) and `:23-37` (dark) both derive from the navy/mint palette; the neon-cyan values (`#01040b`/`#060c1f`/`#4dcfff`/`#00aaff`) appear **only** in the `[data-theme="quantum"]` block (`app/globals.css:39-53`). |
| **AC-6** | "want one special color sheeme this original one as a special vesrion of the sight that will be able to swich as easter egg of sort but will not be default" | `app/globals.css:39-53` preserves the exact EPIC 5 values byte-for-byte; `next-themes`' `system` resolution never yields `quantum` (`ThemeProvider.tsx`); `Header.tsx:31-35` five-tap-in-3s gesture (`lib/theme.ts` `useSecretTap`) calls `unlockQuantum()` + `setTheme("quantum")`; `ThemeToggle.tsx:32-36` only renders the third (atom) segment once `isQuantumUnlocked()`; unlock persists via `localStorage` key `qeaas-quantum-unlocked` (`lib/theme.ts:6`). |

---

## 3. Scope

### In scope
- **Theming infrastructure:** add `next-themes` (small, well-maintained, handles the
  anti-flash-of-unstyled-theme script and `prefers-color-scheme` correctly out of the box; supports
  arbitrary theme names, so `quantum` costs nothing extra) — new dependency in
  `web/package.json`.
- **Design tokens (`app/globals.css`):** replace the single neon `@theme` block with a token system
  keyed by `[data-theme="light" | "dark" | "quantum"]`, covering: background/surface, text/heading,
  accent/primary(+hover), border, and new semantic status tokens (`success`/`warning`/`danger`/
  `info`). `.glow`/`.pill`/`.panel` utilities become theme-aware (soft shadows in light/dark, the
  existing neon glow shadow preserved only under `quantum`).
- **Fonts (`app/layout.tsx`):** add `Inter` (sans) and `JetBrains Mono` (mono) via
  `next/font/google`; **keep** `Orbitron` loaded (still needed for the `quantum` theme).
- **Theme provider + toggle:** new `components/ThemeProvider.tsx` (wraps `next-themes`'
  `ThemeProvider`), new `components/ThemeToggle.tsx` (sun/moon control in the header; a hidden third
  control appears only after the easter egg is unlocked).
- **Easter-egg trigger:** a tap/click gesture on the header logo (5 taps within 3 seconds — chosen
  over a keyboard Konami code specifically because AC-2 requires mobile-first design, and keyboard
  sequences don't work on touch devices) unlocks `quantum` and persists the unlock flag
  (`localStorage`) so it's available again on return visits.
- **Header/Footer restyle:** new palette/typography/spacing, mobile menu polish, `ThemeToggle`
  wired in, logo re-treated as a theme-aware inline SVG/text wordmark instead of a static PNG (see
  §11 Q7 — the raster `logo.png` cannot correctly show a navy wordmark on both light and dark
  surfaces without either two asset variants or a currentColor SVG).
- **Component restyle (classes only, no logic/content changes):** `DicePlayer.tsx`,
  `KemHandshakeDemo.tsx`, `HealthBadge.tsx` (+ semantic color tokens), all of
  `components/sections/*.tsx`, and the three page shells (`app/page.tsx`, `app/dice/page.tsx`,
  `app/demo/page.tsx`) — updated Tailwind utility classes for the new tokens, added responsive
  breakpoints where currently absent, touch-target normalization.
- **Shared page-hero extraction:** `app/dice/page.tsx` and `app/demo/page.tsx` currently duplicate
  an identical wrapper (back-link + glow `h1` + centered intro paragraph). Extract a small
  `components/PageHero.tsx` so the new spacing/typography rules apply once, not twice.
- **Cleanup:** delete the five unreferenced starter SVGs from `public/`.

### Out of scope
- Any backend/API change (`qrng-eaas/api/`) — this is a `web/`-only refactor.
- New content, copy, sections, or pages — this refactors *presentation* of existing sections only.
  `ApiUsage`'s endpoint list, `NetworkingUseCases`' use-case copy, etc. are restyled, not rewritten.
- Designing new brand-mark artwork (a redrawn logo) — out of scope for a code-only session; see
  §11 Q7 for the interim treatment.
- Copying 8888.sk's actual page structure/content (it's an unrelated accounting business) — only
  its design *language* (palette, type, shape, elevation) is in scope, per the prompt.
- Automated tests (project directive, [[qrng-eaas-plan-workflow]]).
- Analytics/telemetry for how often the easter egg is discovered.

---

## 4. Key decisions

**Decision 1 — theming mechanism: `next-themes` + CSS-variable tokens, no Tailwind `dark:` variant.**
Add `next-themes` (`attribute="data-theme"`, `themes={["light","dark","quantum"]}`,
`defaultTheme="system"`, `enableSystem`). It injects the pre-hydration script that sets
`data-theme` before paint (no dependency on the app's client JS running first), reads/writes
`localStorage`, and resolves `system` from `prefers-color-scheme` — but **`system` only ever
resolves to `light` or `dark`**, never `quantum`, since `quantum` isn't tied to any OS
preference — exactly what AC-6 requires ("will not be default"). Keep the existing architecture
where every component consumes semantic Tailwind utility classes (`text-heading`, `bg-primary`,
etc.) backed by CSS custom properties — **do not** introduce Tailwind's `dark:` utility-variant
prefix or a `@custom-variant dark` directive; that would require touching every className in every
component for a cosmetic-only gain. Instead, `app/globals.css` keeps one `@theme` block for
tokens that don't change per-theme (spacing, radii, font vars) and gains three
`[data-theme="..."]` blocks that override just the color custom properties — the same pattern the
codebase already uses today, just parameterized by attribute instead of hardcoded once.

**Decision 2 — the `dark` theme is a new design, not copied from 8888.sk (it doesn't have one).**
8888.sk ships no dark mode. Derive `dark` from the same navy/mint palette: `#052e44`/`#0a2540` as
the dark surface (not the current near-black `#01040b`), `#12eaa6` as the accent (same as light),
light neutral text (`#e2e8f0`/`#f8fafc`-ish, not the neon `#e3f6ff`). This keeps `light` and `dark`
visually related (same brand hue) while giving `dark` its own honest identity — not an inverted
light theme with mismatched contrast.

**Decision 3 — `quantum` is a byte-for-byte preservation of the current look, not a remix.**
`[data-theme="quantum"]` gets exactly the current values (`--color-bg-deep:#01040b`, `--color-bg:
#060c1f`, `--color-text:#e3f6ff`, `--color-heading:#7ad9ff`, `--color-accent:#4dcfff`,
`--color-primary:#00aaff`, `--color-primary-hover:#0077cc`, `--color-border:rgba(0,170,255,.35)`),
the Orbitron font-family switch, and the existing `.glow`/`.pill`/`.panel` shadow values —
carried forward, never re-derived (per [[qrng-eaas-plan-workflow]]'s "audit what earlier epics
shipped" rule, this *is* EPIC 5's shipped work, just gated behind a new switch).

**Decision 4 — semantic status tokens replace the two hardcoded-color spots.**
Add `--color-success`/`--color-warning`/`--color-danger`/`--color-info` (with per-theme values —
mint-family success in light/dark, red/amber/blue kept close to Tailwind defaults for
recognizability) to the `@theme` block. `HealthBadge.tsx` and `VerifyReceipt.tsx`'s amber fallback
switch from raw `emerald-*`/`amber-*` classes to these tokens so status colors read correctly in
all three themes.

**Decision 5 — icons.** `react-icons` is already a dependency. Use `FiSun`/`FiMoon`
(`react-icons/fi`) for the light/dark toggle and `TbAtom2` (`react-icons/tb`) for the
quantum-mode icon, shown only once unlocked.

---

## 5. File plan (concrete paths)

| File | Change |
|------|--------|
| `qrng-eaas/web/package.json` | **Edit.** Add `next-themes` to `dependencies`. |
| `qrng-eaas/web/app/globals.css` | **Rewrite.** Keep `@import "tailwindcss";`. Base `@theme` block keeps non-color tokens (font vars incl. new `--font-sans`/`--font-mono` alongside `--font-orbitron`, radii/spacing if any custom ones are introduced). Add `:root, [data-theme="light"] { --color-bg-deep, --color-bg, --color-text, --color-heading, --color-accent, --color-primary, --color-primary-hover, --color-border, --color-success, --color-warning, --color-danger, --color-info: … }` (8888.sk-derived navy/mint values), a `[data-theme="dark"]` block (Decision 2 values), and a `[data-theme="quantum"]` block (Decision 3 — exact current values + `font-family` override to Orbitron on `body` scoped to this attribute). Update `body` to use `var(--font-sans)` by default; `[data-theme="quantum"] body` overrides to `var(--font-orbitron)`. Update `@utility glow`/`pill`/`panel` so their shadow intensity reads from theme-scoped values (soft shadow in light/dark, neon glow preserved under quantum). |
| `qrng-eaas/web/app/layout.tsx` | **Edit.** Load `Inter` (`variable: "--font-sans"`) and `JetBrains_Mono` (`variable: "--font-mono"`) via `next/font/google`, alongside the existing `Orbitron` load. Wrap `<body>` contents in the new `ThemeProvider`. Apply all three font variable classes on `<html>`. |
| `qrng-eaas/web/components/ThemeProvider.tsx` | **New.** Thin client wrapper around `next-themes`' `ThemeProvider` (`attribute="data-theme"`, `themes={["light","dark","quantum"]}`, `defaultTheme="system"`, `enableSystem`, `storageKey="qeaas-theme"`). |
| `qrng-eaas/web/lib/theme.ts` | **New.** Constants (`QUANTUM_UNLOCK_KEY = "qeaas-quantum-unlocked"`), `isQuantumUnlocked()`/`unlockQuantum()` helpers (localStorage-backed), tap-sequence detector helper (`useSecretTap(count, windowMs)` hook or equivalent) used by `Header.tsx`. |
| `qrng-eaas/web/components/ThemeToggle.tsx` | **New.** Client component: sun/moon segmented toggle via `useTheme()` from `next-themes`; renders a third atom segment only when `isQuantumUnlocked()` is true (read on mount + on unlock event). |
| `qrng-eaas/web/components/Header.tsx` | **Edit.** Restyle nav/logo/mobile-menu for the new tokens; wrap the logo in the secret-tap handler (calls `unlockQuantum()` then sets `theme="quantum"` via `next-themes`, plus a brief framer-motion confirmation toast); mount `<ThemeToggle/>` in both desktop nav and mobile menu; logo becomes an inline SVG/text wordmark reading `currentColor`/theme tokens (see §11 Q7) instead of the static `logo.png` `<img>`. |
| `qrng-eaas/web/components/Footer.tsx` | **Edit.** Restyle only (tokens/spacing/typography), no structural change. |
| `qrng-eaas/web/components/HealthBadge.tsx` | **Edit.** Replace hardcoded `emerald-*`/`amber-*`/`white/*` classes with the new semantic status tokens (Decision 4). |
| `qrng-eaas/web/components/DicePlayer.tsx` | **Edit.** Class-only restyle; verify touch targets on preset-sides chips; confirm `panel`/`pill` still read correctly under the new token shapes. |
| `qrng-eaas/web/components/KemHandshakeDemo.tsx` | **Edit.** Class-only restyle across the four animated `panel` cards; no change to the WebCrypto logic. |
| `qrng-eaas/web/components/sections/ApiUsage.tsx` | **Edit.** Restyle + wrap `<pre>`/`<code>` blocks in an `overflow-x-auto` container (currently missing — AC-2 mobile gap) + responsive spacing. |
| `qrng-eaas/web/components/sections/CryptoFraming.tsx` | **Edit.** Restyle + add responsive spacing (currently none). |
| `qrng-eaas/web/components/sections/NetworkingUseCases.tsx` | **Edit.** Restyle + add responsive grid/spacing for the 5-item use-case list. |
| `qrng-eaas/web/components/sections/PipelineDiagram.tsx` | **Edit.** Restyle tokens only; existing `md:` flex-direction flip logic is kept as-is (already correct). |
| `qrng-eaas/web/components/sections/VerifyReceipt.tsx` | **Edit.** Restyle + replace the hardcoded `amber-600` fallback with the `--color-warning` token. |
| `qrng-eaas/web/components/sections/WhatIsQrng.tsx` | **Edit.** Restyle + add responsive spacing (currently none). |
| `qrng-eaas/web/components/PageHero.tsx` | **New.** Extracts the shared back-link + `h1` + intro-paragraph wrapper currently duplicated in `app/dice/page.tsx` and `app/demo/page.tsx`. |
| `qrng-eaas/web/app/page.tsx` | **Edit.** Restyle hero section tokens/classes; no structural change to section order. |
| `qrng-eaas/web/app/dice/page.tsx` | **Edit.** Use `<PageHero/>` instead of the inline wrapper. |
| `qrng-eaas/web/app/demo/page.tsx` | **Edit.** Use `<PageHero/>` instead of the inline wrapper. |
| `qrng-eaas/web/public/file.svg`, `globe.svg`, `next.svg`, `vercel.svg`, `window.svg` | **Delete.** Confirmed unreferenced anywhere in `app/`/`components/`. |
| `qrng-eaas/README.md` | **Edit.** Short new section documenting the three themes, the easter-egg trigger (for whoever maintains this next), and the token file location — mirrors how EPIC 10 documented its master-key hierarchy. |

---

## 6. Step-by-step (manual — no automated tests)

1. **Install** `next-themes`; confirm `npm run build` and `npm run dev` still succeed with zero
   new TypeScript errors (`strict: true` is on).
2. **Token pass:** implement the three `[data-theme]` blocks in `globals.css` first, in isolation,
   and manually force each via browser devtools (`document.documentElement.dataset.theme = "..."`)
   on the home page before wiring the toggle — confirms the token system itself before any UI work.
3. **Wire `ThemeProvider` + `ThemeToggle`:** load the app, confirm it opens in `light` (or `dark` if
   OS is set to dark) with no flash of the wrong theme; toggle to `dark` and back; reload and
   confirm the explicit choice persisted (not reset to system).
4. **Secret trigger:** tap/click the header logo 5× within 3 seconds; confirm `quantum` theme
   applies (neon palette + Orbitron), a small unlock confirmation appears once, and the
   `ThemeToggle` gains its third segment; reload the page and confirm the segment is still present
   (persisted unlock) and `quantum` can be re-selected.
5. **Component sweep:** visually walk every page (`/`, `/dice`, `/demo`) in all three themes,
   confirming `.pill`/`.panel`/`.glow` render sensibly in each (soft shadows in light/dark, neon
   glow only in quantum) and `HealthBadge`/`VerifyReceipt` status colors read correctly in all
   three.
6. **Mobile pass:** using devtools device emulation (a real phone if available) at ~375px and
   ~768px widths, confirm: header/mobile-menu usable, hero CTA stacking, `ApiUsage` code blocks
   scroll horizontally instead of overflowing the viewport, all interactive elements meet a 44px
   touch target, `PipelineDiagram` still flips to vertical arrows.
7. **Cleanup check:** confirm the five deleted SVGs produce no build/lint errors (grep already
   confirmed zero references).
8. **README:** confirm the new theme-documentation section renders correctly and matches the
   implemented trigger mechanism exactly (don't let docs drift from the actual gesture/keys used).

---

## 7. Design decisions carried from the epic / codebase (do not re-litigate)

- The neon/Orbitron identity itself (colors, font, `.glow`/`.pill`/`.panel` shape language) was a
  deliberate EPIC 5 decision (`feature-epic5-web-app.md`, AC-7) reproducing an older project's look
  — this plan preserves it exactly as the `quantum` theme; it is not being redesigned or corrected.
- Tailwind v4's CSS-first `@theme`/`@utility` config (no `tailwind.config.js`) is the established
  pattern for this project (`feature-epic5-web-app.md:230-231`) — the multi-theme system extends
  it, it doesn't replace it with a config-file-based approach.
- No automated tests, per [[qrng-eaas-plan-workflow]] and every prior epic plan in this project.

---

## 8. Troubleshooting

- **Flash of wrong theme on load:** if this appears, `next-themes`' injected script isn't running
  before paint — check `ThemeProvider` is mounted at the true root (`app/layout.tsx`) and that no
  custom `_document`-equivalent is suppressing the injected inline script.
- **`quantum` theme reachable via OS dark-mode detection:** if toggling the OS to dark mode ever
  selects `quantum`, `defaultTheme="system"`/`enableSystem` is misconfigured — `system` must only
  ever resolve `light`/`dark` (this is `next-themes`' default behavior when `themes` includes a
  third non-`light`/`dark` name; it never auto-selects it).
- **Status colors look wrong in one theme:** check `HealthBadge.tsx`/`VerifyReceipt.tsx` are using
  the new `--color-success`/`--color-warning`/`--color-danger` tokens, not the old raw
  `emerald-*`/`amber-*` Tailwind classes (a stray hardcoded class is the most likely regression
  source since these two files are the only ones that currently deviate from the token system).

---

## 11. Open questions — RESOLVED (developer, 2026-07-13)

All seven questions below were answered by accepting the recommended default, verbatim, with no
changes.

**Q1 — Theming library: `next-themes` vs. hand-rolled `ThemeProvider`.**
Proposal (default): use `next-themes` (Decision 1). It's a small (~1.4kB), widely-used, actively
maintained library that solves the exact three problems a hand-rolled version would need to get
right (pre-paint script to avoid flash, `localStorage` sync, `prefers-color-scheme` resolution) and
supports the arbitrary `quantum` theme name natively. Alternative: hand-roll everything in
`lib/theme.ts` + a blocking inline `<script>` in `layout.tsx` — more code, more to get subtly wrong,
no dependency added. **Recommend `next-themes`.**

**Q2 — Easter-egg trigger mechanism.**
Proposal (default): 5 taps/clicks on the header logo within 3 seconds (Decision, chosen over a
keyboard Konami code because AC-2 requires the site to be mobile-first, and keyboard sequences are
unusable on touch devices). Alternative: a hidden footer element, a specific URL query param
(`?quantum=1`), or a long-press. **Recommend the 5-tap logo gesture** — discoverable by the kind of
person who fidgets with logos, works identically on mobile and desktop, no URL-sharing risk of
accidentally leaking the "easter egg" nature of it.

**Q3 — Does discovering the easter egg unlock it permanently, or must it be re-triggered every
visit?**
Proposal (default): permanent unlock via `localStorage` (`qeaas-quantum-unlocked`) — once
discovered, a third icon appears in the `ThemeToggle` on every future visit from that browser. This
matches typical "easter egg" UX (the delight is in the discovery, not in re-solving a puzzle every
session). Alternative: never persist the toggle-visibility, requiring the tap gesture every visit
even after first discovery (theme choice itself would still persist once *selected*, only the
toggle's visibility would reset). **Recommend permanent unlock.**

**Q4 — Default theme resolution for first-time visitors.**
Proposal (default): `next-themes`' `defaultTheme="system"` — respects the visitor's OS
`prefers-color-scheme`, choosing `light` or `dark` (both built from the 8888.sk palette), never
`quantum`. Alternative: always default to `light` regardless of OS preference. **Recommend
`system`** — standard, accessible behavior, and AC-3 asks for "light and dark mode" as parallel
options, not light-as-forced-default.

**Q5 — Logo treatment (raster PNG vs. theme-aware SVG/text wordmark).**
The current `public/logo.png` was presumably designed against the dark neon background; showing it
as-is on the new light default background risks poor contrast, and there's no way to recolor a
raster PNG per-theme without shipping three separate image files (which this plan can't
art-direct — designing new logo artwork is out of scope, §3). Proposal (default): replace the
`<img src="/logo.png">` in `Header.tsx` with a lightweight inline SVG or styled-text wordmark
("Q‑EaaS") that reads `currentColor`/theme tokens, so it recolors correctly and crisply across all
three themes with zero new asset work — keep `logo.png` only as the `<link rel="icon">`/metadata
favicon (unaffected by theme, browsers render favicons on their own chrome). Alternative: keep the
`<img>` as-is and accept it may look mismatched in `light` theme, flagging it as a known follow-up
for whoever does real brand design later. **Recommend the SVG/text wordmark swap** — it directly
serves AC-4 ("professionally looking") and costs nothing extra to implement.

**Q6 — Should the easter-egg unlock show a confirmation ("toast"), or unlock silently?**
Proposal (default): yes, a brief (~2s) framer-motion toast/badge (e.g. "quantum mode unlocked") —
framer-motion is already a dependency, the cost is a few lines, and silent unlocks risk the visitor
not realizing anything happened (undermining the "easter egg" delight). Alternative: silent unlock,
discoverable only by noticing the new toggle segment. **Recommend the confirmation toast.**

**Q7 — Scope of the mobile-breakpoint pass: minimum viable fixes vs. full audit.**
The survey found `ApiUsage`/`CryptoFraming`/`NetworkingUseCases`/`WhatIsQrng` have *zero*
responsive classes today (they rely on flexbox defaults inside a single max-width column, which
mostly works but isn't tuned). Proposal (default): do the full pass described in §5/§6 (responsive
type/spacing on every static section, `overflow-x-auto` on code blocks, 44px touch targets
everywhere) since AC-2 explicitly calls out "highly mobile friendly" as a named requirement, not an
afterthought. Alternative: narrower pass — only fix the code-block overflow bug (the one clear
mobile *bug*) and leave the rest as "already reflows acceptably." **Recommend the full pass** — it's
the same files being touched for the color/token restyle anyway, so the marginal cost is low.

---

## 12. Summary for the developer

This is a **presentation-only** refactor of `qrng-eaas/web/`: new default light/dark themes built
from `https://www.8888.sk/`'s actual shipped CSS (navy `#052e44`/`#0a2540`/`#084666` + mint
`#12eaa6`, `Inter`/`JetBrains Mono`, large radii, soft shadows), the current neon/Orbitron look
preserved unchanged as a hidden third `quantum` theme reachable only via a secret 5-tap logo
gesture, and a real mobile-responsiveness pass across every static section. No backend, content,
or test changes. Seven open questions above each carry a recommended default — answer or approve
them, then run `/implement-feature qrng-eaas/claude/plans/feature-epic11-design-refactor.md`.

---

## 13. Post-implementation

**Built:** all of §5's file plan, exactly as scoped — `next-themes` theming infra, the three
`[data-theme]` token blocks in `globals.css` (registered inside `@theme` for the `light` defaults
so Tailwind still generates the `bg-*`/`text-*` utilities, then overridden per-attribute for
`dark`/`quantum` — the plan's file-plan wording suggested colors could live outside `@theme`
entirely; that doesn't work with Tailwind v4's utility-generation model, so the base `@theme` block
keeps the light defaults and `dark`/`quantum` are pure CSS-variable overrides), `Inter`/
`JetBrains Mono` fonts, `ThemeProvider`/`ThemeToggle`/`lib/theme.ts`, the 5-tap secret gesture with
toast, Header/Footer restyle, semantic status tokens, the six sections' responsive pass,
`PageHero` extraction, SVG cleanup, and the README theme-documentation section.

**Deviations from the plan (both surfaced and approved before implementing):**
1. **Branch:** implemented directly on `main`, not a `feature-epic11-*` branch — this repo's prior
   ten epics were all committed straight to `main` with no feature-branch convention; developer
   confirmed staying on `main`.
2. **Scope expansion, Decision 4:** the plan named only `HealthBadge.tsx` + `VerifyReceipt.tsx`'s
   `amber-600` badge as hardcoded-color sites. Exploration found three more hardcoded
   `text-amber-300` error-alert spots the plan missed (`VerifyReceipt.tsx:87`,
   `DicePlayer.tsx:110`, `KemHandshakeDemo.tsx:160,262`) — amber-300 is tuned for a dark background
   and would read poorly on the new light theme. Developer approved converting all five sites to
   the new `--color-warning` token for full three-theme consistency.

**Also corrected in passing (not scope changes, just plan-text inaccuracies caught during
exploration):** `Header.tsx`'s logo was already `next/image`, not a raw `<img>`; `ApiUsage.tsx`'s
`<pre>` blocks already had `overflow-x-auto` (no fix needed there).

**Verification performed:** `npm run build`, `npx tsc --noEmit`, and `npm run lint` all pass with
zero errors/warnings on the full touched surface. **Manual in-browser verification (§6 steps 2-8 —
visually toggling themes, triggering the 5-tap easter egg, mobile-viewport pass) was explicitly
not run this session per developer instruction ("dont test anything" when a Playwright browser
install was proposed).** The developer should run `npm run dev` and walk §6 steps 2-8 by hand
before treating this as user-facing-verified, particularly: the flash-of-wrong-theme check, the
5-tap gesture timing/toast, and the `ThemeToggle`'s unlocked third segment persisting across
reloads.

**Follow-ups for the developer to consider (not built, out of scope for this ticket):**
- No dedicated brand-mark artwork was created (per §3 out-of-scope) — the header now uses a
  lightweight inline "Q" mark + text wordmark rather than a designed logo.
- `logo.png` remains the favicon/metadata icon only (unaffected by theme), per §11 Q5.
