"""
Unit tests for SafeSight AI Violation Mapping & Presentation Helper.
Tests status model, type normalization, timestamp splitting, and S.No calculation.
"""
import unittest
from datetime import datetime
from app.services.violation_mapper import (
    map_status_to_ui,
    map_ui_status_to_db,
    get_db_statuses_for_ui_filter,
    map_violation_type,
    split_datetime,
    calculate_sno
)


class TestViolationMapper(unittest.TestCase):
    def test_status_mapping_to_ui(self):
        """Test 5 DB statuses mapped to 3 UI categories."""
        # Pending group
        st_det = map_status_to_ui("detected")
        self.assertEqual(st_det["ui_status"], "Pending")
        self.assertEqual(st_det["tone"], "warning")
        self.assertFalse(st_det["is_dismissed"])

        st_pend = map_status_to_ui("pending review")
        self.assertEqual(st_pend["ui_status"], "Pending")
        self.assertEqual(st_pend["tone"], "warning")
        self.assertFalse(st_pend["is_dismissed"])

        # Reviewed group
        st_conf = map_status_to_ui("confirmed")
        self.assertEqual(st_conf["ui_status"], "Reviewed")
        self.assertEqual(st_conf["tone"], "berry")
        self.assertFalse(st_conf["is_dismissed"])

        st_dism = map_status_to_ui("dismissed")
        self.assertEqual(st_dism["ui_status"], "Reviewed")
        self.assertEqual(st_dism["tone"], "berry")
        self.assertTrue(st_dism["is_dismissed"])
        self.assertIn("Dismissed", st_dism["tooltip"])

        # Resolved group
        st_res = map_status_to_ui("resolved")
        self.assertEqual(st_res["ui_status"], "Resolved")
        self.assertEqual(st_res["tone"], "success")
        self.assertFalse(st_res["is_dismissed"])

    def test_ui_status_to_db(self):
        """Test write values when user selects a UI status."""
        self.assertEqual(map_ui_status_to_db("pending"), "pending review")
        self.assertEqual(map_ui_status_to_db("Pending"), "pending review")
        self.assertEqual(map_ui_status_to_db("reviewed"), "confirmed")
        self.assertEqual(map_ui_status_to_db("Reviewed"), "confirmed")
        self.assertEqual(map_ui_status_to_db("resolved"), "resolved")
        self.assertEqual(map_ui_status_to_db("Resolved"), "resolved")
        # Direct raw statuses preserved
        self.assertEqual(map_ui_status_to_db("dismissed"), "dismissed")

    def test_db_statuses_for_ui_filter(self):
        """Test filter translation to underlying DB statuses."""
        self.assertEqual(set(get_db_statuses_for_ui_filter("pending")), {"detected", "pending review"})
        self.assertEqual(set(get_db_statuses_for_ui_filter("reviewed")), {"confirmed", "dismissed"})
        self.assertEqual(set(get_db_statuses_for_ui_filter("resolved")), {"resolved"})
        self.assertIsNone(get_db_statuses_for_ui_filter("all"))
        self.assertIsNone(get_db_statuses_for_ui_filter(""))

    def test_violation_type_mapping(self):
        """Test friendly type normalization and icon assignments."""
        t_helmet = map_violation_type("helmet")
        self.assertEqual(t_helmet["label"], "Missing Helmet")
        self.assertEqual(t_helmet["icon"], "helmet")

        t_no_helmet = map_violation_type("no helmet")
        self.assertEqual(t_no_helmet["label"], "Missing Helmet")

        t_vest = map_violation_type("vest")
        self.assertEqual(t_vest["label"], "Missing Safety Vest")
        self.assertEqual(t_vest["icon"], "vest")

        t_equip = map_violation_type("several ppe items missing")
        self.assertEqual(t_equip["label"], "No Safety Equipment")

        t_other = map_violation_type("goggles")
        self.assertEqual(t_other["label"], "Other Safety Violation")

        t_unknown = map_violation_type("trespassing")
        self.assertEqual(t_unknown["label"], "Other Safety Violation")

    def test_split_datetime(self):
        """Test date and time splitting format."""
        dt_str = "2026-11-20 10:42:15"
        d_fmt, t_fmt = split_datetime(dt_str)
        self.assertEqual(d_fmt, "20 Nov 2026")
        self.assertEqual(t_fmt, "10:42:15 AM")

        # Datetime object
        dt_obj = datetime(2026, 11, 20, 14, 30, 45)
        d_obj_fmt, t_obj_fmt = split_datetime(dt_obj)
        self.assertEqual(d_obj_fmt, "20 Nov 2026")
        self.assertEqual(t_obj_fmt, "02:30:45 PM")

        # Missing / invalid value
        d_none, t_none = split_datetime(None)
        self.assertEqual(d_none, "Not recorded")
        self.assertEqual(t_none, "Not recorded")

    def test_calculate_sno(self):
        """Test running S.No calculation across pages."""
        # Page 1, size 10
        self.assertEqual(calculate_sno(page=1, page_size=10, index=0), 1)
        self.assertEqual(calculate_sno(page=1, page_size=10, index=9), 10)

        # Page 2, size 10
        self.assertEqual(calculate_sno(page=2, page_size=10, index=0), 11)
        self.assertEqual(calculate_sno(page=2, page_size=10, index=9), 20)

        # Page 3, size 25
        self.assertEqual(calculate_sno(page=3, page_size=25, index=4), 55)


if __name__ == "__main__":
    unittest.main()
