// frontend/src/pages/AssignSubject.tsx
import { useState, useEffect, useCallback } from "react";
import { store, BRANCHES, YEARS } from "@/lib/store";
import { toast } from "sonner";

interface SubjectResponse {
  id: string | number;
  code: string;
  name: string;
  branch: string;
  year: number;
}

interface TeacherResponse {
  id: string | number;
  name: string;
  department: string;
  email: string;
}

const AssignSubject = () => {
  const [branch, setBranch] = useState("");
  const [year, setYear] = useState("1st Year");
  const [subjectId, setSubjectId] = useState("");
  const [teacherId, setTeacherId] = useState("");
  const [section, setSection] = useState("");
  const [subjects, setSubjects] = useState<SubjectResponse[]>([]);
  const [teachers, setTeachers] = useState<TeacherResponse[]>([]);

  const loadSubjects = useCallback(async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/subjects/${branch}/${parseInt(year)}`, {
        headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
      });
      const data = await response.json();
      setSubjects(data.subjects || []);
    } catch (error) {
      console.error("Error loading subjects:", error);
    }
  }, [branch, year]);

  const loadTeachers = useCallback(async () => {
    try {
      const response = await fetch("http://localhost:8000/api/teachers", {
        headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
      });
      const data = await response.json();
      setTeachers(data.teachers || []);
    } catch (error) {
      console.error("Error loading teachers:", error);
    }
  }, []);

  useEffect(() => {
    loadSubjects();
    loadTeachers();
  }, [branch, year, loadSubjects, loadTeachers]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!branch || !subjectId || !teacherId || !section) { 
      toast.error("All fields are required"); 
      return; 
    }
    
    try {
      const response = await fetch("http://localhost:8000/api/admin/subjects/assign", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("token")}`
        },
        body: JSON.stringify({ 
          subject_id: parseInt(subjectId), 
          teacher_id: parseInt(teacherId), 
          section,
          branch,
          year: parseInt(year)
        })
      });
      const data = await response.json();
      if (data.success) {
        toast.success("Subject assigned successfully!");
        setSubjectId("");
        setTeacherId("");
        setSection("");
      } else {
        toast.error(data.message || "Assignment failed");
      }
    } catch (error) {
      toast.error("Failed to assign subject");
    }
  };

  return (
    <div className="bg-card/60 backdrop-blur-md rounded-xl p-8 border border-border">
      <h2 className="text-2xl font-bold mb-6">🔗 Assign Subject to Teacher & Section</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Branch *</label>
            <select 
              value={branch} 
              onChange={e => setBranch(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
            >
              <option value="">Select Branch</option>
              {BRANCHES.map((b, idx) => <option key={`branch-${idx}`} value={b}>{b}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Year *</label>
            <select 
              value={year} 
              onChange={e => setYear(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
            >
              {YEARS.map((y, idx) => <option key={`year-${idx}`} value={y}>{y}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Subject *</label>
            <select 
              value={subjectId} 
              onChange={e => setSubjectId(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
            >
              <option value="">Select Subject</option>
              {subjects.map((s, idx) => (
                <option key={`subject-${s.id || idx}`} value={s.id}>
                  {s.name} ({s.code})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Teacher *</label>
            <select 
              value={teacherId} 
              onChange={e => setTeacherId(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
            >
              <option value="">Select Teacher</option>
              {teachers.map((t, idx) => (
                <option key={`teacher-${t.id || idx}`} value={t.id}>
                  {t.name} ({t.department})
                </option>
              ))}
            </select>
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Section *</label>
          <input 
            value={section} 
            onChange={e => setSection(e.target.value)} 
            placeholder="e.g., A, B, C" 
            className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none" 
          />
        </div>
        <button type="submit" className="px-6 py-2.5 rounded-lg text-primary-foreground font-medium" style={{ background: "var(--gradient-nebula)" }}>
          🔗 Assign Subject
        </button>
      </form>
    </div>
  );
};

export default AssignSubject;