---
name: normativa
description: Analyze zoning envelope rules for lots in Maldonado, Uruguay using GIS data and TONE regulations
allowed-tools:
  - Read
  - Write
  - Edit
  - WebFetch
  - AskUserQuestion
  - Bash
  - Glob
  - Grep
user-invocable: true
---

# /normativa — Zoning Envelope Analysis (Maldonado, Uruguay)

Analyze building envelope rules for one or more lots in Maldonado using GIS data from the ArcGIS cadastral portal and the TONE (Volume V of the Digesto Departamental). When multiple adjoining lots are provided, compares individual, apareada (party wall), and unified (englobamiento) development scenarios.

## Startup Message

When this skill is invoked, **always** display the following before any analysis:

```
Zoning Analysis — Maldonado, Uruguay
TONE (Digesto Departamental, Volumen V)

Normativa coverage:
  Punta del Este       Dto. 3718/1997 → Dto. 4056/2022
  Maldonado (city)     Dto. 3885/2011 → Dto. 4056/2022
  La Barra/Manantiales Dto. 3718/1997 → Dto. 4056/2022
  José Ignacio         Dto. 3718/1997 → Dto. 3970/2017
  San Carlos (urban)   Dto. 3718/1997 → Dto. 4042/2021
  San Carlos (rural)   Resolución 3103/2014
  Garzón/Aiguá/P.Azúcar Dto. 3718/1997 → Dto. 3970/2017

Last decree incorporated: Dto. 4056/2022
Normativa last updated: March 2026

Note: Always verify against the live digesto at
digesto.maldonado.gub.uy for amendments after Dto. 4056/2022.
```

## Workflow

### Step 0: Detect input mode

Three ways to invoke this skill — pick the path that matches what the user provided:

| Invocation | Where the data comes from | Jump to |
|------------|---------------------------|---------|
| `/normativa --input <path>` | `selection.v1.json` envelope — already contains padrones, locality, total area, régimen, per-lot data | **Step 1a** |
| `/normativa 130,131,132 en la-juanita` (padrones + locality phrase) | Look up each padrón via the cadastral portal | **Step 1** |
| Pasted ArcGIS JSON (one or more features) | Direct from the Maldonado ArcGIS cadastral portal | **Step 1** |

The end state is always the same: an in-memory `selection` object containing `{ padrones, locality, area_total_m2, regimen, lots[] }`. From there the workflow is identical.

### Step 1a: Read `selection.v1.json` (envelope input mode)

When invoked with `--input <path>`:

1. Read the JSON. Validate `schema == "estudio-local.selection.v1"`. Reject (with a friendly error) if missing or a different version.
2. **Echo `selection.*` values verbatim into your in-memory selection state.** Do NOT re-derive area, régimen, or padron lists — the envelope is the authoritative source.
3. Only re-derive missing fields. Common case: `frente_estimado_m` may be absent — compute it via the cadastral portal lookup if so.
4. If `selection.regimen == "ph"` or `regimen == "mixed"`, surface this in the analysis: PH (Propiedad Horizontal) lots can't be englobado without copropietarios authorization. Note in `caveats` and downgrade C-scenarios accordingly.
5. If `selection.padrones.length > 1`, also load each padron's geometry (cadastral portal or local cache) for adjacency / combined-frente logic. Areas from the envelope stay authoritative; geometry is only for adjacency checks.
6. Skip ahead to **Step 3** (Convert Coordinates) — Step 2's "extract attributes from ArcGIS JSON" doesn't apply.

If the file is NOT a `selection.v1.json` envelope (user passed an ArcGIS JSON file by mistake), fall back to Step 1's parsing logic.

### Step 1: Parse GIS Input

Accept pasted JSON from the Maldonado ArcGIS cadastral portal. The input is an array — it may contain one or multiple lot features.

