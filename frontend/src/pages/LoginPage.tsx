// frontend/src/pages/LoginPage.tsx
import React, { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { GraduationCap, ShieldCheck, BookOpenCheck, ArrowLeft, Mail, Lock, Clock, CheckCircle2, Eye, EyeOff } from "lucide-react";
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

const LoginPage = () => {
  const { role } = useParams<{ role: string }>();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const config = roleConfig[role || ""] || roleConfig.student;
  const Icon = config.icon;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const result = await authService.login(username, password, role || 'student');
      
      if (result.success) {
        const userRole = result.user.role;
        
        if (userRole === 'admin') {
          navigate('/admin/dashboard');
        } else if (userRole === 'teacher') {
          navigate('/teacher/dashboard');
        } else {
          navigate('/student/dashboard');
        }
      } else {
        setError("Invalid username or password");
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Login failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left panel — gradient with branding */}
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
            Welcome Back
          </h1>
          <p className="text-lg opacity-80 max-w-md leading-relaxed">
            Continue your journey of effortless scheduling and time management with TimeTableX.
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

      {/* Right panel — login form */}
      <div className="flex-1 flex items-center justify-center bg-background px-6 py-12 relative">
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
              {config.label} Login
            </h2>
            <p className="text-muted-foreground text-sm">
              Sign in to your {config.label.toLowerCase()} account
            </p>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-500/10 border border-red-500 rounded-lg text-red-500 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Username
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Enter your username"
                  className="w-full rounded-lg bg-card text-foreground border border-border pl-11 pr-4 py-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-2">Password</label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
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
            </div>

            <div className="flex gap-3">
              <button
                type="submit"
                disabled={loading}
                className={`flex-1 py-3 rounded-lg bg-gradient-to-r ${config.gradient} font-semibold text-sm hover:brightness-110 transition-all shadow-lg disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {loading ? "Logging in..." : "Log in"}
              </button>
              <button
                type="button"
                onClick={() => navigate(`/signup/${role}`)}
                className="flex-1 py-3 rounded-lg border border-border bg-card text-foreground font-semibold text-sm hover:bg-muted transition-all"
              >
                Sign up
              </button>
            </div>
          </form>

          {/* Demo credentials hint */}
          <div className="mt-8 bg-muted/50 border border-border rounded-lg p-4 text-xs space-y-1">
            <p className="font-semibold">Demo Credentials:</p>
            <p>Admin: admin / admin123</p>
            <p>Teacher: teacher / teacher123</p>
            <p>Student: student / student123</p>
          </div>

          <div className="text-center mt-6">
            <a href="#" className="text-primary text-sm hover:underline">Forgot your password?</a>
          </div>

          <div className="relative my-8">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="px-3 bg-background text-muted-foreground">or</span>
            </div>
          </div>

          <button className="w-full py-3 rounded-lg border border-border bg-card text-foreground font-medium text-sm hover:bg-muted transition flex items-center justify-center gap-3">
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
            </svg>
            Continue with Google
          </button>

          <p className="text-center text-xs text-muted-foreground mt-8">
            By logging in, you agree to our{" "}
            <span className="text-primary cursor-pointer hover:underline">Terms of Service</span> and{" "}
            <span className="text-primary cursor-pointer hover:underline">Privacy Policy</span>
          </p>
          
          {/* Demo credentials hint */}
          <div className="mt-4 p-3 bg-muted/20 rounded-lg text-center text-xs text-muted-foreground">
            <p className="font-semibold">Demo Credentials:</p>
            <p>Admin: admin / admin123</p>
            <p>Teacher: teacher / teacher123</p>
            <p>Student: student / student123</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;