// frontend/src/pages/CreateSection.tsx
// Classes & Sections: for each branch and year, choose whether the class is
// taught as ONE WHOLE CLASS (no sections) or DIVIDED INTO SECTIONS (A, B,
// C...), add sections with a student count and home classroom, and remove
// sections. Assign Subject / Generate / View all read this setup.
import { useState, useEffect, useCallback } from "react";
import { BRANCHES, YEARS } from "@/lib/store";
import { toast } from "sonner";
import { Loader2, Plus, Trash2, Users, DoorOpen } from "lucide-react";
import api from "../services/api";
import type { ClassInfo } from "@/hooks/use-class-sections";

interface Room {
  id: number;
  room_code: string;
  capacity: number;
  is_lab: boolean | number;
}

const input = "px-3 py-2 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none text-sm";

const nextSectionName = (existing: string[]) => {
  for (let c = 65; c <= 90; c++) {
    const s = String.fromCharCode(c);
    if (!existing.includes(s)) return s;
  }
  return "";
};

const errMsg = (e: any, fallback: string) => {
  const d = e?.response?.data?.detail;
  return typeof d === "string" ? d : fallback;
};

const CreateSection = ({ onSuccess }: { onSuccess?: () => void } = {}) => {
  const [branch, setBranch] = useState("CSE");
  const [classes, setClasses] = useState<ClassInfo[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loading, setLoading] = useState(false);
  const [busyYear, setBusyYear] = useState<number | null>(null);
  // per-year "add section" form
  const [drafts, setDrafts] = useState<Record<number, { name: string; count: number; roomId: string }>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get("/classes", { params: { branch } });
      setClasses(r.data.classes || []);
    } catch (e) {
      toast.error(errMsg(e, "Failed to load classes"));
    } finally {
      setLoading(false);
    }
  }, [branch]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    api.get("/rooms").then(r => setRooms(r.data.rooms || [])).catch(() => {});
  }, []);

  const lectureRooms = rooms.filter(r => !r.is_lab);
  const draftFor = (c: ClassInfo) =>
    drafts[c.year] ?? { name: nextSectionName(c.sections.map(s => s.section)), count: 60, roomId: "" };
  const setDraft = (c: ClassInfo, patch: Partial<{ name: string; count: number; roomId: string }>) =>
    setDrafts(d => ({ ...d, [c.year]: { ...draftFor(c), ...patch } }));

  const done = async (year: number, msg: string) => {
    toast.success(msg);
    setDrafts(d => { const n = { ...d }; delete n[year]; return n; });
    await load();
    onSuccess?.();
  };

  const setMode = async (c: ClassInfo, hasSections: boolean) => {
    if (c.has_sections === hasSections) return;
    setBusyYear(c.year);
    try {
      await api.put("/admin/classes", { branch, year: c.year, has_sections: hasSections });
      await done(c.year, hasSections
        ? `${branch} ${YEARS[c.year - 1]} is now divided into sections`
        : `${branch} ${YEARS[c.year - 1]} is now one whole class`);
    } catch (e) {
      toast.error(errMsg(e, "Failed to change class setup"));
    } finally {
      setBusyYear(null);
    }
  };

  const addSection = async (c: ClassInfo) => {
    const d = draftFor(c);
    const name = d.name.trim().toUpperCase();
    if (!/^[A-Z]{1,2}$/.test(name)) {
      toast.error("Section name must be a letter, e.g. A, B, C");
      return;
    }
    setBusyYear(c.year);
    try {
      const r = await api.post("/admin/sections", {
        branch, year: c.year, section: name, student_count: d.count,
        room_id: d.roomId ? parseInt(d.roomId) : undefined,
      });
      if (r.data.warning) toast.warning(r.data.warning);
      await done(c.year, `Section ${r.data.group_code} created`);
    } catch (e) {
      toast.error(errMsg(e, "Failed to create section"));
    } finally {
      setBusyYear(null);
    }
  };

  const removeSection = async (c: ClassInfo, groupCode: string) => {
    if (!window.confirm(`Remove section ${groupCode}? Its teacher assignments and generated timetables are deleted too. This cannot be undone.`)) return;
    setBusyYear(c.year);
    try {
      await api.delete(`/admin/sections/${groupCode}`);
      await done(c.year, `Section ${groupCode} removed`);
    } catch (e) {
      toast.error(errMsg(e, "Failed to remove section"));
    } finally {
      setBusyYear(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-card/60 backdrop-blur-md rounded-xl p-8 border border-border">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold">📋 Classes &amp; Sections</h2>
            <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
              Choose, for each year, whether the class is taught as <strong>one whole class</strong> or
              <strong> divided into sections</strong> (A, B, C…). Each section gets its own teachers, timetable
              and home classroom. Assign Subject and Generate Timetable follow this setup.
            </p>
          </div>
          <div className="w-full md:w-48">
            <label className="block text-sm font-medium mb-1">Branch</label>
            <select value={branch} onChange={e => setBranch(e.target.value)} className={`${input} w-full`}>
              {BRANCHES.map(b => <option key={b} value={b}>{b}</option>)}
            </select>
          </div>
        </div>
      </div>

      {loading && !classes.length && (
        <div className="bg-card/60 rounded-xl p-8 border border-border flex items-center justify-center gap-2 text-muted-foreground">
          <Loader2 className="w-5 h-5 animate-spin" /> Loading classes…
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {classes.map(c => {
          const busy = busyYear === c.year;
          const d = draftFor(c);
          return (
            <div key={c.year} className="bg-card/60 backdrop-blur-md rounded-xl p-6 border border-border space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h3 className="text-lg font-bold">{branch} — {YEARS[c.year - 1]}</h3>
                <div className="inline-flex rounded-lg border border-border bg-background/40 p-1" role="radiogroup" aria-label="Class setup">
                  {([[false, "Whole class"], [true, "With sections"]] as const).map(([val, label]) => (
                    <button
                      key={label}
                      role="radio"
                      aria-checked={c.has_sections === val}
                      disabled={busy}
                      onClick={() => setMode(c, val)}
                      className={`px-3 py-1.5 rounded-md text-sm font-medium transition disabled:opacity-50 ${
                        c.has_sections === val ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              {!c.has_sections ? (
                <p className="text-sm text-muted-foreground">
                  Taught as one class — no section to pick when assigning subjects or generating.
                  {c.sections[0] && (
                    <span className="block mt-2 text-foreground">
                      <Users size={14} className="inline mr-1" />{c.sections[0].student_count} students
                      {c.sections[0].home_room && <> · <DoorOpen size={14} className="inline mx-1" />{c.sections[0].home_room}</>}
                    </span>
                  )}
                </p>
              ) : (
                <>
                  <ul className="space-y-2">
                    {c.sections.length === 0 && (
                      <li className="text-sm text-muted-foreground">No sections yet — add them below.</li>
                    )}
                    {c.sections.map(s => (
                      <li key={s.group_code} className="flex items-center justify-between gap-3 rounded-lg border border-border bg-background/30 px-3 py-2">
                        <span className="font-semibold">Section {s.section}</span>
                        <span className="text-sm text-muted-foreground flex-1">
                          <Users size={14} className="inline mr-1" />{s.student_count}
                          {s.home_room && <> · <DoorOpen size={14} className="inline mx-1" />{s.home_room}</>}
                        </span>
                        <button
                          onClick={() => removeSection(c, s.group_code)}
                          disabled={busy}
                          className="text-muted-foreground hover:text-destructive disabled:opacity-50"
                          aria-label={`Remove section ${s.section}`}
                          title="Remove section"
                        >
                          <Trash2 size={16} />
                        </button>
                      </li>
                    ))}
                  </ul>

                  <div className="flex flex-wrap items-end gap-2 pt-1">
                    <label className="block">
                      <span className="block text-xs text-muted-foreground mb-1">Section</span>
                      <input value={d.name} onChange={e => setDraft(c, { name: e.target.value.toUpperCase() })} maxLength={2} className={`${input} w-16`} />
                    </label>
                    <label className="block">
                      <span className="block text-xs text-muted-foreground mb-1">Students</span>
                      <input type="number" min={1} value={d.count} onChange={e => setDraft(c, { count: Number(e.target.value) })} className={`${input} w-20`} />
                    </label>
                    <label className="block flex-1 min-w-[140px]">
                      <span className="block text-xs text-muted-foreground mb-1">Home classroom</span>
                      <select value={d.roomId} onChange={e => setDraft(c, { roomId: e.target.value })} className={`${input} w-full`}>
                        <option value="">Pick automatically</option>
                        {lectureRooms.map(r => <option key={r.id} value={r.id}>{r.room_code} (cap. {r.capacity})</option>)}
                      </select>
                    </label>
                    <button
                      onClick={() => addSection(c)}
                      disabled={busy || !d.name}
                      className="inline-flex items-center gap-1 px-4 py-2 rounded-lg text-primary-foreground text-sm font-medium disabled:opacity-50"
                      style={{ background: "var(--gradient-nebula)" }}
                    >
                      {busy ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />} Add section
                    </button>
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default CreateSection;
