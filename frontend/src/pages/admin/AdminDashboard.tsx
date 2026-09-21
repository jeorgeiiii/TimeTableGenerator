// frontend/src/pages/AdminDashboard.tsx (Updated with React Query)
import { useState } from "react";
import { Menu } from "lucide-react";
import { useQueryClient } from '@tanstack/react-query';
import AppSidebar from "../../components/AppSidebar";
import StarBackground from "../../components/StarBackground";
import AddTeacher from "../../pages/AddTeacher";
import AddSubject from "../../pages/AddSubject";
import AssignSubject from "../../pages/AssignSubject";
import CreateSection from "../../pages/CreateSection";
import GenerateTimetable from "../../pages/GenerateTimetable";
import ViewTimetable from "../../pages/ViewTimetable";
import AdminSettingsPanel from "../../pages/AdminSettingsPanel";
import { useUsers, useAddTeacher, useAddSubject, useGenerateTimetable, queryKeys } from "../../services/queryService";
import api from "../../services/api";

const AdminDashboard = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activePage, setActivePage] = useState("dashboard");
  const queryClient = useQueryClient();

  // Real-time users data (auto-refreshes every 3 seconds)
  const { data: users = [], isLoading: usersLoading, refetch: refetchUsers } = useUsers();

  // Mutations for real-time updates
  const addTeacherMutation = useAddTeacher();
  const addSubjectMutation = useAddSubject();
  const generateTimetableMutation = useGenerateTimetable();

  // Manual refresh function
  const refreshAllData = () => {
    queryClient.invalidateQueries({ queryKey: [queryKeys.teachers] });
    queryClient.invalidateQueries({ queryKey: [queryKeys.subjects] });
    queryClient.invalidateQueries({ queryKey: [queryKeys.users] });
    queryClient.invalidateQueries({ queryKey: [queryKeys.timetable] });
  };

  const updateUserStatus = async (userId: number, isActive: boolean) => {
    try {
      await api.put(`/admin/users/${userId}/status`, { is_active: isActive ? 1 : 0 });
      refetchUsers(); // Refresh users list instantly
    } catch (error) {
      console.error("Error updating user status:", error);
    }
  };

  const deleteUser = async (userId: number) => {
    if (confirm("Are you sure you want to delete this user?")) {
      try {
        await api.delete(`/admin/users/${userId}`);
        refetchUsers(); // Refresh users list instantly
      } catch (error) {
        console.error("Error deleting user:", error);
      }
    }
  };

  const renderPage = () => {
    switch(activePage) {
      case "add-teacher":
        return <AddTeacher onSuccess={refreshAllData} />;
      case "add-subject":
        return <AddSubject onSuccess={refreshAllData} />;
      case "assign-subject":
        return <AssignSubject onSuccess={refreshAllData} />;
      case "create-section":
        return <CreateSection onSuccess={refreshAllData} />;
      case "generate-timetable":
        return <GenerateTimetable onSuccess={refreshAllData} />;
      case "view-timetable":
        return <ViewTimetable />;
      case "settings":
        return <AdminSettingsPanel onSuccess={refreshAllData} />;
      case "users":
        return (
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold" style={{ color: '#1f2937' }}>👥 Registered Users</h2>
              <button 
                onClick={refreshAllData}
                className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
              >
                🔄 Refresh
              </button>
            </div>
            {usersLoading ? (
              <p style={{ color: '#4b5563' }}>Loading users...</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                  <thead className="bg-gray-100">
                    <tr>
                      <th className="p-3 text-left border" style={{ color: '#374151' }}>ID</th>
                      <th className="p-3 text-left border" style={{ color: '#374151' }}>Username</th>
                      <th className="p-3 text-left border" style={{ color: '#374151' }}>Email</th>
                      <th className="p-3 text-left border" style={{ color: '#374151' }}>Full Name</th>
                      <th className="p-3 text-left border" style={{ color: '#374151' }}>Role</th>
                      <th className="p-3 text-left border" style={{ color: '#374151' }}>Signup Date</th>
                      <th className="p-3 text-left border" style={{ color: '#374151' }}>Status</th>
                      <th className="p-3 text-left border" style={{ color: '#374151' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((user: any) => (
                      <tr key={user.id} className="border-b hover:bg-gray-50">
                        <td className="p-3 border" style={{ color: '#374151' }}>{user.id}</td>
                        <td className="p-3 border" style={{ color: '#374151' }}>{user.username}</td>
                        <td className="p-3 border" style={{ color: '#374151' }}>{user.email}</td>
                        <td className="p-3 border" style={{ color: '#374151' }}>{user.full_name}</td>
                        <td className="p-3 border">
                          <span className={`px-2 py-1 rounded text-xs ${
                            user.role === 'admin' ? 'bg-red-100 text-red-800' :
                            user.role === 'teacher' ? 'bg-blue-100 text-blue-800' :
                            'bg-green-100 text-green-800'
                          }`}>
                            {user.role}
                          </span>
                        </td>
                        <td className="p-3 border" style={{ color: '#374151' }}>{new Date(user.created_at).toLocaleDateString()}</td>
                        <td className="p-3 border">
                          <span className={`px-2 py-1 rounded text-xs ${
                            user.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                          }`}>
                            {user.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                        <td className="p-3 border">
                          <button
                            onClick={() => updateUserStatus(user.id, !user.is_active)}
                            className={`text-sm mr-2 ${
                              user.is_active ? 'text-orange-600 hover:text-orange-800' : 'text-green-600 hover:text-green-800'
                            }`}
                          >
                            {user.is_active ? '🔒 Deactivate' : '🔓 Activate'}
                          </button>
                          {user.role !== 'admin' && (
                            <button
                              onClick={() => deleteUser(user.id)}
                              className="text-sm text-red-600 hover:text-red-800"
                            >
                              🗑️ Delete
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        );
      default:
        return (
          <div className="space-y-6">
            <div className="bg-card/60 backdrop-blur-md rounded-xl p-8 border border-border">
              <h2 className="text-2xl font-bold mb-4 text-white">👋 Welcome Admin</h2>
              <p className="text-gray-300">Manage teachers, subjects, sections, and generate timetables.</p>
              <button 
                onClick={refreshAllData}
                className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
              >
                🔄 Refresh All Data
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {/* Cards remain same */}
              <div className="bg-card/60 backdrop-blur-md rounded-xl p-6 border border-border cursor-pointer hover:border-primary/50 transition-all" onClick={() => setActivePage("add-teacher")}>
                <div className="text-4xl mb-3">👨‍🏫</div>
                <h3 className="text-lg font-bold text-white">Add Teacher</h3>
                <p className="text-sm text-gray-300">Register faculty members</p>
              </div>
              <div className="bg-card/60 backdrop-blur-md rounded-xl p-6 border border-border cursor-pointer hover:border-primary/50 transition-all" onClick={() => setActivePage("add-subject")}>
                <div className="text-4xl mb-3">📚</div>
                <h3 className="text-lg font-bold text-white">Add Subject</h3>
                <p className="text-sm text-gray-300">Define courses with credits</p>
              </div>
              <div className="bg-card/60 backdrop-blur-md rounded-xl p-6 border border-border cursor-pointer hover:border-primary/50 transition-all" onClick={() => setActivePage("assign-subject")}>
                <div className="text-4xl mb-3">🔗</div>
                <h3 className="text-lg font-bold text-white">Assign Subject</h3>
                <p className="text-sm text-gray-300">Link subjects to teachers</p>
              </div>
              <div className="bg-card/60 backdrop-blur-md rounded-xl p-6 border border-border cursor-pointer hover:border-primary/50 transition-all" onClick={() => setActivePage("create-section")}>
                <div className="text-4xl mb-3">📋</div>
                <h3 className="text-lg font-bold text-white">Create Section</h3>
                <p className="text-sm text-gray-300">Organize student groups</p>
              </div>
              <div className="bg-card/60 backdrop-blur-md rounded-xl p-6 border border-border cursor-pointer hover:border-primary/50 transition-all" onClick={() => setActivePage("generate-timetable")}>
                <div className="text-4xl mb-3">⚡</div>
                <h3 className="text-lg font-bold text-white">Generate Timetable</h3>
                <p className="text-sm text-gray-300">Auto-create schedules</p>
              </div>
              <div className="bg-card/60 backdrop-blur-md rounded-xl p-6 border border-border cursor-pointer hover:border-primary/50 transition-all" onClick={() => setActivePage("view-timetable")}>
                <div className="text-4xl mb-3">👁️</div>
                <h3 className="text-lg font-bold text-white">View Timetable</h3>
                <p className="text-sm text-gray-300">See generated schedules</p>
              </div>
              <div className="bg-card/60 backdrop-blur-md rounded-xl p-6 border border-border cursor-pointer hover:border-primary/50 transition-all" onClick={() => setActivePage("users")}>
                <div className="text-4xl mb-3">👥</div>
                <h3 className="text-lg font-bold text-white">Manage Users</h3>
                <p className="text-sm text-gray-300">View all registered users</p>
              </div>
            </div>
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen relative">
      <StarBackground />
      <AppSidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} onNavigate={setActivePage} />
      
      <div className="lg:ml-64 relative z-10">
        <header className="sticky top-0 z-30 border-b border-border bg-background/40 backdrop-blur-xl px-6 py-4">
          <div className="flex items-center gap-4">
            <button onClick={() => setSidebarOpen(true)} className="lg:hidden text-foreground">
              <Menu size={24} />
            </button>
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-2 text-white">
                🏫 <span>SGSITS Admin Panel</span>
              </h1>
              <p className="text-sm text-gray-300">Complete Timetable Management System</p>
            </div>
          </div>
        </header>
        
        <main className="p-6">
          {renderPage()}
        </main>
      </div>
    </div>
  );
};

export default AdminDashboard;