// frontend/src/pages/AddSubject.tsx
import { useState, useEffect, useCallback } from "react";
import { BRANCHES, YEARS } from "@/lib/store";
import { toast } from "sonner";

interface Teacher {
  id: string | number;
  name: string;
  department?: string;
  email?: string;
}

const AddSubject = () => {
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [branch, setBranch] = useState("");
  const [year, setYear] = useState("1st Year");
  const [semester, setSemester] = useState("Semester 1");
  const [credits, setCredits] = useState(3);
  const [hours, setHours] = useState(3);
  const [isLab, setIsLab] = useState(false);
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [teacherId, setTeacherId] = useState("");
  const [teacher2Id, setTeacher2Id] = useState("");

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
    loadTeachers();
  }, [loadTeachers]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code || !name) { 
      toast.error("Code and Name are required"); 
      return; 
    }
    
    try {
      const response = await fetch("http://localhost:8000/api/admin/subjects", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("token")}`
        },
        body: JSON.stringify({ 
          code, 
          name, 
          branch, 
          year: parseInt(year), 
          teacher_id: parseInt(teacherId) || null,
          teacher2_id: parseInt(teacher2Id) || null
        })
      });
      const data = await response.json();
      if (data.success) {
        toast.success("Subject added!");
        setCode("");
        setName("");
        setTeacherId("");
        setTeacher2Id("");
      } else {
        toast.error(data.message || "Failed to add subject");
      }
    } catch (error) {
      toast.error("Failed to add subject");
    }
  };

  return (
    <div className="bg-card/60 backdrop-blur-md rounded-xl p-8 border border-border">
      <h2 className="text-2xl font-bold mb-6">📚 Add New Subject</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Subject Code *</label>
            <input 
              value={code} 
              onChange={e => setCode(e.target.value)} 
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none" 
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Subject Name *</label>
            <input 
              value={name} 
              onChange={e => setName(e.target.value)} 
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none" 
            />
          </div>
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
            <label className="block text-sm font-medium mb-1">Primary Teacher</label>
            <select 
              value={teacherId} 
              onChange={e => setTeacherId(e.target.value)} 
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
            >
              <option value="">Select Primary Teacher</option>
              {teachers.map((t, idx) => (
                <option key={`teacher-${t.id || idx}`} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Second Teacher (Optional)</label>
            <select 
              value={teacher2Id} 
              onChange={e => setTeacher2Id(e.target.value)} 
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
            >
              <option value="">Select Second Teacher</option>
              {teachers.map((t, idx) => (
                <option key={`teacher2-${t.id || idx}`} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Credits</label>
            <input 
              type="number" 
              value={credits} 
              onChange={e => setCredits(Number(e.target.value))} 
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none" 
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Hours/Week</label>
            <input 
              type="number" 
              value={hours} 
              onChange={e => setHours(Number(e.target.value))} 
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none" 
            />
          </div>
          <div className="flex items-center gap-3 pt-6">
            <input 
              type="checkbox" 
              checked={isLab} 
              onChange={e => setIsLab(e.target.checked)} 
              className="w-4 h-4 rounded border-border" 
            />
            <label className="text-sm font-medium">Is Lab Course?</label>
          </div>
        </div>
        <button type="submit" className="px-6 py-2.5 rounded-lg text-primary-foreground font-medium" style={{ background: "var(--gradient-nebula)" }}>
          + Add Subject
        </button>
      </form>
    </div>
  );
};

export default AddSubject;