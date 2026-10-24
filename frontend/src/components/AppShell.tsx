"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Navbar } from "./Navbar";
import { Footer } from "./Footer";
import { useAuth } from "@/lib/auth-context";
import {
  LayoutDashboard,
  User,
  FileText,
  CheckCircle2,
  TrendingUp,
  Sparkles,
  Briefcase,
  ShieldAlert,
  BarChart2,
  ChevronRight
} from "lucide-react";

interface AppShellProps {
  children: React.ReactNode;
  title?: string;
  description?: string;
  actions?: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
  children,
  title,
  description,
  actions,
}) => {
  const pathname = usePathname();
  const { user, loading } = useAuth();

  const navItems = [
    { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { label: "Skill Assessment", href: "/assessment", icon: CheckCircle2 },
    { label: "Skill Analytics", href: "/skills", icon: BarChart2 },
    { label: "Resume Analysis", href: "/resume", icon: FileText },
    { label: "Learning Roadmap", href: "/roadmap", icon: Sparkles },
    { label: "Career Domains", href: "/careers", icon: TrendingUp },
    { label: "Job Matches", href: "/jobs", icon: Briefcase },
    { label: "Student Profile", href: "/profile", icon: User },
  ];

  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => {
    setMounted(true);
  }, []);

  if (mounted && !loading && user?.role === "admin") {
    navItems.push({ label: "Admin Console", href: "/admin", icon: ShieldAlert });
  }

  // Generate breadcrumb title from path
  const currentNav = navItems.find((item) => item.href === pathname);
  const pageTitle = title || currentNav?.label || "SkillPath AI";

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <Navbar />

      <div className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
          {/* Sidebar */}
          <aside className="hidden lg:block lg:col-span-1">
            <div className="sticky top-24 bg-white border border-slate-200 rounded-xl p-3 shadow-xs space-y-1">
              <div className="px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Menu
              </div>
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                const isAdminItem = item.href === "/admin";

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-2.5 px-3 py-2 text-sm font-medium rounded-lg transition ${
                      isActive
                        ? isAdminItem
                          ? "bg-purple-50 text-purple-700 font-semibold shadow-xs"
                          : "bg-indigo-50 text-indigo-700 font-semibold shadow-xs"
                        : isAdminItem
                        ? "text-purple-600 hover:bg-purple-50"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    }`}
                  >
                    <Icon className={`w-4 h-4 ${isActive ? (isAdminItem ? "text-purple-600" : "text-indigo-600") : "text-slate-400"}`} />
                    <span>{item.label}</span>
                  </Link>
                );
              })}

              {/* Verified Status badge */}
              <div className="mt-6 pt-4 border-t border-slate-100 px-3">
                <div className="flex items-center gap-2 text-xs text-slate-500 font-medium">
                  <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                  <span>AI Engine Connected</span>
                </div>
              </div>
            </div>
          </aside>

          {/* Main Content Area */}
          <main className="lg:col-span-4 space-y-6">
            {/* Page Header & Breadcrumbs */}
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <nav className="flex items-center gap-1.5 text-xs text-slate-400 mb-1 font-medium">
                  <Link href="/dashboard" className="hover:text-slate-600">
                    Home
                  </Link>
                  <ChevronRight className="w-3.5 h-3.5" />
                  <span className="text-slate-600 font-semibold">{pageTitle}</span>
                </nav>
                <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{pageTitle}</h1>
                {description && <p className="text-sm text-slate-500 mt-1">{description}</p>}
              </div>
              {actions && <div className="flex items-center gap-3">{actions}</div>}
            </div>

            {/* Dynamic View Children */}
            {children}
          </main>
        </div>
      </div>

      <Footer />
    </div>
  );
};
