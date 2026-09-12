# curriculum_data.py
# Official SGSITS subject curriculum, used to auto-populate the `subjects` table
# so admins don't have to type every subject by hand. Manual add/assign (AddSubject,
# AssignSubject) keeps working exactly as before on top of whatever this seeds in.
#
# Each subject tuple is: (name, credits, hours_per_week, is_lab, is_elective)
#
# Source: provided directly by the user (SGSITS official scheme references), for the
# CSE branch and the first-year syllabus (common to all branches). Branches other than
# CSE do not yet have verified year 2-4 data — see backend_api.py load-curriculum
# endpoint docstring.
#
# Lab entries added later came from a lab-by-branch/year TABLE the user provided
# giving only generic categories (e.g. "Networks, OS, DBMS, AI/Data-related labs"),
# not exact official lab titles - each was translated into a specific, plausible
# lab name (is_lab=True) to fit this schema. Treat these lab names as best-effort,
# not verified official titles - rename via Add Subject if you have the real ones.
#
# EI, BME, CHE are brand-new branches added from that same table - they have ONLY
# the labs from the table (plus the common first year) and NO theory subjects,
# since none were ever provided. IPE was mentioned but had no row in that table at
# all, so it has no curriculum here (common first year + faculty only) - paste its
# subjects/labs whenever you have them, same as everything else in this file.

BRANCHES = ["CSE", "EE", "ME", "ECE", "CE", "IT", "EI", "IPE", "BME", "CHE"]

# First Year — common to all branches (Semester 1 / Semester 2 split by Group A/B
# is not modeled; subjects are grouped into a semester using the typical pattern).
COMMON_YEAR1 = {
    1: [
        ("Mathematics - I", 4, 4, False, False),
        ("Physics", 4, 4, False, False),
        ("Fundamentals of Electrical Engineering", 3, 3, False, False),
        ("Fundamentals of Mechanical Engineering", 3, 3, False, False),
        ("Engineering Graphics", 2, 3, True, False),
        ("Technical English / Communication Skills", 2, 2, False, False),
        ("Manufacturing Practices", 2, 3, True, False),
    ],
    2: [
        ("Mathematics - II", 4, 4, False, False),
        ("Chemistry", 4, 4, False, False),
        ("Computer Programming (Intro to C / C++)", 3, 3, False, False),
        ("Fundamentals of Civil Engineering & Applied Mechanics", 3, 3, False, False),
        ("Environmental Science", 2, 2, False, False),
    ],
}

