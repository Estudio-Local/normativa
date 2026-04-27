#!/usr/bin/env python3
"""
/informe renderer — normativa.v1.json → printable A4 HTML report.

Pure stdlib. No external dependencies.

Usage:
  python3 render.py <input.normativa.v1.json> [<output.html>]

If <output.html> is omitted, writes alongside the input with `.informe.html` suffix.
"""

import sys
import os
import json
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_SCHEMA = "estudio-local.normativa.v1"

SPANISH_MONTHS = [
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
]


# ───────── helpers ─────────

def fmt_m2(n):
    if n is None:
        return "—"
    try:
        n = int(round(float(n)))
    except (TypeError, ValueError):
        return "—"
    return f"{n:,}".replace(",", ".") + " m²"


def fmt_m(n):
    if n is None:
        return "—"
    try:
        f = float(n)
    except (TypeError, ValueError):
        return "—"
    if f == int(f):
        return f"{int(f)} m"
    return f"{f:.1f}".replace(".", ",") + " m"


def fmt_pct(n):
    if n is None:
        return "—"
    try:
        return f"{int(round(float(n)))}%"
    except (TypeError, ValueError):
        return "—"


def fmt_int(n):
    if n is None:
        return "—"
    try:
        return f"{int(round(float(n))):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "—"


def fmt_es_date(iso_string):
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return iso_string or "—"
    return f"{dt.day} {SPANISH_MONTHS[dt.month - 1]} {dt.year}"


def short_id(envelope):
    import hashlib
    seed = "|".join([
        ",".join(envelope.get("selection", {}).get("padrones", [])),
        envelope.get("selection", {}).get("locality", ""),
        (envelope.get("generated_at") or "")[:10],
    ])
    return hashlib.sha1(seed.encode()).hexdigest()[:8]


def regimen_label(r):
    return {
        "comun": "PC (Común)",
        "ph": "PH (Propiedad Horizontal)",
        "otro": "Otro",
        "mixed": "Mixto",
    }.get(r, r or "—")


def esc(s):
    if s is None:
        return ""
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


# ───────── builders ─────────

def build_lots_rows(lots, total_area, total_frente):
    rows = []
    for lot in lots:
        rows.append(
            f"<tr>"
            f"<td>{esc(lot.get('padron'))}</td>"
            f"<td>{esc(lot.get('manzana'))}</td>"
            f"<td>{fmt_m2(lot.get('area_m2'))}</td>"
            f"<td>{fmt_m(lot.get('frente_m'))}</td>"
            f"<td>{esc(regimen_label(lot.get('regimen')))}</td>"
            f"</tr>"
        )
    rows.append(
        f'<tr style="border-top:2px solid var(--rule);">'
        f'<td colspan="2" style="font-weight:700;">Total — predio'
        f'{" unificado" if len(lots) > 1 else ""}</td>'
        f'<td style="font-weight:700;">{fmt_m2(total_area)}</td>'
        f'<td style="font-weight:700;">{fmt_m(total_frente)}</td>'
        f'<td>—</td>'
        f'</tr>'
    )
    return "\n".join(rows)


def build_zone_rows(zone, sources):
    decretos = ", ".join(sources.get("decretos", [])) or zone.get("decreto", "—")
    rows = [
        f'<tr><td>Localidad</td><td>{esc(zone.get("locality_name") or "—")}</td></tr>',
        f'<tr><td>Sector / Zona</td><td>Zona {esc(zone.get("code"))} {esc(zone.get("name") or "")}</td></tr>',
        f'<tr><td>Decreto vigente</td><td>{esc(decretos)}</td></tr>',
        f'<tr><td>Calidad de datos</td><td>{esc(zone.get("data_quality") or "—")}</td></tr>',
        f'<tr><td>Última actualización</td><td>{esc(sources.get("last_updated") or "—")}</td></tr>',
    ]
    return "\n".join(rows)


def build_scenario_grid(scenarios, recommendation):
    rec_id = (recommendation or {}).get("scenario_id")
    cols = scenarios
    if not cols:
        return '<p class="note">Sin escenarios evaluados.</p>'

    def cell(s, key, formatter=esc):
        val = s.get("envelope", {}).get(key)
        return formatter(val)

    def col_class(s):
        return ' class="col-recommended"' if s.get("id") == rec_id else ""

    def header(s):
        star = " ★" if s.get("id") == rec_id else ""
        return f'<th{col_class(s)}>{esc(s.get("id"))} — {esc(s.get("label") or "")}{star}</th>'

    rows = ["<thead><tr><th></th>" + "".join(header(s) for s in cols) + "</tr></thead>"]
    body = ["<tbody>"]

    def row(label, cell_fn, row_class=""):
        cells = "".join(f'<td{col_class(s)}>{cell_fn(s)}</td>' for s in cols)
        body.append(f'<tr{row_class}><td>{label}</td>{cells}</tr>')

    row("Tipología", lambda s: esc((s.get("tipologia") or {}).get("nombre", "—")))
    row("Altura", lambda s: fmt_m(cell(s, "altura_m", lambda v: v)))
    row("FOS", lambda s: fmt_pct(cell(s, "FOS_pct", lambda v: v)) + " · " +
                         fmt_m2(cell(s, "area_ocupacion_m2", lambda v: v)))
    row("FOT", lambda s: fmt_pct(cell(s, "FOT_pct", lambda v: v)))
    row("Total edificable", lambda s: fmt_m2(cell(s, "area_edificable_m2", lambda v: v)),
        row_class=' class="headline"')
    row("Viviendas estimadas", lambda s: fmt_int(cell(s, "viviendas_estimadas", lambda v: v)))

    body.append("</tbody>")
    return f'<table class="scenario-grid">{"".join(rows)}{"".join(body)}</table>'


