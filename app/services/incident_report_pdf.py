"""
Incident Investigation PDF Report Service for SafeSight AI - Milestone 3.
Generates an executive-ready investigation summary PDF using ReportLab.
"""
import os
import logging
from datetime import datetime
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

import config
from app.db import execute_query

logger = logging.getLogger(__name__)


def generate_report(run_id: str) -> Optional[str]:
    """
    Generates a PDF incident report for a completed or approved investigation run.
    Returns the relative path inside reports/ or None on error.
    """
    try:
        runs = execute_query(
            "SELECT * FROM investigation_runs WHERE run_id = %s",
            (run_id,),
            fetch=True
        )
        if not runs:
            logger.warning(f"Investigation run {run_id} not found for PDF generation.")
            return None

        run_data = dict(runs[0])
        v_id = run_data.get("violation_id")
        v_rows = execute_query("SELECT * FROM violations WHERE id = %s", (v_id,), fetch=True)
        v_data = dict(v_rows[0]) if v_rows else {}

        filename = f"investigation_{run_id}.pdf"
        filepath = os.path.join(config.REPORT_FOLDER, filename)

        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            leftMargin=40,
            rightMargin=40,
            topMargin=40,
            bottomMargin=40
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "InvTitle",
            parent=styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#FF6B4A"),
            spaceAfter=10
        )
        subtitle_style = ParagraphStyle(
            "InvSubtitle",
            parent=styles["Normal"],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#9A6B7E"),
            spaceAfter=15
        )
        h2_style = ParagraphStyle(
            "InvH2",
            parent=styles["Heading2"],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#4A1D2F"),
            spaceBefore=12,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            "InvBody",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#4A1D2F")
        )

        elements = []

        # Header
        elements.append(Paragraph("🛡️ SafeSight AI — Incident Investigation Report", title_style))
        elements.append(Paragraph(
            f"Run ID: <b>{run_id}</b> | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            subtitle_style
        ))
        elements.append(Spacer(1, 10))

        # Overview Table
        overview_data = [
            ["Investigation Status", run_data.get("status", "N/A").upper()],
            ["Risk Level", run_data.get("risk_level", "LOW")],
            ["Risk Score", str(run_data.get("risk_score", 1))],
            ["Violation ID", f"#{v_id}"],
            ["Violation Type", v_data.get("violation_type", "PPE Infraction")],
            ["Camera / Location", f"{v_data.get('camera', 'Cam 01')} ({v_data.get('location', 'Site')})"],
            ["Detected At", str(v_data.get("detected_at", "N/A"))],
            ["Approval Status", run_data.get("approval_status", "pending").upper()]
        ]

        t_overview = Table(overview_data, colWidths=[160, 340])
        t_overview.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#FFE3D3")),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#4A1D2F")),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#F3D9CF")),
        ]))
        elements.append(t_overview)
        elements.append(Spacer(1, 15))

        # Investigation Summary
        elements.append(Paragraph("Executive Summary & Visual Intelligence", h2_style))
        summary_text = run_data.get("summary") or "Visual detection confirmed PPE non-compliance in monitored camera zone."
        elements.append(Paragraph(summary_text, body_style))
        elements.append(Spacer(1, 10))

        # AI Recommendations
        elements.append(Paragraph("Recommended Corrective Actions & Policies", h2_style))
        recs_text = run_data.get("recommendations") or "Verify worker equipment assignment and review safety protocol manual."
        elements.append(Paragraph(recs_text.replace("\n", "<br/>"), body_style))
        elements.append(Spacer(1, 10))

        # Supervisor Review & Sign-off
        elements.append(Paragraph("Supervisor Review & Decision", h2_style))
        notes_text = run_data.get("supervisor_notes") or "Pending supervisor review or approved via workflow."
        elements.append(Paragraph(f"<b>Supervisor Notes:</b> {notes_text}", body_style))
        elements.append(Spacer(1, 20))

        # Build Document
        doc.build(elements)
        logger.info(f"Generated incident report PDF at {filepath}")
        return filename
    except Exception as e:
        logger.error(f"Failed to generate incident PDF: {e}")
        return None
