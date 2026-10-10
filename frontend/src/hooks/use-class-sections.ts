// frontend/src/hooks/use-class-sections.ts
// Whether a class (branch + year) is one whole class or divided into
// sections, and which sections exist - from the backend's class_config
// (managed on the Classes & Sections page). Replaces the old hard-coded
// "only CSE/IT have sections" rule.
import { useCallback, useEffect, useState } from "react";
import api from "../services/api";
import { hasMultipleSections } from "@/lib/store";

export interface ClassSection {
  id: number;
  group_code: string;
  section: string;
  student_count: number;
  home_room: string | null;
  room_id: number | null;
}

export interface ClassInfo {
  branch: string;
  year: number;
  has_sections: boolean;
  sections: ClassSection[];
}

/** Sentinel value for "every section of this class" in section pickers. */
export const ALL_SECTIONS = "__ALL__";

export function useClassSections(branch: string, year: number) {
  const [info, setInfo] = useState<ClassInfo | null>(null);

  const reload = useCallback(async () => {
    if (!branch || !year) { setInfo(null); return; }
    try {
      const r = await api.get("/classes", { params: { branch, year } });
      setInfo(r.data.classes?.[0] ?? null);
    } catch {
      // Older backend without /classes: fall back to the old rule.
      setInfo({ branch, year, has_sections: hasMultipleSections(branch), sections: [] });
    }
  }, [branch, year]);

  useEffect(() => { reload(); }, [reload]);

  const hasSections = info?.has_sections ?? false;
  // A sectioned class with no sections created yet still offers A and B,
  // the same as before this was configurable.
  const sectionNames = hasSections
    ? (info?.sections.length ? info.sections.map(s => s.section) : ["A", "B"])
    : ["A"];

  return { info, hasSections, sectionNames, reload };
}
