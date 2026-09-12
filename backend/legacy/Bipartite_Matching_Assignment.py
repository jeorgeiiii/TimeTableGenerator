# Bipartite_Matching_Assignment.py - Enhanced with Teacher Collision Prevention for FastAPI

import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# ============ DATA CLASSES ============

@dataclass
class Teacher:
    """Teacher with availability and schedule tracking"""
    id: str
    name: str
    department: str
    max_hours_per_day: int = 6
    unavailable_slots: List[str] = field(default_factory=list)
    schedule: Dict[str, str] = field(default_factory=dict)  # slot_id -> course_id
    
    def is_available(self, slot_id: str) -> bool:
        return slot_id not in self.schedule and slot_id not in self.unavailable_slots
    
    def assign_slot(self, slot_id: str, course_id: str) -> bool:
        if self.is_available(slot_id):
            self.schedule[slot_id] = course_id
            return True
        return False
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "department": self.department,
            "schedule": self.schedule
        }


@dataclass
class StudentGroup:
    """Student group/section with schedule tracking"""
    id: str
    name: str
    semester: int
    department: str
    student_count: int = 0
    schedule: Dict[str, str] = field(default_factory=dict)  # slot_id -> course_id
    
    def is_available(self, slot_id: str) -> bool:
        return slot_id not in self.schedule
    
    def assign_slot(self, slot_id: str, course_id: str) -> bool:
        if self.is_available(slot_id):
            self.schedule[slot_id] = course_id
            return True
        return False
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "semester": self.semester,
            "department": self.department,
            "student_count": self.student_count,
            "schedule": self.schedule
        }


@dataclass
class Room:
    """Room/classroom with capacity and schedule"""
    id: str
    name: str
    capacity: int
    room_type: str = "lecture"  # lecture, lab, auditorium
    has_projector: bool = False
    schedule: Dict[str, str] = field(default_factory=dict)  # slot_id -> course_id
    
    def is_available(self, slot_id: str) -> bool:
        return slot_id not in self.schedule
    
    def can_accommodate(self, student_count: int) -> bool:
        return self.capacity >= student_count
    
    def assign_slot(self, slot_id: str, course_id: str) -> bool:
        if self.is_available(slot_id):
            self.schedule[slot_id] = course_id
            return True
        return False
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "capacity": self.capacity,
            "room_type": self.room_type,
            "schedule": self.schedule
        }


@dataclass
class TimeSlot:
    """Time slot definition"""
    id: str
    day: int  # 0=Monday, 1=Tuesday, etc.
    day_name: str
    start_time: str
    end_time: str
    name: str
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "day": self.day,
            "day_name": self.day_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "name": self.name
        }


@dataclass
class Course:
    """Course with teacher and group assignments"""
    id: str
    name: str
    code: str
    teacher_id: str
    group_id: str
    hours_per_week: int = 3
    is_lab: bool = False
    preferred_room: Optional[str] = None
    priority: int = 1  # Higher = scheduled first
    assigned_slots: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "teacher_id": self.teacher_id,
            "group_id": self.group_id,
            "hours_per_week": self.hours_per_week,
            "is_lab": self.is_lab,
            "assigned_slots": self.assigned_slots
        }


# ============ BIPARTITE MATCHING ALGORITHM (Original) ============

class BipartiteGraph():
    def __init__(self, V1, V2, E=[], W=None):
        self.V1 = set(V1)
        self.V2 = set(V2)
        self.V = self.V1 | self.V2
        self.Adj = {v: set() for v in self.V}
        for (v1, v2) in E:
            self.Adj[v1].add(v2)
            self.Adj[v2].add(v1)
        
        if W is not None:
            self.W = {tuple(e): W[k] for (k, (u, v)) in enumerate(E) for e in [(u, v), (v, u)]}
        self.E = set(tuple(e) for e in E)


