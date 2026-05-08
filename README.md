# Norma — Maldonado UY zoning plugin for Claude Code

Norma is a Claude Code plugin for working with Maldonado department zoning rules: pick parcels (on the [Mapa app](https://estudio-local.com/mapa) or by padron number), get a written envelope analysis grounded in the TONE (Texto Ordenado de Normas Edilicias, Volumen V del Digesto Departamental), and render a printable report.

The plugin ships **one entry point — `/norma` — that dispatches to two sub-skills**:

| Slash command | Does | When |
|---|---|---|
| **`/norma`** | Dispatcher — reads your task, routes to the right sub-skill | Always start here |
| `/norma-analyze` | Envelope analysis (FOS, FOT, height, retiros, scenario filtering) | Padrón + locality, ArcGIS JSON, or `selection.v1.json` from the Mapa |
| `/norma-informe` | Printable A4 HTML report | An existing `*.normativa.v1.json` envelope |

## Install

### Option A — Claude Code marketplace (recommended)

```
/plugin marketplace add Estudio-Local/normativa
/plugin install norma@normativa
```

That's it. `/norma`, `/norma-analyze`, and `/norma-informe` all become available.

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
        ▼ (dispatcher routes to /norma-analyze)
 /norma-analyze --input selection.v1.json
        │
        ├─→ <basename>.md                    (humans read this; carries
        │                                     norma:requires-disclaimer marker)
        └─→ <basename>.normativa.v1.json     (validated against
                                │             normativa-v1-schema.md
                                │             before exit)
                                ▼
                         /norma --input <basename>.normativa.v1.json
                                │
                                ▼ (dispatcher routes to /norma-informe)
                         /norma-informe --input <basename>.normativa.v1.json
                                │
                                └─→ <basename>.informe.html  (printable A4)
```

You can also call the sub-skills directly if you know what you need (`/norma-analyze 130,131,132 en la-juanita`, `/norma-informe path/to/envelope.normativa.v1.json`).

Three files per analysis:

| File | Reader | Purpose |
|------|--------|---------|
| `*.md` | human | Full written analysis (with disclaimer + marker) |
| `*.normativa.v1.json` | machine | Structured envelope — feeds `/norma-informe` |
| `*.informe.html` | human | Printable A4 report (open in browser, print to PDF) |

The `*.normativa.v1.json` filename and its internal `schema: "estudio-local.normativa.v1"` field are versioned data contracts — they intentionally preserve the historical token across skill renames so downstream consumers (the Mapa app, other tools) don't break. `/norma-analyze` runs `normativa-v1-validate.py` against its own output before exiting; if validation fails, the envelope is fixed before `/norma-informe` ever sees it.

## Try it

Without installing anything, render the bundled example:

```bash
git clone https://github.com/Estudio-Local/normativa.git && cd normativa
python3 skills/norma-analyze/normativa-v1-validate.py \
  examples/padrones-130-132-la-juanita.normativa.v1.json
python3 skills/norma-informe/norma-informe-render.py \
  examples/padrones-130-132-la-juanita.normativa.v1.json
open examples/padrones-130-132-la-juanita.informe.html
```

Validates the canonical envelope, renders a 4-page printable report, opens it in your browser. ⌘P / Ctrl+P → "Save as PDF" to share.

## Repo layout (v0.8 architecture)

```
normativa/                              ← this repo (plugin slug: norma)
├── .claude-plugin/
│   ├── marketplace.json                marketplace manifest
│   └── plugin.json                     plugin manifest
├── rules/                              CROSS-SKILL ENFORCEMENT COPY
│   ├── README.md                       index — when to add a rule
│   ├── envelope-contract.md            strict types for *.normativa.v1.json
│   ├── professional-disclaimer.md      disclaimer block + norma:requires-disclaimer marker
│   ├── units-and-measurements.md       SI conventions, ISO-8601, enums
│   └── terminology.md                  tipología codes, frente principal hierarchy, decreto format
├── hooks/
│   ├── README.md                       how to wire hooks into ~/.claude/settings.json
│   ├── post-write-disclaimer-check.sh  marker-driven disclaimer enforcement
│   └── settings-snippet.json           ready-to-paste settings.json block
├── scripts/
│   └── lint.sh                         structural lint (frontmatter, schema refs, version drift)
├── skills/
│   ├── norma/                          ← /norma DISPATCHER (no work, just routing)
│   │   ├── SKILL.md                    routing table + rules
│   │   └── README.md
│   ├── norma-analyze/                  ← /norma-analyze (envelope analysis)
│   │   ├── SKILL.md
│   │   ├── README.md
│   │   ├── normativa-v1-schema.md      envelope schema spec
│   │   ├── normativa-v1-validate.py    strict stdlib validator (mandatory before exit)
│   │   ├── norma-scenarios.py          engine (applicable_tipologias)
│   │   ├── norma-extract-tipologias.py markdown → JSON extractor
│   │   ├── norma-merge-tipologias.py   reviewed extractions → tone-zones.json
│   │   └── datos/                      TONE source data (preserves tone- prefix)
│   └── norma-informe/                  ← /norma-informe (printable HTML report)
│       ├── SKILL.md
│       ├── README.md
│       ├── norma-informe-plantilla.html
│       └── norma-informe-render.py
├── examples/
│   ├── selection.v1.json
│   ├── padrones-130-132-la-juanita.normativa.v1.json
│   └── padrones-130-132-la-juanita.informe.html
├── README.md
└── LICENSE
```

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

## Architecture (v0.8 — adopting layered plugin pattern)

Norma's directory structure follows a layered plugin pattern that scales as more skills land. The current six layers are:

1. **Plugin** (`.claude-plugin/`) — manifest + marketplace entry. Single plugin today; upgradable to multi-plugin marketplace when /proforma and /mercado go public.
2. **Skills** (`skills/<slug>/SKILL.md`) — invocable units of behavior. Today: dispatcher `/norma` + `/norma-analyze` + `/norma-informe`.
3. **Rules** (`rules/`) — cross-skill enforcement copy. One source of truth; skills cite rules by relative path. Lint verifies citations resolve.
4. **Hooks** (`hooks/`) — Claude Code tool-event hooks that enforce contracts. Today: marker-driven disclaimer check on Write events.
5. **Scripts** (`scripts/lint.sh`) — structural lint, run pre-commit and pre-release. Catches frontmatter drift, missing schema docs, version mismatches between plugin.json and marketplace.json.
6. **Schema artifacts** (`<schema-id>-schema.md`, `<schema-id>-validate.py`) — named after the schema id, not the skill, so they survive skill renames intact.

The dispatcher pattern (`/norma` is a router, sub-skills do the work) means the user-facing entry point stays stable as the catalog grows. Adding a new sub-skill is: drop `skills/norma-foo/SKILL.md`, add a row to the dispatcher's routing table, run `scripts/lint.sh`. No rename of the user-facing command.

## Schemas

- **`selection.v1.json`** — optional input to `/norma-analyze` (typically produced by the Mapa app). Shape: `{ schema, padrones[], locality, area_total_m2, regimen, lots[].frentes[], … }`. See [`skills/norma-analyze/normativa-v1-schema.md`](./skills/norma-analyze/normativa-v1-schema.md) "Sister envelope" section.
- **`normativa.v1.json`** — produced by `/norma-analyze`, consumed by `/norma-informe`. Shape: `{ schema, selection, zone, scenarios[], recommendation, caveats, sources }`. See [`skills/norma-analyze/normativa-v1-schema.md`](./skills/norma-analyze/normativa-v1-schema.md) for the full spec, strict-types table, and common pitfalls.

`schema` field on every envelope is `estudio-local.<name>.v1` — version-bump on breaking changes only. The schema name is decoupled from the skill name on purpose: renaming the skills (`/normativa` → `/TONE` → `/norma` → `/norma-analyze`) does not bump the schema version. Downstream consumers keep working through brand changes.

## Requirements

- [Claude Code](https://claude.ai/claude-code) ≥ 2.0
- Python 3.9+ (for the renderer + validator; the analysis itself is markdown-driven)
- `bash` + `jq` (for the lint script + disclaimer hook)

## License

MIT. See [LICENSE](./LICENSE).