**Detect urban vs rural:** Check the attribute keys to determine the parcel type:
- **Urban lots** have: `nomloccat`, `nummancat`, `valaream2`, `tiporegime`
- **Rural lots** have: `areaha`, `areamc`, `seccat` (and lack `nomloccat`)

**If RURAL → immediately flag as non-viable for multi-unit development:**

Rural lots in Maldonado are governed by Resolución 3103/2014 and Decreto 3866/2010, not the urban TONE. The constraints make starter home development impractical:
- **50,000 m²/dwelling** minimum → an 8 ha lot supports only 1-2 houses
- **FOS 5%, FOT 8%** — extremely low density
- **90% must remain natural/unpaved**
- **Only isolated units** — no blocks, no paired, no apartments
- **No subdivision** for housing without soil category transformation (Decreto 3866/2010)
- Soil transformation requires Executive approval and existing luxury dwellings on site

Present this as a short verdict:
```
## Rural Lot — Not Viable for Starter Home Development

| Parameter | Value |
|-----------|-------|
| Padrón | [number] |
| Area | [X] ha ([Y] m²) |
| Sección catastral | [N] |
| Coordinates | lat, lon |

### Why This Doesn't Work
- Min 50,000 m²/dwelling → only [N] unit(s) possible
- FOS 5% / FOT 8% — rural density limits
- 90% must remain natural
- No blocks, paired units, or apartments — isolated viviendas only
- Rural → suburban conversion requires Executive approval (Dto. 3866/2010)

### Path to Viability
Soil category transformation (rural → suburban) under Decreto 3866/2010, but requires:
1. Executive (Intendencia) approval
2. Existing luxury dwellings (Cat. D/E) on site
3. 25m buffer from public domain
4. 15m service roads
5. SRN land is excluded entirely

**Recommendation:** Skip this lot for the starter home program. Focus on urban/suburban parcels where density is permitted by right.
```

Do NOT proceed to Steps 2-7 for rural lots.

**If URBAN → continue with normal workflow:**

Extract key attributes:
- `nomloccat` — locality name (e.g., "LA BARRA")
- `padron` — lot number
- `nummancat` — block (manzana) number
- `valaream2` — lot area in m²
- `tiporegime` — property regime (PC = Propiedad Común, PH = Propiedad Horizontal)
- `geometry.rings` — polygon coordinates in Web Mercator (EPSG:3857)

**Multiple lots:** If the input contains more than one feature, proceed to Step 1b.

### Step 1b: Detect Adjoining Lots (multi-lot input only)

When multiple lots are provided:
1. Check if they share the same `nomloccat` and `nummancat` (same locality and block)
2. Test adjacency by checking if any polygon edges are shared or nearly coincident (within 1m tolerance). Two lots are adjoining if they share a common edge (not just a corner point).
3. Compute the **combined polygon** by merging the rings — remove the shared internal edge to get the outer boundary of the unified parcel.
4. Calculate the combined area (sum of `valaream2` values) and combined dimensions from the merged polygon.
5. Determine the combined frente (front) by measuring the merged polygon's frontage.

If lots are NOT adjoining, analyze each lot independently (run the full workflow per lot).

If lots ARE adjoining, continue with **both** tracks:
- **Individual analysis** — each lot on its own (Steps 2–7)
- **Combined analysis** — the unified parcel (Steps 2–7 using combined area/geometry)
- **Comparison** — side-by-side comparison at the end (Step 7)

### Step 2: Convert Coordinates

Use the geometry rings to calculate approximate lot dimensions:
1. Rings are in Web Mercator (EPSG:3857) — units are meters but distorted by projection
2. For x-axis (east-west): multiply distances by `cos(latitude)` where latitude ≈ -34.8° → cos factor ≈ 0.821
3. For y-axis (north-south): distances are approximately correct
4. Convert first ring to pairs, calculate edge lengths, estimate front × depth
5. Verify calculated area against `valaream2`

To convert EPSG:3857 to lat/lon for reference:
- `lon = x / 20037508.34 × 180`
- `lat = (atan(exp(y / 20037508.34 × π)) × 360 / π) - 90`

