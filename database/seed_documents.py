"""
Seed Demo Documents Generator for SafeSight AI - Milestone 2.
Generates realistic fictional PDF files using ReportLab:
- 3 Inspection Reports (1 table style, 1 paragraph style, 1 with missing helmet HIGH finding and open corrective actions).
- 2 Safety Manuals (PPE policy, numbered procedures for welding & confined space entry).
- 1 Standard Operating Procedure (SOP).
Loads them into the database, executes the document pipeline, and builds the knowledge index.
Run with: python database/seed_documents.py --reset
"""
import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Ensure parent directory is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import config
from app.db import execute_query, execute_insert, init_db, init_db_milestone2
from app.services import doc_pipeline


def generate_demo_files():
    """Generates the 6 realistic ReportLab PDF files on disk."""
    demo_dir = os.path.join(config.DOC_UPLOAD_FOLDER, "demo_files")
    os.makedirs(demo_dir, exist_ok=True)
    styles = getSampleStyleSheet()

    # Style modifications
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0B1B3F'),
        spaceAfter=12
    )
    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#F97316'),
        spaceBefore=10,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1E293B')
    )

    generated_docs = []

    # 1. Inspection Report 1 (Table Style - Site Compliance Audit)
    p1 = os.path.join(demo_dir, "Site_A_Monthly_Safety_Audit.pdf")
    doc1 = SimpleDocTemplate(p1, pagesize=letter)
    story1 = [
        Paragraph("SafeSight Inspection Report: Site A Monthly Audit", title_style),
        Paragraph("<b>Report ID:</b> SAF-2026-0881<br/><b>Inspection Date:</b> 2026-04-12<br/><b>Site Location:</b> Sector 4 Metro Extension<br/><b>Area / Zone:</b> Zone A - Fabrication Yard<br/><b>Inspector Name:</b> Marcus Vance<br/><b>Supervisor Name:</b> Elena Rostova<br/><b>Company:</b> Apex Structural Engineering<br/><b>Shift:</b> Day Shift<br/><b>Weather:</b> Clear, 28C", body_style),
        Spacer(1, 14),
        Paragraph("Inspection Findings & Observed Infractions", h2_style),
        Table([
            ["ID", "Finding Description", "Category", "Severity", "Corrective Action", "Responsible", "Due Date", "Status"],
            ["F-01", "Two scaffolding riggers observed without hardhats near hoist", "helmet", "HIGH", "Immediate halt, issue hardhats with chin straps", "M. Vance", "2026-04-14", "open"],
            ["F-02", "Worker operating angle grinder without protective goggles", "goggles", "HIGH", "Provide ANSI Z87.1 face shield and eye protection", "E. Rostova", "2026-04-13", "open"],
            ["F-03", "Worn and soiled reflective vest lacking retro-reflective tape", "vest", "LOW", "Issue replacement Class 2 hi-vis safety vest", "Site Store", "2026-04-20", "closed"],
            ["F-04", "Heavy lifting carried out with damaged fabric gloves", "gloves", "MEDIUM", "Replace with EN388 heavy-duty grip gloves", "Foreman Dave", "2026-04-16", "open"]
        ], style=[
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0B1B3F')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')])
        ]),
        Spacer(1, 14),
        Paragraph("Summary: Site overall compliance rating is 82%. Corrective actions must be verified within 48 hours.", body_style)
    ]
    doc1.build(story1)
    generated_docs.append((p1, "Site A Monthly Safety Audit", "inspection_report", 1))

    # 2. Inspection Report 2 (Paragraph Style - Urgent PPE Walkthrough)
    p2 = os.path.join(demo_dir, "Zone_B_Urgent_PPE_Walkthrough.pdf")
    doc2 = SimpleDocTemplate(p2, pagesize=letter)
    story2 = [
        Paragraph("Site Walkthrough Observation Report", title_style),
        Paragraph("<b>Report No:</b> AUD-PPE-402<br/><b>Date of Inspection:</b> 2026-04-18<br/><b>Facility:</b> Main Structural Warehouse<br/><b>Zone:</b> Zone B Loading Bay<br/><b>Inspected By:</b> Sarah Jenkins<br/><b>Supervisor:</b> David Miller<br/><b>Shift:</b> Night Shift", body_style),
        Spacer(1, 12),
        Paragraph("Observations and Corrective Actions", h2_style),
        Paragraph("<b>Finding 1:</b> Forklift operator observed driving without safety vest in high traffic transit lane. Severity: HIGH. Action: Issue reprimand and mandate high-visibility clothing. Due: 2026-04-20. Status: open.", body_style),
        Spacer(1, 8),
        Paragraph("<b>Finding 2:</b> Chemical decanting area workers missing neoprene chemical gloves. Severity: CRITICAL. Action: Immediate supply of chemical hazard protection gear. Due: 2026-04-19. Status: open.", body_style),
        Spacer(1, 8),
        Paragraph("<b>Finding 3:</b> Tripping hazard due to unsecured hydraulic hose near entry ramp. Severity: LOW. Action: Secure cables with rubber ramp covers. Status: closed.", body_style)
    ]
    doc2.build(story2)
    generated_docs.append((p2, "Zone B Urgent PPE Walkthrough", "inspection_report", 1))

    # 3. Inspection Report 3 (Safety Audit with Missing Helmet finding)
    p3 = os.path.join(demo_dir, "Weekly_Crane_Zone_Audit.pdf")
    doc3 = SimpleDocTemplate(p3, pagesize=letter)
    story3 = [
        Paragraph("Heavy Equipment & Crane Zone Safety Audit", title_style),
        Paragraph("<b>Report ID:</b> CRN-2026-119<br/><b>Inspection Date:</b> 2026-04-25<br/><b>Location:</b> Tower Crane Pad #2<br/><b>Inspector Name:</b> Frank Castle<br/><b>Supervisor:</b> Elena Rostova<br/><b>Company:</b> SafeSight Construction Partners", body_style),
        Spacer(1, 12),
        Paragraph("Audit Findings", h2_style),
        Paragraph("<b>Finding 1:</b> Subcontractor personnel entered the active crane swing radius without hardhat and steel-toed boots. Severity: HIGH. Category: helmet. Corrective Action: Restrict gate access and enforce mandatory hardhat rule before entry. Due Date: 2026-04-27. Status: open.", body_style),
        Spacer(1, 8),
        Paragraph("<b>Finding 2:</b> Rigger signalman wearing non-compliant vest with faded reflective strips. Category: vest. Severity: MEDIUM. Corrective Action: Replace with fluorescent green EN ISO 20471 class 3 vest. Status: in progress.", body_style)
    ]
    doc3.build(story3)
    generated_docs.append((p3, "Weekly Crane Zone Audit", "inspection_report", 1))

    # 4. Safety Manual 1 (General PPE Policy & Compliance Standards)
    p4 = os.path.join(demo_dir, "General_PPE_Safety_Manual.pdf")
    doc4 = SimpleDocTemplate(p4, pagesize=letter)
    story4 = [
        Paragraph("SafeSight AI: Corporate PPE Safety Manual (v4.2)", title_style),
        Paragraph("1.0 SCOPE AND MANDATORY REQUIREMENTS", h2_style),
        Paragraph("All employees, contractors, and site visitors must wear approved Type 1 Class E industrial hardhats at all times while present inside designated active construction and fabrication zones.", body_style),
        Spacer(1, 6),
        Paragraph("High-visibility safety vests with reflective striping must be worn by all personnel working within 15 meters of vehicle traffic or heavy mechanical plant.", body_style),
        Spacer(1, 6),
        Paragraph("Safety glasses or goggles complying with ANSI Z87.1 standard are strictly mandatory in areas where cutting, grinding, or chemical splashing hazards exist.", body_style),
        Spacer(1, 6),
        Paragraph("Puncture-resistant, steel-toed safety boots are required across the entire industrial perimeter. Sneakers or open-toed footwear are strictly prohibited.", body_style),
        Spacer(1, 10),
        Paragraph("2.0 PPE CARE AND INSPECTION", h2_style),
        Paragraph("Workers shall inspect all personal protective equipment daily prior to commencement of work. Any hardhat subjected to severe impact must be immediately decommissioned and discarded.", body_style)
    ]
    doc4.build(story4)
    generated_docs.append((p4, "General PPE Safety Manual", "safety_manual", 2))

    # 5. Safety Manual 2 (Welding & Confined Space Safety Handbook)
    p5 = os.path.join(demo_dir, "Hot_Work_and_Welding_Safety_Guide.pdf")
    doc5 = SimpleDocTemplate(p5, pagesize=letter)
    story5 = [
        Paragraph("Industrial Hot Work & Welding Safety Handbook", title_style),
        Paragraph("1.0 PPE REQUIREMENTS FOR WELDING OPERATIONS", h2_style),
        Paragraph("What PPE is required for welding: Operators must wear shade 10-12 welding helmets with auto-darkening filters, flame-retardant split cowhide leather welding jackets or aprons, heat-resistant welding gloves, and safety goggles underneath the helmet at all times.", body_style),
        Spacer(1, 6),
        Paragraph("Synthetic clothing like polyester or nylon is prohibited near open arc welding due to severe melting hazards.", body_style),
        Spacer(1, 10),
        Paragraph("2.0 PROCEDURE FOR CONFINED SPACE ENTRY", h2_style),
        Paragraph("Step 1: Obtain a valid Confined Space Entry Permit signed by the appointed Safety Officer.", body_style),
        Paragraph("Step 2: Test atmospheric conditions for oxygen levels (19.5% to 23.5%), flammable gases (<10% LEL), and toxic contaminants.", body_style),
        Paragraph("Step 3: Establish continuous forced mechanical ventilation throughout the work period.", body_style),
        Paragraph("Step 4: Wear a full body harness connected to a mechanical retrieval tripod system.", body_style),
        Paragraph("Step 5: Maintain a dedicated standby attendant outside the entrance at all times.", body_style)
    ]
    doc5.build(story5)
    generated_docs.append((p5, "Hot Work and Welding Safety Guide", "safety_manual", 2))

    # 6. Standard Operating Procedure (SOP - Angle Grinder & Cutting Operations)
    p6 = os.path.join(demo_dir, "SOP_Angle_Grinder_Operations.pdf")
    doc6 = SimpleDocTemplate(p6, pagesize=letter)
    story6 = [
        Paragraph("SOP-042: Safe Operation of Portable Angle Grinders", title_style),
        Paragraph("1.0 PURPOSE AND PPE PREREQUISITES", h2_style),
        Paragraph("Operators must verify that the wheel guard is properly fitted and securely tightened before connecting power. Full face shield, safety goggles, leather gloves, and hearing protection must be worn at all times.", body_style),
        Spacer(1, 10),
        Paragraph("2.0 OPERATING PROCEDURE", h2_style),
        Paragraph("Step 1: Visually inspect grinding disc for cracks, chips, or excessive wear before startup.", body_style),
        Paragraph("Step 2: Clamp workpiece firmly to workbench; holding workpieces by hand is prohibited.", body_style),
        Paragraph("Step 3: Allow the grinder to reach full operating speed before contacting the material.", body_style),
        Paragraph("Step 4: Maintain two-handed grip on grinder body and auxiliary handle throughout cutting.", body_style)
    ]
    doc6.build(story6)
    generated_docs.append((p6, "SOP Angle Grinder Operations", "sop", 3))

    return generated_docs


