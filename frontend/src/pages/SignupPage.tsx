import React, { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { 
  GraduationCap, ShieldCheck, BookOpenCheck, ArrowLeft, 
  Mail, Lock, Clock, CheckCircle2, User, Eye, EyeOff, Building
} from "lucide-react";
import authService from "../services/auth.service";

const roleConfig: Record<string, { label: string; icon: React.ElementType; gradient: string; benefits: string[] }> = {
  student: {
    label: "Student",
    icon: GraduationCap,
    gradient: "from-sky-500 via-blue-600 to-indigo-700",
    benefits: [
      "View your weekly class schedule",
      "Access timetables anywhere, anytime",
      "Get notified about schedule changes",
    ],
  },
  teacher: {
    label: "Teacher",
    icon: BookOpenCheck,
    gradient: "from-emerald-500 via-teal-600 to-green-700",
    benefits: [
      "Manage your classes & availability",
      "View room allocations instantly",
      "Coordinate with substitutes easily",
    ],
  },
  admin: {
    label: "Admin",
    icon: ShieldCheck,
    gradient: "from-primary via-accent to-orange-600",
    benefits: [
      "Create & publish timetables",
      "Manage users, rooms & subjects",
      "Generate reports & analytics",
    ],
  },
};

const SignupPage = () => {
  const { role: urlRole } = useParams<{ role: string }>();
  const navigate = useNavigate();
  const [selectedRole, setSelectedRole] = useState<string>(urlRole || "student");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  const [formData, setFormData] = useState({
    full_name: "",
    email: "",
    username: "",
    password: "",
    department: "CSE"
  });

  const config = roleConfig[selectedRole] || roleConfig.student;
  const Icon = config.icon;

  // Student usernames must start with "st", teacher with "te" - admin has no
  // required prefix. Backend enforces the same rule; this just gives
  // immediate feedback instead of a round-trip.
  const requiredPrefix = selectedRole === "student" ? "st" : selectedRole === "teacher" ? "te" : null;

  const handleRoleChange = (role: string) => {
    setSelectedRole(role);
    setError("");
    navigate(`/signup/${role}`, { replace: true });
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setError("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    if (formData.password.length < 6) {
      setError("Password must be at least 6 characters");
      setLoading(false);
      return;
    }

    if (requiredPrefix && !formData.username.toLowerCase().startsWith(requiredPrefix)) {
      setError(`${config.label} usernames must start with "${requiredPrefix}" (e.g. "${requiredPrefix}rahul")`);
      setLoading(false);
      return;
    }

    try {
      const result = await authService.signup({
        username: formData.username,
        email: formData.email,
        password: formData.password,
        full_name: formData.full_name,
        role: selectedRole
      });

      if (result.success) {
        localStorage.setItem("token", result.token);
        localStorage.setItem("user", JSON.stringify(result.user));
        
        if (selectedRole === "admin") {
          navigate("/admin/dashboard");
        } else if (selectedRole === "teacher") {
          navigate("/teacher/dashboard");
        } else {
          navigate("/student/dashboard");
        }
      } else {
        setError(result.message || "Signup failed. Email may already exist.");
      }
    } catch (err: any) {
      console.error("Signup error:", err);
      setError(err?.response?.data?.detail || "Failed to signup. Email may already be registered.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left panel */}
      <div
        className={`hidden lg:flex lg:w-1/2 relative bg-gradient-to-br ${config.gradient} flex-col justify-between p-12 overflow-hidden`}
      >
        <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full bg-white/5" />
        <div className="absolute -bottom-40 -right-40 w-[500px] h-[500px] rounded-full bg-white/5" />

        <div className="relative z-10">
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-2 text-white/70 hover:text-white transition text-sm mb-16"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Home
          </button>

          <div className="flex items-center gap-2.5 mb-10">
            <Clock className="w-8 h-8" />
            <span className="text-2xl font-display font-bold">
              TimeTableX
            </span>
          </div>

          <h1 className="text-4xl font-display font-bold leading-tight mb-4">
            Join TimeTableX
          </h1>
          <p className="text-lg opacity-80 max-w-md leading-relaxed">
            Create your account and start managing your schedule efficiently.
          </p>
        </div>

        <div className="relative z-10 space-y-4">
          {config.benefits.map((benefit) => (
            <div key={benefit} className="flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 opacity-80 shrink-0" />
              <span className="text-sm opacity-90">{benefit}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Right panel - signup form */}
      <div className="flex-1 flex items-center justify-center bg-background px-6 py-12 relative overflow-y-auto">
        <button
          onClick={() => navigate("/")}
          className="lg:hidden absolute top-6 left-6 flex items-center gap-2 text-muted-foreground hover:text-foreground transition text-sm"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>

        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <div className="lg:hidden flex items-center justify-center gap-2 mb-6">
              <Clock className="w-6 h-6 text-primary" />
              <span className="text-lg font-display font-bold text-foreground">
                Timetable<span className="text-primary">X</span>
              </span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-display font-bold text-foreground mb-2">
              Create {config.label} Account
            </h2>
            <p className="text-muted-foreground text-sm">
              Join us and streamline your scheduling experience
            </p>
          </div>

          {/* Role Selection Tabs - Added without disturbing existing UI */}
          <div className="flex rounded-lg bg-muted/50 p-1 mb-8">
            <button
              onClick={() => handleRoleChange("student")}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-md text-sm font-medium transition-all ${
                selectedRole === "student"
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <GraduationCap className="w-4 h-4" />
              Student
            </button>
            <button
              onClick={() => handleRoleChange("teacher")}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-md text-sm font-medium transition-all ${
                selectedRole === "teacher"
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <BookOpenCheck className="w-4 h-4" />
              Teacher
            </button>
            <button
              onClick={() => handleRoleChange("admin")}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-md text-sm font-medium transition-all ${
                selectedRole === "admin"
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <ShieldCheck className="w-4 h-4" />
              Admin
            </button>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-500/10 border border-red-500 rounded-lg text-red-500 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">Full Name</label>
              <div className="relative">
                <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type="text"
                  name="full_name"
                  value={formData.full_name}
                  onChange={handleChange}
                  placeholder="Enter your full name"
                  className="w-full rounded-lg bg-card text-foreground border border-border pl-11 pr-4 py-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-2">Username</label>
              <div className="relative">
                <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type="text"
                  name="username"
                  value={formData.username}
                  onChange={handleChange}
                  placeholder={requiredPrefix ? `e.g. ${requiredPrefix}rahul` : "Choose a username"}
                  className="w-full rounded-lg bg-card text-foreground border border-border pl-11 pr-4 py-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition"
                  required
                />
              </div>
              {requiredPrefix && (
                <p className="text-xs text-muted-foreground mt-1">
                  {config.label} usernames must start with "{requiredPrefix}"
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-2">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="Enter your email"
                  className="w-full rounded-lg bg-card text-foreground border border-border pl-11 pr-4 py-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition"
                  required
                />
              </div>
            </div>

            {selectedRole === "teacher" && (
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">Department</label>
                <div className="relative">
                  <Building className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <select
                    name="department"
                    value={formData.department}
                    onChange={handleChange}
                    className="w-full rounded-lg bg-card text-foreground border border-border pl-11 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring transition"
                  >
                    <option value="CSE">Computer Science Engineering</option>
                    <option value="EE">Bio Medical Engineering</option>
                       <option value="EE">Civil Engineering</option>
                    <option value="E&TC">E&TC Engineering</option>
                    <option value="EE">Electrical Engineering</option>
                    <option value="ME">Mechanical Engineering</option>
                    <option value="EE">IT Engineering</option>
                  </select>
                </div>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-foreground mb-2">Password</label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type={showPassword ? "text" : "password"}
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="Create a password"
                  className="w-full rounded-lg bg-card text-foreground border border-border pl-11 pr-12 py-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Password must be at least 6 characters
              </p>
            </div>

            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                disabled={loading}
                className={`flex-1 py-3 rounded-lg bg-gradient-to-r ${config.gradient} font-semibold text-sm hover:brightness-110 transition-all shadow-lg disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {loading ? "Creating Account..." : "Sign Up"}
              </button>
              <button
                type="button"
                onClick={() => navigate(`/login/${selectedRole}`)}
                className="flex-1 py-3 rounded-lg border border-border bg-card text-foreground font-semibold text-sm hover:bg-muted transition-all"
              >
                Log In
              </button>
            </div>
          </form>

          <p className="text-center text-xs text-muted-foreground mt-8">
            By signing up, you agree to our{" "}
            <span className="text-primary cursor-pointer hover:underline">Terms of Service</span> and{" "}
            <span className="text-primary cursor-pointer hover:underline">Privacy Policy</span>
          </p>
        </div>
      </div>
    </div>
  );
};

export default SignupPage;