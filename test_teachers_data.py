# test_teachers_data.py
# Purely fictional filler teachers for testing (load/scheduling/conflict-checking
# with more teachers than the real SGSITS directory currently has). These are NOT
# real people - kept in a separate file/dict from teachers_data.py (the real,
# best-effort SGSITS directory) so the two are never confused. Every entry is
# tagged "(Test Data)" in its designation and uses a distinct @test.sgsits.edu
# email domain so it's obvious in every dropdown/table which rows are fake.

TEST_TEACHERS = {
    "CSE": [
        ("Rohan Kapoor", "Assistant Professor", "Web Development"),
        ("Priyanka Nair", "Assistant Professor", "Data Structures"),
        ("Sameer Joshi", "Associate Professor", "Operating Systems"),
        ("Anjali Deshmukh", "Assistant Professor", "Machine Learning"),
        ("Rahul Bhatt", "Professor", "Computer Networks"),
    ],
    "EE": [
        ("Neeraj Chandra", "Assistant Professor", "Power Systems"),
        ("Kavita Rane", "Assistant Professor", "Control Systems"),
        ("Manish Oberoi", "Associate Professor", "Electrical Machines"),
        ("Divya Kulkarni", "Assistant Professor", "Power Electronics"),
        ("Ajay Saxena", "Professor", "Circuit Theory"),
    ],
    "ME": [
        ("Sanjay Rathore", "Assistant Professor", "Thermodynamics"),
        ("Pooja Iyer", "Assistant Professor", "Fluid Mechanics"),
        ("Vikram Solanki", "Associate Professor", "Manufacturing"),
        ("Nisha Kapadia", "Assistant Professor", "Machine Design"),
        ("Arvind Menon", "Professor", "CAD/CAM"),
    ],
    "CE": [
        ("Ramesh Pillai", "Assistant Professor", "Structural Engineering"),
        ("Swati Bhalla", "Assistant Professor", "Geotechnical Engineering"),
        ("Deepak Nagpal", "Associate Professor", "Transportation Engineering"),
        ("Ritu Chawla", "Assistant Professor", "Environmental Engineering"),
        ("Sunil Kohli", "Professor", "Surveying"),
    ],
    "ECE": [
        ("Alok Verma", "Assistant Professor", "Digital Signal Processing"),
        ("Meenal Shroff", "Assistant Professor", "VLSI Design"),
        ("Tarun Sethi", "Associate Professor", "Communication Systems"),
        ("Ishita Bose", "Assistant Professor", "Embedded Systems"),
        ("Naveen Kapur", "Professor", "Microwave Engineering"),
    ],
    "IT": [
        ("Abhishek Rao", "Assistant Professor", "Web Technologies"),
        ("Sneha Kulkarni", "Assistant Professor", "Cloud Computing"),
        ("Rajeev Malhotra", "Associate Professor", "Database Systems"),
        ("Pallavi Das", "Assistant Professor", "Cybersecurity"),
        ("Vinay Chopra", "Professor", "Software Engineering"),
    ],
}


def _slugify(name: str) -> str:
    cleaned = "".join(ch for ch in name.lower() if ch.isalnum() or ch == " ")
    return ".".join(cleaned.split())


def build_test_teacher_rows(branch: str = None):
    """Flatten the fictional test roster into insertable rows: (name, email,
    department, designation, specialization). Optionally filtered by branch."""
    rows = []
    branches = [branch] if branch else TEST_TEACHERS.keys()
    for b in branches:
        for name, designation, specialization in TEST_TEACHERS.get(b, []):
            email = f"{_slugify(name)}.{b.lower()}@test.sgsits.edu"
            rows.append((name, email, b, f"{designation} (Test Data)", specialization))
    return rows
