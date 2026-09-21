// frontend/src/components/AppSidebar.tsx
import { Home, UserPlus, BookOpen, Link, LayoutGrid, Zap, Eye, Settings, LogOut } from "lucide-react";
import { useNavigate } from "react-router-dom";
import authService from "../services/auth.service";

const menuItems = [
  { id: "dashboard", label: "Dashboard", icon: Home },
  { id: "add-teacher", label: "Add Teacher", icon: UserPlus },
  { id: "add-subject", label: "Add Subject", icon: BookOpen },
  { id: "assign-subject", label: "Assign Subject", icon: Link },
  { id: "create-section", label: "Create Section", icon: LayoutGrid },
  { id: "generate-timetable", label: "Generate Timetable", icon: Zap },
  { id: "view-timetable", label: "View Timetable", icon: Eye },
  { id: "settings", label: "Settings", icon: Settings },
];

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (page: string) => void;
}

const AppSidebar = ({ isOpen, onClose, onNavigate }: Props) => {
  const navigate = useNavigate();

  const handleLogout = () => {
    authService.logout();
    navigate("/");
    onClose();
  };

  const handleNav = (pageId: string) => {
    onNavigate(pageId);
    onClose();
  };

  return (
    <>
      {isOpen && <div className="fixed inset-0 bg-background/60 z-40 lg:hidden" onClick={onClose} />}
      <aside className={`fixed top-0 left-0 h-full w-64 bg-sidebar border-r border-sidebar-border z-50 transition-transform duration-300 lg:translate-x-0 ${isOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="p-6 border-b border-sidebar-border">
          <h1 className="text-xl font-bold text-sidebar-primary-foreground flex items-center gap-2">
            🏫 <span className="bg-clip-text text-transparent" style={{ backgroundImage: "var(--gradient-nebula)" }}>timetablemaster</span>
          </h1>
        </div>

        <nav className="p-4 space-y-2 overflow-y-auto h-[calc(100%-88px)]">
          {menuItems.map(item => (
            <button
              key={item.id}
              onClick={() => handleNav(item.id)}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all text-sidebar-foreground hover:bg-sidebar-accent/50"
            >
              <item.icon size={18} />
              {item.label}
            </button>
          ))}
          
          <div className="pt-4 mt-4 border-t border-sidebar-border">
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all text-red-400 hover:bg-red-400/10"
            >
              <LogOut size={18} />
              Logout
            </button>
          </div>
        </nav>
      </aside>
    </>
  );
};

export default AppSidebar;