# simple_scheduler.py - Simple working scheduler
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Teacher:
    id: str
    name: str
    department: str
    max_hours_per_day: int = 6
    schedule: Dict[str, str] = field(default_factory=dict)
    
    def is_available(self, slot_id: str) -> bool:
        return slot_id not in self.schedule
    
    def assign_slot(self, slot_id: str, course_id: str) -> bool:
        if self.is_available(slot_id):
            self.schedule[slot_id] = course_id
            return True
        return False
    
    def clear_schedule(self):
        self.schedule = {}


@dataclass
class StudentGroup:
    id: str
    name: str
    semester: int
    department: str
    student_count: int = 0
    schedule: Dict[str, str] = field(default_factory=dict)
    
    def is_available(self, slot_id: str) -> bool:
        return slot_id not in self.schedule
    
    def assign_slot(self, slot_id: str, course_id: str) -> bool:
        if self.is_available(slot_id):
            self.schedule[slot_id] = course_id
            return True
        return False
    
    def clear_schedule(self):
        self.schedule = {}


@dataclass
class Room:
    id: str
    name: str
    capacity: int
    room_type: str = "lecture"
    schedule: Dict[str, str] = field(default_factory=dict)
    
    def is_available(self, slot_id: str) -> bool:
        return slot_id not in self.schedule
    
    def assign_slot(self, slot_id: str, course_id: str) -> bool:
        if self.is_available(slot_id):
            self.schedule[slot_id] = course_id
            return True
        return False
    
    def clear_schedule(self):
        self.schedule = {}


@dataclass
class TimeSlot:
    id: str
    day: int
    day_name: str
    start_time: str
    end_time: str
    name: str


@dataclass
class Course:
    id: str
    name: str
    code: str
    teacher_id: str
    group_id: str
    hours_per_week: int = 3
    is_lab: bool = False
    preferred_room: Optional[str] = None


class TimetableScheduler:
    def __init__(self):
        self.teachers: Dict[str, Teacher] = {}
        self.student_groups: Dict[str, StudentGroup] = {}
        self.rooms: Dict[str, Room] = {}
        self.time_slots: Dict[str, TimeSlot] = {}
        self.courses: List[Course] = []
        self.assignments: List[Dict] = []
        self.conflicts: List[Dict] = []
    
    def add_teacher(self, teacher_id: str, name: str, department: str, max_hours: int = 6):
        self.teachers[teacher_id] = Teacher(teacher_id, name, department, max_hours)
    
    def add_student_group(self, group_id: str, name: str, semester: int, department: str, student_count: int = 0):
        self.student_groups[group_id] = StudentGroup(group_id, name, semester, department, student_count)
    
    def add_room(self, room_id: str, name: str, capacity: int, room_type: str = "lecture", has_projector: bool = False):
        self.rooms[room_id] = Room(room_id, name, capacity, room_type)
    
    def add_time_slot(self, slot_id: str, day: int, day_name: str, start_time: str, end_time: str, name: str):
        self.time_slots[slot_id] = TimeSlot(slot_id, day, day_name, start_time, end_time, name)
    
    def add_course(self, course_id: str, name: str, code: str, teacher_id: str, group_id: str, 
                   hours_per_week: int = 3, is_lab: bool = False, preferred_room: str = None):
        self.courses.append(Course(course_id, name, code, teacher_id, group_id, hours_per_week, is_lab, preferred_room))
    
    def check_teacher_conflict(self, teacher_id: str, slot_id: str) -> bool:
        teacher = self.teachers.get(teacher_id)
        return not teacher.is_available(slot_id) if teacher else False
    
    def check_group_conflict(self, group_id: str, slot_id: str) -> bool:
        group = self.student_groups.get(group_id)
        return not group.is_available(slot_id) if group else False
    
    def assign_course_to_slot(self, course: Course, slot_id: str, room_id: str) -> bool:
        if self.check_teacher_conflict(course.teacher_id, slot_id):
            return False
        if self.check_group_conflict(course.group_id, slot_id):
            return False
        
        teacher = self.teachers.get(course.teacher_id)
        group = self.student_groups.get(course.group_id)
        room = self.rooms.get(room_id)
        
        if teacher:
            teacher.assign_slot(slot_id, course.id)
        if group:
            group.assign_slot(slot_id, course.id)
        if room:
            room.assign_slot(slot_id, course.id)
        
        course.assigned_slots = getattr(course, 'assigned_slots', [])
        course.assigned_slots.append(slot_id)
        
        self.assignments.append({
            'course_id': course.id,
            'course_name': course.name,
            'teacher_id': course.teacher_id,
            'group_id': course.group_id,
            'room_id': room_id,
            'slot_id': slot_id,
        })
        return True
    
    def generate_timetable(self) -> Dict:
        self.clear_all_schedules()
        self.assignments = []
        
        assigned_count = 0
        total_hours = sum(c.hours_per_week for c in self.courses)
        
        for course in self.courses:
            hours_assigned = 0
            while hours_assigned < course.hours_per_week:
                assigned = False
                for slot_id in self.time_slots.keys():
                    for room_id in self.rooms.keys():
                        if self.assign_course_to_slot(course, slot_id, room_id):
                            assigned = True
                            assigned_count += 1
                            hours_assigned += 1
                            break
                    if assigned:
                        break
                if not assigned:
                    break
        
        return {
            'success': True,
            'assigned_count': assigned_count,
            'total_hours': total_hours,
            'completion_rate': (assigned_count / total_hours * 100) if total_hours > 0 else 0,
            'assignments': self.assignments,
            'conflicts': []
        }
    
    def clear_all_schedules(self):
        for teacher in self.teachers.values():
            teacher.clear_schedule()
        for group in self.student_groups.values():
            group.clear_schedule()
        for room in self.rooms.values():
            room.clear_schedule()
        for course in self.courses:
            course.assigned_slots = []