def MaximumCardinalityMatching(B, M=[], returnLabeled=False):
    mate = {v: None for v in B.V}
    for (v1, v2) in M:
        mate[v1], mate[v2] = v2, v1
    
    label = {v: None for v in B.V}
    labeledV1, labeledV2 = set(), set()
    
    L = set(v for v in B.V1 if mate[v] is None)
    for v in L:
        label[v] = '*'
    
    while L:
        v = L.pop()
        if v in B.V1:
            labeledV1.add(v)
            for u in B.Adj[v]:
                if u != mate[v]:
                    label[u] = v
                    L.add(u)
        else:
            labeledV2.add(v)
            if mate[v] is None:
                while v != '*':
                    u = label[v]
                    mate[u], mate[v] = v, u
                    v = label[u]
                
                label = {v: None for v in B.V}
                L = set(v for v in B.V1 if mate[v] is None)
                for v in L:
                    label[v] = '*'
            else:
                u = mate[v]
                label[u] = v
                L.add(u)
    
    M = [(v1, v2) for (v1, v2) in B.E if mate[v1] == v2]
    
    if returnLabeled:
        return M, labeledV1, labeledV2
    return M


def AssignmentProblem(B):
    d = {v: max(B.W[(v, u)] for u in B.Adj[v]) for v in B.V}
    modW = {(u, v): (B.W[(u, v)] - d[u] - d[v]) for (u, v) in B.E}
    
    M = []
    while True:
        modB = BipartiteGraph(B.V1, B.V2, E=[e for e in B.E if abs(modW[e]) < 1e-6])
        M, lV1, lV2 = MaximumCardinalityMatching(modB, M, returnLabeled=True)
        
        if len(M) != len(B.V1):
            delta = min(-modW[(v1, v2)] for v1 in lV1 for v2 in B.V2 - lV2)
            
            for v1 in lV1:
                d[v1] -= delta / 2
            for v2 in lV2:
                d[v2] += delta / 2
            for v1 in B.V1 - lV1:
                d[v1] += delta / 2
            for v2 in B.V2 - lV2:
                d[v2] -= delta / 2
            
            modW = {(u, v): (B.W[(u, v)] - d[u] - d[v]) for (u, v) in B.E}
        else:
            break
    
    return M


# ============ ENHANCED TIMETABLE SCHEDULER ============