### Step 3: Look Up Location

Read `~/.claude/skills/normativa/datos/location-map.md` to match `nomloccat` to a TONE sector/region.

If no match is found, search the digesto website at `https://digesto.maldonado.gub.uy/` for the location.

### Step 4: Load Normativa

Read the corresponding normativa file from `~/.claude/skills/normativa/datos/`.

If the file doesn't exist yet:
1. Fetch the relevant articles from the digesto using WebFetch
2. The section index pages are at `https://digesto.maldonado.gub.uy/index.php/armado-seccion/{id}`
3. Individual articles are at `https://digesto.maldonado.gub.uy/index.php/detalle-articulo/{id}`
4. Present the raw content to the user
5. Offer to save it as a new normativa reference file for future use

### Step 5: Determine Zone/Subzone

1. **First**, read `~/.claude/skills/normativa/datos/tone-zones.json` — a structured index of all 10 localities, 33 zones, 91 subzones. Each subzone carries a `tipologias[]` array (per Phase 2 schema, April 2026) with per-tipología `thresholds` (area_min_m2, frente_min_m), altura, pisos, FOT/FOS/FOS_SS/FOS_V, and retiros. Also carries `_data_quality` (verified / partial / estimated / pending / conditional) and optional `_applicability_note`. Use it to narrow candidates by matching `nomloccat` to a locality and `nummancat` to manzana descriptions. When `_data_quality !== 'verified'`, surface the caveat in the analysis output.
2. **Then**, cross-reference against the full normativa text (loaded in Step 4) to verify zone boundaries described by street names and geographic features.
3. Use `nomloccat` and `nummancat` (block number) to match zone boundary descriptions
4. Check position relative to Ruta 10, coastline, and named streets
5. If the zone is ambiguous, present the possible options via AskUserQuestion
6. State your reasoning for the zone determination

### Step 6: Calculate Building Envelope

Apply the normativa rules to the specific lot.

**Prefer the scenario engine when available:** if the subzone carries a `tipologias[]` array, use `normativa/scenarios.py` → `applicable_tipologias(zone, area_m2, frente_m)` to filter tipologías whose `thresholds` are met. The returned list drives per-tipología envelope math (altura/FOT/FOS/retiros come from each tipología entry directly). Fall back to legacy scalar fields (`altura_maxima`, `FOT`, `FOS`, `retiros`) only for subzones that don't carry `tipologias[]` yet (27 pending zones as of 2026-04-24).

1. **Permitted building types**: For each tipología in the subzone, check `thresholds.area_min_m2` and `thresholds.frente_min_m` against the lot. Use `scenarios.applicable_tipologias` when available
2. **Maximum height and floors**: Per-tipología — read `altura_m` and `pisos_label` from the tipología entry
3. **Setbacks**: Per-tipología `retiros: { frontal_m, lateral_m, fondo_m }`. Symbolic values (e.g. `"2/7_altura_min_3"` = 2/7 of altura with 3m min) must be evaluated at envelope computation time. Additional conditions:
   - Ruta 10 frontage (larger setbacks — typically in `notas`)
   - Small-lot provisions (frente ≤ 15m)
   - Auxiliary construction allowances in setbacks
4. **Occupation factors**: `FOT_pct`, `FOS_pct`, `FOS_SS_pct`, `FOS_V_pct` per tipología
   - Interpolate by lot area when `notas` mention interpolation (some zones like 2-3/2-5.1 Maldonado and Balnearios D.209 have area-based FOT curves)
   - Calculate actual m² from percentages
5. **Buildable footprint**: Lot area minus setback areas
6. **Maximum built area**: FOT × lot area
7. **Special conditions**: Galibo (last floor setback), overhangs, piloti requirements (see `notas`)
8. **Data quality caveat**: If `_data_quality !== 'verified'`, prefix the envelope output with a warning (e.g. "⚠ Datos de esta zona: `partial` — verificar contra el decreto original antes de tomar decisiones de inversión"). For `conditional` zones, require the user to confirm the applicability condition (e.g., frentista a vía principal) before applying the tipologías.

