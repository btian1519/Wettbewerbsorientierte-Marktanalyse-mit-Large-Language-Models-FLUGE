"""Print-optimised PDF of the full results page (all details expanded).

Uses ReportLab Platypus so the document flows naturally across pages. Every
result is rendered with its complete detail table — the export is the
"all sections open" counterpart to the interactive page.
"""

from __future__ import annotations

import html
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


_KEY_COLOR = colors.HexColor("#5a7c89")
_VAL_COLOR = colors.HexColor("#12303b")


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("FSTitle", parent=ss["Title"], textColor=_TEAL, fontSize=20, spaceAfter=4))
    ss.add(ParagraphStyle("FSMeta", parent=ss["Normal"], textColor=colors.grey, fontSize=9, spaceAfter=10))
    ss.add(ParagraphStyle("FSCard", parent=ss["Heading2"], textColor=_CARD, fontSize=13,
                          spaceBefore=10, spaceAfter=3, leading=16))
    # Table cell styles (Paragraphs wrap within the column — plain strings do not).
    ss.add(ParagraphStyle("FSKey", parent=ss["Normal"], textColor=_KEY_COLOR, fontSize=9, leading=12))
    ss.add(ParagraphStyle("FSVal", parent=ss["Normal"], textColor=_VAL_COLOR, fontSize=9, leading=12))
    ss.add(ParagraphStyle("FSValB", parent=ss["Normal"], textColor=_VAL_COLOR,
                          fontName="Helvetica-Bold", fontSize=9, leading=12))
    return ss


def _airport_line(name, iata, city, country, continent) -> str:
    """`Name (IATA) — City, Country — Region`, dropping any missing parts."""
    head = f"{name} ({iata})" if name else iata
    loc = ", ".join(p for p in (city, country) if p)
    return " — ".join(p for p in (head, loc, continent) if p)


def _detail_table(r, ss) -> Table:
    def key(text: str) -> Paragraph:
        return Paragraph(html.escape(str(text)), ss["FSKey"])

    def val(text: str, *, bold: bool = True) -> Paragraph:
        return Paragraph(html.escape(str(text)), ss["FSValB"] if bold else ss["FSVal"])

    rows = [
        [key("Origin"),
         val(_airport_line(r.origin_name, r.origin_iata, r.origin_city, r.origin_country, r.origin_continent),
             bold=False)],
        [key("Destination"),
         val(_airport_line(r.dest_name, r.dest_iata, r.dest_city, r.dest_country, r.dest_continent), bold=False)],
        [key("Distance"), val(f"{r.distance_km:,.0f} km")],
        [key("Average price"), val(f"EUR {r.avg_price_eur:,.0f}")],
        [key("Total demand"), val(f"{format_pax(r.demand)} pax/wk")],
        [key("Total supply"), val(f"{format_pax(r.total_supply)} seats/wk")],
        [key("Market share (selected airline)"), val(f"{r.selected_airline_share * 100:.1f}%")],
        [key("Active airlines on route"), val(str(r.num_airlines))],
        [key(r.gap_label), val(f"{format_pax(r.display_delta)} pax/wk")],
        [key("Benefit"), val(f"{format_eur(r.display_benefit)}/wk")],
    ]
    t = Table(rows, colWidths=[52 * mm, 118 * mm], hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
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
                f"&nbsp;—&nbsp; Benefit {format_eur(r.display_benefit)}/wk "
                f"&nbsp;·&nbsp; {r.gap_label}: {format_pax(r.display_delta)} pax/wk",
                ss["FSCard"],
            )
        )
        story.append(_detail_table(r, ss))
        story.append(Spacer(1, 8))

    doc.build(story)
    return buf.getvalue()