# Branch-specific curriculum for years 2-4. Only CSE is populated with verified data.
BRANCH_CURRICULUM = {
    "CSE": {
        2: {
            3: [
                ("Mathematics - III", 4, 4, False, False),
                ("Object Oriented Programming Systems (OOPS)", 3, 3, False, False),
                ("Computer Architecture", 3, 3, False, False),
                ("Microprocessors and Microcontrollers", 3, 3, False, False),
                ("Economics for Engineers", 2, 2, False, False),
                ("Programming Practices Lab", 1, 2, True, False),
                ("Electronics Workshop", 1, 2, True, False),
            ],
            4: [
                ("Discrete Structures", 3, 3, False, False),
                ("Mathematics - IV", 4, 4, False, False),
                ("Data Structures", 3, 3, False, False),
                ("Operating Systems", 3, 3, False, False),
                ("Digital Communication", 3, 3, False, False),
                ("Computer Workshop", 1, 2, True, False),
                ("Design Thinking Lab - I", 1, 2, True, False),
                ("Values, Humanities and Professional Ethics", 2, 2, False, False),
            ],
        },
        3: {
            5: [
                ("Theory of Computation", 3, 3, False, False),
                ("Database Management Systems", 3, 3, False, False),
                ("Computer Networks", 3, 3, False, False),
                ("Agile Software Methodology / Software Engineering", 3, 3, False, False),
                ("Department Elective - I", 3, 3, False, True),
                ("Database Management Systems Lab", 1, 2, True, False),
                ("Computer Networks Lab", 1, 2, True, False),
            ],
            6: [
                ("Compiler Design", 3, 3, False, False),
                ("Design and Analysis of Algorithms", 3, 3, False, False),
                ("Machine Learning", 3, 3, False, False),
                ("Department Elective - II", 3, 3, False, True),
                ("Open Elective - I", 3, 3, False, True),
                ("Machine Learning Lab", 1, 2, True, False),
            ],
        },
        4: {
            7: [
                ("Artificial Intelligence", 3, 3, False, False),
                ("Information & Cloud Security", 3, 3, False, False),
                ("Department Elective - III", 3, 3, False, True),
                ("Open Elective - II", 3, 3, False, True),
                ("Major Project (Phase - I)", 4, 6, True, False),
                ("Industrial Training Evaluation", 1, 1, False, False),
            ],
            8: [
                ("Department Elective - IV", 3, 3, False, True),
                ("Open Elective - III", 3, 3, False, True),
                ("Major Project (Phase - II)", 8, 12, True, False),
            ],
        },
    },
    # IT, ECE, EE: sourced from the user, but only at year granularity (not
    # already split into semester A/B like CSE's official reference) - the
    # semester split below is a reasonable even division, not verified
    # semester-by-semester. Reassign via Add Subject/edit if it's off.
    "IT": {
        2: {
            3: [
                ("Object Oriented Programming Systems (OOPS)", 3, 3, False, False),
                ("Data Structures and Algorithms (DSA)", 3, 3, False, False),
                ("Digital Electronics and Logic Design", 3, 3, False, False),
                ("Data Structures Lab", 1, 2, True, False),
                ("Digital Electronics Lab", 1, 2, True, False),
            ],
            4: [
                ("Discrete Structures / Engineering Mathematics - III", 4, 4, False, False),
                ("Computer System Architecture (CSA)", 3, 3, False, False),
                ("Software Engineering", 3, 3, False, False),
                ("Object Oriented Programming Lab", 1, 2, True, False),
                ("Computer System Architecture Lab", 1, 2, True, False),
            ],
        },
        3: {
            5: [
                ("Database Management Systems (DBMS)", 3, 3, False, False),
                ("Computer Networks", 3, 3, False, False),
                ("Operating Systems", 3, 3, False, False),
                ("Database Management Systems Lab", 1, 2, True, False),
                ("Computer Networks Lab", 1, 2, True, False),
            ],
            6: [
                ("Theory of Computation / Compiler Design", 3, 3, False, False),
                ("Web Technology and Web Services", 3, 3, False, False),
                ("Design and Analysis of Algorithms (DAA)", 3, 3, False, False),
                ("Web Technology Lab", 1, 2, True, False),
                ("Design and Analysis of Algorithms Lab", 1, 2, True, False),
            ],
        },
        4: {
            7: [
                ("Information & Network Security", 3, 3, False, False),
                ("Cloud Computing & Big Data Analytics", 3, 3, False, False),
                ("Internet of Things (IoT)", 3, 3, False, False),
            ],
            8: [
                ("Artificial Intelligence & Machine Learning", 3, 3, False, False),
                ("Department Elective (Data Mining / Mobile Computing / Distributed Systems)", 3, 3, False, True),
                ("Major Project", 8, 12, True, False),
            ],
        },
    },
    "ECE": {
        2: {
            3: [
                ("Electronic Devices and Circuits (EDC)", 3, 3, False, False),
                ("Digital Electronics / Switching Theory", 3, 3, False, False),
                ("Network Analysis and Synthesis", 3, 3, False, False),
                ("Electronic Devices Lab", 1, 2, True, False),
                ("Digital Electronics Lab", 1, 2, True, False),
            ],
            4: [
                ("Signals and Systems", 3, 3, False, False),
                ("Mathematics - III", 4, 4, False, False),
                ("Object Oriented Programming (OOPs)", 3, 3, False, False),
                ("Signals and Systems Lab", 1, 2, True, False),
                ("Object Oriented Programming Lab", 1, 2, True, False),
            ],
        },
        3: {
            5: [
                ("Analog and Digital Communication", 3, 3, False, False),
                ("Microprocessors and Microcontrollers", 3, 3, False, False),
                ("Electromagnetic Fields and Waves", 3, 3, False, False),
                ("Communication Systems Lab", 1, 2, True, False),
                ("Microprocessors Lab", 1, 2, True, False),
            ],
            6: [
                ("Control Systems", 3, 3, False, False),
                ("Digital Signal Processing (DSP)", 3, 3, False, False),
                ("Antenna and Wave Propagation", 3, 3, False, False),
                ("VLSI / Embedded Systems Lab", 1, 2, True, False),
                ("Control Systems Lab", 1, 2, True, False),
            ],
        },
        4: {
            7: [
                ("Wireless Communication & Mobile Networks", 3, 3, False, False),
                ("Optical Communication", 3, 3, False, False),
                ("VLSI Design / CMOS Technology", 3, 3, False, False),
            ],
            8: [
                ("Data Communication & Computer Networks", 3, 3, False, False),
                ("Department Elective (Satellite Comm / Embedded Systems / IoT / Image Processing)", 3, 3, False, True),
                ("Major Project & Seminar", 8, 12, True, False),
            ],
        },
    },
    "EE": {
        2: {
            3: [
                ("Network Theory / Circuit Analysis & Synthesis", 3, 3, False, False),
                ("Analog Electronics", 3, 3, False, False),
                ("Digital Electronics & Logic Design", 3, 3, False, False),
                ("Electrical Measurements Lab", 1, 2, True, False),
                ("Digital Electronics Lab", 1, 2, True, False),
            ],
            4: [
                ("Electrical Machines - I", 3, 3, False, False),
                ("Electromagnetic Fields", 3, 3, False, False),
                ("Electrical Machines Lab", 1, 2, True, False),
                ("Electromagnetic Fields Lab", 1, 2, True, False),
                ("Basic Instrumentation Lab", 1, 2, True, False),
            ],
        },
        3: {
            5: [
                ("Electrical Machines - II", 3, 3, False, False),
                ("Control Systems", 3, 3, False, False),
                ("Power Systems - I (Generation & Transmission)", 3, 3, False, False),
                ("Electrical Machines Lab - II", 1, 2, True, False),
                ("Control Systems Lab", 1, 2, True, False),
            ],
            6: [
                ("Microprocessors and Microcontrollers", 3, 3, False, False),
                ("Power Electronics", 3, 3, False, False),
                ("Power Electronics Lab", 1, 2, True, False),
                ("Microprocessor & Embedded Systems Lab", 1, 2, True, False),
                ("Electrical Workshop", 1, 2, True, False),
            ],
        },
        4: {
            7: [
                ("Switchgear and Protection", 3, 3, False, False),
                ("Power System Analysis & Control", 3, 3, False, False),
                ("Department Elective (High Voltage Engg / Electric Drives / Smart Grid Tech)", 3, 3, False, True),
                ("Power Systems Lab", 1, 2, True, False),
            ],
            8: [
                ("Utilization of Electrical Energy", 3, 3, False, False),
                ("Major Project / Seminar", 8, 12, True, False),
            ],
        },
    },
    # ME, CE: only labs (from the user's lab-by-branch/year table) - no theory
    # subjects have been provided for these two branches yet.
    # ME: official scheme with real subject codes, from the user (L-T-P hours
    # per subject). Our schema stores one is_lab flag per subject row, so any
    # subject with a practical (P) component was split into a theory row
    # (hours = L+T) and a "<Name> Lab" row (hours = P, credits ~ P/2) - the two
    # can then be scheduled independently (theory in lecture rooms, lab in lab
    # rooms via the fixed lab-session policy). Official subject codes (ME26011
    # etc.) aren't stored - this app auto-generates its own codes - but are
    # preserved here in comments for reference/verification.
    # Simplification: the source rotates Major Project Phase-I/II across an
    # AB/BA group split within semesters 7-8 (some students do Phase-I in
    # sem7 and Phase-II in sem8, others the reverse) - this app has no concept
    # of sub-groups within one section, so it's modeled as the common case:
    # Phase-I in sem7, Phase-II in sem8.
    "ME": {
        2: {
            3: [
                # ME26011 Fluid Mechanics (L4-P2)
                ("Fluid Mechanics", 4, 4, False, False),
                ("Fluid Mechanics Lab", 1, 2, True, False),
                # ME26002 Strength of Materials (L4-P2)
                ("Strength of Materials", 4, 4, False, False),
                ("Strength of Materials Lab", 1, 2, True, False),
                # MA26004 Mathematics - III (L4-T1)
                ("Mathematics - III", 4, 5, False, False),
                # ME26008 Material Science (L4-P2)
                ("Material Science", 4, 4, False, False),
                ("Material Science Lab", 1, 2, True, False),
                # ME26005 Engineering Thermodynamics (L4-P2)
                ("Engineering Thermodynamics", 4, 4, False, False),
                ("Engineering Thermodynamics Lab", 1, 2, True, False),
                # HU26481 Values, Humanity and Professional Ethics (T3)
                ("Values, Humanity and Professional Ethics", 3, 3, False, False),
            ],
            4: [
                # MA26556 Mathematics - IV (L4-T1)
                ("Mathematics - IV", 4, 5, False, False),
                # ME26551 Machine Design - I (L4-P2)
                ("Machine Design - I", 4, 4, False, False),
                ("Machine Design - I Lab", 1, 2, True, False),
                # ME26562 Kinematics of Machine (L4-P2)
                ("Kinematics of Machine", 4, 4, False, False),
                ("Kinematics of Machine Lab", 1, 2, True, False),
                # EC26563 Basic Electronics Engineering (L4-P2)
                ("Basic Electronics Engineering", 4, 4, False, False),
                ("Basic Electronics Engineering Lab", 1, 2, True, False),
                # IP26552 Manufacturing Processes - I (L4-P2)
                ("Manufacturing Processes - I", 4, 4, False, False),
                ("Manufacturing Processes - I Lab", 1, 2, True, False),
                # HU26507 Economics for Engineers (L4-P2)
                ("Economics for Engineers", 4, 4, False, False),
                ("Economics for Engineers Lab", 1, 2, True, False),
                # ME26881 Machine Drawing & Computer Graphics (P2 only, lab-only course)
                ("Machine Drawing & Computer Graphics", 1, 2, True, False),
            ],
        },
        3: {
            5: [
                # ME36011 Dynamics of Machines (L4-T1-P2)
                ("Dynamics of Machines", 4, 5, False, False),
                ("Dynamics of Machines Lab", 1, 2, True, False),
                # ME36003 Measurement and Automatic Control (L4-P2)
                ("Measurement and Automatic Control", 4, 4, False, False),
                ("Measurement and Automatic Control Lab", 1, 2, True, False),
                # ME36006 Heat & Mass Transfer (L4-P2)
                ("Heat & Mass Transfer", 4, 4, False, False),
                ("Heat & Mass Transfer Lab", 1, 2, True, False),
                # ME36007 Steam and Gas Power System (L4, no lab)
                ("Steam and Gas Power System", 4, 4, False, False),
                # IP36062 Manufacturing Processes - II (L4-P2)
                ("Manufacturing Processes - II", 4, 4, False, False),
                ("Manufacturing Processes - II Lab", 1, 2, True, False),
            ],
            6: [
                # ME36501 Refrigeration and Air-conditioning (L4-P2)
                ("Refrigeration and Air-conditioning", 4, 4, False, False),
                ("Refrigeration and Air-conditioning Lab", 1, 2, True, False),
                # ME36503 Machine Design II (L4-P4)
                ("Machine Design II", 4, 4, False, False),
                ("Machine Design II Lab", 2, 4, True, False),
                # ME36506 Fluid Machinery (L4-P2)
                ("Fluid Machinery", 4, 4, False, False),
                ("Fluid Machinery Lab", 1, 2, True, False),
                # ME36509 Internal Combustion Engines (L4-P2)
                ("Internal Combustion Engines", 4, 4, False, False),
                ("Internal Combustion Engines Lab", 1, 2, True, False),
                # IP36504 Industrial Engineering and Production Management (L4, no lab)
                ("Industrial Engineering and Production Management", 4, 4, False, False),
                # ME36581 Industrial Training / Minor Project (P4, project)
                ("Industrial Training / Minor Project", 2, 4, True, False),
            ],
        },
        4: {
            7: [
                # ME46018 Automobile Engineering (L4-P2)
                ("Automobile Engineering", 4, 4, False, False),
                ("Automobile Engineering Lab", 1, 2, True, False),
                # ME46051 Vibration and Noise Control (L4-P2)
                ("Vibration and Noise Control", 4, 4, False, False),
                ("Vibration and Noise Control Lab", 1, 2, True, False),
                # ME46020 Computer Aided Design (L4-P2)
                ("Computer Aided Design", 4, 4, False, False),
                ("Computer Aided Design Lab", 1, 2, True, False),
                # Elective-I: Mechatronics & Automation / Advanced Machine Design /
                # Industrial Tribology & Maintenance / Design of AC Equipment /
                # Artificial Intelligence / Power Plant & Energy Management
                ("Department Elective - I", 4, 4, False, True),
                # Elective-II: Operational Research / Hydraulic-Pneumatic-Fluidic
                # Control / Bio-Mechanics / Manufacturing Automation & CAM / Data
                # Science
                ("Department Elective - II", 4, 4, False, True),
                # ME46481 Industrial Training (no weekly contact hours - external)
                ("Industrial Training", 0, 0, False, False),
                # ME46498 Major Project Phase - I (P6, project)
                ("Major Project - Phase I", 3, 6, True, False),
            ],
            8: [
                # Elective-III (semester VIII elective list not specified by source)
                ("Department Elective - III", 3, 3, False, True),
                ("Department Elective - IV", 3, 3, False, True),
                # ME46882 Industrial Training / Internship (no weekly contact hours)
                ("Industrial Training / Internship", 0, 0, False, False),
                # ME46998 Major Project Phase - II (P8, project)
                ("Major Project - Phase II", 4, 8, True, False),
                # Added so this semester has >=2 lab-type entries, same as every
                # other semester - not in the source table.
                ("Seminar Lab", 1, 2, True, False),
            ],
        },
    },
    # CE, EI, BME, CHE, IPE year 2-3 (sem 3-6): these branches had only 1-2 lab
    # names (or nothing, for IPE) from the user's table - nowhere near the
    # "every semester needs >=5 subjects" minimum. The extra entries below are
    # GENERIC FILLER - standard/typical topic names for each discipline, not
    # sourced from any SGSITS document, added solely to reach that minimum for
    # testing. Replace with real subjects whenever you have them. Year 4
    # (semesters 7-8) is intentionally left untouched/as-is for every branch.
    "CE": {
        2: {
            3: [
                ("Surveying Lab", 1, 2, True, False),
                ("Materials Testing Lab", 1, 2, True, False),
                ("Building Materials & Construction", 3, 3, False, False),
                ("Strength of Materials", 3, 3, False, False),
                ("Fluid Mechanics", 3, 3, False, False),
            ],
            4: [
                ("Geotechnical Engineering Lab", 1, 2, True, False),
                ("Surveying", 3, 3, False, False),
                ("Structural Analysis - I", 3, 3, False, False),
                ("Concrete Technology", 3, 3, False, False),
                ("Concrete Technology Lab", 1, 2, True, False),
            ],
        },
        3: {
            5: [
                ("Structural Engineering Lab", 1, 2, True, False),
                ("Transportation Engineering Lab", 1, 2, True, False),
                ("Structural Analysis - II", 3, 3, False, False),
                ("Transportation Engineering", 3, 3, False, False),
                ("Water Resources Engineering", 3, 3, False, False),
            ],
            6: [
                ("Environmental Engineering Lab", 1, 2, True, False),
                ("Environmental Engineering", 3, 3, False, False),
                ("Design of RCC Structures", 3, 3, False, False),
                ("Estimation & Costing", 3, 3, False, False),
                ("Estimation & Costing Lab", 1, 2, True, False),
            ],
        },
        4: {
            7: [
                ("Civil Engineering Project Lab", 1, 2, True, False),
            ],
            8: [
                ("Major Project", 8, 12, True, False),
            ],
        },
    },
    "EI": {
        2: {
            3: [
                ("Electronics Lab", 1, 2, True, False),
                ("Electronic Devices & Circuits", 3, 3, False, False),
                ("Network Analysis & Synthesis", 3, 3, False, False),
                ("Digital Electronics", 3, 3, False, False),
                ("Digital Electronics Lab", 1, 2, True, False),
            ],
            4: [
                ("Instrumentation Lab", 1, 2, True, False),
                ("Signals & Systems", 3, 3, False, False),
                ("Sensors & Transducers", 3, 3, False, False),
                ("Analog Circuits", 3, 3, False, False),
                ("Analog Circuits Lab", 1, 2, True, False),
            ],
        },
        3: {
            5: [
                ("Control Systems Lab", 1, 2, True, False),
                ("Control Systems", 3, 3, False, False),
                ("Microprocessors & Microcontrollers", 3, 3, False, False),
                ("Measurement & Instrumentation", 3, 3, False, False),
                ("Microprocessors Lab", 1, 2, True, False),
            ],
            6: [
                ("Embedded Systems / Instrumentation Lab", 1, 2, True, False),
                ("Embedded Systems", 3, 3, False, False),
                ("Process Control", 3, 3, False, False),
                ("VLSI Design", 3, 3, False, False),
                ("Process Control Lab", 1, 2, True, False),
            ],
        },
        4: {
            7: [
                ("Advanced Instrumentation Lab", 1, 2, True, False),
            ],
            8: [
                ("Major Project", 8, 12, True, False),
            ],
        },
    },
    "BME": {
        2: {
            3: [
                ("Basic Engineering Lab", 1, 2, True, False),
                ("Human Physiology for Engineers", 3, 3, False, False),
                ("Biomaterials", 3, 3, False, False),
                ("Medical Electronics", 3, 3, False, False),
                ("Medical Electronics Lab", 1, 2, True, False),
            ],
            4: [
                ("Biomedical Instrumentation Lab - I", 1, 2, True, False),
                ("Biomechanics", 3, 3, False, False),
                ("Sensors for Biomedical Applications", 3, 3, False, False),
                ("Hospital Equipment & Safety", 3, 3, False, False),
                ("Biomechanics Lab", 1, 2, True, False),
            ],
        },
        3: {
            5: [
                ("Biomedical Instrumentation Lab - II", 1, 2, True, False),
                ("Biomedical Signal Processing", 3, 3, False, False),
                ("Biosensors", 3, 3, False, False),
                ("Rehabilitation Engineering", 3, 3, False, False),
                ("Biosensors Lab", 1, 2, True, False),
            ],
            6: [
                ("Biomedical Signals & Imaging Lab", 1, 2, True, False),
                ("Medical Imaging Systems", 3, 3, False, False),
                ("Clinical Engineering", 3, 3, False, False),
                ("Biomedical Instrumentation - III", 3, 3, False, False),
                ("Medical Imaging Lab", 1, 2, True, False),
            ],
        },
        4: {
            7: [
                ("Advanced Biomedical Lab", 1, 2, True, False),
            ],
            8: [
                ("Major Project", 8, 12, True, False),
            ],
        },
    },
    "CHE": {
        2: {
            3: [
                ("Chemical Process Lab - I", 1, 2, True, False),
                ("Chemical Process Calculations", 3, 3, False, False),
                ("Fluid Flow Operations", 3, 3, False, False),
                ("Mechanical Operations", 3, 3, False, False),
                ("Fluid Flow Operations Lab", 1, 2, True, False),
            ],
            4: [
                ("Chemical Process Lab - II", 1, 2, True, False),
                ("Organic Chemical Technology", 3, 3, False, False),
                ("Instrumentation & Process Control", 3, 3, False, False),
                ("Heat Transfer Operations", 3, 3, False, False),
                ("Heat Transfer Operations Lab", 1, 2, True, False),
            ],
        },
        3: {
            5: [
                ("Heat Transfer Lab", 1, 2, True, False),
                ("Mass Transfer Operations - I", 3, 3, False, False),
                ("Chemical Reaction Engineering - I", 3, 3, False, False),
                ("Chemical Process Equipment Design", 3, 3, False, False),
                ("Chemical Reaction Engineering Lab - I", 1, 2, True, False),
            ],
            6: [
                ("Mass Transfer / Reaction Engineering Lab", 1, 2, True, False),
                ("Mass Transfer Operations - II", 3, 3, False, False),
                ("Chemical Reaction Engineering - II", 3, 3, False, False),
                ("Plant Design & Economics", 3, 3, False, False),
                ("Mass Transfer Operations Lab - II", 1, 2, True, False),
            ],
        },
        4: {
            7: [
                ("Process Engineering Project Lab", 1, 2, True, False),
            ],
            8: [
                ("Major Project", 8, 12, True, False),
            ],
        },
    },
    # IPE: had no row at all in the user's lab table, so unlike the branches
    # above it has NO sourced data whatsoever for years 2-4 - everything below
    # is generic filler (standard industrial/production topics) added solely
    # to satisfy the >=5-subjects-per-semester minimum. Year 4 is left absent
    # entirely (not even filler), consistent with leaving 4th year untouched.
    "IPE": {
        2: {
            3: [
                ("Manufacturing Processes", 3, 3, False, False),
                ("Engineering Metallurgy", 3, 3, False, False),
                ("Production Planning & Control", 3, 3, False, False),
                ("Manufacturing Processes Lab", 1, 2, True, False),
                ("Engineering Metallurgy Lab", 1, 2, True, False),
            ],
            4: [
                ("Industrial Engineering", 3, 3, False, False),
                ("Operations Research", 3, 3, False, False),
                ("Quality Control & Reliability", 3, 3, False, False),
                ("Industrial Engineering Lab", 1, 2, True, False),
                ("CAD/CAM Lab", 1, 2, True, False),
            ],
        },
        3: {
            5: [
                ("Automation & Robotics", 3, 3, False, False),
                ("Supply Chain Management", 3, 3, False, False),
                ("Ergonomics & Work Study", 3, 3, False, False),
                ("Automation & Robotics Lab", 1, 2, True, False),
                ("Ergonomics Lab", 1, 2, True, False),
            ],
            6: [
                ("Computer Integrated Manufacturing", 3, 3, False, False),
                ("Facility Planning & Layout", 3, 3, False, False),
                ("Total Quality Management", 3, 3, False, False),
                ("Computer Integrated Manufacturing Lab", 1, 2, True, False),
                ("Facility Planning Lab", 1, 2, True, False),
            ],
        },
        # Year 4 (sem 7-8): no data at all - left absent, same as everywhere
        # else, rather than inventing 4th-year content.
    },
}