### Step 6b: Development Strategy (Decision Tree)

After calculating the envelope, evaluate the optimal development strategy for the lot. This determines the **recommended unit count and building type** that maximizes affordable housing potential.

#### Decision Tree

```
START
  │
  ├─ What building types are permitted in this zone/subzone?
  │   List all: aislada, apareada, conjunto, bloque bajo, edificación baja, bloque medio
  │
  ├─ For each permitted type, does the lot meet minimum area/frente?
  │   Filter to viable types only
  │
  ├─ For each viable type, calculate max units:
  │
  │   AISLADA (isolated):
  │     - If zone has conjunto rule (1,000 m²/unit): units = floor(lot_area / 1,000)
  │     - If no conjunto rule: 1 unit per lot (Art. D.257 always allows 1 vivienda)
  │     - Minimum 1 unit regardless
  │
  │   APAREADA (paired/duplex):
  │     - Conjunto rule is per PAIR: 1,000 m² per pair = 2 units per 1,000 m²
  │     - So units = floor(lot_area / 1,000) × 2
  │     - Shared party wall = 0 m lateral setback on shared side
  │     - Example: 1,028 m² → 1 pair → 2 units
  │
  │   CONJUNTO (group):
  │     - Aisladas: 1,000 m² per unit, 6 m separation
  │     - Apareadas: 1,000 m² per pair, 6 m between pairs
  │     - Units = (aislada count) or (apareada count × 2)
  │
  │   BLOQUE BAJO:
  │     - Min lot typically 1,200 m² (30 m frente)
  │     - Units = floor(FOT m² × (1 - circulation) / avg_unit_area)
  │     - No per-unit lot area rule — density driven by FOT
  │
  │   EDIFICACIÓN BAJA:
  │     - Min lot typically 2,000 m² (30 m frente)
  │     - Similar to bloque bajo but lower height
  │
  │   BLOQUE MEDIO:
  │     - Min lot typically 1,000 m² (30 m frente)
  │     - Highest density — FOT up to 290%
  │
  ├─ SUBDIVISION option:
  │     - Can the lot be subdivided to unlock more units?
  │     - Smaller lots get HIGHER FOS/FOT (40%/60% under 400 m²)
  │     - Each subdivided lot gets 1 vivienda under Art. D.257
  │     - Trade-off: more units but subdivision requires municipal approval
  │     - Calculate: if split into N lots of lot_area/N m² each:
  │       total_buildable = N × (lot_area/N × FOT_at_that_size)
  │     - Compare to single-lot buildable
  │
  ├─ Rank strategies by:
  │     1. Maximum unit count (more units = lower cost per unit = more affordable)
  │     2. Total buildable m² (more area = more flexibility)
  │     3. Administrative feasibility (apareada > subdivision > englobamiento)
  │
  └─ OUTPUT: Recommended strategy with reasoning
```

#### Output: Development Strategy Table

Include this in the report after the Building Envelope section:

```markdown
## Development Strategy

| Strategy | Type | Units | Buildable m² | m²/Unit | Feasibility |
|----------|------|-------|-------------|---------|-------------|
| A: Single vivienda | Aislada | 1 | 514 m² | 514 | Immediate |
| B: Duplex | Apareada | 2 | 514 m² | 257 | Immediate |
| C: Subdivide ×3 | Aislada | 3 | 617 m² | 206 | Requires approval |
| **Recommended: B** | | | | | |

**Reasoning:** Apareada (duplex) doubles units without subdivision, leveraging the 1,000 m²/pair rule. Each unit at 257 m² (PB+PA) is generous for first-time buyers. Strategy C yields more units but requires municipal subdivision approval.
```

#### Envelope Data addition

