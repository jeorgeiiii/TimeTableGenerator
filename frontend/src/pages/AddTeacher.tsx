// frontend/src/pages/AddTeacher.tsx
import { useState, useEffect, useCallback } from "react";
import { BRANCHES } from "@/lib/store";
import { toast } from "sonner";

interface Teacher {
  id: string | number;
  name: string;
  department: string;
  email?: string;
  max_hours_per_day?: number;
}

const AddTeacher = () => {
  const [name, setName] = useState("");
  const [department, setDepartment] = useState("");
  const [email, setEmail] = useState("");
  const [maxHours, setMaxHours] = useState(6);
  const [teachers, setTeachers] = useState<Teacher[]>([]);

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
    if (!name || !department) { 
      toast.error("Name and Department are required"); 
      return; 
    }
    
    try {
      const response = await fetch("http://localhost:8000/api/admin/teachers", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("token")}`
        },
        body: JSON.stringify({ name, email, department })
      });
      const data = await response.json();
      if (data.success) {
        toast.success("Teacher added successfully!");
        setName("");
        setDepartment("");
        setEmail("");
        loadTeachers();
      } else {
        toast.error(data.message || "Failed to add teacher");
      }
    } catch (error) {
      toast.error("Failed to add teacher");
    }
  };

  return (
    <div className="bg-card/60 backdrop-blur-md rounded-xl p-8 border border-border">
      <h2 className="text-2xl font-bold mb-6">👨‍🏫 Add New Teacher</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Teacher Name *</label>
            <input 
              value={name} 
              onChange={e => setName(e.target.value)} 
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none" 
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Department *</label>
            <select 
              value={department} 
              onChange={e => setDepartment(e.target.value)} 
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
            >
              <option value="">Select Department</option>
              {BRANCHES.map((b, idx) => <option key={`dept-${idx}`} value={b}>{b}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <input 
              type="email" 
              value={email} 
              onChange={e => setEmail(e.target.value)} 
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none" 
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Max Hours/Day</label>
            <input 
              type="number" 
              value={maxHours} 
              onChange={e => setMaxHours(Number(e.target.value))} 
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none" 
            />
          </div>
        </div>
        <button type="submit" className="px-6 py-2.5 rounded-lg text-primary-foreground font-medium" style={{ background: "var(--gradient-nebula)" }}>
          + Add Teacher
        </button>
      </form>

      {teachers.length > 0 && (
        <div className="mt-8">
          <h3 className="text-lg font-bold mb-4">📋 Existing Teachers</h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Name</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Department</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Max Hours/Day</th>
                </tr>
              </thead>
              <tbody>
                {teachers.map((t, idx) => (
                  <tr key={`teacher-${t.id || idx}`} className="border-b border-border/50 hover:bg-muted/20">
                    <td className="py-3 px-4">{t.name}</td>
                    <td className="py-3 px-4">{t.department}</td>
                    <td className="py-3 px-4">{t.max_hours_per_day || 6}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default AddTeacher;