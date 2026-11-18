"""
Unit tests for Milestone 2 Extractors (inspection_extractor, manual_extractor, doc_classifier).
"""
import unittest
from app.services.doc_classifier import classify_document
from app.services.inspection_extractor import extract_report_data
from app.services.manual_extractor import extract_manual_data


class TestDocClassifier(unittest.TestCase):
    def test_classify_inspection_report(self):
        text = "Site Safety Audit Report. Report ID: AUD-101. Inspector Name: Marcus. Findings and non-compliance observed."
        doc_type, conf = classify_document(text, "audit_april.pdf")
        self.assertEqual(doc_type, "inspection_report")
        self.assertGreater(conf, 0.5)

    def test_classify_safety_manual(self):
        text = "Occupational Health & Safety Manual. Section 1.0 General PPE Requirements and Safety Policy. Mandatory compliance."
        doc_type, conf = classify_document(text, "safety_manual.pdf")
        self.assertEqual(doc_type, "safety_manual")
        self.assertGreater(conf, 0.5)

    def test_classify_sop(self):
        text = "Standard Operating Procedure for Grinding. SOP Number 402. Step 1: Pre-use inspection. Step 2: Isolation."
        doc_type, conf = classify_document(text, "sop_grinder.pdf")
        self.assertEqual(doc_type, "sop")
        self.assertGreater(conf, 0.5)


class TestInspectionExtractor(unittest.TestCase):
    def setUp(self):
        self.sample_report = [
            {
                "page_no": 1,
                "text": (
                    "SafeSight Inspection Report: Site A\n"
                    "Report ID: SAF-2026-99\n"
                    "Inspection Date: 2026-04-12\n"
                    "Site Location: Sector 4 Extension\n"
                    "Inspector Name: John Doe\n\n"
                    "Finding 1: Worker operating without goggles. Category: goggles. Severity: HIGH. "
                    "Corrective action: Issue safety goggles. Due: 2026-04-13."
                )
            }
        ]

    def test_extract_header_fields(self):
        res = extract_report_data(self.sample_report)
        fields = {f["field_name"]: f["field_value"] for f in res["fields"]}
        self.assertIn("report_id", fields)
        self.assertEqual(fields["report_id"], "SAF-2026-99")
        self.assertIn("inspector_name", fields)
        self.assertIn("John Doe", fields["inspector_name"])

    def test_extract_findings(self):
        res = extract_report_data(self.sample_report)
        findings = res["findings"]
        self.assertGreaterEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding["category"], "goggles")
        self.assertIn(finding["severity"], ("HIGH", "CRITICAL", "MEDIUM", "LOW"))
        self.assertIn("goggles", finding["description"].lower())

    def test_summary_calculation(self):
        res = extract_report_data(self.sample_report)
        summary = res["summary"]
        self.assertGreaterEqual(summary["total_findings"], 1)
        self.assertIn("category_counts", summary)
        self.assertIn("severity_counts", summary)


class TestManualExtractor(unittest.TestCase):
    def setUp(self):
        self.sample_manual = [
            {
                "page_no": 1,
                "text": (
                    "1.0 EYE AND FACE PROTECTION\n"
                    "All personnel must wear approved safety glasses with side shields in designated fabrication zones.\n"
                    "Failure to wear eye protection is strictly prohibited.\n\n"
                    "2.0 PROCEDURE FOR HOT WORK\n"
                    "Step 1: Inspect the workspace and clear flammable materials within 10 meters.\n"
                    "Step 2: Check fire extinguisher pressure gauge and keep within arm's reach.\n"
                    "Step 3: Wear flame-retardant welding gloves and shade 10 helmet."
                )
            }
        ]

    def test_extract_sections(self):
        res = extract_manual_data(self.sample_manual)
        sections = res["sections"]
        self.assertGreaterEqual(len(sections), 1)
        titles = [s["title"] for s in sections]
        self.assertTrue(any("EYE" in t or "HOT WORK" in t for t in titles))

    def test_extract_rules(self):
        res = extract_manual_data(self.sample_manual)
        rules = res["rules"]
        self.assertGreaterEqual(len(rules), 1)
        rule_texts = " ".join([r["rule_text"] for r in rules])
        self.assertIn("safety glasses", rule_texts.lower())

    def test_extract_procedures(self):
        res = extract_manual_data(self.sample_manual)
        procs = res["procedures"]
        self.assertGreaterEqual(len(procs), 1)
        proc = procs[0]
        self.assertGreaterEqual(len(proc["steps"]), 2)


if __name__ == "__main__":
    unittest.main()