def build_envelope_kv(env):
    rows = [
        f'<tr><td>FOS</td><td>{fmt_pct(env.get("FOS_pct"))} · {fmt_m2(env.get("area_ocupacion_m2"))} en PB</td></tr>',
        f'<tr><td>FOT</td><td>{fmt_pct(env.get("FOT_pct"))} · {fmt_m2(env.get("area_edificable_m2"))} edificable total</td></tr>',
        f'<tr><td>Altura máxima</td><td>{fmt_m(env.get("altura_m"))}</td></tr>',
        f'<tr><td>Viviendas estimadas</td><td>{fmt_int(env.get("viviendas_estimadas"))}</td></tr>',
    ]
    return "\n".join(rows)


def build_retiros_rows(ret):
    if not ret:
        return '<tr><td colspan="3">Sin retiros definidos.</td></tr>'
    rows = []
    if ret.get("frontal_m") is not None:
        rows.append(f'<tr><td>Frente</td><td>{fmt_m(ret["frontal_m"])}</td><td>—</td></tr>')
    if ret.get("lateral_m") is not None:
        rows.append(f'<tr><td>Lateral</td><td>{fmt_m(ret["lateral_m"])}</td><td>Ambos lados</td></tr>')
    if ret.get("fondo_m") is not None:
        rows.append(f'<tr><td>Fondo</td><td>{fmt_m(ret["fondo_m"])}</td><td>—</td></tr>')
    if ret.get("entre_volumenes_m") is not None:
        rows.append(f'<tr><td>Entre volúmenes</td><td>{fmt_m(ret["entre_volumenes_m"])}</td><td>—</td></tr>')
    return "\n".join(rows) or '<tr><td colspan="3">Sin retiros definidos.</td></tr>'


def build_tipologias_list(scenario, zone):
    habilitadas = set(scenario.get("tipologias_habilitadas") or [])
    catalog = zone.get("tipologias_catalog") or []
    if not habilitadas:
        return '<li><span class="check">—</span><span class="name">Sin tipologías habilitadas listadas.</span></li>'
    items = []
    for t in catalog:
        if t.get("codigo") not in habilitadas:
            continue
        nombre = esc(t.get("nombre") or t.get("codigo"))
        th = t.get("thresholds") or {}
        bits = []
        if th.get("area_min_m2"):
            bits.append(f'≥ {fmt_int(th["area_min_m2"])} m²')
        if th.get("frente_min_m"):
            bits.append(f'+ {fmt_m(th["frente_min_m"])} frente')
        threshold = " · ".join(bits) or "—"
        marker = " · seleccionado" if t.get("codigo") == (scenario.get("tipologia") or {}).get("codigo") else ""
        items.append(
            f'<li><span class="check">✓</span>'
            f'<span class="name">{nombre}</span>'
            f'<span class="threshold">{threshold}{marker}</span></li>'
        )
    return "\n".join(items) or '<li><span class="check">—</span><span class="name">—</span></li>'


def build_normativa_rows(sources):
    decretos = sources.get("decretos") or []
    rows = []
    for d in decretos:
        rows.append(f'<tr><td>{esc(d)}</td><td>Vigente</td><td>TONE — Volumen V Digesto Departamental</td></tr>')
    if not rows:
        rows.append('<tr><td colspan="3">Sin decretos listados.</td></tr>')
    return "\n".join(rows)


def build_caveats_html(caveats):
    if not caveats:
        return ""
    items = "\n".join(f"<li>{esc(c)}</li>" for c in caveats)
    return f'<h2 class="section">Advertencias</h2>\n<ul class="disclaimer">{items}</ul>'


# ───────── main ─────────