def seed_documents(reset: bool = True):
    """Generates and indexes the demo documents."""
    print("Initializing Milestone 2 Database tables...")
    init_db()
    init_db_milestone2()

    if reset:
        print("Clearing previous demo documents...")
        execute_query("DELETE FROM documents WHERE original_name LIKE '%.pdf'", commit=True)

    print("Generating ReportLab demo PDF documents...")
    doc_entries = generate_demo_files()

    loaded_ids = []
    for filepath, title, doc_type, repo_id in doc_entries:
        filename = os.path.basename(filepath)
        size = os.path.getsize(filepath)

        doc_id = execute_insert(
            """INSERT INTO documents (repository_id, original_name, stored_name, file_type, file_size, doc_type, title, status, progress_percent)
               VALUES (%s, %s, %s, 'pdf', %s, %s, %s, 'uploaded', 0)""",
            (repo_id, filename, filepath, size, doc_type, title)
        )
        print(f"  -> Created document #{doc_id}: {title}")
        doc_pipeline._run_pipeline(doc_id)
        loaded_ids.append(doc_id)

    print(f"\nSuccessfully processed and indexed {len(loaded_ids)} demo documents into Knowledge Base!")
    return len(loaded_ids)


if __name__ == "__main__":
    do_reset = "--reset" in sys.argv
    seed_documents(reset=do_reset)
