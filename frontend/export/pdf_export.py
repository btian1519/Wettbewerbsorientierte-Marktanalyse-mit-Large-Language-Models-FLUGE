"""Print-optimised PDF of the full results page (all details expanded).

Uses ReportLab Platypus so the document flows naturally across pages. Every
result is rendered with its complete detail table — the export is the
"all sections open" counterpart to the interactive page.
"""

from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from backend.dto import AnalysisResponse
from frontend.theme import COLORS
from shared.utils import format_eur, format_pax

_TEAL = colors.HexColor(COLORS["teal"])
_CARD = colors.HexColor(COLORS["card"])


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("FSTitle", parent=ss["Title"], textColor=_TEAL, fontSize=20, spaceAfter=4))
    ss.add(ParagraphStyle("FSMeta", parent=ss["Normal"], textColor=colors.grey, fontSize=9, spaceAfter=10))
    ss.add(ParagraphStyle("FSCard", parent=ss["Heading2"], textColor=_CARD, fontSize=13, spaceBefore=8, spaceAfter=2))
    return ss


def _detail_table(r) -> Table:
    rows = [
        ["Origin", f"{r.origin_name or r.origin_iata} ({r.origin_iata}) — {r.origin_country or r.origin_continent}"],
        ["Destination", f"{r.dest_name or r.dest_iata} ({r.dest_iata}) — {r.dest_country or r.dest_continent}"],
        ["Distance", f"{r.distance_km:,.0f} km"],
        ["Average price", f"EUR {r.avg_price_eur:,.0f} ({r.price_source})"],
        ["Total demand", f"{format_pax(r.demand)} pax/wk"],
        ["Total supply", f"{format_pax(r.total_supply)} seats/wk"],
        ["Supply share (selected airline)", f"{r.selected_airline_share * 100:.1f}%"],
        ["Active airlines on route", str(r.num_airlines)],
        ["Delta (demand - supply)", f"{format_pax(r.delta_pax)} pax"],
        ["Benefit", format_eur(r.benefit_eur)],
    ]
    t = Table(rows, colWidths=[70 * mm, 95 * mm])
    t.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#5a7c89")),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e6e8")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7f9fa")),
            ]
        )
    )
    return t


def build_results_pdf(response: AnalysisResponse, airline_label: str) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, topMargin=18 * mm, bottomMargin=16 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm, title="FlightScope AI Report",
    )
    ss = _styles()
    story = [
        Paragraph("FlightScope AI — " + response.title.rstrip(":"), ss["FSTitle"]),
        Paragraph(
            f"Airline: <b>{airline_label}</b> &nbsp;|&nbsp; Scope: <b>{response.scope}</b> "
            f"&nbsp;|&nbsp; Task: <b>{response.task.value}</b> &nbsp;|&nbsp; Week: <b>{response.week}</b><br/>"
            f"Generated: {response.generated_at:%Y-%m-%d %H:%M UTC} &nbsp;|&nbsp; "
            f"Routes considered: {response.stats.get('routes_considered', 'n/a')}",
            ss["FSMeta"],
        ),
    ]
    for r in response.results:
        story.append(
            Paragraph(
                f"{r.rank}. {r.origin_iata} &ndash; {r.dest_iata} "
                f"&nbsp;—&nbsp; Benefit {format_eur(r.benefit_eur)} "
                f"&nbsp;·&nbsp; {r.gap_label}: {format_pax(r.delta_pax)} pax",
                ss["FSCard"],
            )
        )
        story.append(_detail_table(r))
        story.append(Spacer(1, 6))

    doc.build(story)
    return buf.getvalue()
