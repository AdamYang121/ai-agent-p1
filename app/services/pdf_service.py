"""Generate a professional PDF quote using ReportLab."""

from io import BytesIO
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)


BRAND_COLOR = colors.HexColor("#1B4F72")
ACCENT_COLOR = colors.HexColor("#2E86C1")
LIGHT_GRAY = colors.HexColor("#F2F3F4")


def generate_quote_pdf(project, estimate, cover_letter: str) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    story = []

    # --- Header ---
    header_style = ParagraphStyle("header", fontSize=22, textColor=BRAND_COLOR,
                                   spaceAfter=4, fontName="Helvetica-Bold")
    sub_style = ParagraphStyle("sub", fontSize=10, textColor=colors.gray,
                                spaceAfter=2, fontName="Helvetica")
    story.append(Paragraph("Northwest Remodel Co.", header_style))
    story.append(Paragraph("Seattle, WA · Licensed & Insured · (206) 555-0100", sub_style))
    story.append(HRFlowable(width="100%", thickness=2, color=BRAND_COLOR, spaceAfter=12))

    # --- Quote Info ---
    valid_until = (datetime.utcnow() + timedelta(days=estimate.valid_days)).strftime("%B %d, %Y")
    info_data = [
        ["Quote #:", f"Q-{estimate.id:04d}", "Date:", datetime.utcnow().strftime("%B %d, %Y")],
        ["Client:", project.homeowner_name or "—", "Valid Until:", valid_until],
        ["Address:", project.address or "—", "", ""],
    ]
    info_table = Table(info_data, colWidths=[1.1 * inch, 2.8 * inch, 1.0 * inch, 1.9 * inch])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), BRAND_COLOR),
        ("TEXTCOLOR", (2, 0), (2, -1), BRAND_COLOR),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 12))

    # --- Cover Letter ---
    body_style = ParagraphStyle("body", fontSize=9, leading=14, spaceAfter=8)
    story.append(Paragraph(cover_letter.replace("\n", "<br/>"), body_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=10))

    # --- Line Items Table ---
    heading_style = ParagraphStyle("heading", fontSize=12, textColor=BRAND_COLOR,
                                    fontName="Helvetica-Bold", spaceAfter=8)
    story.append(Paragraph("Detailed Estimate", heading_style))

    col_headers = ["Description", "Category", "Notes", "Amount"]
    rows = [col_headers]
    current_category = None

    for item in estimate.line_items:
        cat = item.get("category", "")
        if cat != current_category:
            current_category = cat
            rows.append([Paragraph(f"<b>{cat}</b>", ParagraphStyle("cat", fontSize=8,
                         textColor=BRAND_COLOR, fontName="Helvetica-Bold")),
                         "", "", ""])
        rows.append([
            item["name"],
            "",
            Paragraph(item.get("notes", ""), ParagraphStyle("note", fontSize=7,
                      textColor=colors.gray)),
            f"${item['cost']:,.0f}",
        ])

    line_table = Table(rows, colWidths=[2.3 * inch, 0 * inch, 3.0 * inch, 1.0 * inch])
    line_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_COLOR),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(line_table)
    story.append(Spacer(1, 14))

    # --- Totals ---
    totals_data = [
        ["Subtotal", f"${estimate.subtotal:,.0f}"],
        ["GC Overhead & Profit (20%)", f"${estimate.gc_markup:,.0f}"],
        ["Seattle Sales Tax (10.25% on materials)", f"${estimate.sales_tax:,.0f}"],
        ["TOTAL", f"${estimate.total:,.0f}"],
    ]
    totals_table = Table(totals_data, colWidths=[5.5 * inch, 1.2 * inch])
    totals_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 3), (-1, 3), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTSIZE", (0, 3), (-1, 3), 11),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TEXTCOLOR", (0, 3), (-1, 3), BRAND_COLOR),
        ("LINEABOVE", (0, 3), (-1, 3), 1.5, BRAND_COLOR),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(totals_table)

    # --- GC Notes ---
    if estimate.gc_notes:
        story.append(Spacer(1, 14))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=8))
        story.append(Paragraph("Notes & Exclusions", heading_style))
        story.append(Paragraph(estimate.gc_notes.replace("\n", "<br/>"), body_style))

    # --- Footer ---
    story.append(Spacer(1, 20))
    footer_style = ParagraphStyle("footer", fontSize=7, textColor=colors.gray,
                                   alignment=1, leading=10)
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))
    story.append(Paragraph(
        "This quote is valid for 30 days from the date issued. Prices subject to change after expiration.<br/>"
        "Northwest Remodel Co. · Seattle, WA · License #NORTHWR123AB",
        footer_style
    ))

    doc.build(story)
    return buffer.getvalue()