class TimetableScheduler:
    """Enhanced scheduler with collision prevention and bipartite matching"""
    
    def __init__(self):
        self.teachers: Dict[str, Teacher] = {}
        self.student_groups: Dict[str, StudentGroup] = {}
        self.rooms: Dict[str, Room] = {}
        self.time_slots: Dict[str, TimeSlot] = {}
        self.courses: List[Course] = []
        self.conflicts: List[Dict] = []
        self.assignments: List[Dict] = []  # Store successful assignments
        
    # ============ ADD METHODS ============
    
    def add_teacher(self, teacher_id: str, name: str, department: str, max_hours: int = 6) -> Teacher:
        self.teachers[teacher_id] = Teacher(teacher_id, name, department, max_hours)
        return self.teachers[teacher_id]
    
    def add_student_group(self, group_id: str, name: str, semester: int, 
                          department: str, student_count: int = 0) -> StudentGroup:
        self.student_groups[group_id] = StudentGroup(group_id, name, semester, department, student_count)
        return self.student_groups[group_id]
    
    def add_room(self, room_id: str, name: str, capacity: int, 
                 room_type: str = "lecture", has_projector: bool = False) -> Room:
        self.rooms[room_id] = Room(room_id, name, capacity, room_type, has_projector)
        return self.rooms[room_id]
    
    def add_time_slot(self, slot_id: str, day: int, day_name: str, 
                      start_time: str, end_time: str, name: str) -> TimeSlot:
        self.time_slots[slot_id] = TimeSlot(slot_id, day, day_name, start_time, end_time, name)
        return self.time_slots[slot_id]
    
    def add_course(self, course_id: str, name: str, code: str, teacher_id: str,
                   group_id: str, hours_per_week: int = 3, is_lab: bool = False,
                   preferred_room: Optional[str] = None, priority: int = 1) -> Course:
        course = Course(course_id, name, code, teacher_id, group_id, 
                       hours_per_week, is_lab, preferred_room, priority)
        self.courses.append(course)
        return course
    
    # ============ CONFLICT CHECKING METHODS ============
    
    def check_teacher_conflict(self, teacher_id: str, slot_id: str) -> bool:
        """Check if teacher is already assigned to this slot"""
        teacher = self.teachers.get(teacher_id)
        if teacher:
            return not teacher.is_available(slot_id)
        return False
    
    def check_group_conflict(self, group_id: str, slot_id: str) -> bool:
        """Check if student group already has a class at this slot"""
        group = self.student_groups.get(group_id)
        if group:
            return not group.is_available(slot_id)
        return False
    
    def check_room_conflict(self, room_id: str, slot_id: str) -> bool:
        """Check if room is already booked at this slot"""
        room = self.rooms.get(room_id)
        if room:
            return not room.is_available(slot_id)
        return False
    
    def check_all_conflicts(self, course: Course, slot_id: str, room_id: str) -> List[str]:
        """Check all possible conflicts for a course assignment"""
        conflicts = []
        
        # Teacher conflict
        if self.check_teacher_conflict(course.teacher_id, slot_id):
            teacher = self.teachers.get(course.teacher_id)
            conflicts.append(f"Teacher {teacher.name if teacher else course.teacher_id} already has a class at this time")
        
        # Student group conflict
        if self.check_group_conflict(course.group_id, slot_id):
            group = self.student_groups.get(course.group_id)
            conflicts.append(f"Group {group.name if group else course.group_id} already has a class at this time")
        
        # Room conflict
        if self.check_room_conflict(room_id, slot_id):
            room = self.rooms.get(room_id)
            conflicts.append(f"Room {room.name if room else room_id} is already booked at this time")
        
        # Room capacity check
        group = self.student_groups.get(course.group_id)
        room = self.rooms.get(room_id)
        if group and room and not room.can_accommodate(group.student_count):
            conflicts.append(f"Room capacity ({room.capacity}) insufficient for {group.student_count} students")
        
        # Lab room check
        if course.is_lab and room and room.room_type != "lab":
            conflicts.append(f"Course '{course.name}' requires a lab room, but '{room.name}' is a {room.room_type} room")
        
        # Teacher max hours per day check (simplified)
        teacher = self.teachers.get(course.teacher_id)
        if teacher:
            # Count how many classes teacher has on this day
            slot = self.time_slots.get(slot_id)
            if slot:
                daily_classes = sum(1 for s_id, _ in teacher.schedule.items() 
                                  if s_id in self.time_slots and self.time_slots[s_id].day == slot.day)
                if daily_classes >= teacher.max_hours_per_day:
                    conflicts.append(f"Teacher {teacher.name} would exceed {teacher.max_hours_per_day} hours on this day")
        
        return conflicts
    
    def assign_course_to_slot(self, course: Course, slot_id: str, room_id: str) -> Tuple[bool, List[str]]:
        """Assign a course to a specific slot and room with conflict checking"""
        conflicts = self.check_all_conflicts(course, slot_id, room_id)
        
        if conflicts:
            self.conflicts.append({
                'course_id': course.id,
                'course_name': course.name,
                'slot_id': slot_id,
                'room_id': room_id,
                'conflicts': conflicts
            })
            return False, conflicts
        
        # Make the assignment
        teacher = self.teachers.get(course.teacher_id)
        group = self.student_groups.get(course.group_id)
        room = self.rooms.get(room_id)
        
        if teacher:
            teacher.assign_slot(slot_id, course.id)
        if group:
            group.assign_slot(slot_id, course.id)
        if room:
            room.assign_slot(slot_id, course.id)
        
        course.assigned_slots.append(slot_id)
        self.assignments.append({
            'course_id': course.id,
            'course_name': course.name,
            'teacher_id': course.teacher_id,
            'group_id': course.group_id,
            'room_id': room_id,
            'slot_id': slot_id,
            'slot_name': self.time_slots[slot_id].name if slot_id in self.time_slots else slot_id
        })
        
        return True, []
    
    # ============ TIMETABLE GENERATION ============

    def _unassign_slot(self, course: 'Course', slot_id: str, room_id: str) -> None:
        """Undo a single slot assignment made by assign_course_to_slot (used to roll
        back a partially-placed lab block when one of its slots can't be placed)."""
        teacher = self.teachers.get(course.teacher_id)
        group = self.student_groups.get(course.group_id)
        room = self.rooms.get(room_id)

        if teacher and teacher.schedule.get(slot_id) == course.id:
            del teacher.schedule[slot_id]
        if group and group.schedule.get(slot_id) == course.id:
            del group.schedule[slot_id]
        if room and room.schedule.get(slot_id) == course.id:
            del room.schedule[slot_id]
        if slot_id in course.assigned_slots:
            course.assigned_slots.remove(slot_id)
        if self.assignments and self.assignments[-1]['course_id'] == course.id \
                and self.assignments[-1]['slot_id'] == slot_id:
            self.assignments.pop()

    def _room_priority_for(self, course: 'Course') -> List[str]:
        room_priority = []
        if course.preferred_room and course.preferred_room in self.rooms:
            room_priority.append(course.preferred_room)
        room_priority.extend([r for r in self.rooms.keys() if r != course.preferred_room])
        return room_priority

    def _assign_lab_course(self, course: 'Course', slots_by_day: Dict[int, List[str]],
                            group_lab_days: Dict[str, set]) -> int:
        """Assign a lab course as 2-hour consecutive blocks ("2 box" double periods),
        placing at most one lab session per day for the group so sessions spread
        across the week (e.g. 6 lab hours -> 3 sessions on 3 different days)."""
        hours_assigned = 0
        used_days = group_lab_days.setdefault(course.group_id, set())
        room_priority = self._room_priority_for(course)

        remaining = course.hours_per_week
        while remaining > 0:
            block_size = 2 if remaining >= 2 else 1

            # Prefer days this group has no lab on yet, so sessions spread out
            # one-per-day instead of stacking on the same day.
            day_order = [d for d in slots_by_day if d not in used_days]

            block_assigned = False
            for day in day_order:
                day_slots = slots_by_day[day]

                for i in range(len(day_slots) - block_size + 1):
                    candidate_slots = day_slots[i:i + block_size]

                    for room_id in room_priority:
                        if room_id not in self.rooms:
                            continue

                        placed = []
                        ok = True
                        for slot_id in candidate_slots:
                            success, _ = self.assign_course_to_slot(course, slot_id, room_id)
                            if not success:
                                ok = False
                                break
                            placed.append(slot_id)

                        if ok:
                            hours_assigned += len(placed)
                            remaining -= len(placed)
                            used_days.add(day)
                            block_assigned = True
                            break
                        else:
                            for slot_id in reversed(placed):
                                self._unassign_slot(course, slot_id, room_id)

                    if block_assigned:
                        break
                if block_assigned:
                    break

            if not block_assigned:
                break  # no free day/room can fit this session - stop, leave remainder unassigned

        return hours_assigned

    def generate_timetable(self, priority_order: str = "lab") -> Dict:
        """Generate timetable using priority-based assignment"""

        # Clear previous schedules
        self.clear_all_schedules()
        self.conflicts = []
        self.assignments = []

        # Sort courses by priority
        if priority_order == "lab":
            # Labs first
            self.courses.sort(key=lambda c: (not c.is_lab, -c.priority))
        elif priority_order == "teacher":
            # Sort by teacher workload (teachers with fewer courses first)
            teacher_course_count = {}
            for c in self.courses:
                teacher_course_count[c.teacher_id] = teacher_course_count.get(c.teacher_id, 0) + 1
            self.courses.sort(key=lambda c: (teacher_course_count.get(c.teacher_id, 0), -c.priority))
        elif priority_order == "hours":
            # Courses with more hours first
            self.courses.sort(key=lambda c: (-c.hours_per_week, -c.priority))

        assigned_count = 0
        total_hours = sum(c.hours_per_week for c in self.courses)
        failed_courses = []

        # Slots grouped by day, ordered by start time, so lab blocks can be
        # placed as consecutive same-day pairs ("2 box" double periods).
        slots_by_day: Dict[int, List[str]] = {}
        for slot_id, slot in self.time_slots.items():
            slots_by_day.setdefault(slot.day, []).append(slot_id)
        for day in slots_by_day:
            slots_by_day[day].sort(key=lambda sid: self.time_slots[sid].start_time)

        # Tracks which days already have a lab session for each group, so labs
        # for that group land one-per-day and spread across the week.
        group_lab_days: Dict[str, set] = {}

        for course in self.courses:
            hours_assigned = 0

            if course.is_lab:
                hours_assigned = self._assign_lab_course(course, slots_by_day, group_lab_days)
                assigned_count += hours_assigned
            else:
                # Try to assign each required hour
                while hours_assigned < course.hours_per_week:
                    assigned = False

                    room_priority = self._room_priority_for(course)

                    for room_id in room_priority:
                        if room_id not in self.rooms:
                            continue

                        # Try each time slot
                        for slot_id in self.time_slots.keys():
                            success, _ = self.assign_course_to_slot(course, slot_id, room_id)
                            if success:
                                assigned = True
                                assigned_count += 1
                                hours_assigned += 1
                                break

                        if assigned:
                            break

                    if not assigned:
                        break

            if hours_assigned < course.hours_per_week:
                failed_courses.append({
                    'course_id': course.id,
                    'course_name': course.name,
                    'hours_assigned': hours_assigned,
                    'hours_needed': course.hours_per_week
                })

        return {
            'success': len(failed_courses) == 0,
            'assigned_count': assigned_count,
            'total_hours': total_hours,
            'completion_rate': (assigned_count / total_hours * 100) if total_hours > 0 else 0,
            'failed_courses': failed_courses,
            'conflicts': self.conflicts,
            'assignments': self.assignments
        }

    # ============ GETTER METHODS ============
    
    def get_teacher_schedule(self, teacher_id: str) -> Dict:
        """Get formatted schedule for a teacher"""
        teacher = self.teachers.get(teacher_id)
        if not teacher:
            return {}
        
        schedule = {}
        for slot_id, course_id in teacher.schedule.items():
            slot = self.time_slots.get(slot_id)
            course = next((c for c in self.courses if c.id == course_id), None)
            if slot and course:
                schedule[f"{slot.day_name} {slot.start_time}-{slot.end_time}"] = {
                    'course_id': course.id,
                    'course_name': course.name,
                    'course_code': course.code,
                    'group_id': course.group_id
                }
        return schedule
    
    def get_group_schedule(self, group_id: str) -> Dict:
        """Get formatted schedule for a student group"""
        group = self.student_groups.get(group_id)
        if not group:
            return {}
        
        schedule = {}
        for slot_id, course_id in group.schedule.items():
            slot = self.time_slots.get(slot_id)
            course = next((c for c in self.courses if c.id == course_id), None)
            if slot and course:
                # Find which room this course is in
                room_id = None
                for rid, room in self.rooms.items():
                    if room.schedule.get(slot_id) == course_id:
                        room_id = rid
                        break
                
                schedule[f"{slot.day_name} {slot.start_time}-{slot.end_time}"] = {
                    'course_id': course.id,
                    'course_name': course.name,
                    'course_code': course.code,
                    'teacher_id': course.teacher_id,
                    'room_id': room_id,
                    'room_name': self.rooms[room_id].name if room_id and room_id in self.rooms else None
                }
        return schedule
    
    def get_room_schedule(self, room_id: str) -> Dict:
        """Get formatted schedule for a room"""
        room = self.rooms.get(room_id)
        if not room:
            return {}
        
        schedule = {}
        for slot_id, course_id in room.schedule.items():
            slot = self.time_slots.get(slot_id)
            course = next((c for c in self.courses if c.id == course_id), None)
            if slot and course:
                schedule[f"{slot.day_name} {slot.start_time}-{slot.end_time}"] = {
                    'course_id': course.id,
                    'course_name': course.name,
                    'teacher_id': course.teacher_id,
                    'group_id': course.group_id
                }
        return schedule
    
    def get_all_schedules(self) -> Dict:
        """Get all schedules in one object"""
        return {
            'teachers': {tid: self.get_teacher_schedule(tid) for tid in self.teachers},
            'groups': {gid: self.get_group_schedule(gid) for gid in self.student_groups},
            'rooms': {rid: self.get_room_schedule(rid) for rid in self.rooms}
        }
    
    def clear_all_schedules(self):
        """Clear all schedules for fresh generation"""
        for teacher in self.teachers.values():
            teacher.schedule = {}
        for group in self.student_groups.values():
            group.schedule = {}
        for room in self.rooms.values():
            room.schedule = {}
        for course in self.courses:
            course.assigned_slots = []
        self.assignments = []
        self.conflicts = []
    
    # ============ EXPORT METHODS ============
    
    def to_dict(self) -> Dict:
        """Export entire scheduler state to dictionary"""
        return {
            'teachers': {tid: t.to_dict() for tid, t in self.teachers.items()},
            'student_groups': {gid: g.to_dict() for gid, g in self.student_groups.items()},
            'rooms': {rid: r.to_dict() for rid, r in self.rooms.items()},
            'time_slots': {sid: s.to_dict() for sid, s in self.time_slots.items()},
            'courses': [c.to_dict() for c in self.courses],
            'assignments': self.assignments,
            'conflicts': self.conflicts
        }
    
    def to_json(self) -> str:
        """Export entire scheduler state to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    def export_timetable_to_txt(self, filename: str = "generated_timetable.txt") -> str:
        """Export timetable to formatted text file"""
        content = []
        content.append("=" * 80)
        content.append("GENERATED TIMETABLE")
        content.append("=" * 80)
        content.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        content.append("")
        
        # Student Group Schedules
        content.append("=" * 80)
        content.append("STUDENT GROUP SCHEDULES")
        content.append("=" * 80)
        
        for group_id, group in self.student_groups.items():
            content.append(f"\n📚 {group.name} (Semester {group.semester}, {group.department})")
            content.append("-" * 40)
            schedule = self.get_group_schedule(group_id)
            if schedule:
                for time, info in sorted(schedule.items()):
                    content.append(f"  {time}: {info['course_name']} ({info['course_code']})")
                    content.append(f"      Room: {info['room_name']}, Teacher: {info['teacher_id']}")
            else:
                content.append("  No classes assigned")
        
        # Teacher Schedules
        content.append("\n" + "=" * 80)
        content.append("TEACHER SCHEDULES")
        content.append("=" * 80)
        
        for teacher_id, teacher in self.teachers.items():
            content.append(f"\n👨‍🏫 {teacher.name} ({teacher.department})")
            content.append("-" * 40)
            schedule = self.get_teacher_schedule(teacher_id)
            if schedule:
                for time, info in sorted(schedule.items()):
                    content.append(f"  {time}: {info['course_name']} ({info['course_code']}) - {info['group_id']}")
            else:
                content.append("  No classes assigned")
        
        # Room Schedules
        content.append("\n" + "=" * 80)
        content.append("ROOM SCHEDULES")
        content.append("=" * 80)
        
        for room_id, room in self.rooms.items():
            content.append(f"\n🏠 {room.name} (Capacity: {room.capacity}, Type: {room.room_type})")
            content.append("-" * 40)
            schedule = self.get_room_schedule(room_id)
            if schedule:
                for time, info in sorted(schedule.items()):
                    content.append(f"  {time}: {info['course_name']} - {info['group_id']}")
            else:
                content.append("  No classes assigned")
        
        # Conflict Report
        if self.conflicts:
            content.append("\n" + "=" * 80)
            content.append("CONFLICT REPORT")
            content.append("=" * 80)
            for conflict in self.conflicts:
                content.append(f"\n⚠ Course: {conflict['course_name']}")
                for c in conflict['conflicts']:
                    content.append(f"   - {c}")
        
        # Write to file
        output = "\n".join(content)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(output)
        
        return output


# ============ FACTORY FUNCTION FOR FASTAPI ============

def create_timetable_scheduler() -> TimetableScheduler:
    """Create a fully configured timetable scheduler for FastAPI"""
    scheduler = TimetableScheduler()
    
    # Add default teachers
    default_teachers = [
        ("T001", "Prof. Abhijeet", "CSE", 6),
        ("T002", "Prof. Subhit", "Mathematics", 6),
        ("T003", "Prof. Sharma", "Physics", 5),
        ("T004", "Prof. Patel", "Chemistry", 5),
        ("T005", "Prof. Kumar", "CSE", 6),
    ]
    
    for tid, name, dept, hours in default_teachers:
        scheduler.add_teacher(tid, name, dept, hours)
    
    # Add default student groups
    default_groups = [
        ("G001", "SE Comp A", 3, "CSE", 60),
        ("G002", "SE Comp B", 3, "CSE", 58),
        ("G003", "TE Comp A", 5, "CSE", 55),
        ("G004", "TE Comp B", 5, "CSE", 53),
        ("G005", "TE Mech A", 5, "ME", 50),
    ]
    
    for gid, name, sem, dept, count in default_groups:
        scheduler.add_student_group(gid, name, sem, dept, count)
    
    # Add default rooms
    default_rooms = [
        ("R101", "Room 101", 60, "lecture", True),
        ("R102", "Room 102", 50, "lecture", False),
        ("R103", "Room 103", 50, "lecture", False),
        ("R201", "Room 201", 80, "lecture", True),
        ("R202", "Room 202", 70, "lecture", True),
        ("LAB1", "Computer Lab 1", 40, "lab", True),
        ("LAB2", "Computer Lab 2", 40, "lab", True),
        ("LAB3", "Chemistry Lab", 40, "lab", False),
        ("LAB4", "Physics Lab", 40, "lab", False),
    ]
    
    for rid, name, cap, rtype, proj in default_rooms:
        scheduler.add_room(rid, name, cap, rtype, proj)
    
    # Add time slots (Monday to Friday)
    days = [
        (0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), 
        (3, "Thursday"), (4, "Friday")
    ]
    times = [
        ("08:00", "09:00", "S1"), ("09:00", "10:00", "S2"),
        ("10:00", "11:00", "S3"), ("11:00", "12:00", "S4"),
        ("12:00", "13:00", "S5"), ("14:00", "15:00", "S6"),
        ("15:00", "16:00", "S7"), ("16:00", "17:00", "S8")
    ]
    
    slot_counter = 1
    for day_idx, day_name in days:
        for start, end, name in times:
            scheduler.add_time_slot(
                f"SLOT{slot_counter}", day_idx, day_name, start, end, 
                f"{day_name[:3]}-{name}"
            )
            slot_counter += 1
    
    # Add default courses
    default_courses = [
        ("C001", "Basic Electrical Engineering", "BEE101", "T001", "G001", 3, False, "R101", 1),
        ("C002", "Basic Electrical Engineering", "BEE101", "T001", "G002", 3, False, "R102", 1),
        ("C003", "Mathematics 2", "MATH201", "T002", "G001", 4, False, "R103", 2),
        ("C004", "Mathematics 2", "MATH201", "T002", "G002", 4, False, "R103", 2),
        ("C005", "Engineering Physics", "PHY101", "T003", "G001", 3, False, "R201", 1),
        ("C006", "Engineering Physics Lab", "PHY101L", "T003", "G001", 2, True, "LAB4", 3),
        ("C007", "Data Structures", "CS201", "T005", "G003", 4, False, "R201", 2),
        ("C008", "Data Structures Lab", "CS201L", "T005", "G003", 2, True, "LAB1", 3),
        ("C009", "Organic Chemistry", "CHEM101", "T004", "G004", 3, False, "R202", 1),
        ("C010", "Chemistry Lab", "CHEM101L", "T004", "G004", 2, True, "LAB3", 3),
    ]
    
    for cid, name, code, tid, gid, hours, lab, room, priority in default_courses:
        scheduler.add_course(cid, name, code, tid, gid, hours, lab, room, priority)
    
    return scheduler


# ============ RUN EXAMPLE ============

def create_sample_timetable():
    """Create and generate a sample timetable (for testing)"""
    print("=" * 60)
    print("Creating Timetable Scheduler...")
    print("=" * 60)
    
    scheduler = create_timetable_scheduler()
    
    print(f"✅ Loaded {len(scheduler.teachers)} teachers")
    print(f"✅ Loaded {len(scheduler.student_groups)} student groups")
    print(f"✅ Loaded {len(scheduler.rooms)} rooms")
    print(f"✅ Loaded {len(scheduler.time_slots)} time slots")
    print(f"✅ Loaded {len(scheduler.courses)} courses")
    
    print("\n" + "=" * 60)
    print("Generating Timetable...")
    print("=" * 60)
    
    result = scheduler.generate_timetable(priority_order="lab")
    
    print(f"\n📊 Generation Results:")
    print(f"   Success: {result['success']}")
    print(f"   Assigned: {result['assigned_count']}/{result['total_hours']} hours")
    print(f"   Completion Rate: {result['completion_rate']:.1f}%")
    print(f"   Failed Courses: {len(result['failed_courses'])}")
    print(f"   Conflicts Detected: {len(result['conflicts'])}")
    
    # Export to file
    scheduler.export_timetable_to_txt("generated_timetable.txt")
    
    return scheduler


if __name__ == "__main__":
    scheduler = create_sample_timetable()