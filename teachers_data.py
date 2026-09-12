# teachers_data.py
# Best-effort, publicly-sourced SGSITS faculty directory, used to auto-populate the
# `teachers` table so admins don't have to type every name by hand. Manual add
# (AddTeacher) keeps working exactly as before on top of whatever this seeds in.
#
# IMPORTANT LIMITATION: SGSITS's own site has migrated to a JS single-page app,
# so its live faculty directory pages could not be fetched directly (they render
# client-side). This list was assembled from what turned up in public web search
# results (search snippets citing sgsits.ac.in department pages, collegedunia,
# and faculty research profiles) - it is NOT scraped from an official directory,
# is likely incomplete, and department/designation/specialization may be outdated
# by the time you read this. Verify before relying on it, and edit/remove/add
# freely via the Add Teacher page - this is a starting point, not a source of truth.
#
# Each tuple is: (name, designation, specialization_or_None)
# Placeholder emails are generated (name.branch@sgsits.edu) since real official
# emails weren't reliably available - edit them after loading if you have the
# real ones.
#
# Coverage: CSE, EE, CE, IT, ECE, ME, EI, IPE, BME all have names now. CHE
# (Chemical Engineering) has none sourced at all - add via Add Teacher. Some
# designations conflicted across sources (e.g. who is current HOD) - the most
# specific/recent-looking source won on each; add/correct anything wrong via
# the Add Teacher page. Dr. Prashant P. Bansod appears in both EI and BME with
# a different designation in each - that's a real joint appointment, not a
# duplicate.
#
# ELECTIVE_TEACHERS below is a separate, clearly-generic addition (not
# sourced) - 2 elective/humanities faculty per branch so every branch has
# someone assignable to the common electives added in curriculum_data.py.

TEACHERS = {
    "CSE": [
        ("Vandan Tewari", "Professor & Head", "Data Mining, Data Analytics, Machine Learning, Database Engineering"),
        ("D A Mehta", "Professor", None),
        ("Urjita Thakar", "Professor / Former Head", None),
        ("Anuradha Purohit", "Professor", None),
        ("Surendra Gupta", "Associate Professor", "Head of Computer Centre"),
    ],
    "EE": [
        ("Shailendra Kumar Sharma", "Professor & Head", "Power Electronics, Machine Design"),
        ("Sandeep Bhongade", "Professor", "Electrical Systems, Analytical Techniques, Circuit Theory"),
        ("Deepti Rai", "Professor", "Electronic Components, Foundational Systems; Council Coordinator"),
        ("Sukhlal Sisodiya", "Professor", "Control Systems, Automation, Industrial Electrical Applications"),
        ("Mamata Bhattacharya", "Professor", "Power Systems, High-Voltage Engineering"),
        ("Rinki Rajpal", "Professor", "Major Project Guidance, Technical Research"),
        ("Mayuri Sunhare", "Assistant Professor", None),
    ],
    "CE": [
        ("Sunil Ajmera", "Professor & Head", None),
        ("S. M. Narulkar", "Professor & Former Head", None),
        ("H. K. Mahiyar", "Professor", "Geotechnical Engineering"),
        ("R. K. Khare", "Professor", None),
        ("Vivek Tiwari", "Assistant Professor", None),
        ("Pranav Thepe", "Assistant Professor", None),
    ],
    "IT": [
        ("K. K. Sharma", "Professor & Head", "Computer Science, Advanced Information Technology"),
        ("Lalit Purohit", "Professor & Dean, Academics/Research/Skill Development (ARSD)",
         "Web Services, Semantic Web, Software Architecture, Machine Learning, Deep Learning"),
        ("Sunita Varma", "Professor", "Academic Governance, Outcome-Based Education, Data Structures, Software Engineering"),
        ("Mukul Shukla", "Associate Professor", "Internet of Things (IoT), Computer Networks, Advanced Systems"),
        ("Puja Gupta", "Assistant Professor", "Computer Vision, AI/ML, Cloud Computing, Embedded Systems, IoT"),
        ("Upendra Singh", "Assistant Professor / Program Coordinator", "Systems Programming, Project Development, IT Lab Supervision"),
        ("Mukesh Sakle", "Assistant Professor / Coordinator", "Software Engineering, Machine Learning Project Mentorship"),
        ("Akshay Gupta", "Assistant Professor", "Fundamental IT Concepts, Web Technologies, Database Systems"),
        ("Prapti Godheshwar", "Assistant Professor", "Network Security, Core Information Technology"),
        ("Shraddha Verma", "Assistant Professor", None),
        ("Megha Kuliha", "Assistant Professor", None),
    ],
    "ECE": [
        ("Shekhar Sharma", "Professor", None),
        ("Anjulata Yadav", "Professor", None),
        ("L. D. Malviya", "Professor", None),
        ("Manish Panchal", "Associate Professor", None),
        ("Rekha Jain", "Professor", None),
        ("Preeti Trivedi", "Professor", None),
        ("Amit Naik", "Professor", None),
        ("Neha Pande", "Professor", None),
        ("Sumit Dwivedi", "Professor", None),
    ],
    "ME": [
        ("B. R. Rawal", "Professor & Head", None),
        ("M. L. Jain", "Professor", "Thermal Engineering & Fluid Mechanics"),
        ("Manoj Chouksey", "Professor", "Design & Vibrations"),
        ("R. K. Porwal", "Professor", "Manufacturing & Production"),
        ("Basant Agrawal", "Professor", "Thermal Engineering & Solar Energy"),
        ("Sudhir Tiwari", "Professor", "Material Science & Manufacturing"),
        ("Vinod Pare", "Professor", "CAD/CAM & Industrial Automation"),
        ("B. S. More", "Professor", "Heat and Mass Transfer"),
    ],
    "EI": [
        ("R. C. Gurjar", "Associate Professor & Head", "RFIC Design, CMOS Systems"),
        ("Rajesh Khatri", "Associate Professor & Former Head", "VLSI and Chip Design, RFIC, Semiconductors"),
        ("Prashant P. Bansod", "Professor", "Biomedical Instrumentation, Signal Processing"),
        ("Gireesh Gaurav Soni", "Assistant Professor", "Instrumentation & Control"),
        ("Tarni Joshi", "Assistant Professor", "CMOS VLSI Design, Microprocessors, Digital Electronics"),
    ],
    "IPE": [
        ("G. D. Thakar", "Professor & Head", None),
        ("F. Ujjainwala", "Associate Professor", "CIM and Lean Manufacturing"),
        ("Krishnakant Dhakad", "Assistant Professor / Coordinator, IDEA Lab", None),
    ],
    "BME": [
        ("Vibha Bhatnagar", "Associate Professor & Head", None),
        ("Prashant P. Bansod", "Professor / Former Head", None),
        ("Maya Makwana", "Assistant Professor", None),
        ("Varad Pathak", "Assistant Professor", None),
    ],
    # CHE: no faculty could be sourced - add via Add Teacher.
    "CHE": [],
}

