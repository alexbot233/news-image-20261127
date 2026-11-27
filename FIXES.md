# FIXES.md — defect sweep (one defect per line)

- Defect: the Russia/Ukraine card omitted the oil-region specificity; fixed by adding "SITES IN THREE REGIONS" as a full sub-line while keeping every measured line inside its card.
- Defect: "pledged no nuclear weapons" could be misread as a pledge about possession rather than use; fixed to "PUTIN PLEDGED NOT TO USE / NUCLEAR WEAPONS" (faithful to the report).
- Defect: digit 0 could be mistaken for letter O; fixed with a distinct slashed zero glyph in the embedded 5x7 font, verified against the separate O glyph.
- Defect: headline/sub-lines risk clipping at card edges; fixed with `text()` width assertions (headlines <=460 px, sub-lines <=356 px) plus vertical spacing checks (last sub-line ends 5 px above the card border).
- Defect: extra date-like text risk in story copy; fixed with a render-time sweep that rejects any month or year string other than the single masthead date "27 NOVEMBER 2026".
- Defect: small pictograms could leave empty card bodies; fixed by scaling all flat icons into a 92x84 area over a pale anchor disc, plus measured ink coverage in every card zone.
- Defect: wrong output filename risk; fixed by writing only `$OUT_DIR/entry.png` (default `/output`).
- Verified clean: final two runs produced byte-identical 28,606-byte PNGs, sha256 `f15ba95e2a14e73192a5b1d8f308ce7bb13a9a9686df6d9a473d64d2f3f5408e`; PNG is 1024x1024 with valid CRCs, and the only month/year text in the image is the masthead date.
