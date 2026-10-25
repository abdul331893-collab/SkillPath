"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { useAuth } from "@/lib/auth-context";
import {
  Compass,
  CheckCircle2,
  TrendingUp,
  Briefcase,
  FileText,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Cpu,
  Target,
  Layers,
  GraduationCap
} from "lucide-react";

export default function LandingPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [redirecting, setRedirecting] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const explicitLogout = sessionStorage.getItem("skillpath_explicit_logout");
    if (explicitLogout === "true") return;

    const savedUserStr = localStorage.getItem("skillpath_user") || localStorage.getItem("skillpath_last_account");
    if (savedUserStr) {
      try {
        const parsed = JSON.parse(savedUserStr);
        if (parsed?.uid) {
          setRedirecting(true);
          const lastRoute = localStorage.getItem("skillpath_last_route");
          if (lastRoute && lastRoute !== "/" && lastRoute !== "/login" && lastRoute !== "/register") {
            router.replace(lastRoute);
            return;
          }
          if (parsed.role === "admin") {
            router.replace("/admin");
          } else {
            router.replace("/career-assessment");
          }
          return;
        }
      } catch {
        // ignore
      }
    }

    if (!loading && user) {
      setRedirecting(true);
      const lastRoute = localStorage.getItem("skillpath_last_route");
      if (lastRoute && lastRoute !== "/" && lastRoute !== "/login" && lastRoute !== "/register") {
        router.replace(lastRoute);
      } else if (user.role === "admin") {
        router.replace("/admin");
      } else {
        router.replace("/career-assessment");
      }
    }
  }, [user, loading, router]);

  if (redirecting) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-slate-50">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600 mb-4" />
        <p className="text-xs font-semibold text-slate-500">Opening your SkillPath account...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-white text-slate-900">
      <Navbar />

      {/* Hero Section */}
      <section className="relative overflow-hidden pt-20 pb-20 md:pt-28 md:pb-28 border-b border-slate-100 bg-linear-to-b from-slate-50/70 to-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto space-y-6">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-slate-950 tracking-tight leading-[1.15]">
              Validate Real Skills.{" "}
              <span className="text-purple-600 block sm:inline">Close Skill Gaps.</span>{" "}
              Land Real Tech Jobs.
            </h1>

            <p className="text-lg sm:text-xl text-slate-600 font-normal leading-relaxed">
              SkillPath AI combines deterministic skill evaluation, adaptive technical assessments based on your resume and projects, personalized learning roadmaps, and direct job & internship applications.
            </p>
          </div>
        </div>
      </section>

      {/* 4 Pillars of SkillPath AI */}
      <section className="py-20 bg-slate-50/50 border-b border-slate-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-xs font-bold text-purple-600 uppercase tracking-widest mb-2">Core Platform Capabilities</h2>
            <p className="text-3xl font-bold text-slate-900 tracking-tight">
              An End-to-End Pipeline from Resume to Verified Employment
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Card 1 */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs hover:shadow-md transition">
              <div className="w-12 h-12 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center mb-5">
                <FileText className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">1. Resume & Skill Extraction</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Extracts claimed skills and real project details from PDF/DOCX resumes. Distinguishes resume-claimed from student-added competencies.
              </p>
            </div>

            {/* Card 2 */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs hover:shadow-md transition">
              <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center mb-5">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">2. Adaptive Assessment</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Evaluates theoretical and practical proficiency with MCQs and project-relevant challenges tailored to your confirmed experience.
              </p>
            </div>

            {/* Card 3 */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs hover:shadow-md transition">
              <div className="w-12 h-12 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center mb-5">
                <Sparkles className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">3. Personalized Roadmap</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Generates a multi-phase learning plan targeting weak skills, backed by approved documentation and hands-on milestones.
              </p>
            </div>

            {/* Card 4 */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs hover:shadow-md transition">
              <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center mb-5">
                <Briefcase className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">4. Direct Applications</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Browse verified jobs and internships, submit direct applications with cover letters, and track hiring stages in real time.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Call to Action */}
      <section className="py-20 bg-purple-700 text-white text-center">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
            Ready to Begin Your Technical Journey?
          </h2>
          <p className="text-purple-100 text-lg max-w-2xl mx-auto">
            Take your assessment, review your diagnostic skill report, and discover engineering opportunities matching your profile.
          </p>
          <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/career-assessment"
              className="px-8 py-3.5 rounded-xl bg-white text-purple-700 hover:bg-purple-50 font-bold shadow-sm transition"
            >
              Get Started with Skill Assessment
            </Link>
            <Link
              href="/jobs"
              className="px-8 py-3.5 rounded-xl bg-purple-800 hover:bg-purple-900 text-white font-semibold transition border border-purple-600"
            >
              Explore Jobs & Internships
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
