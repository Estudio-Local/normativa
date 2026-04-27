# normativa — Maldonado UY zoning skills for Claude Code

Two Claude Code skills bundled as a single plugin:

- **`/normativa`** — analyze building envelope rules (FOS, FOT, height, retiros) for one or more parcels in Maldonado department, using the TONE (Texto Ordenado de Normas Edilicias, Volumen V del Digesto Departamental).
- **`/informe`** — render the analysis as a printable A4 HTML report.

## Install

### Option A — Claude Code marketplace (recommended)

```
/plugin marketplace add Estudio-Local/normativa
/plugin install normativa@normativa
```

That's it. Both skills appear as `/normativa` and `/informe`.

### Option B — Symlink (local dev)

```bash
git clone https://github.com/Estudio-Local/normativa.git
ln -s "$(pwd)/normativa" ~/.claude/plugins/normativa
```

## End-to-end flow

```
selection.v1.json (optional)
        │
        ▼
 /normativa --input selection.v1.json
        │
        ├─→ <basename>.md                    (humans read this)
        └─→ <basename>.normativa.v1.json     (informe reads this)
                                │
                                ▼
                         /informe --input <basename>.normativa.v1.json
                                │
                                └─→ <basename>.informe.html  (printable A4)
```

You can also run `/normativa` directly without an envelope:

- `/normativa 130,131,132 en la-juanita` — padron list + locality
- Or paste GIS JSON from the cadastral portal

Three files per run:

| File | Reader | Purpose |
|------|--------|---------|
| `*.md` | human | Full written analysis |
| `*.normativa.v1.json` | machine | Same data, structured — feeds `/informe` |
| `*.informe.html` | human | Printable A4 report (open in browser, print to PDF) |

## Try it

Without installing anything, render the bundled example:

```bash
git clone https://github.com/Estudio-Local/normativa.git && cd normativa
python3 skills/informe/render.py examples/padrones-130-132-la-juanita.normativa.v1.json
open examples/padrones-130-132-la-juanita.informe.html
```

Reads the sample analysis envelope, renders a 4-page printable report, opens it in your browser. ⌘P / Ctrl+P → "Save as PDF" to share.

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
normativa/                              ← this repo
├── .claude-plugin/
│   ├── marketplace.json                ← marketplace manifest
│   └── plugin.json                     ← plugin manifest
├── skills/
│   ├── normativa/                      ← /normativa skill
│   │   ├── SKILL.md                    ← instructions for Claude
│   │   ├── SCHEMA.md                   ← normativa.v1.json spec
│   │   ├── scenarios.py                ← engine (applicable_tipologias)
│   │   ├── extract-tipologias.py       ← markdown → JSON extractor
│   │   ├── merge-tipologias.py         ← reviewed extractions → tone-zones.json
│   │   ├── README.md
│   │   └── datos/
│   │       ├── tone-zones.json         ← 10 localities, 33 zones, ~91 subzones
│   │       ├── titulo-*.md             ← full normativa text by sector (7 files)
│   │       ├── extractions/            ← per-titulo extraction artifacts (audit trail)
│   │       └── zoning/                 ← per-zone GeoJSON (116 files)
│   └── informe/                        ← /informe skill
│       ├── SKILL.md
│       ├── plantilla.html              ← A4 report template
│       └── render.py                   ← JSON → HTML renderer (Python stdlib)
├── examples/
│   ├── selection.v1.json                                    ← sample input envelope
│   ├── padrones-130-132-la-juanita.normativa.v1.json        ← sample /normativa output
│   └── padrones-130-132-la-juanita.informe.html             ← sample /informe output
├── README.md
└── LICENSE
```

## Schemas

- **`selection.v1.json`** — optional input to `/normativa`. Shape: `{ schema, padrones[], locality, area_total_m2, regimen, lots[], … }`. See [`skills/normativa/SCHEMA.md`](./skills/normativa/SCHEMA.md) "Sister envelope" section.
- **`normativa.v1.json`** — produced by `/normativa`, consumed by `/informe`. Shape: `{ schema, selection, zone, scenarios[], recommendation, caveats }`. See [`skills/normativa/SCHEMA.md`](./skills/normativa/SCHEMA.md) for the full spec.

`schema` field on every envelope is `estudio-local.<name>.v1` — version-bump on breaking changes.

## Requirements

- [Claude Code](https://claude.ai/claude-code) ≥ 2.0
- Python 3.9+ (for `/informe`'s renderer; `/normativa` is markdown-driven)

## License

MIT. See [LICENSE](./LICENSE).