def render(envelope, template):
    selection = envelope.get("selection") or {}
    zone = envelope.get("zone") or {}
    scenarios = envelope.get("scenarios") or []
    recommendation = envelope.get("recommendation") or {}
    caveats = envelope.get("caveats") or []
    sources = envelope.get("sources") or {}

    zone = dict(zone)
    zone["locality_name"] = selection.get("locality_name") or selection.get("locality")

    rec_id = recommendation.get("scenario_id")
    rec_scenario = next((s for s in scenarios if s.get("id") == rec_id), None)
    if rec_scenario is None and scenarios:
        rec_scenario = scenarios[0]
    if rec_scenario is None:
        rec_scenario = {"label": "—", "envelope": {}, "retiros": {}, "tipologia": {}}

    n_lots = len(selection.get("lots") or selection.get("padrones") or [])
    adjacency_desc = (
        f"{n_lots} lote{'s' if n_lots != 1 else ''} adyacente{'s' if n_lots != 1 else ''}"
        if selection.get("adjacent")
        else f"{n_lots} lote{'s' if n_lots != 1 else ''} no contiguos"
    )

    subs = {
        "{{ANALYSIS_ID}}":          short_id(envelope),
        "{{DOC_DATE}}":             fmt_es_date(envelope.get("generated_at")),
        "{{SKILL_VERSION}}":        envelope.get("skill_version") or "—",
        "{{LOT_COUNT}}":            f"{n_lots} lote{'s' if n_lots != 1 else ''}",
        "{{ZONE_HEADLINE}}":        f'Zona {esc(zone.get("code"))} {esc(zone.get("name") or "")}'.strip(),
        "{{LOCALITY_NAME}}":        esc(zone.get("locality_name") or "—"),
        "{{ADJACENCY_DESC}}":       esc(adjacency_desc),
        "{{PADRONES_RANGE}}":       esc(", ".join(selection.get("padrones") or []) or "—"),

        "{{LOTS_TABLE_ROWS}}":      build_lots_rows(
                                        selection.get("lots") or [],
                                        selection.get("area_total_m2"),
                                        selection.get("frente_estimado_m"),
                                    ),
        "{{LOTS_NOTE}}":            esc(
                                        "Adyacencia confirmada (Turf union)."
                                        if selection.get("adjacent") else
                                        "⚠ Lotes no contiguos — los escenarios de unión no aplican."
                                    ) + (
                                        f" Régimen mayoritario: {regimen_label(selection.get('regimen'))}."
                                    ),

        "{{ZONE_TABLE_ROWS}}":      build_zone_rows(zone, sources),
        "{{ZONE_DATA_QUALITY}}":    esc(zone.get("data_quality") or "—"),

        "{{SCENARIO_GRID}}":        build_scenario_grid(scenarios, recommendation),
        "{{RECOMMENDATION_HEADLINE}}": esc(
                                        (rec_scenario.get("headline") or "—")
                                        if recommendation.get("scenario_id") else
                                        "Sin escenario recomendado — ver advertencias."
                                    ),
        "{{RECOMMENDATION_RATIONALE}}": esc(recommendation.get("rationale") or ""),
        "{{RECOMMENDATION_TRADEOFFS}}": "\n".join(
                                        f"<li>{esc(t)}</li>"
                                        for t in (recommendation.get("tradeoffs") or [])
                                    ) or "<li>—</li>",

        "{{REC_SCENARIO_LABEL}}":   esc(rec_scenario.get("label") or rec_scenario.get("id") or "—"),
        "{{REC_SCENARIO_ID}}":      esc(rec_scenario.get("id") or "—"),
        "{{REC_ENVELOPE_ROWS}}":    build_envelope_kv(rec_scenario.get("envelope") or {}),
        "{{REC_RETIROS_ROWS}}":     build_retiros_rows(rec_scenario.get("retiros") or {}),
        "{{REC_GALIBO_NOTE}}":      esc(rec_scenario.get("notes") or ""),
        "{{REC_TIPOLOGIAS_LIST}}":  build_tipologias_list(rec_scenario, zone),
        "{{REC_PROGRAMA}}":         esc(rec_scenario.get("programa") or "—"),
        "{{REC_PLAZOS}}":           esc(rec_scenario.get("plazos") or "—"),

        "{{NORMATIVA_ROWS}}":       build_normativa_rows(sources),
        "{{SOURCES_LAST_UPDATED}}": esc(sources.get("last_updated") or "—"),

        "{{CAVEATS_BLOCK}}":        build_caveats_html(caveats),

        "{{GENERATOR_LINE}}":       f'/normativa v{esc(envelope.get("skill_version") or "—")} · '
                                    f'github.com/Estudio-Local/normativa',
    }

    out = template
    for k, v in subs.items():
        out = out.replace(k, v if isinstance(v, str) else str(v))
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(2)

    in_path = Path(sys.argv[1]).expanduser().resolve()
    if not in_path.is_file():
        print(f"error: input file not found: {in_path}", file=sys.stderr)
        sys.exit(1)

    out_path = (
        Path(sys.argv[2]).expanduser().resolve()
        if len(sys.argv) >= 3
        else in_path.with_suffix("").with_suffix(".informe.html")
    )

    with in_path.open() as f:
        envelope = json.load(f)

    schema = envelope.get("schema")
    if schema != REQUIRED_SCHEMA:
        print(
            f"error: expected schema={REQUIRED_SCHEMA!r}, got {schema!r}. "
            f"Bailing — render.py only knows v1.",
            file=sys.stderr,
        )
        sys.exit(1)

    template_path = Path(__file__).parent / "plantilla.html"
    template = template_path.read_text()

    html = render(envelope, template)
    out_path.write_text(html)
    print(f"wrote {out_path} ({out_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
