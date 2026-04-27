# `/normativa` skill

Zoning envelope analyzer for lots in Maldonado, Uruguay. Paste GIS JSON from the cadastral portal — or pass a `selection.v1.json` envelope via `--input` — and get a building envelope analysis based on the TONE (Texto Ordenado de Normas de Edificación, Volumen V del Digesto Departamental).

For install instructions and the full plugin overview, see the [repo README](../../README.md).

## What this skill writes per run

| File | Format | Audience |
|------|--------|----------|
| `<basename>.md` | Markdown | Humans — full written analysis |
| `<basename>.normativa.v1.json` | JSON envelope | Machines — fed to `/informe` for the printable HTML report |

## Files in this directory

| File | Purpose |
|------|---------|
| `SKILL.md` | Instructions Claude follows when the skill runs |
| `SCHEMA.md` | Spec for the `normativa.v1.json` envelope |
| `scenarios.py` | Pure-function engine — `applicable_tipologias(zone, area, frente)` |
| `extract-tipologias.py` | Deterministic markdown → JSON extractor (data pipeline) |
| `merge-tipologias.py` | Reviewed extractions → `tone-zones.json` merger |
| `datos/tone-zones.json` | 10 localities, 33 zones, ~91 subzones with `tipologias[]` schema |
| `datos/titulo-*.md` | Full normativa text by sector (audit trail) |
| `datos/extractions/` | Per-titulo extraction artifacts (audit trail) |
| `datos/zoning/` | Per-zone GeoJSON polygons (reference geometry, 116 files) |
