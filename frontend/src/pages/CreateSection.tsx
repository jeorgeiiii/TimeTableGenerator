// frontend/src/pages/CreateSection.tsx
import { useState, useEffect, useCallback } from "react";
import { BRANCHES, YEARS } from "@/lib/store";
import { toast } from "sonner";
import api from "../services/api";

interface Room {
  id: number;
  room_code: string;
  room_name: string;
  capacity: number;
  room_type: string;
  is_lab: boolean | number;
}

// Maps year label ("1st Year", "2nd Year", ...) to integer (1, 2, ...)
const yearLabelToInt = (yearLabel: string): number => {
  const idx = YEARS.indexOf(yearLabel);
  return idx >= 0 ? idx + 1 : 1;
};

const CreateSection = () => {
  const [branch, setBranch] = useState("");
  const [year, setYear] = useState("1st Year");
  const [name, setName] = useState("");
  const [count, setCount] = useState(60);
  const [roomId, setRoomId] = useState("");
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loading, setLoading] = useState(false);

  const loadRooms = useCallback(async () => {
    try {
      const response = await api.get("/rooms");
      setRooms(response.data.rooms || []);
    } catch (error) {
      console.error("Error loading rooms:", error);
    }
  }, []);

  useEffect(() => {
    loadRooms();
  }, [loadRooms]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!branch || !name) {
      toast.error("Branch and Section Name are required");
      return;
    }

    setLoading(true);
    try {
      const response = await api.post("/admin/sections", {
        branch,
        year: yearLabelToInt(year),
        section: name,
        student_count: count,
        room_id: roomId ? parseInt(roomId) : undefined,
      });
      const data = response.data;
      if (data.success) {
        toast.success(`Section ${data.group_code} created!`);
        if (data.warning) {
          toast.warning(data.warning);
        }
        setName("");
      } else {
        toast.error(data.message || "Failed to create section");
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to create section");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-card/60 backdrop-blur-md rounded-xl p-8 border border-border">
      <h2 className="text-2xl font-bold mb-6">📋 Create New Section</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Branch *</label>
            <select value={branch} onChange={e => setBranch(e.target.value)} className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none">
              <option value="">Select Branch</option>{BRANCHES.map(b => <option key={b} value={b}>{b}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Year *</label>
            <select value={year} onChange={e => setYear(e.target.value)} className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none">
              {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Section Name *</label>
            <input value={name} onChange={e => setName(e.target.value.toUpperCase())} placeholder="e.g., A, B, C" className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Student Count</label>
            <input type="number" value={count} onChange={e => setCount(Number(e.target.value))} className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Room (Optional)</label>
            <select value={roomId} onChange={e => setRoomId(e.target.value)} className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none">
              <option value="">No default room</option>
              {rooms.filter(r => !r.is_lab).map(r => (
                <option key={r.id} value={r.id}>{r.room_code} (cap. {r.capacity})</option>
              ))}
            </select>
            <p className="text-xs text-muted-foreground mt-1">
              Home room for this section's lectures. You'll be warned if another section already uses it.
            </p>
          </div>
        </div>
        <button type="submit" disabled={loading} className="px-6 py-2.5 rounded-lg text-primary-foreground font-medium disabled:opacity-50" style={{ background: "var(--gradient-nebula)" }}>
          {loading ? "Creating..." : "+ Create Section"}
        </button>
      </form>
    </div>
  );
};

export default CreateSection;
