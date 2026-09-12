import { useNavigate } from "react-router-dom";
import { GraduationCap, ShieldCheck, BookOpenCheck, Clock, Calendar, Zap, CheckCircle2, School, LogIn, UserPlus } from "lucide-react";
import SpaceScene from "@/components/SpaceScene";

const Index = () => {
  const navigate = useNavigate();

  const roles = [
    {
      label: "Student",
      icon: GraduationCap,
      loginPath: "/login/student",
      signupPath: "/signup/student",
      description: "View your class schedule, assignments and exam timetable",
      gradient: "from-sky-500 to-blue-600",
    },
    {
      label: "Teacher",
      icon: BookOpenCheck,
      loginPath: "/login/teacher",
      signupPath: "/signup/teacher",
      description: "Manage classes, set availability and create schedules",
      gradient: "from-emerald-500 to-teal-600",
    },
    {
      label: "Admin",
      icon: ShieldCheck,
      loginPath: "/login/admin",
      signupPath: "/signup/admin",
      description: "Full control over timetables, users, rooms and settings",
      gradient: "from-primary to-accent",
    },
  ];

  const features = [
    {
      icon: Zap,
      title: "Instant Scheduling",
      description: "Generate conflict-free timetables in seconds with smart algorithms",
      color: "text-primary",
      bg: "bg-primary/10",
    },
    {
      icon: Calendar,
      title: "Calendar Integration",
      description: "Sync schedules with your calendar and get instant notifications",
      color: "text-feature-green",
      bg: "bg-feature-green/10",
    },
  ];

  const stats = [
    { value: "10,000+", label: "Institutes Worldwide" },
    { value: "500K+", label: "Schedules Created" },
    { value: "99.9%", label: "Uptime" },
  ];

  return (
    <div className="min-h-screen relative overflow-x-hidden">
      <SpaceScene />

      {/* Navbar */}
      <nav className="relative z-20 flex items-center justify-between px-6 sm:px-10 py-5 max-w-7xl mx-auto">
        <div className="flex items-center gap-2.5">
          <Clock className="w-7 h-7 text-primary" />
          <span className="text-xl font-display font-bold text-foreground">
            Timetable<span className="text-primary">X</span>
          </span>
        </div>
        
        <div className="hidden sm:flex items-center gap-8 text-sm text-muted-foreground">
          <a href="#features" className="hover:text-foreground transition">Features</a>
          <a href="#roles" className="hover:text-foreground transition">Login</a>
        </div>

        {/* Login & Signup Buttons in Navbar - scroll to role picker rather than
            defaulting to student, so Teacher/Admin are just as discoverable */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => document.getElementById("roles")?.scrollIntoView({ behavior: "smooth" })}
            className="hidden sm:flex items-center gap-2 px-4 py-2 rounded-lg bg-primary/10 text-primary hover:bg-primary/20 transition-all text-sm font-medium"
          >
            <LogIn className="w-4 h-4" />
            Login
          </button>
          <button
            onClick={() => document.getElementById("roles")?.scrollIntoView({ behavior: "smooth" })}
            className="hidden sm:flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-primary to-accent text-primary-foreground hover:brightness-110 transition-all text-sm font-medium shadow-lg shadow-primary/20"
          >
            <UserPlus className="w-4 h-4" />
            Sign Up
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 sm:px-10 pt-12 pb-20 sm:pt-20 sm:pb-28">
        <div className="max-w-3xl">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary/10 border border-primary/20 text-primary text-sm mb-6">
            <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
            Smart Scheduling for Education
          </div>

          <h1 className="text-4xl sm:text-6xl font-display font-bold text-foreground leading-tight mb-6">
            Effortless Timetables.{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-accent">
              Powered by AI.
            </span>
          </h1>

          <p className="text-lg sm:text-xl text-muted-foreground leading-relaxed max-w-2xl mb-10">
            Our intelligent timetable generator creates perfect, conflict-free school schedules in minutes.
            Built for universities, colleges and schools — automate complex scheduling and save hours.
          </p>

          <div className="flex flex-wrap gap-4">
            <button
              onClick={() => {
                document.getElementById("roles")?.scrollIntoView({ behavior: "smooth" });
              }}
              className="px-7 py-3 rounded-lg bg-primary text-primary-foreground font-semibold text-sm hover:brightness-110 transition-all shadow-lg shadow-primary/20"
            >
              Get Started Free
            </button>
            <a
              href="#features"
              className="px-7 py-3 rounded-lg bg-secondary text-secondary-foreground font-semibold text-sm hover:bg-muted transition-all border border-border"
            >
              View Features
            </a>
          </div>
        </div>

        {/* Stats */}
        <div className="flex flex-wrap gap-12 mt-16 pt-10 border-t border-border/50">
          {stats.map((stat) => (
            <div key={stat.label} className="text-center">
              <div className="text-3xl sm:text-4xl font-display font-bold text-foreground">{stat.value}</div>
              <div className="text-sm text-muted-foreground mt-1">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="relative z-10 max-w-7xl mx-auto px-6 sm:px-10 py-20">
        <div className="text-center mb-14">
          <h2 className="text-3xl sm:text-4xl font-display font-bold text-foreground mb-4">
            Everything You Need
          </h2>
          <p className="text-muted-foreground text-lg max-w-xl mx-auto">
            Powerful features to streamline timetable management across your entire institution
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          {features.map((f) => (
            <div
              key={f.title}
              className="rounded-xl bg-card/70 backdrop-blur-xl border border-border p-6 hover:border-primary/30 transition-all group"
            >
              <div className={`w-11 h-11 rounded-lg ${f.bg} flex items-center justify-center mb-4`}>
                <f.icon className={`w-5 h-5 ${f.color}`} />
              </div>
              <h3 className="font-display font-semibold text-foreground mb-2">{f.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{f.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Substitute / Auto Feature */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 sm:px-10 py-16">
        <div className="rounded-2xl overflow-hidden bg-feature-green/90">
          <div className="p-8 sm:p-12">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/15 text-sm mb-5">
              <span className="w-2 h-2 rounded-full bg-yellow-400" />
              Fully Automated
            </div>
            <h2 className="text-3xl sm:text-4xl font-display font-bold mb-4">
              Automatic Substitute Assignment
            </h2>
            <p className="text-lg opacity-80 max-w-xl mb-8">
              When faculty members are absent, our system automatically finds and assigns the best available substitute in seconds.
            </p>
            <div className="space-y-3">
              {[
                "Staff attendance integration",
                "Smart cover faculty matching by subject & availability",
                "Customizable workload limits per faculty member",
              ].map((item) => (
                <div key={item} className="flex items-center gap-3">
                  <CheckCircle2 className="w-5 h-5 text-yellow-300 shrink-0" />
                  <span className="text-sm sm:text-base">{item}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Login & Signup Roles Section */}
      <section id="roles" className="relative z-10 max-w-7xl mx-auto px-6 sm:px-10 py-20">
        <div className="text-center mb-12">
          <h2 className="text-3xl sm:text-4xl font-display font-bold text-foreground mb-4">
            Choose Your Role
          </h2>
          <p className="text-muted-foreground text-lg">
            Sign in to access your personalized dashboard or create a new account
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 max-w-4xl mx-auto">
          {roles.map((role) => (
            <div
              key={role.label}
              className="group rounded-2xl bg-card/70 backdrop-blur-xl border border-border p-6 hover:border-primary/40 transition-all duration-300 hover:scale-[1.02]"
            >
              <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${role.gradient} flex items-center justify-center mb-5 group-hover:shadow-lg transition-shadow`}>
                <role.icon className="w-7 h-7 text-foreground" />
              </div>
              <div className="font-display font-bold text-xl text-foreground mb-2">
                {role.label}
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed mb-5">
                {role.description}
              </p>
              
              {/* Button Group for Login and Signup */}
              <div className="flex gap-3">
                <button
                  onClick={() => navigate(role.loginPath)}
                  className="flex-1 py-2.5 rounded-lg bg-primary/10 text-primary hover:bg-primary/20 transition-all text-sm font-medium flex items-center justify-center gap-2"
                >
                  <LogIn className="w-4 h-4" />
                  Login
                </button>
                <button
                  onClick={() => navigate(role.signupPath)}
                  className="flex-1 py-2.5 rounded-lg bg-gradient-to-r from-primary to-accent text-primary-foreground hover:brightness-110 transition-all text-sm font-medium flex items-center justify-center gap-2 shadow-md"
                >
                  <UserPlus className="w-4 h-4" />
                  Sign Up
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-border/50 py-8 text-center">
        <div className="flex items-center justify-center gap-2 text-muted-foreground text-sm">
          <School className="w-4 h-4" />
          <span>© 2026 TimeTableX — Smart Scheduling for Education</span>
        </div>
      </footer>
    </div>
  );
};

export default Index;