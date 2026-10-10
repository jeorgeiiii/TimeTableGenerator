// frontend/src/components/ClassroomPicker.tsx
// Pick the home classroom (lecture room) for a whole class or for each of
// its sections. Every theory period of that section is held there; labs are
// placed in the department's lab rooms automatically.
import { useEffect, useMemo, useState } from "react";
import { DoorOpen, Loader2, Save } from "lucide-react";
import { toast } from "sonner";
import api from "../services/api";
import type { ClassInfo } from "@/hooks/use-class-sections";

interface Room { id: number; room_code: string; capacity: number; is_lab: boolean | number }

interface Props {
  branch: string;
  year: number;
  /** Sections to show a picker for: ["A"] for a whole class. */
  targets: string[];
  info: ClassInfo | null;
  onSaved: () => void;
}

const select = "flex-1 min-w-[180px] px-3 py-2 rounded-lg bg-background/50 border border-border text-sm focus:ring-2 focus:ring-primary focus:outline-none";

const ClassroomPicker = ({ branch, year, targets, info, onSaved }: Props) => {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [homes, setHomes] = useState<Record<number, string[]>>({}); // room_id -> group codes using it
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);

  const loadHomes = () =>
    api.get("/classes").then(r => {
      const map: Record<number, string[]> = {};
      for (const c of r.data.classes as ClassInfo[])
        for (const s of c.sections)
          if (s.room_id) (map[s.room_id] ||= []).push(s.group_code);
      setHomes(map);
    }).catch(() => {});

  useEffect(() => {
    api.get("/rooms").then(r => setRooms((r.data.rooms || []).filter((x: Room) => !x.is_lab))).catch(() => {});
    loadHomes();
  }, []);
  useEffect(() => { setDrafts({}); }, [branch, year]);

  const current = useMemo(() => {
    const m: Record<string, number | null> = {};
    for (const s of info?.sections ?? []) m[s.section] = s.room_id;
    return m;
  }, [info]);

  const save = async (section: string) => {
    const value = drafts[section] ?? String(current[section] ?? "");
    setBusy(section);
    try {
      const r = await api.put(`/admin/sections/${branch}/${year}/${section}/room`, { room_id: value ? Number(value) : null });
      toast.success(r.data.home_room
        ? `${targets.length > 1 || info?.has_sections ? `Section ${section}` : "Class"} classroom set to ${r.data.home_room}. Regenerate its timetable to apply.`
        : "Classroom cleared - the generator will pick one automatically.");
      if (r.data.warning) toast.warning(r.data.warning);
      setDrafts(d => { const n = { ...d }; delete n[section]; return n; });
      onSaved();
      loadHomes();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to set classroom");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="rounded-lg border border-border bg-background/30 p-4 space-y-3">
      <div>
        <h3 className="font-semibold flex items-center gap-2"><DoorOpen size={16} /> Classroom</h3>
        <p className="text-xs text-muted-foreground">
          The lecture room where every theory class is held. Labs go to the {branch || "branch's"} department labs automatically.
          Leave it on "Pick automatically" to let the generator choose a free room.
        </p>
      </div>
      {/* Always visible, so it's clear where rooms are set - with a hint until there's a class to set it for. */}
      {!branch && <p className="text-sm text-muted-foreground">Select a <strong>Branch</strong> above to choose its classroom.</p>}
      {branch && !targets.length && <p className="text-sm text-muted-foreground">Select a <strong>Section</strong> above (or "All sections") to choose its classroom.</p>}
      {branch && targets.map(section => {
        const value = drafts[section] ?? String(current[section] ?? "");
        const changed = value !== String(current[section] ?? "");
        const myCode = `${branch}${year}${section}`;
        return (
          <div key={section} className="flex flex-wrap items-center gap-2">
            {(targets.length > 1 || info?.has_sections) && <span className="w-24 text-sm font-medium">Section {section}</span>}
            <select value={value} onChange={e => setDrafts(d => ({ ...d, [section]: e.target.value }))} className={select}
              aria-label={`Classroom for section ${section}`}>
              <option value="">Pick automatically</option>
              {rooms.map(r => {
                const users = (homes[r.id] || []).filter(g => g !== myCode);
                return (
                  <option key={r.id} value={r.id}>
                    {r.room_code} (cap. {r.capacity}){users.length ? ` — classroom of ${users.join(", ")}` : ""}
                  </option>
                );
              })}
            </select>
            <button type="button" onClick={() => save(section)} disabled={!changed || busy === section}
              className="inline-flex items-center gap-1 px-3 py-2 rounded-lg border border-border text-sm hover:bg-muted/30 disabled:opacity-40">
              {busy === section ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} Save
            </button>
          </div>
        );
      })}
    </div>
  );
};

export default ClassroomPicker;