Add the recommended strategy to the Envelope Data JSON:

```json
{
  "strategy": {
    "recommended": "apareada",
    "max_units": 2,
    "building_type": "Unidades apareadas",
    "reasoning": "1,000 m²/pair rule allows 2 units without subdivision",
    "alternatives": [
      { "type": "aislada", "units": 1, "buildable": 514 },
      { "type": "subdivide_3", "units": 3, "buildable": 617, "requires": "municipal approval" }
    ]
  }
}
```

Downstream consumers of the `strategy` block read `strategy.max_units` to cap units and `strategy.recommended` to label the building type.

### Step 7: Present Analysis

Use the output format below to present a structured analysis.

### Step 8: Save Report

Save the report as a markdown file to `./`:
- Single lot: `padron-{number}-{location}.md`
- Multiple lots: `padrones-{range}-{location}-{count}-lots.md`

Use lowercase, hyphens for spaces, and the locality name (e.g., `buenos-aires`, `la-barra`, `punta-del-este`).

### Step 8b: Save the JSON sidecar (`*.normativa.v1.json`)

**Always** write a structured JSON sidecar next to the markdown report. Same directory, same basename, `.normativa.v1.json` extension:

- Single lot: `padron-{number}-{location}.normativa.v1.json`
- Multiple lots: `padrones-{range}-{location}-{count}-lots.normativa.v1.json`

This file is the contract between `/normativa` and downstream skills. `/informe` reads it to render the printable HTML report. The schema is locked — see [`SCHEMA.md`](./SCHEMA.md) for the full spec, field-by-field rules, and validation requirements.

**Top-level shape (mandatory keys):**

```json
{
  "schema":         "estudio-local.normativa.v1",
  "generated_at":   "2026-04-26T23:45:00Z",
  "skill_version":  "0.1.0",
  "selection":      { "padrones": [...], "locality": "...", "area_total_m2": ..., "regimen": "...", "lots": [...] },
  "zone":           { "code": "...", "name": "...", "data_quality": "...", "tipologias_catalog": [...] },
  "scenarios":      [ { "id": "A", "label": "...", "applicable": true, "envelope": {...}, "retiros": {...}, ... } ],
  "recommendation": { "scenario_id": "C1", "rationale": "...", "uplift_vs_individual_pct": ... },
  "caveats":        [ "..." ],
  "sources":        { "decretos": ["..."], "last_updated": "..." }
}
```

**Key rules** (full detail in `SCHEMA.md`):

- Always write the file, **including for single-lot and rural-lot analyses**. For rural lots, `scenarios` is `[{ "id": "A", "applicable": false, "reason": "Rural — 50.000 m²/vivienda mínimo" }]` and `recommendation.scenario_id` is `null`.
- When the input came from `selection.v1.json`, **echo its `selection.*` values verbatim**. Do not re-derive area/régimen — the envelope is authoritative.
- `tipologias_catalog` lists ALL tipologías defined for the zone. Per-scenario `applicable` flags say whether each is reachable for *this* selection.
- Bias `recommendation` by **m² edificable yield** unless an explicit constraint kills the high-yield path (régimen PH blocking englobamiento, special_rule overrides, etc.).
- Validate before writing: every key in `SCHEMA.md`'s "Validation" section must be present.

The markdown report (Step 8) and this JSON sidecar carry the same information — markdown for humans, JSON for machines (next skill in the chain). Keep them in sync.

### Step 9: Save Normativa (if fetched)

If new articles were fetched from the digesto during this analysis:
1. Ask the user if they want to save them as a local normativa reference file
2. If yes, write to `~/.claude/skills/normativa/datos/` with a descriptive filename
3. Update `location-map.md` with the new mapping

## Output Format

### Single Lot

