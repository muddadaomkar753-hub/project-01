import io
import csv
from typing import List, Dict, Any
from .sorting import sort_students

def export_attendance_to_csv(session_info: Dict[str, Any], attendance_records: List[Dict[str, Any]]) -> str:
    """
    Generates a formal, printable A-Z formatted CSV attendance register.
    """
    # Sort students alphabetically by name (A-Z)
    sorted_records = sort_students(attendance_records, sort_by="name_asc")
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header metadata block
    writer.writerow(["============================================================"])
    writer.writerow(["ALPHABETAI ATTENDANCE SYSTEM - FORMAL ATTENDANCE REGISTER"])
    writer.writerow(["Session Date:", session_info.get("session_date", "")])
    writer.writerow(["Course / Subject:", session_info.get("course_name", "")])
    writer.writerow(["Teacher / Proctor:", session_info.get("teacher_name", "")])
    writer.writerow(["Status:", "Locked (Finalized)" if session_info.get("is_locked") else "Open / In-Progress"])
    writer.writerow(["============================================================"])
    writer.writerow([])
    
    # Column headers
    writer.writerow([
        "S.No",
        "Student Name",
        "Roll Number",
        "Department",
        "Class / Section",
        "Attendance Status",
        "Verification Mode",
        "Match Confidence",
        "Timestamp Marked",
        "Notes"
    ])
    
    for idx, r in enumerate(sorted_records, start=1):
        conf_str = f"{round(r.get('confidence', 0) * 100, 1)}%" if r.get('confidence') else "N/A"
        writer.writerow([
            idx,
            r.get("name", ""),
            r.get("roll_number", ""),
            r.get("department", ""),
            r.get("class_name", ""),
            r.get("status", "Absent"),
            r.get("verification_mode", "Manual"),
            conf_str,
            r.get("timestamp", ""),
            r.get("note", "")
        ])
        
    writer.writerow([])
    # Summary calculation
    total = len(sorted_records)
    present = sum(1 for r in sorted_records if r.get("status") == "Present")
    late = sum(1 for r in sorted_records if r.get("status") == "Late")
    absent = sum(1 for r in sorted_records if r.get("status") == "Absent")
    rate = round((present + late) / total * 100, 1) if total > 0 else 0
    
    writer.writerow(["--- SUMMARY ---"])
    writer.writerow(["Total Students:", total])
    writer.writerow(["Present:", present])
    writer.writerow(["Late:", late])
    writer.writerow(["Absent:", absent])
    writer.writerow(["Overall Attendance Rate:", f"{rate}%"])
    
    return output.getvalue()
