# Norma — Maldonado UY zoning analysis for Claude Code

Norma is a single-product family for working with Maldonado department zoning rules: pick parcels on a map, get a written envelope analysis grounded in the TONE (Texto Ordenado de Normas Edilicias, Volumen V del Digesto Departamental), and render a printable report. This repo ships the Claude Code plugin half — two skills bundled together:

- **`/norma`** — analyze building envelope rules (FOS, FOT, height, retiros) for one or more parcels.
- **`/norma-informe`** — render the analysis as a printable A4 HTML report.

The companion Mapa app (parcel selection, exports `selection.v1.json` envelopes) lives in a separate repo. Both fall under the Norma umbrella.

## Install

### Option A — Claude Code marketplace (recommended)

```
/plugin marketplace add Estudio-Local/normativa
/plugin install norma@normativa
```

That's it. Both skills appear as `/norma` and `/norma-informe`.

### Option B — Symlink (local dev)

```bash
git clone https://github.com/Estudio-Local/normativa.git
ln -s "$(pwd)/normativa" ~/.claude/plugins/norma
```

## End-to-end flow

```
selection.v1.json (optional, from Mapa)
        │
        ▼
 /norma --input selection.v1.json
        │
        ├─→ <basename>.md                    (humans read this)
        └─→ <basename>.normativa.v1.json     (validated against
                                │             normativa-v1-schema.md
                                │             before exit)
                                ▼
                         /norma-informe --input <basename>.normativa.v1.json
                                │
                                └─→ <basename>.informe.html  (printable A4)
```

You can also run `/norma` directly without an envelope:

- `/norma 130,131,132 en la-juanita` — padron list + locality
- Or paste GIS JSON from the cadastral portal

Three files per run:

| File | Reader | Purpose |
|------|--------|---------|
| `*.md` | human | Full written analysis |
| `*.normativa.v1.json` | machine | Same data, structured — feeds `/norma-informe` |
| `*.informe.html` | human | Printable A4 report (open in browser, print to PDF) |

The `*.normativa.v1.json` filename and its internal `schema: "estudio-local.normativa.v1"` field are versioned data contracts — they intentionally preserve the historical token across skill renames so downstream consumers (the Mapa app, other tools) don't break. `/norma` runs `norma-validate-envelope.py` against its own output before exiting; if validation fails, the envelope is fixed before `/norma-informe` ever sees it.

## Try it

Without installing anything, render the bundled example:

```bash
git clone https://github.com/Estudio-Local/normativa.git && cd normativa
python3 skills/norma/norma-validate-envelope.py examples/padrones-130-132-la-juanita.normativa.v1.json
python3 skills/norma-informe/norma-informe-render.py examples/padrones-130-132-la-juanita.normativa.v1.json
open examples/padrones-130-132-la-juanita.informe.html
```

Validates the canonical envelope, renders a 4-page printable report, opens it in your browser. ⌘P / Ctrl+P → "Save as PDF" to share.

## What's covered

| Locality | Decretos | Coverage |
|----------|----------|----------|
| Punta del Este | Dto. 3718/1997 → Dto. 4056/2022 | Verified |
| Maldonado (city) | Dto. 3885/2011 → Dto. 4056/2022 | Verified |
| La Barra / Manantiales | Dto. 3718/1997 → Dto. 4056/2022 | Verified |
| José Ignacio | Dto. 3718/1997 → Dto. 3970/2017 | Partial |
| San Carlos (urbano) | Dto. 3718/1997 → Dto. 4042/2021 | Verified |
| San Carlos (rural) | Resolución 3103/2014 | Verified |
| Garzón / Aiguá / Pan de Azúcar | Dto. 3718/1997 → Dto. 3970/2017 | Partial |

10 localities · 33 zones · ~91 subzones. Per-zone `_data_quality` flag (`verified` / `partial` / `estimated` / `pending` / `conditional`) surfaces uncertainty.

Last decree incorporated: Dto. 4056/2022. Always verify against the live digesto at https://digesto.maldonado.gub.uy.

## Repo layout