# Generic elective/humanities faculty - NOT sourced from any real directory,
# added so every branch has >=2 teachers assignable to the common 2nd-year
# electives in curriculum_data.py's COMMON_YEAR2_ELECTIVES (Constitution of
# India, Economics for Engineers). Merged into every branch below.
ELECTIVE_TEACHERS = {
    "CSE": [("Ramesh Trivedi", "Assistant Professor (Humanities & Social Sciences)", "Economics for Engineers"),
            ("Sunita Agarwal", "Assistant Professor (Humanities & Social Sciences)", "Constitution of India")],
    "EE":  [("Anil Deshpande", "Assistant Professor (Humanities & Social Sciences)", "Economics for Engineers"),
            ("Kavita Menon", "Assistant Professor (Humanities & Social Sciences)", "Constitution of India")],
    "ME":  [("Suresh Bhatt", "Assistant Professor (Humanities & Social Sciences)", "Economics for Engineers"),
            ("Meera Iyer", "Assistant Professor (Humanities & Social Sciences)", "Constitution of India")],
    "ECE": [("Rajendra Nair", "Assistant Professor (Humanities & Social Sciences)", "Economics for Engineers"),
            ("Pooja Saxena", "Assistant Professor (Humanities & Social Sciences)", "Constitution of India")],
    "CE":  [("Vikas Choudhary", "Assistant Professor (Humanities & Social Sciences)", "Economics for Engineers"),
            ("Anita Rawat", "Assistant Professor (Humanities & Social Sciences)", "Constitution of India")],
    "IT":  [("Deepak Malhotra", "Assistant Professor (Humanities & Social Sciences)", "Economics for Engineers"),
            ("Shalini Bose", "Assistant Professor (Humanities & Social Sciences)", "Constitution of India")],
    "EI":  [("Manoj Trivedi", "Assistant Professor (Humanities & Social Sciences)", "Economics for Engineers"),
            ("Rekha Sinha", "Assistant Professor (Humanities & Social Sciences)", "Constitution of India")],
    "IPE": [("Ramesh Gupta", "Assistant Professor (Humanities & Social Sciences)", "Economics for Engineers"),
            ("Anjali Mishra", "Assistant Professor (Humanities & Social Sciences)", "Constitution of India")],
    "BME": [("Ashok Verma", "Assistant Professor (Humanities & Social Sciences)", "Economics for Engineers"),
            ("Neelam Dubey", "Assistant Professor (Humanities & Social Sciences)", "Constitution of India")],
    "CHE": [("Vijay Kulkarni", "Assistant Professor (Humanities & Social Sciences)", "Economics for Engineers"),
            ("Sarita Pandey", "Assistant Professor (Humanities & Social Sciences)", "Constitution of India")],
}


def _slugify(name: str) -> str:
    cleaned = "".join(ch for ch in name.lower() if ch.isalnum() or ch == " ")
    return ".".join(cleaned.split())


def build_teacher_rows(branch: str = None):
    """Flatten the directory into insertable rows: (name, email, department,
    designation, specialization). Optionally filtered by branch. Includes the
    real (best-effort) directory plus the generic elective/humanities filler
    from ELECTIVE_TEACHERS."""
    rows = []
    branches = [branch] if branch else TEACHERS.keys()
    for b in branches:
        combined = TEACHERS.get(b, []) + ELECTIVE_TEACHERS.get(b, [])
        for name, designation, specialization in combined:
            email = f"{_slugify(name)}.{b.lower()}@sgsits.edu"
            rows.append((name, email, b, designation, specialization))
    return rows
