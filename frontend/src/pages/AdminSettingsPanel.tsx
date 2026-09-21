// frontend/src/pages/AdminSettingsPanel.tsx
import { useState } from "react";
import { toast } from "sonner";
import { ShieldAlert, RotateCcw, Loader2 } from "lucide-react";
import api from "../services/api";

interface RoomConflict {
  room_code: string;
  day_name: string;
  start_time: string;
  group_codes: string[];
}

interface Props {
  onSuccess?: () => void;
}

const AdminSettingsPanel = ({ onSuccess }: Props) => {
  const [checking, setChecking] = useState(false);
  const [resetting, setResetting] = useState(false);

  const checkRoomConflicts = async () => {
    setChecking(true);
    try {
      const { data } = await api.get("/conflicts/rooms");
      const conflicts: RoomConflict[] = data.conflicts;
      if (data.count === 0) {
        toast.success("No room conflicts found — every room is booked at most once per slot.");
      } else {
        const details = conflicts
          .map((c) => `${c.room_code} · ${c.day_name} ${c.start_time} (${c.group_codes.join(" vs ")})`)
          .join("; ");
        toast.error(`${data.count} room conflict(s) found: ${details}`);
      }
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to check room conflicts.");
    } finally {
      setChecking(false);
    }
  };

  const resetTimetables = async () => {
    if (
      !confirm(
        "This clears every generated timetable across every branch/year/section and frees all rooms and time slots so they can be assigned again. This cannot be undone. Continue?"
      )
    ) {
      return;
    }
    setResetting(true);
    try {
      const { data } = await api.post("/admin/reset-timetables");
      toast.success(data.message);
      onSuccess?.();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to reset timetables.");
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-card/60 backdrop-blur-md rounded-xl p-8 border border-border">
        <h2 className="text-2xl font-bold mb-1 text-white">⚙️ Settings</h2>
        <p className="text-gray-300">Schedule-wide checks and actions that affect every generated timetable.</p>
      </div>

      <div className="bg-card/60 backdrop-blur-md rounded-xl p-6 border border-red-500/30">
        <h3 className="text-lg font-semibold text-white mb-1">Danger Zone</h3>
        <p className="text-sm text-gray-400 mb-5">These actions apply across all branches, years, and sections.</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="border border-border rounded-xl p-5 bg-background/40">
            <div className="w-10 h-10 rounded-lg flex items-center justify-center mb-3 bg-sky-100 text-sky-600">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <h4 className="font-semibold text-white mb-1">Check Room Conflicts</h4>
            <p className="text-sm text-gray-400 mb-4">
              Scans every generated timetable for a room booked twice in the same time slot.
            </p>
            <button
              onClick={checkRoomConflicts}
              disabled={checking}
              className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-sm font-medium flex items-center gap-2 disabled:opacity-50"
            >
              {checking && <Loader2 className="w-4 h-4 animate-spin" />}
              {checking ? "Checking..." : "Run Check"}
            </button>
          </div>

          <div className="border border-red-500/40 rounded-xl p-5 bg-background/40">
            <div className="w-10 h-10 rounded-lg flex items-center justify-center mb-3 bg-red-100 text-red-600">
              <RotateCcw className="w-5 h-5" />
            </div>
            <h4 className="font-semibold text-white mb-1">Reset All Timetables</h4>
            <p className="text-sm text-gray-400 mb-4">
              Clears every allotted room and time slot across all classes so they can be reassigned from scratch.
            </p>
            <button
              onClick={resetTimetables}
              disabled={resetting}
              className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white text-sm font-medium flex items-center gap-2 disabled:opacity-50"
            >
              {resetting && <Loader2 className="w-4 h-4 animate-spin" />}
              {resetting ? "Resetting..." : "Reset Now"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminSettingsPanel;