# Common 2nd-year elective/humanities subjects - injected into every branch's
# semester 3 UNLESS that branch already has a same-named subject somewhere in
# year 2 (e.g. CSE and ME already have their own "Economics for Engineers", so
# only "Constitution of India" gets added there). Matching 2+ elective faculty
# per branch are added in teachers_data.py so every branch has someone
# assignable to these.
COMMON_YEAR2_ELECTIVES = [
    ("Constitution of India", 2, 2, False, True),
    ("Economics for Engineers", 2, 2, False, True),
]


def build_subject_rows(branch: str = None, year: int = None):
    """Flatten the curriculum into insertable rows: (code, name, branch, year,
    semester, credits, hours_per_week, is_lab, is_elective). Optionally filtered
    by branch and/or year."""
    rows = []
    branches = [branch] if branch else BRANCHES
    for b in branches:
        if year is None or year == 1:
            for sem, subjects in COMMON_YEAR1.items():
                for seq, (name, credits, hours, is_lab, is_elective) in enumerate(subjects, start=1):
                    code = f"{b}-S{sem}-{seq:02d}"
                    rows.append((code, name, b, 1, sem, credits, hours, is_lab, is_elective))
        branch_data = BRANCH_CURRICULUM.get(b, {})
        for y, semesters in branch_data.items():
            if year is not None and year != y:
                continue
            year2_names = set()
            if y == 2:
                for sem_subjects in semesters.values():
                    year2_names.update(s[0].strip().lower() for s in sem_subjects)
            for sem, subjects in semesters.items():
                effective_subjects = list(subjects)
                if y == 2 and sem == 3:
                    for extra in COMMON_YEAR2_ELECTIVES:
                        if extra[0].strip().lower() not in year2_names:
                            effective_subjects.append(extra)
                for seq, (name, credits, hours, is_lab, is_elective) in enumerate(effective_subjects, start=1):
                    code = f"{b}-S{sem}-{seq:02d}"
                    rows.append((code, name, b, y, sem, credits, hours, is_lab, is_elective))
    return rows