def create_scheduler():
    scheduler = TimetableScheduler()
    
    # Add default teachers
    teachers = [
        ("T001", "Prof. Abhijeet", "CSE", 6),
        ("T002", "Prof. Subhit", "Mathematics", 6),
        ("T003", "Prof. Sharma", "Physics", 5),
    ]
    for tid, name, dept, hours in teachers:
        scheduler.add_teacher(tid, name, dept, hours)
    
    # Add student groups
    groups = [
        ("G001", "SE Comp A", 3, "CSE", 60),
        ("G002", "SE Comp B", 3, "CSE", 58),
    ]
    for gid, name, sem, dept, count in groups:
        scheduler.add_student_group(gid, name, sem, dept, count)
    
    # Add rooms
    rooms = [
        ("R101", "Room 101", 60, "lecture"),
        ("R102", "Room 102", 50, "lecture"),
        ("LAB1", "Computer Lab", 40, "lab"),
    ]
    for rid, name, cap, rtype in rooms:
        scheduler.add_room(rid, name, cap, rtype)
    
    # Add time slots (Monday to Friday)
    days = [(0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"), (4, "Friday")]
    times = [
        ("09:00", "10:00", "S1"), ("10:00", "11:00", "S2"),
        ("11:00", "12:00", "S3"), ("12:00", "13:00", "S4"),
        ("14:00", "15:00", "S5"), ("15:00", "16:00", "S6"),
        ("16:00", "17:00", "S7")
    ]
    
    slot_counter = 1
    for day_idx, day_name in days:
        for start, end, name in times:
            scheduler.add_time_slot(f"SLOT{slot_counter}", day_idx, day_name, start, end, f"{day_name[:3]}-{name}")
            slot_counter += 1
    
    # Add courses
    courses = [
        ("C001", "Basic Electrical Engineering", "BEE101", "T001", "G001", 3),
        ("C002", "Mathematics 2", "MATH201", "T002", "G001", 4),
        ("C003", "Engineering Physics", "PHY101", "T003", "G001", 3),
    ]
    for cid, name, code, tid, gid, hours in courses:
        scheduler.add_course(cid, name, code, tid, gid, hours)
    
    return scheduler


if __name__ == "__main__":
    scheduler = create_scheduler()
    result = scheduler.generate_timetable()
    print(f"✅ Generated {result['assigned_count']}/{result['total_hours']} hours")
    print(f"📊 Completion: {result['completion_rate']:.1f}%")