import os
import sys
import unittest
import numpy as np

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.db import (
    init_db,
    create_student,
    get_all_students,
    mark_attendance,
    get_or_create_today_session,
    get_session_attendance,
    delete_student,
    get_student_by_roll
)
from server.services.sorting import sort_students, filter_by_alphabet, natural_sort_key
from server.services.exporter import export_attendance_to_csv
from server.services.face_engine import face_engine

class TestAlphabetAISystem(unittest.TestCase):

    def setUp(self):
        init_db()

    def test_natural_sorting(self):
        roll_numbers = ["CS-10", "CS-01", "CS-2", "CS-100", "CS-20"]
        sorted_rolls = sorted(roll_numbers, key=natural_sort_key)
        self.assertEqual(sorted_rolls, ["CS-01", "CS-2", "CS-10", "CS-20", "CS-100"])
        print("[PASSED] Natural roll number sorting test.")

    def test_student_and_attendance_flow(self):
        # Clean up if already exists
        existing = get_student_by_roll("TEST-CS-01")
        if existing:
            delete_student(existing["id"])

        # Create dummy normalized embedding
        dummy_embedding = [float(x) for x in (np.ones(128) / np.sqrt(128))]
        
        # Test student enrollment
        student = create_student(
            name="Alice Smith",
            roll_number="TEST-CS-01",
            class_name="CS-A",
            department="Computer Science",
            embedding=dummy_embedding
        )
        self.assertIsNotNone(student)
        self.assertEqual(student["name"], "Alice Smith")
        self.assertEqual(student["roll_number"], "TEST-CS-01")

        # Test session and attendance
        session = get_or_create_today_session()
        record = mark_attendance(
            session_id=session["id"],
            student_id=student["id"],
            status="Present",
            confidence=0.95,
            verification_mode="face"
        )
        self.assertEqual(record["status"], "Present")

        # Test roster attendance
        attendance = get_session_attendance(session["id"])
        self.assertTrue(any(a["student_id"] == student["id"] and a["status"] == "Present" for a in attendance))

        # Test CSV export
        csv_out = export_attendance_to_csv(session, attendance)
        self.assertIn("Alice Smith", csv_out)
        self.assertIn("TEST-CS-01", csv_out)
        self.assertIn("Present", csv_out)
        print("[PASSED] Student enrollment, attendance, and CSV export test.")

        # Clean up test student
        delete_student(student["id"])

    def test_cosine_similarity(self):
        v1 = [float(x) for x in (np.ones(128) / np.sqrt(128))]
        v2 = [float(x) for x in (np.ones(128) / np.sqrt(128))]
        
        dummy_student = {"id": 999, "name": "Test Face", "roll_number": "T-01", "embedding": v2}
        match = face_engine.match_student(v1, [dummy_student], threshold=0.363)
        self.assertIsNotNone(match)
        self.assertEqual(match["name"], "Test Face")
        self.assertGreaterEqual(match["similarity_score"], 0.99)
        print("[PASSED] Face engine vector similarity calculation test.")

if __name__ == "__main__":
    unittest.main()
