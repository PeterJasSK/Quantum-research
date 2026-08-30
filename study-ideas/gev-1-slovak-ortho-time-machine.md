# GEV-1 — Slovak Ortho Time-Machine → God's Eye View (portfolio project)

**Status: PORTFOLIO / NON-COMMERCIAL.** Goal is to show off engineering skill, not make money. No buyers, no product, no revenue. Optimize for **(a)** a jaw-dropping public demo, **(b)** near-zero hosting cost so it can stay live for free, **(c)** clean legal footing for personal/non-commercial use.

**One-liner:** Fork the MIT `gods-eye-view` globe, strip the paid dependencies, rebuild it as a free-to-run Slovak showcase in two parts: **(1)** a tiny orthophoto *time-machine* MVP, then **(2)** the full "God's Eye" with live public cameras and the original plan/laser overlay.

**Base project:** [bilawalsidhu/gods-eye-view](https://github.com/bilawalsidhu/gods-eye-view) — MIT license, 3D globe, 13 live layers, OpenAI voice agent. We fork it.

**North star:** deploy something visually stunning that runs on **free / peanut-cost** infra indefinitely, all on open/self-hosted data.

---

## What this demonstrates (portfolio value)

The whole point. Each piece is a skill on display:
- **Geospatial engineering** — WMTS/WMS, tiling, orthophoto pipelines, 3D globe rendering.
- **Cost/architecture judgment** — taking a project that burns money on Google + OpenAI and re-architecting it to run for free. That story itself is impressive.
- **Data fusion** — many live public feeds into one coherent 3D place.
- **Frontend polish** — the "forbidden cockpit" HUD, timeline scrubbing, camera projection.
- **Using open public data legally** — resourcefulness + integrity.

Frame the README/writeup around *"I took a $$$-per-session viral demo and made it run for free on Slovak open data."* That's the headline.

---

## Cost architecture (must stay free / peanuts to keep it live)

Marginal cost per visitor ≈ €0 so it can sit on the internet forever without a bill.

**Cut entirely:**
- **OpenAI voice agent** — remove `OPENAI_API_KEY`, delete the realtime voice tool layer. Biggest per-minute burn; map showcase loses nothing. Bonus: no audio egress.
- **Google Photorealistic 3D Tiles** — billed $6.00 CPM per session (free only ≤1k/mo) and **caching is banned by Google ToS** even for non-commercial use. Don't build on it.

**Replace with open / self-hosted:**
| Need | Free source | Cache/self-host? |
|---|---|---|
| Aerial imagery (SK) | ÚGKK SR / ZBGIS orthophoto WMTS/WMS | ✅ verify terms, then tile + serve ourselves |
| Historical imagery | ZBGIS multi-year ortho archive | ✅ the whole point of Part 1 |
| Satellite fill | Sentinel-2 / Copernicus | ✅ fully open |
| Terrain (3D relief) | Cesium World Terrain (ion free tier) or self-rendered DEM | partial |
| Base vector map | OpenStreetMap | ✅ self-host tiles for volume |

**Rule:** never cache someone else's *licensed* tiles (Google/Bing/TomTom = permanent-cache banned). Only cache/self-host what we may redistribute (open state data, OSM, Copernicus).

**Serving:** pre-rendered raster tiles on free-tier object storage / CDN → unlimited views, no metered API. Boot in 2D/light mode, load 3D only on demand.

### ✅ VERIFIED — ÚGKK / ZBGIS orthophoto (2026-08-28)

**License = CC BY 4.0, fees = none.** Confirmed both in the live `GetCapabilities` and on the official GKÚ service list ([gku.sk WMS/WMTS list](https://www.gku.sk/gku/produkty-sluzby/zbgis/wms.html)):

```
<Fees>bez poplatkov</Fees>                                  (no fees)
<AccessConstraints>CC BY Creative Commons Attribution 4.0</AccessConstraints>
```

CC BY 4.0 = we may **cache, self-host, redistribute, commercial or not** — the only obligation is **attribution**. Blocker CLEARED (even commercial would be fine; portfolio easily is).

**Required attribution** (put in map credits + link the service metadata):
> `ZBGIS®, Úrad geodézie, kartografie a katastra Slovenskej republiky` + link to CC BY 4.0.

**Confirmed endpoints** (host `zbgisws.skgeodesy.sk`, all CC BY 4.0, author GKÚ Bratislava):

| Service | URL | GetCapabilities |
|---|---|---|
| **Ortofoto WMS** ✅ tested live | `https://zbgisws.skgeodesy.sk/zbgis_ortofoto_wms/service.svc/get` | `?request=GetCapabilities&service=WMS` |
| **Ortofoto WMTS** (S-JTSK) | `https://zbgisws.skgeodesy.sk/zbgis_ortofoto_wmts_sjtsk/service.svc/get` | `?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetCapabilities` |
| ZBGIS base WMTS (S-JTSK) | `https://zbgisws.skgeodesy.sk/zbgis_wmts_sjtsk/service.svc/get` | same pattern |
| ZBGIS base WMS (all layers) | `https://zbgisws.skgeodesy.sk/zbgis_wms_featureinfo/service.svc/get` | `?request=GetCapabilities&service=WMS` |

**Ortofoto WMS details** (from live caps):
- Layer title: `Ortofotomozaika SR`, MaxWidth/Height 4096.
- CRS supported: **EPSG:3857 / 102100 (Web Mercator)** ✅, 4326, 5514 (S-JTSK), 4258, 32633/32634 (UTM). Web Mercator support = drops straight into a web/globe client, no reprojection.
- National bbox (3857): x `1854264 … 2518510`, y `6047649 … 6397492`.

⚠️ **Projection note:** the **WMTS** ortofoto is **S-JTSK only** (EPSG:5514). For a Web-Mercator globe, either use the **WMS with EPSG:3857** (works, but tile-per-request, so pre-render + cache our own tiles) or reproject the WMTS. Plan around WMS-3857 → self-tiled.

⚠️ **Historical vintages — NOT solved.** The live ortho WMS serves only the **current mosaic** (single latest layer). GKÚ's service list has **no multi-year ortho archive** as separate live services — only *Historická mapa III. vojenského mapovania* (1880s military maps, raster, CC BY 4.0) exists as a "historical" layer. So the **time-machine core needs a real old-imagery source**. Options to resolve:
  - Request archival ortho cycles from ÚGKK (they capture ~3-yr cycles: 2017–19, 2020–22, 2023–25) — may be download/order, not live WMS.
  - Use **III. vojenské mapovanie** for a dramatic *deep*-history compare (1880s ↔ today) — already live + CC BY 4.0. Different flavor but zero-cost and striking.
  - Fill recent years with **Sentinel-2** (open) for lower-res but genuinely annual change.
  - **Decision for MVP:** if archival ortho cycles aren't easily fetchable, pivot Part 1 to *III. vojenské mapovanie ↔ current ortho* swipe — still the time-machine hook, fully free, fully live today.

### ✅ VERIFIED — III. vojenské mapovanie WMS (2026-08-28) → Part 1 layer pair LOCKED

Tested live. **`bez poplatkov` + CC BY 4.0**, and crucially **EPSG:3857 supported** — same projection as the ortho, so the two overlay/swipe with no reprojection.

| Era | Layer | WMS endpoint | Layer id (3857) |
|---|---|---|---|
| ~1880s | Historická mapa III. vojenského mapovania | `https://zbgisws.skgeodesy.sk/hm_III_vm/service.svc/get` | `1` (title `HM_III_VM`) |
| today | Ortofotomozaika SR | `https://zbgisws.skgeodesy.sk/zbgis_ortofoto_wms/service.svc/get` | `Ortofotomozaika SR` |

- III.vm: formats incl. `image/png32` (transparency for the top layer), MaxW/H 4096, whole-SK coverage (lon 16.52–22.70, lat 47.50–49.83), bbox 3857 x `1839388–2526774` / y `6024313–6416929` — **contains** the ortho bbox, so Bratislava is in both.
- Both host `zbgisws.skgeodesy.sk`, both CC BY 4.0, both `bez poplatkov`.
- **Part 1 is now buildable with zero paid API.** Pull both via WMS GetMap in EPSG:3857, pre-render tiles, self-host, timeline/swipe between the two eras. Attribution: `ZBGIS®, ÚGKK SR` + CC BY 4.0 link.

---

## Part 1 — MVP: Ortho Time-Machine (very small)

**Goal:** smallest thing that proves the pipeline and looks cool. One AOI — Bratislava center. Slide a timeline, imagery of the same place swaps across years.

**Scope — deliberately tiny:**
- Single map view (2D is fine for MVP — 3D is Part 2 polish).
- One AOI, a handful of ortho vintages (e.g. 2012 / 2018 / 2023 / latest).
- **Timeline slider** → swaps the ortho layer for the selected year.
- Optional: split-screen / swipe compare (before ↔ after).
- Self-hosted tiles only. Zero paid API. Deploy static + free CDN.

**Explicitly OUT of MVP:** 3D mesh, cameras, live layers, voice, accounts, multi-city, change-detection algorithms. All deferred to Part 2 / later.

**What it proves:** the free Slovak-data pipeline works end-to-end, and the "watch it change over time" hook is genuinely striking.

**MVP definition of done:**
- [ ] ÚGKK/ZBGIS ortho terms verified OK for cache + public re-serving (non-commercial)
- [ ] N ortho vintages for 1 AOI tiled and served from our own free storage
- [ ] Timeline slider swaps years smoothly
- [ ] Runs with €0 recurring cost
- [ ] Live public URL, shareable in portfolio

---

## Part 2 — God's Eye with cameras + plan/laser overlay

Built on the fork, after Part 1 validates the pipeline. This is the flashy centerpiece of the portfolio.

**Keep from the original:**
- **3D globe** — on free terrain + our self-hosted ortho draped, not Google tiles.
- **Plan / laser overlay** — keep the original's HUD/plan-overlay + laser/viewshed visuals (the "forbidden cockpit" grammar). Pure client-side render, cheap, and the main wow factor.
- **CCTV mesh** — wired to **Slovak public agency cameras** (NDS highway cams, city traffic portals) instead of Austin/California/London. Keep the "positions published, poses calibrated by dragging a gizmo" mechanic.
- **Viewshed / coverage volumes** — per-camera "where it reaches / where it's blind."

**Optionally add (all keyless / free):**
- Live flights (OpenSky anonymous / adsb.lol), earthquakes (USGS), satellites (CelesTrak) — global, no Slovak-specific work.
- SK sensor layers nobody fuses: SHMÚ weather radar, transit GTFS-realtime, air quality.

**Still cut:** OpenAI voice, any paid tile provider, anything person-level (faces/plates/individual tracking — GDPR hard line + the upstream author blocks it too).

---

## Legal / GDPR guardrails

Even non-commercial, if it's hosted publicly the rules apply:
- **MIT fork:** free to modify + host — keep the license/copyright notice.
- **Cameras:** only feeds a public authority *already publishes for public viewing*. No private/covert cams (Insecam-style = illegal access + data-protection breach under Act 18/2018 + GDPR).
- **No person-level features:** no faces, no plate→person, no individual tracking. Ever.
- **Per-source terms:** each live feed carries its own terms (see the repo's `DATA_SOURCES.md`).
- **Non-commercial helps** but does not exempt data-protection law — hosting publicly still makes us a controller; keep cams wide/low-res traffic feeds only.

---

## Sequencing

1. **Part 1 MVP** — ortho time-machine, 1 AOI, timeline slider, self-hosted free tiles. Prove pipeline + get a live URL.
2. **Part 2** — fork the full globe, drape our ortho on free terrain, wire Slovak cameras, keep plan/laser overlay + viewshed. Add keyless global layers.
3. **Writeup** — README/blog framing the "made a $$$ viral demo run for free on Slovak open data" story.

**First action:** verify ÚGKK / ZBGIS orthophoto terms (cache + public re-serve, non-commercial). Everything depends on it.
