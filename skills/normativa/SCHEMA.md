# `normativa.v1.json` — schema spec

Machine-readable envelope produced by `/normativa` alongside the markdown report. Consumed by `/informe` (HTML report renderer).

## Conventions

- **`schema` field** is `estudio-local.normativa.v1`. Bump to `.v2` only on breaking changes; additive fields stay v1.
- **Numbers** are SI units (m, m², %). Integers where natural; floats where decimals matter (e.g. `altura_m: 13.6`).
- **`null` vs missing**: prefer `null` for "known-unknown" (data exists but value not applicable); omit the key only when the concept doesn't apply.
- **Spanish-language strings** for headlines, programa, plazos, rationale, caveats — the report is Spanish-facing.
- **`generated_at`** is ISO-8601 UTC.

## Top-level shape

```json
{
  "schema": "estudio-local.normativa.v1",
  "generated_at": "2026-04-26T23:45:00Z",
  "skill_version": "0.1.0",

  "selection":      { ... },     // what was analyzed
  "zone":           { ... },     // resolved TONE zone + per-zone tipologias catalog
  "scenarios":      [ ... ],     // applicable scenarios in evaluation order
  "recommendation": { ... },     // pick one scenario + rationale
  "caveats":        [ ... ],     // free-form warnings (data quality, assumptions)
  "sources":        { ... }      // provenance for the analysis
}
```

## `selection`

```json
{
  "padrones":           ["130", "131", "132"],
  "locality":           "la-juanita",
  "locality_name":      "José Ignacio – La Juanita",
  "regimen":            "comun",     // "comun" | "ph" | "otro" | "mixed"
  "area_total_m2":      13050,
  "frente_estimado_m":  90,          // longest contiguous edge if multi-lot
  "adjacent":           true,        // false = non-contiguous selection
  "lots": [
    { "padron": "130", "manzana": "045", "area_m2": 4350, "regimen": "comun" },
    { "padron": "131", "manzana": "045", "area_m2": 4350, "regimen": "comun" },
    { "padron": "132", "manzana": "045", "area_m2": 4350, "regimen": "comun" }
  ]
}
```

## `zone`

```json
{
  "code":         "2.1",
  "name":         "Amanzanado",
  "decreto":      "Dto. 3970/2017",
  "data_quality": "verified",      // "verified"|"partial"|"estimated"|"pending"|"conditional"
  "tipologias_catalog": [
    {
      "codigo":     "vivienda_unifamiliar",
      "nombre":     "Vivienda unifamiliar",
      "altura_m":   7,
      "FOS_pct":    50,
      "FOT_pct":    80,
      "thresholds": { "area_min_m2": 300, "frente_min_m": 12 },
      "retiros":    { "frontal_m": 4, "lateral_m": 3, "fondo_m": 5, "entre_volumenes_m": null }
    }
    // ... bloque_bajo, bloque_medio, etc.
  ],
  "retiros_zone":   { "frontal_m": 4, "lateral_m": 3, "fondo_m": 5 },
  "special_rules": [
    "Frente sobre rambla: gálibo de 4 m sobre el plano de fachada"
  ]
}
```

`tipologias_catalog` is the FULL list of tipologías defined for the zone — applicability per scenario lives in `scenarios[]`.

## `scenarios`

Array of evaluated scenarios. Conventional ordering: A (individual lots) → B (apareadas / party-wall) → C (englobamiento — unified). Each scenario is self-contained:

```json
{
  "id":             "C1",
  "label":          "Englobamiento — Bloque Medio",
  "headline":       "13.050 m² edificables, +480% sobre desarrollo individual",
  "applicable":     true,
  "tipologia": {
    "codigo":  "bloque_medio",
    "nombre":  "Bloque Medio"
  },
  "envelope": {
    "FOS_pct":              50,
    "FOT_pct":              290,
    "altura_m":             28,
    "viviendas_estimadas":  96,
    "area_edificable_m2":   13050,
    "area_ocupacion_m2":    6525
  },
  "retiros": {
    "frontal_m":          4,
    "lateral_m":          3,
    "fondo_m":            5,
    "entre_volumenes_m":  6
  },
  "tipologias_habilitadas": ["bloque_bajo", "bloque_medio"],
  "programa":  "Aprox. 96 unidades de 80 m² (3 dorm) o 120 unidades de 60 m² (2 dorm)…",
  "plazos":    "Permiso de construcción ~6–9 meses; englobamiento previo ~3 meses…",
  "notes":     "Frente union de 90 m supera el mínimo de 30 m. FOS 50% × 13.050 = 6.525 m² ocupación."
}
```