```markdown
# Zoning Envelope Analysis — Padrón [number], [location]

## Lot Data
| Parameter | Value |
|-----------|-------|
| Padrón | ... |
| Manzana | ... |
| Location | ... |
| Area | ... m² |
| Regime | ... |
| Approx. dimensions | ... m × ... m |
| Coordinates | lat, lon |

## Applicable Zone
**[Zone name] → [Subzone name]**
Reasoning for zone determination.

## Permitted Building Types
Which types are viable given this lot's area, with minimum area requirements listed.

## Building Envelope

### Height
| Parameter | Value |
|-----------|-------|
| Max height | ... m |
| Floors | ... |
| Notes | ... |

### Occupation Factors
| Factor | % | m² |
|--------|---|-----|
| FOS SS | ... | ... |
| FOS | ... | ... |
| FOS V | ... | ... |
| FOT | ... | ... |

(Interpolated by lot area if between defined ranges)

### Setbacks
| Direction | Distance | Notes |
|-----------|----------|-------|
| Front | ... m | ... |
| Lateral 1 | ... m | ... |
| Lateral 2 | ... m | ... |
| Rear | ... m | ... |

### Auxiliary Constructions in Setbacks
What can be built in setbacks, with limits (area, height).

### Overhangs (Salientes)
Projection allowances over setbacks.

## Buildable Envelope Sketch
ASCII diagram showing the lot with setbacks and buildable zone, oriented with front at bottom.

## Key Constraints
- Bullet list of the most important limiting factors
- Compliance issues (undersized lot, etc.)
- Special conditions that apply

## Envelope Data

Machine-readable data for `/zoning-envelope`. Include the exact lot polygon from the GIS input converted to local meters, plus all computed envelope parameters.

```json
{
  "lot_poly": [[x, y], ...],
  "unit": "m",
  "setbacks": { "front": 6, "rear": 3, "lateral1": 3, "lateral2": 2 },
  "volumes": [
    { "type": "base", "inset": 3.5, "h_bottom": 0, "h_top": 7, "label": "unidad aislada" }
  ],
  "height_cap": 7,
  "info": { "title": "Padrón ..., ...", "zone": "...", "id": "Padrón ...", "area": "... m²" },
  "stats": { "FOS": "25% → ... m²", "FOT": "50% → ... m²", ... }
}
```

For multi-lot analyses, add a `"scenarios"` key:
```json
{
  "scenarios": {
    "A": { "label": "Individual", "volumes": [...], "stats": {...} },
    "B": { "label": "Apareadas", "volumes": [...], "stats": {...} },
    "C1": { "label": "Unified", "volumes": [...], "stats": {...} }
  }
}
```

To generate an interactive 3D viewer from this data, run: `/zoning-envelope path/to/this-report.md`
```

### Multiple Adjoining Lots

When analyzing adjoining lots, present three sections:

```markdown
# Zoning Envelope Analysis — Padrones [A], [B], [...], [location]

## Lot Data
Table listing each lot's attributes side by side.

| Parameter | Padrón A | Padrón B | Combined |
|-----------|----------|----------|----------|
| Area | ... m² | ... m² | ... m² |
| Dimensions | ... | ... | ... |
| ... | | | |

## Applicable Zone
Zone determination (typically the same for adjoining lots in the same manzana).

---

## Scenario A: Individual Lots (separate padrones)

For each lot, present the full envelope analysis (height, occupation factors, setbacks, sketch).
Note which building types are available at each individual lot size.

## Scenario B: Apareadas (party wall, no unification)

If the zone permits unidades apareadas:
- Each lot keeps its own padrón and is calculated independently
- Party-wall side: 0 m setback (shared boundary)
- Free lateral: standard setback
- Show combined sketch with both units and the party wall indicated
- Total built area = sum of individual FOTs

## Scenario C: Unificación (englobamiento into single padrón)

Calculate the envelope for the merged lot:
- Combined area for occupation factor interpolation
- Eliminated internal setbacks (shared boundary disappears)
- New combined dimensions and frontage
- Check if the larger area unlocks new building types (bloque bajo at 1,200 m², edificación baja at 2,000 m², etc.)
- Show unified buildable sketch

## Comparison

| Parameter | Individual (×N) | Apareadas | Unified |
|-----------|-----------------|-----------|---------|
| Total area | ... m² | ... m² | ... m² |
| FOS (m²) | ... | ... | ... |
| FOT (m²) | ... | ... | ... |
| Max height | ... | ... | ... |
| Building types | ... | ... | ... |
| Setback efficiency | ... | ... | ... |

## Recommendation
Which scenario offers the best development potential, considering:
- Total buildable area (FOT)
- Layout flexibility (footprint shape and setback efficiency)
- Building types unlocked
- Administrative complexity (englobamiento requires Catastro procedure)
```

