// frontend/src/lib/store.ts - This is the ONLY file you need to add!

export const BRANCHES = ["CSE", "EE", "ME", "ECE", "CE", "IT", "EI", "IPE", "BME", "CHE"];
export const YEARS = ["1st Year", "2nd Year", "3rd Year", "4th Year"];
export const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

// Only CSE and IT run multiple sections (A, B, ...) at SGSITS - every other
// branch is a single section, always "A". Forms should hide the Section field
// for those branches and default it to "A" rather than asking.
export const MULTI_SECTION_BRANCHES = ["CSE", "IT"];
export const hasMultipleSections = (branch: string) => MULTI_SECTION_BRANCHES.includes(branch);

export interface Teacher {
  id: string;
  name: string;
  department: string;
  email: string;
  maxHoursPerDay: number;
}

export interface Subject {
  id: string;
  code: string;
  name: string;
  branch: string;
  year: string;
  semester: string;
  credits: number;
  hoursPerWeek: number;
  isLab: boolean;
}

export interface Section {
  id: string;
  branch: string;
  year: string;
  name: string;
  studentCount: number;
}

export interface Assignment {
  id: string;
  branch: string;
  year: string;
  subjectId: string;
  teacherId: string;
  section: string;
}

export interface TimetableEntry {
  day: string;
  period: number;
  subjectCode: string;
  teacherName: string;
}

export interface Timetable {
  branch: string;
  year: string;
  section: string;
  entries: TimetableEntry[];
}

// Simple in-memory store (replace with API calls later)
class Store {
  private teachers: Teacher[] = [];
  private subjects: Subject[] = [];
  private sections: Section[] = [];
  private assignments: Assignment[] = [];
  private timetables: Timetable[] = [];

  constructor() {
    this.loadFromLocalStorage();
  }

  private saveToLocalStorage() {
    localStorage.setItem('timetable_teachers', JSON.stringify(this.teachers));
    localStorage.setItem('timetable_subjects', JSON.stringify(this.subjects));
    localStorage.setItem('timetable_sections', JSON.stringify(this.sections));
    localStorage.setItem('timetable_assignments', JSON.stringify(this.assignments));
    localStorage.setItem('timetable_timetables', JSON.stringify(this.timetables));
  }

  private loadFromLocalStorage() {
    const teachers = localStorage.getItem('timetable_teachers');
    const subjects = localStorage.getItem('timetable_subjects');
    const sections = localStorage.getItem('timetable_sections');
    const assignments = localStorage.getItem('timetable_assignments');
    const timetables = localStorage.getItem('timetable_timetables');
    
    if (teachers) this.teachers = JSON.parse(teachers);
    if (subjects) this.subjects = JSON.parse(subjects);
    if (sections) this.sections = JSON.parse(sections);
    if (assignments) this.assignments = JSON.parse(assignments);
    if (timetables) this.timetables = JSON.parse(timetables);
    
    // Add sample data if empty
    if (this.teachers.length === 0) this.addSampleData();
  }

  private addSampleData() {
    // Sample teachers
    this.addTeacher({ name: "Dr. Rahul Sharma", department: "CSE", email: "rahul@sgsits.edu", maxHoursPerDay: 6 });
    this.addTeacher({ name: "Prof. Neha Verma", department: "CSE", email: "neha@sgsits.edu", maxHoursPerDay: 6 });
    this.addTeacher({ name: "Dr. Amit Tiwari", department: "EE", email: "amit@sgsits.edu", maxHoursPerDay: 5 });
    
    // Sample subjects
    this.addSubject({ code: "CS301", name: "Data Structures", branch: "CSE", year: "2nd Year", semester: "Semester 3", credits: 4, hoursPerWeek: 4, isLab: false });
    this.addSubject({ code: "CS302", name: "Algorithms", branch: "CSE", year: "2nd Year", semester: "Semester 4", credits: 4, hoursPerWeek: 4, isLab: false });
    this.addSubject({ code: "EE201", name: "Circuit Theory", branch: "EE", year: "2nd Year", semester: "Semester 3", credits: 3, hoursPerWeek: 3, isLab: false });
  }

  // Teacher methods
  getTeachers(): Teacher[] { return this.teachers; }
  
  addTeacher(data: Omit<Teacher, 'id'>): Teacher {
    const newTeacher = { ...data, id: Date.now().toString() };
    this.teachers.push(newTeacher);
    this.saveToLocalStorage();
    return newTeacher;
  }

  // Subject methods
  getSubjects(): Subject[] { return this.subjects; }
  
  addSubject(data: Omit<Subject, 'id'>): Subject {
    const newSubject = { ...data, id: Date.now().toString() };
    this.subjects.push(newSubject);
    this.saveToLocalStorage();
    return newSubject;
  }

  // Section methods
  getSections(): Section[] { return this.sections; }
  
  addSection(data: Omit<Section, 'id'>): Section {
    const newSection = { ...data, id: Date.now().toString() };
    this.sections.push(newSection);
    this.saveToLocalStorage();
    return newSection;
  }

  // Assignment methods
  getAssignments(): Assignment[] { return this.assignments; }
  
  addAssignment(data: Omit<Assignment, 'id'>): Assignment {
    const newAssignment = { ...data, id: Date.now().toString() };
    this.assignments.push(newAssignment);
    this.saveToLocalStorage();
    return newAssignment;
  }

  // Timetable methods
  getTimetables(): Timetable[] { return this.timetables; }
  
  generateTimetable(branch: string, year: string, section: string): Timetable {
    const assignments = this.assignments.filter(a => a.branch === branch && a.year === year && a.section === section);
    const subjects = this.subjects;
    const teachers = this.teachers;
    
    const entries: TimetableEntry[] = [];
    const days = DAYS;
    const periods = 7;
    
    // Simple scheduling algorithm
    assignments.forEach((assignment, index) => {
      const subject = subjects.find(s => s.id === assignment.subjectId);
      const teacher = teachers.find(t => t.id === assignment.teacherId);
      
      if (subject && teacher) {
        const day = days[index % days.length];
        const period = (index % periods) + 1;
        
        entries.push({
          day,
          period,
          subjectCode: subject.code,
          teacherName: teacher.name
        });
      }
    });
    
    const timetable = { branch, year, section, entries };
    this.timetables.push(timetable);
    this.saveToLocalStorage();
    return timetable;
  }
}

export const store = new Store();