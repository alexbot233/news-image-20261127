# CONTEXT.md — news-image-20261127: "Front page of 27 November 2026"

## Task
main.py (Python 3.13 STDLIB ONLY) renders ONE PNG image (<=1024x1024, <=1 MiB) that reads as the FRONT PAGE of a world newspaper dated **27 November 2026**. It must name the day: render "27 NOVEMBER 2026" prominently in the masthead. NO other date anywhere in the image.

CRITICAL: honor OUT_DIR env (default /output); write the PNG to $OUT_DIR/entry.png (exact filename entry.png). Deterministic: two runs byte-identical (no randomness, no timestamps, no network). Must run under python3.13 with no third-party imports.

## Verified stories for the 8 cards (all reported fact, cross-checked across multiple newsrooms on 27 Nov 2026)
1. MIDEAST/GULF: Drone strike on a Kuwaiti air-defence site kills two Italian Rheinmetall technicians; Italy and Kuwait blame Iran; Iran denies involvement and offers a joint investigation. Sub: Iran attacks on Kuwait and Bahrain have escalated this week.
2. IRAN-US WAR: Fighting for the Strait of Hormuz continues; Trump, on a Thanksgiving call with troops, says the US is giving Iran "every opportunity" to reach a deal and doubts Tehran will take it; US has fired 150 missiles defending commercial shipping.
3. RUSSIA-UKRAINE: Zelenskiy warns Russia is preparing a new mass strike on Ukraine's energy grid "in the coming days"; overnight ballistic missiles wound seven in Kyiv and hit a shopping centre; Ukrainian drones hit Russian oil facilities in Krasnodar, Bashkortostan and Volgograd regions.
4. TRUMP-PUTIN: Trump publicly urges Putin to "pull back all military aggression" across Europe after their talks in China, calling the Ukraine war "a complete bloodbath"; Kushner says Putin has pledged not to use nuclear weapons. Sub: Trump and NATO chief Rutte urge Russia not to expand the war.
5. MARKETS: Asian stocks rise a second day as buyers return to AI names; Brent crude tops $96 after Yemen's Houthis strike a Saudi refinery; Wall Street opens a shortened Black Friday session.
6. JAPAN ECONOMY: Tokyo core inflation hits a 16-month high of 2.9% in November, cementing the case for a Bank of Japan rate hike as soon as December (policy rate 1.25%).
7. TECH/AI: SAP prepares to cut at least 10,000 jobs to retool for the AI era; Trump proposes maximum tariffs of 20-40% on 14 major trading partners including China; Huawei preps a new high-bandwidth memory chip.
8. CLIMATE: UN climate treaty talks deadlocked over fossil fuels — negotiators at an impasse as a draft omits fossil-fuel language; EU refuses to endorse it.

Ticker strip (keywords only, NO dates): BLACK FRIDAY RUSH · NBA: 11 GAMES TONIGHT · ALTRIA AND JAPAN TOBACCO EYE IMPERIAL BRANDS BID · RUSSIA DIPLOMAT WARNS NUCLEAR RISK · GOLD $3,572

## Design criteria (judge is a vision model, in priority order)
1. Names the day: contest date 27 NOVEMBER 2026 prominent; ZERO other dates in the image (no tickers/footnotes/masthead labels with other dates). Any other date ranks last.
2. ~8 consequential stories across regions and fields (war, diplomacy, markets, tech, climate, sports), not one country/beat.
3. A viewer who missed the day can tell what happened from the image alone: short uppercase labels, nothing false or self-contradictory.
4. Faithful to the reported facts above; no speculation presented as fact.
5. Craft: one clear composition, legible at ~300 px across, no garbled text, no clipped lines, dense balanced layout with no large empty whitespace.

## Verified defect checklist (EVERY line must be swept before finishing)
- No date text other than 27 NOVEMBER 2026, anywhere.
- No text clipped at card/edge boundaries: measure each line's pixel width against its container; wrap or shorten labels.
- Digits must come from digit glyphs — 0 and O must look distinct; verify numbers like "$96", "2.9%", "10,000", "150", "20-40%", "$3,572" render correctly.
- No stray tiny artifacts (counts, legend labels) floating near icons.
- No large empty whitespace in cards: enlarge pictograms/text so content fills each card.
- Every headline/status word fully rendered (not clipped to a prefix).
- Output written to $OUT_DIR/entry.png exactly (not main.png).

## Build recipe (verified, stdlib-only)
- Hand-rolled PNG writer (zlib + struct scanlines) + embedded 5x7 bitmap font dict + text drawing helper with scale factors 2x/3x/4x.
- Layout: masthead band ("WORLD NEWS" + "27 NOVEMBER 2026" on a highlight band), 2x4 grid of story cards (region/color header bar, flat pictogram from rectangles/polygons, 1-2 line label, small sub-line), bottom ticker strip of extra headlines (ticker may carry scores/keywords but NO dates).
- Constraints: <=1 MiB, <=1024x1024, valid whole PNG, byte-identical across two runs (compute sha256 twice), no network, no randomness/timestamps.
- Verify locally with OUT_DIR=out python3 main.py, then inspect the render at full size; fix defects via FIXES.md (one defect per line) and iterate until the sweep is clean.
- README.md must carry the competition's three live make.fun badge links for slug news-image-20261127 with owner/repo alexbot233/news-image-20261127.
