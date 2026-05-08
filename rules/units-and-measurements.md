# Units and measurements

Conventions every Norma skill follows when emitting numbers, dates, and enum values. The validator + schema doc reference this file as authoritative.

## SI units only

- Linear: **meters (m)**. Never feet, never inches.
- Area: **square meters (m²)** — written `m²` with the superscript-2 character, not `m2`.
- Density / coverage: **percent (%)** as a number. The JSON envelope stores `FOS_pct: 50` (number); the renderer formats as `50%`. Skills MUST NOT emit strings like `"50%"` in JSON.
- Heights / counts: **integers** unless the source decimal is meaningful (e.g., `altura_m: 13.6`).

## Decimal formatting (display)

UY locale: comma as decimal separator, period as thousands separator. The renderer uses `Intl.NumberFormat('es-UY')` / `f"{n:,}".replace(",", ".")` to produce:

- `13.050 m²` (thirteen thousand fifty)
- `7,5 m` (seven and a half)
- `27.881 m² · FOS 50%` (mixed)

JSON envelope numbers are always **plain numerics** (`13050`, not `"13.050"`). Display formatting happens at render time only.

## ISO-8601 dates

`generated_at` and any timestamp field uses ISO-8601 UTC:

- `2026-05-08T14:32:00Z` ✓
- `2026-05-08` (date-only when time isn't relevant) ✓
- `"May 8, 2026"` ✗
- `"08/05/2026"` ✗

## Enum values (lowercase, no abbreviations)

`selection.regimen` and `selection.lots[].regimen`:
- `comun` — Propiedad Común (PC)
- `ph` — Propiedad Horizontal
- `otro` — neither (unusual)
- `mixed` — multi-lot selection where lots disagree

`zone.data_quality`:
- `verified` — full source citation, recommended for production decisions
- `partial` — some fields null; surface caveat in analysis
- `estimated` — inferred from similar zones; flag for verification
- `pending` — source not transcribed; avoid committing to numbers
- `conditional` — applies only under condition (see `_applicability_note`); confirm with user

`scenarios[].applicable`:
- `true` — viable in this selection
- `false` — not viable; include `reason` field

## Coordinate system

Geometric calculations (parcel frente, intersection with calles) happen in **EPSG:32721 (UY UTM Zone 21S, meters)**. WGS84 lat/lon (EPSG:4326) is used only for visual map rendering and data interchange. See [`reference_ide_ejes_vialidad.md`](https://github.com/Estudio-Local/mapa) for the producer-side projection details.

## How to apply

- When emitting JSON: numbers stay numeric, dates ISO-8601, enums lowercase.
- When emitting markdown reports for humans: format via the renderer's `fmt_m`, `fmt_m2`, `fmt_pct`, `fmt_int`, `fmt_es_date` helpers. Don't hand-format.
- When citing this rule in a SKILL.md: `See [units-and-measurements](../../rules/units-and-measurements.md) for SI conventions and enum values.`