When a tipología does NOT apply (lot too small, etc.), still include the scenario with `applicable: false` and a `reason` field — `/informe` shows it greyed out.

## `recommendation`

```json
{
  "scenario_id":              "C1",
  "rationale":                "El englobamiento de los 3 padrones desbloquea Bloque Medio (área mín 1.000 m², frente mín 30 m), maximizando m² edificables.",
  "uplift_vs_individual_pct": 480,
  "tradeoffs": [
    "Englobamiento requiere fusión catastral (~3 meses)",
    "Pérdida de 3 padrones independientes — menos flexibilidad de venta por etapas"
  ]
}
```

Bias by **m² yield** by default. Override only when explicit constraints kill the high-yield path (régimen PH, special_rule overrides, etc.) — explain in `rationale`.

## `caveats`

Free-form Spanish strings, one per line. Keep ≤ 200 chars each.

```json
[
  "Frente estimado a partir de la unión geométrica — verificar con plano de obra.",
  "data_quality=verified para zona 2.1; revisar special_rules manualmente."
]
```

## `sources`

```json
{
  "tone_zones":    "skills/normativa/datos/tone-zones.json",
  "decretos":      ["Dto. 3970/2017"],
  "last_updated":  "2026-03-15"
}
```

`last_updated` is the date of the most recent decreto incorporated into `tone-zones.json` (not the date of *this* analysis — that's `generated_at`).

## Validation

`/normativa` should write a valid envelope on every run. Minimum required keys:

- `schema`, `generated_at`, `skill_version`
- `selection.padrones`, `selection.locality`, `selection.area_total_m2`
- `zone.code`, `zone.data_quality`
- `scenarios` (at least one entry, even if just `applicable: false`)
- `recommendation.scenario_id` (or `null` if no applicable scenario)
- `caveats` (empty array OK)

`/informe` refuses to render if any required key is missing.

## Versioning

- **v1**: this document.
- **Additive changes** (new optional fields): stay v1, document under "Changelog".
- **Breaking changes** (removed/renamed fields, changed types): bump to v2, ship side-by-side support in `/informe` for one minor release, then drop v1.

## Sister envelope: `selection.v1.json` (optional input)

When `/normativa` is invoked with `--input <path>`, the file is a `selection.v1.json` envelope that pre-resolves the parcel selection. Shape:

```json
{
  "schema":         "estudio-local.selection.v1",
  "generated_at":   "2026-04-26T22:30:00Z",
  "padrones":       ["130", "131", "132"],
  "locality":       "la-juanita",
  "locality_name":  "José Ignacio – La Juanita",
  "regimen":        "comun",
  "area_total_m2":  13050,
  "frente_estimado_m": 90,
  "adjacent":       true,
  "lots": [
    { "padron": "130", "manzana": "045", "area_m2": 4350, "regimen": "comun" }
  ],
  "zone_hint":      { "code": "2.1", "data_quality": "verified" }
}
```

**Authority rules for `/normativa` when consuming this:**
- `padrones`, `locality`, `area_total_m2`, `regimen`, `lots[]` are **authoritative** — copy verbatim into the output's `selection.*`.
- `zone_hint.code` is a **suggestion** — `/normativa` should still resolve the zone independently from `tone-zones.json` and only use the hint if its own resolution is ambiguous.
- `frente_estimado_m` is best-effort — re-compute if a more authoritative geometry is available.

This input mode is optional. `/normativa` works equally well with padron lists or pasted GIS JSON (see SKILL.md).

## Changelog

- **v1.0** (2026-04): initial schema.
