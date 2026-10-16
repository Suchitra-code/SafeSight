"""
PDF Report Generation Service for SafeSight AI.
Builds professional A4 PDF compliance reports using ReportLab with embedded
Matplotlib statistical charts, executive summaries, status distributions,
and detailed violation audit logs with automatic page numbering.
"""
import os
import uuid
import logging
from datetime import datetime
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

import config
from app.services import analytics, violation_service

logger = logging.getLogger(__name__)


class NumberedCanvas(canvas.Canvas):
    """Custom canvas that calculates total page count dynamically for page numbering."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#64748B"))

        # Footer
        footer_text = "SafeSight AI – AI-Powered PPE Safety Analytics Platform"
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawString(54, 36, footer_text)
        self.drawRightString(A4[0] - 54, 36, page_text)

        # Thin rule line above footer
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, 50, A4[0] - 54, 50)

        self.restoreState()


def _generate_report_charts(v_by_type: dict, time_series: dict, v_by_status: dict) -> str:
    """Generates a composite 3-panel statistical figure and saves it as a temporary PNG."""
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.2), dpi=200)
    fig.patch.set_facecolor("#FFFFFF")

    # Chart 1: Violations by Type (Bar)
    labels = ["Helmet", "Vest", "Goggles", "Other"]
    vals = [v_by_type.get("helmet", 0), v_by_type.get("vest", 0),
            v_by_type.get("goggles", 0), v_by_type.get("other", 0)]
    bar_colors = ["#EF4444", "#F59E0B", "#3B82F6", "#8B5CF6"]

    ax1 = axes[0]
    ax1.set_facecolor("#F8FAFC")
    bars = ax1.bar(labels, vals, color=bar_colors, width=0.55, edgecolor="#E2E8F0")
    ax1.set_title("Violations by Type", fontsize=10, fontweight="bold", color="#1E293B", pad=8)
    ax1.tick_params(colors="#64748B", labelsize=8)
    ax1.grid(axis="y", linestyle="--", alpha=0.4)
    for bar in bars:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., h + 0.5, f"{int(h)}",
                 ha="center", va="bottom", fontsize=8, color="#1E293B", fontweight="bold")

    # Chart 2: 21-Day Trend (Line)
    ax2 = axes[1]
    ax2.set_facecolor("#F8FAFC")
    dates = time_series.get("dates", [])
    # Subsample if too many points
    step = max(1, len(dates) // 7)
    x_indices = list(range(len(dates)))
    total_daily = [
        time_series["helmet"][i] + time_series["vest"][i] +
        time_series["goggles"][i] + time_series["other"][i]
        for i in range(len(dates))
    ] if dates else [0]
    ax2.plot(x_indices, total_daily, color="#F97316", marker="o", linewidth=2, markersize=3.5)
    ax2.set_title("Incident Trend Over Time", fontsize=10, fontweight="bold", color="#1E293B", pad=8)
    ax2.tick_params(colors="#64748B", labelsize=7)
    ax2.grid(True, linestyle="--", alpha=0.4)
    if dates:
        ax2.set_xticks(x_indices[::step])
        ax2.set_xticklabels([dates[i][-5:] for i in x_indices[::step]], rotation=30)

    # Chart 3: Status Distribution (Donut)
    ax3 = axes[2]
    status_keys = list(v_by_status.keys())
    status_vals = list(v_by_status.values())
    if sum(status_vals) == 0:
        status_keys = ["No Data"]
        status_vals = [1]
        donut_colors = ["#CBD5E1"]
    else:
        donut_colors = ["#3B82F6", "#F59E0B", "#EF4444", "#94A3B8", "#10B981"]

    ax3.pie(status_vals, labels=status_keys, colors=donut_colors[:len(status_keys)],
            autopct="%1.0f%%" if sum(status_vals) > 0 else "", startangle=140,
            textprops={"fontsize": 7, "color": "#1E293B"}, wedgeprops=dict(width=0.45, edgecolor="w"))
    ax3.set_title("Status Resolution", fontsize=10, fontweight="bold", color="#1E293B", pad=8)

    plt.tight_layout()
    chart_filename = f"chart_{uuid.uuid4().hex[:8]}.png"
    chart_path = os.path.join(config.REPORT_FOLDER, chart_filename)
    fig.savefig(chart_path, format="png", bbox_inches="tight")
    plt.close(fig)

    return chart_path


def generate_report(date_from: Optional[str] = None, date_to: Optional[str] = None,
                    camera: Optional[str] = None, include_charts: bool = True) -> str:
    """
    Generates a PDF compliance report and returns the full path to the generated PDF.
    """
    os.makedirs(config.REPORT_FOLDER, exist_ok=True)
    report_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"SafeSight_Report_{report_id}.pdf"
    pdf_path = os.path.join(config.REPORT_FOLDER, pdf_filename)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0B1B3F")
    )
    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748B")
    )
    section_h2 = ParagraphStyle(
        "SectionH2",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#0B1B3F"),
        spaceBefore=14,
        spaceAfter=6
    )
    cell_style = ParagraphStyle(
        "Cell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1E293B")
    )
    cell_bold = ParagraphStyle(
        "CellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1E293B")
    )

    story = []

    # 1. Header & Title Block
    header_data = [
        [
            Paragraph("<b>SAFESIGHT AI</b><br/><font color='#F97316'>PPE Safety Violation & Compliance Audit Report</font>", title_style),
            Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}<br/>"
                      f"<b>Range:</b> {date_from or 'All Available'} to {date_to or 'Present'}<br/>"
                      f"<b>Facility / Camera:</b> {camera or 'All Cameras'}", subtitle_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[315, 200])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LINEBELOW", (0, 0), (-1, -1), 1.5, colors.HexColor("#F97316"))
    ]))
    story.append(header_table)
    story.append(Spacer(1, 12))

    # 2. Executive Summary Metrics
    kpi = analytics.get_kpi_summary(date_from, date_to, camera)
    total_workers = kpi["total_people"]
    safe_workers = kpi["safe_count"]
    unsafe_workers = kpi["unsafe_count"]
    comp_rate = kpi["compliance_percent"]
    total_v = kpi["total_violations"]

    summary_data = [
        ["Total People Detected", "Safe Workers", "Unsafe Workers", "Compliance Rate", "Total Violations"],
        [f"{total_workers:,}", f"{safe_workers:,}", f"{unsafe_workers:,}", f"{comp_rate:.1f}%", f"{total_v}"]
    ]
    summary_table = Table(summary_data, colWidths=[103, 103, 103, 103, 103])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B1B3F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F8FAFC")),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 13),
        ("TEXTCOLOR", (3, 1), (3, 1), colors.HexColor("#22C55E") if comp_rate >= 90 else colors.HexColor("#EF4444")),
        ("TEXTCOLOR", (4, 1), (4, 1), colors.HexColor("#EF4444")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6)
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 14))

    # 3. Violation Breakdown Table
    v_by_type = analytics.get_violations_by_type(date_from, date_to)
    tot = max(1, v_by_type["total"])
    type_data = [
        ["PPE Category", "Severity", "Violation Count", "Percentage of Total", "Risk Level"],
        ["Hardhat / Helmet", "HIGH", str(v_by_type["helmet"]), f"{(v_by_type['helmet']/tot)*100:.1f}%", "Critical Head Trauma Hazard"],
        ["Safety Vest", "MEDIUM", str(v_by_type["vest"]), f"{(v_by_type['vest']/tot)*100:.1f}%", "Reduced Worker Visibility"],
        ["Safety Goggles", "MEDIUM", str(v_by_type["goggles"]), f"{(v_by_type['goggles']/tot)*100:.1f}%", "Eye Injury / Foreign Particle"],
        ["Other / Restricted Area", "LOW", str(v_by_type["other"]), f"{(v_by_type['other']/tot)*100:.1f}%", "Perimeter Trespass / Protocol"],
        ["TOTAL ALL CATEGORIES", "—", str(v_by_type["total"]), "100.0%", "—"]
    ]
    type_table = Table(type_data, colWidths=[135, 65, 85, 100, 130])
    type_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (3, -1), "CENTER"),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#FEF2F2")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#FFFBEB")),
        ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#EFF6FF")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F1F5F9")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4)
    ]))
    story.append(Paragraph("<b>1. Violation Breakdown & Severity Analysis</b>", section_h2))
    story.append(type_table)
    story.append(Spacer(1, 10))

    # 4. Embedded Charts
    if include_charts:
        time_series = analytics.get_timeseries(date_from, date_to, camera)
        stats = violation_service.get_violation_stats()
        chart_png = _generate_report_charts(v_by_type, time_series, stats.get("by_status", {}))
        story.append(Paragraph("<b>2. Visual Analytics & Incident Trends</b>", section_h2))
        story.append(Image(chart_png, width=7.2 * inch, height=2.0 * inch))
        story.append(Spacer(1, 10))

    # 5. Status Resolution Table
    stats = violation_service.get_violation_stats()
    by_stat = stats.get("by_status", {})
    status_summary = [
        ["Status", "Count", "Description"],
        ["Detected", str(by_stat.get("detected", 0)), "Automatically identified by YOLOv8 vision pipeline"],
        ["Pending Review", str(by_stat.get("pending review", 0)), "Queued for safety officer verification"],
        ["Confirmed", str(by_stat.get("confirmed", 0)), "Verified safety protocol breach requiring corrective action"],
        ["Dismissed", str(by_stat.get("dismissed", 0)), "False positive or authorized exception granted"],
        ["Resolved", str(by_stat.get("resolved", 0)), "Correction applied and verified on site"]
    ]
    status_table = Table(status_summary, colWidths=[120, 75, 320])
    status_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4)
    ]))
    story.append(Paragraph("<b>3. Resolution Workflow Status</b>", section_h2))
    story.append(status_table)
    story.append(Spacer(1, 14))

    # 6. Detailed Violations Log (Automatic Page Breaks)
    story.append(Paragraph("<b>4. Detailed Audit Log (Recent Incidents)</b>", section_h2))
    recent_violations = violation_service.get_violations(
        {"date_from": date_from, "date_to": date_to, "camera": camera}, page=1, per_page=40
    )

    log_headers = ["ID", "Type", "Severity", "Camera / Zone", "Detected At", "Status", "Confidence"]
    log_rows = [log_headers]

    for item in recent_violations.get("items", []):
        log_rows.append([
            str(item["id"]),
            item["violation_type"].upper(),
            item["severity"],
            Paragraph(f"{item['camera_name']}<br/><font color='#64748B'>{item['location']}</font>", cell_style),
            str(item["detected_at"])[:16],
            item["status"].title(),
            f"{float(item.get('confidence', 0.9))*100:.0f}%"
        ])

    log_table = Table(log_rows, colWidths=[35, 75, 60, 155, 95, 65, 30])
    log_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B1B3F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("ALIGN", (0, 0), (2, -1), "CENTER"),
        ("ALIGN", (5, 0), (6, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4)
    ]))
    story.append(log_table)

    # Build PDF with dynamic footer numbering
    doc.build(story, canvasmaker=NumberedCanvas)
    return pdf_path