```
normativa/                              ← this repo (plugin slug: norma)
├── .claude-plugin/
│   ├── marketplace.json                ← marketplace manifest
│   └── plugin.json                     ← plugin manifest
├── skills/
│   ├── norma/                          ← /norma skill
│   │   ├── SKILL.md                    ← instructions for Claude (harness convention name)
│   │   ├── README.md                   ← per-skill overview
│   │   ├── normativa-v1-schema.md      ← envelope schema spec
│   │   ├── norma-validate-envelope.py  ← strict stdlib validator (run before exit)
│   │   ├── norma-scenarios.py          ← engine (applicable_tipologias)
│   │   ├── norma-extract-tipologias.py ← markdown → JSON extractor
│   │   ├── norma-merge-tipologias.py   ← reviewed extractions → tone-zones.json
│   │   └── datos/
│   │       ├── tone-zones.json         ← 10 localities, 33 zones, ~91 subzones (TONE-derived)
│   │       ├── norma-sync-zoning.py    ← pull/refresh zoning polygons
│   │       ├── titulo-*.md             ← full normativa text by sector (7 files)
│   │       ├── extractions/            ← per-titulo extraction artifacts (audit trail)
│   │       └── zoning/                 ← per-zone GeoJSON (116 files)
│   └── norma-informe/                  ← /norma-informe skill
│       ├── SKILL.md                    ← (harness convention name)
│       ├── README.md
│       ├── norma-informe-plantilla.html ← A4 report template
│       └── norma-informe-render.py     ← JSON → HTML renderer (Python stdlib)
├── examples/
│   ├── selection.v1.json                                    ← sample input envelope
│   ├── padrones-130-132-la-juanita.normativa.v1.json        ← sample /norma output
│   └── padrones-130-132-la-juanita.informe.html             ← sample /norma-informe output
├── README.md
└── LICENSE
```

## Naming convention

This repo follows a deliberate naming convention so files stay legible across multiple skills and repos. Generic names (`render.py`, `SCHEMA.md`, `helpers.py`) become indistinguishable in editor tabs, grep results, and stack traces once you have more than one skill.

**Inviolate names — never rename**, the harness or community standards require these exact filenames:
- `SKILL.md` (Anthropic skill discovery)
- `plugin.json`, `marketplace.json` (Claude Code plugin manifests)
- `README.md`, `LICENSE` (github / OSS convention)

**Code & templates — prefixed:** kebab-case, lowercase, prefixed with the skill slug.

| Pattern | When to use | Example |
|---|---|---|
| `<skill-slug>-<role>.<ext>` | Code, templates, helpers belonging to one skill | `norma-scenarios.py`, `norma-informe-render.py` |
| `<schema-id>-schema.md` | Data contract docs (named after the schema id, stable across skill renames) | `normativa-v1-schema.md` |

**Content files keep their domain names** — `tone-zones.json` and `titulo-*.md` are TONE-derived data, not Norma-product code, so the `tone-` prefix is appropriate there. The brand prefix only applies to product surfaces (skills, plugins, code).

Why prefix even though the skill folder already namespaces them: a filename is what shows up in editor tabs, error stack traces, grep results across repos, and pasted code snippets — places where the surrounding folder context isn't visible. The prefix is defensive against the file ever being seen out of context.

## Schemas

- **`selection.v1.json`** — optional input to `/norma` (typically produced by the Mapa app). Shape: `{ schema, padrones[], locality, area_total_m2, regimen, lots[], … }`. See [`skills/norma/normativa-v1-schema.md`](./skills/norma/normativa-v1-schema.md) "Sister envelope" section.
- **`normativa.v1.json`** — produced by `/norma`, consumed by `/norma-informe`. Shape: `{ schema, selection, zone, scenarios[], recommendation, caveats }`. See [`skills/norma/normativa-v1-schema.md`](./skills/norma/normativa-v1-schema.md) for the full spec, strict-types table, and common pitfalls.

`schema` field on every envelope is `estudio-local.<name>.v1` — version-bump on breaking changes only. The schema name is decoupled from the skill name on purpose: renaming the skills (e.g. `/normativa` → `/TONE` → `/norma`) does not bump the schema version. Downstream consumers keep working through brand changes.

`/norma` runs `norma-validate-envelope.py` against its own output before declaring done. The validator is pure stdlib, surfaces concrete per-field errors (e.g. `selection.padrones[0]: expected string, got int (130)`), and refuses to accept malformed envelopes — so `/norma-informe` never has to defend itself against bad input.

## Requirements

- [Claude Code](https://claude.ai/claude-code) ≥ 2.0
- Python 3.9+ (for the renderer + validator; the analysis itself is markdown-driven)

## License

MIT. See [LICENSE](./LICENSE).
