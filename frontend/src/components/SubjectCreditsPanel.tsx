// frontend/src/components/SubjectCreditsPanel.tsx
// Shown under a timetable: every subject of that semester with its credits,
// L-T-P, the teacher assigned to this section, how many periods the
// generated timetable gave it, and where it's held.
import { useEffect, useState } from "react";
import { GraduationCap, Loader2 } from "lucide-react";
import api from "../services/api";

interface SubjectRow {
  code: string;
  name: string;
  credits: number;
  ltp: string | null;
  is_lab: boolean;
  is_elective: boolean;
  custom: boolean;
  teacher: string | null;
  periods_per_week: number;
  rooms: string[];
}

interface Summary {
  subjects: SubjectRow[];
  total_credits: number;
  assigned_credits: number;
  scheduled: boolean;
}

interface Props {
  branch: string;
  year: number;
  section: string;
  semester: number;
  /** Change this to refetch (e.g. after generating). */
  refreshKey?: unknown;
}

const SubjectCreditsPanel = ({ branch, year, section, semester, refreshKey }: Props) => {
  const [data, setData] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!branch || !year || !section) return;
    setLoading(true);
    api.get("/timetable/subjects", { params: { branch, year, section, semester } })
      .then(r => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [branch, year, section, semester, refreshKey]);

  if (loading && !data) {
    return (
      <div className="bg-card/60 backdrop-blur-md rounded-xl p-6 border border-border flex items-center gap-2 text-muted-foreground">
        <Loader2 className="w-4 h-4 animate-spin" /> Loading subjects &amp; credits…
      </div>
    );
  }
  if (!data) return null;

  return (
    <div className="bg-card/60 backdrop-blur-md rounded-xl p-6 border border-border overflow-x-auto">
      <div className="flex flex-wrap items-baseline justify-between gap-2 mb-3">
        <h3 className="text-lg font-bold flex items-center gap-2"><GraduationCap size={18} /> Subjects &amp; credits — Semester {semester}</h3>
        <p className="text-sm text-muted-foreground">
          <strong className="text-foreground">{data.total_credits}</strong> credits this semester
          {data.assigned_credits !== data.total_credits && <> · {data.assigned_credits} assigned to this section</>}
        </p>
      </div>
      {data.subjects.length === 0 ? (
        <p className="text-sm text-muted-foreground">No subjects for this semester yet — add them on Add Subject or Load Curriculum.</p>
      ) : (
        <table className="w-full text-sm min-w-[640px]">
          <thead>
            <tr className="text-left text-muted-foreground border-b border-border">
              <th className="py-2 pr-3 font-medium">Code</th>
              <th className="py-2 pr-3 font-medium">Subject</th>
              <th className="py-2 pr-3 font-medium">L-T-P</th>
              <th className="py-2 pr-3 font-medium text-right">Credits</th>
              <th className="py-2 pr-3 font-medium">Teacher</th>
              <th className="py-2 pr-3 font-medium text-right">Periods/wk</th>
              <th className="py-2 font-medium">Room</th>
            </tr>
          </thead>
          <tbody>
            {data.subjects.map(s => (
              <tr key={s.code} className={`border-b border-border/50 ${s.teacher ? "" : "text-muted-foreground"}`}>
                <td className="py-1.5 pr-3 font-mono text-xs">{s.code}</td>
                <td className="py-1.5 pr-3">
                  {s.name}
                  {s.is_lab && <span className="ml-1.5 text-[10px] uppercase border border-border rounded px-1">Lab</span>}
                  {s.is_elective && <span className="ml-1.5 text-[10px] uppercase border border-border rounded px-1">Elective</span>}
                  {s.custom && <span className="ml-1.5 text-[10px] uppercase border border-border rounded px-1">Custom</span>}
                </td>
                <td className="py-1.5 pr-3 font-mono text-xs">{s.ltp ?? "—"}</td>
                <td className="py-1.5 pr-3 text-right tabular-nums font-semibold">
                  {s.credits === 0 ? <span className="font-normal text-muted-foreground">0 (audit)</span> : s.credits}
                </td>
                <td className="py-1.5 pr-3">{s.teacher ?? <span className="italic">not assigned</span>}</td>
                <td className="py-1.5 pr-3 text-right tabular-nums">{data.scheduled ? s.periods_per_week : "—"}</td>
                <td className="py-1.5 text-xs">{s.rooms.join(", ") || "—"}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="font-semibold">
              <td className="pt-2" colSpan={3}>Total</td>
              <td className="pt-2 text-right tabular-nums">{data.total_credits}</td>
              <td colSpan={3} />
            </tr>
          </tfoot>
        </table>
      )}
    </div>
  );
};

export default SubjectCreditsPanel;