## Notes

- The TONE is Volume V of the Digesto Departamental de Maldonado
- Normativa files are organized by Título/Capítulo/Sector following the digesto structure
- Zone-specific rules override general sector rules
- When in doubt about zone boundaries, always ask the user — zone determination is the most critical step
- Occupation factors between defined area ranges should be linearly interpolated

### Phase 2 schema + scenario engine (April 2026)

`datos/tone-zones.json` carries a `tipologias[]` array per subzone:

```json
"2.3": {                               // MALDONADO Barrio Jardín
  "tipologias": [
    { "codigo": "bloque_bajo",  "thresholds": { "area_min_m2": 450,  "frente_min_m": 14 }, "altura_m": 13.60, "FOT_pct": 180, "retiros": {...} },
    { "codigo": "bloque_medio", "thresholds": { "area_min_m2": 1000, "frente_min_m": 30 }, "altura_m": 28,    "FOT_pct": 290, "retiros": {...} }
  ],
  "_data_quality": "verified"
}
```

Canonical tipología codes: `unidad_aislada`, `unidad_apareada`, `edificacion_baja`, `bloque_bajo_9m`, `bloque_bajo_12m`, `bloque_bajo`, `bloque_medio`, `bloque_alto`, `conjunto_unidades`, `conjunto_bloques`, `torre_media`, `torre_alta`, `hotelero`.

Engine: `normativa/scenarios.py` exposes `applicable_tipologias(zone, area_m2, frente_m, es_manzana_entera=False)` — a pure function returning the filtered tipologías.

Data-quality levels drive both the analysis and any UI warnings:
- **verified** — full source citation
- **partial** — some fields null; flag for verification
- **estimated** — inferred from similar zones
- **pending** — source not transcribed; avoid committing to numbers
- **conditional** — applies only under condition (see `_applicability_note`); confirm with user before applying

Extraction pipeline: `extract-tipologias.py` + `merge-tipologias.py` (with AI review per titulo). See `estudios/phase2-extraction-report-2026-04-24.md` for coverage snapshot and human review items.

### Multi-lot notes
- **Apareadas** (party wall): each lot retains its own padrón and is calculated independently; the shared boundary has 0 m setback; the TONE permits this wherever "unidades apareadas" are listed as an allowed building type
- **Unificación / englobamiento**: merging padrones at Catastro creates a single lot; all parameters (FOS, FOT, setbacks, building types) are recalculated on the unified area; the internal shared boundary disappears entirely
- **Key thresholds** are now data-driven per zone — read from each tipología's `thresholds.area_min_m2` and `thresholds.frente_min_m`. Classic examples: 1,000 m² (conjunto), 1,200 m² (Bloque Bajo 9 m), 2,000 m² + 30 m frente (Bloque Bajo 12 m / Edificación Baja per Maldonado 1.4), 450 m² + 14 m (Bloque Bajo per MALDONADO 2.3), 1,000 m² + 30 m (Bloque Medio per MALDONADO 2.3). When combining lots, re-run `applicable_tipologias` on the merged (area, frente) to see which tipologías unlock
- When lots span different zones (rare for adjoining lots), each portion must comply with its own zone's parameters — flag this as a constraint
