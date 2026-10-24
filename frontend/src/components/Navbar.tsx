"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import {
  Compass,
  Briefcase,
  Sparkles,
  ShieldAlert,
  LogOut,
  User,
  Menu,
  X,
  FileCheck2,
  ChevronDown
} from "lucide-react";

export const Navbar: React.FC = () => {
  const pathname = usePathname();
  const { user, loading, logout, switchRole } = useAuth();
  const [mounted, setMounted] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [profileDropdownOpen, setProfileDropdownOpen] = useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  // Guarantee matching SSR and initial hydration
  const isAuthenticated = mounted && !loading && Boolean(user);

  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Brand Logo - Consistent href="/" on initial render to prevent hydration mismatch */}
          <Link href={isAuthenticated ? "/career-assessment" : "/"} className="flex items-center gap-2.5 group">
            <div className="w-10 h-10 rounded-xl bg-purple-700 flex items-center justify-center text-white shadow-xs group-hover:bg-purple-800 transition">
              <Compass className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-lg text-slate-900 tracking-tight flex items-center gap-1.5">
                SkillPath <span className="text-purple-700">AI</span>
              </span>
              <span className="hidden sm:block text-[10px] text-slate-500 font-medium -mt-1 tracking-wider uppercase">
                Career Guidance & Assessment
              </span>
            </div>
          </Link>

          {/* Student & Admin Navigation - Rendered only after hydration resolves */}
          {isAuthenticated && user && (
            <nav className="hidden md:flex items-center space-x-1 lg:space-x-3 text-sm font-semibold text-slate-700">
              <Link
                href="/jobs"
                className={`flex items-center gap-2 px-3.5 py-2 rounded-lg transition ${
                  pathname === "/jobs"
                    ? "bg-purple-50 text-purple-800 font-bold border border-purple-100"
                    : "hover:text-slate-900 hover:bg-slate-50 text-slate-600"
                }`}
              >
                <Briefcase className="w-4 h-4 text-purple-700" />
                <span>Jobs & Internships</span>
              </Link>

              <Link
                href="/career-assessment"
                className={`flex items-center gap-2 px-3.5 py-2 rounded-lg transition ${
                  pathname === "/career-assessment"
                    ? "bg-purple-50 text-purple-800 font-bold border border-purple-100"
                    : "hover:text-slate-900 hover:bg-slate-50 text-slate-600"
                }`}
              >
                <Sparkles className="w-4 h-4 text-purple-700" />
                <span>Skill Assessment & Career Guidance</span>
              </Link>

              {user.role === "admin" && (
                <Link
                  href="/admin"
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg transition ${
                    pathname === "/admin"
                      ? "bg-amber-50 text-amber-900 font-bold border border-amber-200"
                      : "text-amber-700 hover:bg-amber-50 hover:text-amber-800"
                  }`}
                >
                  <ShieldAlert className="w-4 h-4" />
                  <span>Admin Panel</span>
                </Link>
              )}
            </nav>
          )}

          {/* Right Action buttons */}
          <div className="flex items-center gap-3">
            {!mounted || loading ? (
              <div className="flex items-center gap-2" aria-hidden="true">
                <div className="h-8 w-16 rounded-lg bg-slate-100 animate-pulse" />
                <div className="h-8 w-24 rounded-lg bg-slate-100 animate-pulse" />
              </div>
            ) : user ? (
              <div className="flex items-center gap-2 relative">
                {/* Switch Role Quick Button for Development Testing */}
                <button
                  onClick={() => switchRole(user.role === "student" ? "admin" : "student")}
                  title="Toggle active role between Student and Administrator"
                  className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-300 transition"
                >
                  <span>Role:</span>
                  <span className={`capitalize font-bold ${user.role === "admin" ? "text-amber-700" : "text-purple-700"}`}>
                    {user.role}
                  </span>
                </button>

                {/* Profile Dropdown */}
                <div className="relative">
                  <button
                    onClick={() => setProfileDropdownOpen(!profileDropdownOpen)}
                    className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 transition text-xs font-semibold text-slate-800"
                  >
                    <div className="w-7 h-7 rounded-full bg-purple-100 text-purple-800 flex items-center justify-center font-bold text-xs">
                      {user.name ? user.name[0].toUpperCase() : "U"}
                    </div>
                    <span className="hidden lg:inline max-w-[120px] truncate">{user.name || user.email.split("@")[0]}</span>
                    <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                  </button>

                  {profileDropdownOpen && (
                    <div
                      onMouseLeave={() => setProfileDropdownOpen(false)}
                      className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-lg border border-slate-200 py-1.5 z-50 text-xs"
                    >
                      <div className="px-3.5 py-2 border-b border-slate-100">
                        <div className="font-bold text-slate-900 truncate">{user.name || "Student"}</div>
                        <div className="text-slate-500 truncate text-[11px]">{user.email}</div>
                      </div>

                      <Link
                        href="/profile"
                        onClick={() => setProfileDropdownOpen(false)}
                        className="flex items-center gap-2 px-3.5 py-2 text-slate-700 hover:bg-slate-50 transition"
                      >
                        <User className="w-4 h-4 text-slate-400" />
                        <span>Profile & Settings</span>
                      </Link>

                      <Link
                        href="/jobs?tab=applications"
                        onClick={() => setProfileDropdownOpen(false)}
                        className="flex items-center gap-2 px-3.5 py-2 text-slate-700 hover:bg-slate-50 transition"
                      >
                        <FileCheck2 className="w-4 h-4 text-purple-600" />
                        <span>My Applications</span>
                      </Link>

                      {user.role === "admin" && (
                        <Link
                          href="/admin"
                          onClick={() => setProfileDropdownOpen(false)}
                          className="flex items-center gap-2 px-3.5 py-2 text-amber-800 hover:bg-amber-50 transition"
                        >
                          <ShieldAlert className="w-4 h-4 text-amber-600" />
                          <span>Admin Dashboard</span>
                        </Link>
                      )}

                      <div className="border-t border-slate-100 mt-1 pt-1">
                        <button
                          onClick={() => {
                            setProfileDropdownOpen(false);
                            logout();
                          }}
                          className="w-full flex items-center gap-2 px-3.5 py-2 text-rose-700 hover:bg-rose-50 transition text-left"
                        >
                          <LogOut className="w-4 h-4 text-rose-500" />
                          <span>Sign Out</span>
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  href="/login"
                  className="text-xs font-semibold text-slate-700 hover:text-slate-900 px-3 py-2 rounded-lg hover:bg-slate-100 transition"
                >
                  Sign In
                </Link>
                <Link
                  href="/register"
                  className="text-xs font-semibold text-white bg-purple-700 hover:bg-purple-800 px-4 py-2 rounded-lg shadow-xs transition"
                >
                  Create Account
                </Link>
              </div>
            )}

            {/* Mobile menu button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 text-slate-600 hover:text-slate-900 rounded-lg hover:bg-slate-100"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Mobile dropdown */}
        {mobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-slate-200 space-y-1.5 text-sm font-semibold">
            {loading ? (
              <div className="py-2 text-center text-xs text-slate-400">Loading navigation...</div>
            ) : user ? (
              <>
                <Link
                  href="/jobs"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-slate-700 hover:bg-slate-50"
                >
                  <Briefcase className="w-4 h-4 text-purple-700" />
                  <span>Jobs & Internships</span>
                </Link>
                <Link
                  href="/career-assessment"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-slate-700 hover:bg-slate-50"
                >
                  <Sparkles className="w-4 h-4 text-purple-700" />
                  <span>Skill Assessment & Career Guidance</span>
                </Link>
                <Link
                  href="/jobs?tab=applications"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-slate-700 hover:bg-slate-50"
                >
                  <FileCheck2 className="w-4 h-4 text-purple-700" />
                  <span>My Applications</span>
                </Link>
                <Link
                  href="/profile"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-slate-700 hover:bg-slate-50"
                >
                  <User className="w-4 h-4 text-slate-400" />
                  <span>Profile & Account Settings</span>
                </Link>
                {user.role === "admin" && (
                  <Link
                    href="/admin"
                    onClick={() => setMobileMenuOpen(false)}
                    className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-amber-800 hover:bg-amber-50"
                  >
                    <ShieldAlert className="w-4 h-4 text-amber-600" />
                    <span>Administrator Panel</span>
                  </Link>
                )}
                <div className="pt-2 border-t border-slate-100">
                  <button
                    onClick={() => {
                      setMobileMenuOpen(false);
                      logout();
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg text-rose-700 hover:bg-rose-50"
                  >
                    <LogOut className="w-4 h-4 text-rose-500" />
                    <span>Log Out</span>
                  </button>
                </div>
              </>
            ) : (
              <div className="space-y-2 pt-2">
                <Link
                  href="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block text-center py-2 rounded-lg border border-slate-200 text-slate-700"
                >
                  Sign In
                </Link>
                <Link
                  href="/register"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block text-center py-2 rounded-lg bg-purple-700 text-white"
                >
                  Register
                </Link>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
};
