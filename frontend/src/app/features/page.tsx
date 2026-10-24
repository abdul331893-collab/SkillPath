import React from "react";
import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import {
  FileText,
  CheckCircle2,
  TrendingUp,
  Briefcase,
  Sparkles,
  ShieldAlert,
  Cpu,
  BarChart2,
  Database,
  ArrowRight
} from "lucide-react";

export default function FeaturesPage() {
  const features = [
    {
      icon: FileText,
      title: "Document & Resume Parsing",
      desc: "Robust PDF and DOCX extraction using pdfplumber and python-docx. Structured extraction of education, projects, certifications, and claimed technical skills.",
      highlight: "Distinguishes claimed vs verified skills"
    },
    {
      icon: CheckCircle2,
      title: "Hybrid Assessment Engine",
      desc: "Dual question evaluation: deterministic MCQ scoring with protected answer keys, and rubric-governed descriptive question evaluation.",
      highlight: "Deterministic scoring formula"
    },
    {
      icon: Sparkles,
      title: "Semantic Knowledge Engine",
      desc: "Ingests curated documentation, rubrics, and industry requirements into grounded vector storage. Answers questions with validated evidence and source citations.",
      highlight: "Semantic Vector Retrieval"
    },
    {
      icon: TrendingUp,
      title: "Career Recommendation System",
      desc: "Translates measured proficiencies into weighted domain match scores. Evaluates education prerequisites independently of skill similarity.",
      highlight: "Separated eligibility checks"
    },
    {
      icon: Cpu,
      title: "Adaptive Learning Roadmaps",
      desc: "Multi-phase customized learning plans prioritizing the candidate's exact measured skill gaps. Interactive completion checkboxes track real-time progress.",
      highlight: "Authentic, non-hallucinated resources"
    },
    {
      icon: Briefcase,
      title: "Verified Job Matching",
      desc: "Ranks actual verified job listings by required and preferred skill overlap, enforcing mandatory minimum experience and degree prerequisites.",
      highlight: "Real administrator-managed jobs"
    },
    {
      icon: ShieldAlert,
      title: "Role-Based Access Control",
      desc: "Enforced at the FastAPI route level via Firebase Admin ID token verification and authoritative Firestore database checks.",
      highlight: "Student & Administrator roles"
    },
    {
      icon: Database,
      title: "Administrator Governance Portal",
      desc: "Full administrative controls for question-bank authoring, job creation, bulk CSV imports with row-level error validation, and platform analytics.",
      highlight: "Data validation & bulk CSV import"
    }
  ];

  return (
    <div className="min-h-screen flex flex-col bg-white">
      <Navbar />

      <main className="flex-1 py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h1 className="text-3xl sm:text-5xl font-extrabold text-slate-900 tracking-tight mb-4">
              Platform Features & Architecture
            </h1>
            <p className="text-lg text-slate-600 leading-relaxed">
              SkillPath AI is engineered with full architectural rigor: combining Next.js 16, FastAPI REST services, Firebase Authentication, Cloud Firestore, advanced AI evaluation models, and semantic vector retrieval.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feat, i) => {
              const Icon = feat.icon;
              return (
                <div key={i} className="bg-slate-50/70 border border-slate-200 rounded-2xl p-6 shadow-xs hover:shadow-md transition flex flex-col justify-between">
                  <div>
                    <div className="w-12 h-12 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center mb-4">
                      <Icon className="w-6 h-6" />
                    </div>
                    <div className="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-purple-100 text-purple-700 mb-3">
                      {feat.highlight}
                    </div>
                    <h3 className="text-xl font-bold text-slate-900 mb-2">{feat.title}</h3>
                    <p className="text-sm text-slate-600 leading-relaxed">{feat.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-16 text-center">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl bg-purple-600 hover:bg-purple-700 text-white font-semibold transition"
            >
              <span>Explore Student Dashboard</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
