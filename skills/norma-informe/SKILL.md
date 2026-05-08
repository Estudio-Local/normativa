---
name: norma-informe
description: Render a /norma-analyze envelope as a printable A4 HTML report. Input is the *.normativa.v1.json envelope produced by /norma-analyze. Invoked directly or via the /norma dispatcher.
allowed-tools:
  - Read
  - Bash
  - Glob
user-invocable: true
---

# /norma-informe — Printable HTML report from a `/norma-analyze` envelope

Invoked directly (`/norma-informe path/to/envelope.normativa.v1.json`) or routed-to by the `/norma` dispatcher when the user asks for a printable report from an existing analysis.

## Rules this skill follows

- [`rules/envelope-contract.md`](../../rules/envelope-contract.md) — strict types this skill consumes (validates schema id; falls back to "—" cells on missing values).
- [`rules/professional-disclaimer.md`](../../rules/professional-disclaimer.md) — the rendered HTML carries the disclaimer block + `norma:requires-disclaimer` marker via `norma-informe-plantilla.html`.
- [`rules/units-and-measurements.md`](../../rules/units-and-measurements.md) — display formatting (es-UY locale) for all numeric cells.

## Original docstring

Take a `*.normativa.v1.json` envelope and render it as a self-contained, printable A4 HTML report. No analysis here — pure rendering. Thin wrapper around `norma-informe-render.py` (Python stdlib only, no dependencies).

## Startup message

```
Norma Informe — printable report builder
Input:  <path-to>.normativa.v1.json
Output: <basename>.informe.html  (open in browser, print to PDF for sharing)
```

## Workflow

### Step 1: Locate the input

| Invocation | What you do |
|------------|-------------|
| `/norma-informe <path>` | Use that path directly. |
| `/norma-informe` (no args) | Search the current working directory for `*.normativa.v1.json` via `Glob`. If exactly one match, use it. If multiple, list them and ask which. If none, error out with a friendly message. |
| `/norma-informe N1,N2[,…]` (padron list) | Search cwd for `*.normativa.v1.json` whose `selection.padrones` match. If found, use it; if not, tell the user to run `/norma-analyze` first. |

### Step 2: Validate the envelope

1. File exists and is valid JSON.
2. Top-level `schema` field equals `"estudio-local.normativa.v1"`. If different (e.g. `.v2`), bail with: *"This /norma-informe expects schema v1; the input is `<schema>`. Re-run /norma-analyze with the latest version, or install a matching /norma-informe."*
3. Required keys present (per `../norma-analyze/normativa-v1-schema.md`'s "Validation" section): `selection.padrones`, `selection.locality`, `selection.area_total_m2`, `zone.code`, `scenarios` (≥ 1), `recommendation` (object), `caveats`.

Surface missing keys as a clear error pointing back at `/norma-analyze`. Do not try to render a partial envelope.

### Step 3: Run the renderer

```bash
python3 "$CLAUDE_PLUGIN_ROOT/skills/norma-informe/norma-informe-render.py" <input-path> [<output-path>]
```

If `<output-path>` is omitted, the script writes alongside the input with `.informe.html` suffix. Print the script's stdout (the "wrote …" line) verbatim — don't paraphrase.

### Step 4: Confirm + how to share

```
✓ Wrote <path>.informe.html (<size> KB)

Open it: open "<path>.informe.html"
Print to PDF: open the file, ⌘P / Ctrl+P, "Save as PDF"
```

The HTML is self-contained — single file, no external assets except Google Fonts (Martian Mono) over CDN. Works offline once cached, prints cleanly to A4.

## Output structure

The rendered HTML is 4 A4 pages:

| Page | Content | Source field(s) |
|------|---------|-----------------|
| 1 — Cover + lot data | Title, lot table, zone summary | `selection.lots[]`, `zone.{code,name,decreto,data_quality}` |
| 2 — Comparativa | Per-scenario grid, recommendation box | `scenarios[]`, `recommendation` |
| 3 — Detalle escenario recomendado | Envelope, retiros, tipologías habilitadas, programa, plazos | `scenarios[recommended]`, `zone.tipologias_catalog` |
| 4 — Normativa, fuentes, descargo | Decretos table, sources, caveats, disclaimer | `sources`, `caveats` |

To change the report shape: edit `norma-informe-plantilla.html` (HTML/CSS) and / or `norma-informe-render.py`'s `build_*` helpers — they map JSON keys to HTML chunks. No template engine; just `str.replace` on `{{PLACEHOLDER}}` markers.

## Limitations (v0.1)

- **No envelope plan SVG** — geometry rendering deferred to a future schema bump.
- **One scenario detail page** — only the recommended scenario gets a detail page. Multi-scenario detail is a v0.2 feature.

## Troubleshooting

| Error | Likely cause | Fix |
|-------|--------------|-----|
| `error: expected schema='estudio-local.normativa.v1', got '...'` | Envelope is v2 or hand-edited | Re-run `/norma`; update the schema field |
| Missing required key | `/norma` aborted mid-write | Re-run `/norma`; check `normativa-v1-schema.md` for required set |
| Empty scenarios grid | All scenarios have `applicable: false` | Expected for selections that fail every threshold — report still renders the recommendation as "Sin escenario recomendado" |
