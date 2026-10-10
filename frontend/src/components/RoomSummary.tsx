// frontend/src/components/RoomSummary.tsx
// One line under a timetable's title: the section's home classroom (where
// every theory class is held), its lab rooms, and its subject/lab layout.
import { DoorOpen, FlaskConical, LayoutGrid } from "lucide-react";
import type { TimetableData } from "../services/timetable_service";

const RoomSummary = ({ timetable }: { timetable: TimetableData }) => {
  const { home_room, layout } = timetable;
  if (!home_room && !layout) return <div className="mb-4" />;
  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-sm text-muted-foreground mt-1 mb-4">
      {home_room && (
        <span className="inline-flex items-center gap-1.5">
          <DoorOpen size={15} /> Classroom <strong className="text-foreground">{home_room}</strong>
        </span>
      )}
      {layout?.lab_rooms && layout.lab_rooms.length > 0 && (
        <span className="inline-flex items-center gap-1.5">
          <FlaskConical size={15} /> Labs in <strong className="text-foreground">{layout.lab_rooms.join(", ")}</strong>
        </span>
      )}
      {layout?.label && (
        <span className="inline-flex items-center gap-1.5">
          <LayoutGrid size={15} /> {layout.label}
        </span>
      )}
    </div>
  );
};

export default RoomSummary;
