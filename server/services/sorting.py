import re
from typing import List, Dict, Any

def natural_sort_key(text: str):
    """
    Produces a natural sort key for alphanumeric strings.
    E.g., 'CS-01', 'CS-2', 'CS-10' are sorted logically by numerical value.
    """
    if not text:
        return []
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', str(text))]

def get_name_sort_key(name: str):
    """
    Produces a tuple key for sorting by Last Name, then First Name.
    E.g. 'Rahul Sharma' -> ('sharma', 'rahul')
    """
    if not name:
        return ("", "")
    parts = name.strip().split()
    if len(parts) > 1:
        return (parts[-1].lower(), " ".join(parts[:-1]).lower())
    return (parts[0].lower(), "")

def sort_students(students: List[Dict[str, Any]], sort_by: str = "name_asc") -> List[Dict[str, Any]]:
    """
    Sorts student records according to the AlphabetAI sorting specifications:
    - 'name_asc': Alphabetical A-Z (Last Name, First Name)
    - 'name_desc': Alphabetical Z-A (Last Name, First Name)
    - 'roll_asc': Natural Sequential Roll Number (e.g., CS-01, CS-02, CS-10)
    - 'roll_desc': Natural Sequential Roll Number descending
    - 'status': Status priority (Present -> Late -> Absent -> Unmarked)
    """
    status_order = {
        "Present": 1,
        "Late": 2,
        "Excused": 3,
        "Absent": 4,
        "unmarked": 5
    }

    if sort_by == "name_asc":
        return sorted(students, key=lambda s: get_name_sort_key(s.get("name", "")))
    elif sort_by == "name_desc":
        return sorted(students, key=lambda s: get_name_sort_key(s.get("name", "")), reverse=True)
    elif sort_by == "roll_asc":
        return sorted(students, key=lambda s: natural_sort_key(s.get("roll_number", "")))
    elif sort_by == "roll_desc":
        return sorted(students, key=lambda s: natural_sort_key(s.get("roll_number", "")), reverse=True)
    elif sort_by == "status":
        return sorted(
            students,
            key=lambda s: (
                status_order.get(s.get("status", "Absent"), 99),
                natural_sort_key(s.get("roll_number", ""))
            )
        )
    else:
        # Default fallback to name A-Z
        return sorted(students, key=lambda s: get_name_sort_key(s.get("name", "")))

def filter_by_alphabet(students: List[Dict[str, Any]], letter: str) -> List[Dict[str, Any]]:
    """Filters students whose last name or first name starts with the given letter."""
    if not letter or letter.upper() == "ALL":
        return students
    letter = letter.upper()
    return [
        s for s in students
        if s.get("name", "").strip().upper().startswith(letter) or
           (s.get("name", "").strip().split()[-1].upper().startswith(letter) if s.get("name") else False)
    ]
