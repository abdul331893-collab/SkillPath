import React from "react";
import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { ArrowRight, CheckCircle2, FileUp, Sparkles, Award, Briefcase } from "lucide-react";

export default function HowItWorksPage() {
  const steps = [
    {
      num: "01",
      title: "Upload & Parse Technical Resume",
      icon: FileUp,
      desc: "Upload your resume in PDF or DOCX format. The system extracts structured education, projects, and claimed skills, storing them in your candidate profile.",
      detail: "Skills identified in this stage are classified as 'claimed' until validated."
    },
    {
      num: "02",
      title: "Take Domain Skill Assessment",
      icon: Award,
      desc: "Select a technical domain (such as Frontend, Backend, or Data Science). Complete timed multiple-choice and rubric-evaluated descriptive engineering questions.",
      detail: "Deterministic scoring calculates exact earned vs available points without guessing."
    },
    {
      num: "03",
      title: "Discover Skill Gaps & Career Alignment",
      icon: CheckCircle2,
      desc: "Review a comprehensive breakdown of your verified proficiencies vs target career domain requirements. See your exact skill gap percentages.",
      detail: "Skill Gap = Max(0, Required Level - Current Verified Level)."
    },
    {
      num: "04",
      title: "Execute Personalized Learning Roadmap",
      icon: Sparkles,
      desc: "Receive a structured, phased learning roadmap tailored to your highest priority skill gaps. Follow curated documentation, practical exercises, and mini-projects.",
      detail: "Check off completed topics to track your progress percentage in real time."
    },
    {
      num: "05",
      title: "Match with Verified Job Opportunities",
      icon: Briefcase,
      desc: "Explore administrator-verified job listings filtered by your validated competencies, work mode, and career domain. Verify your eligibility before applying.",
      detail: "Mandatory eligibility criteria (education, years of experience) are checked transparently."
    }
  ];

  return (
    <div className="min-h-screen flex flex-col bg-white">
      <Navbar />

      <main className="flex-1 py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h1 className="text-3xl sm:text-5xl font-extrabold text-slate-900 tracking-tight mb-4">
              How SkillPath AI Works
            </h1>
            <p className="text-lg text-slate-600 leading-relaxed">
              A transparent, evidence-based roadmap taking you from self-reported skills to verified engineering proficiency and job placement.
            </p>
          </div>

          <div className="space-y-8">
            {steps.map((step, idx) => {
              const Icon = step.icon;
              return (
                <div key={idx} className="flex gap-6 p-6 rounded-2xl bg-slate-50 border border-slate-200">
                  <div className="flex-shrink-0">
                    <div className="w-12 h-12 rounded-xl bg-indigo-600 text-white flex items-center justify-center font-bold text-lg shadow-sm">
                      {step.num}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Icon className="w-5 h-5 text-indigo-600" />
                      <h3 className="text-xl font-bold text-slate-900">{step.title}</h3>
                    </div>
                    <p className="text-sm text-slate-600 leading-relaxed">{step.desc}</p>
                    <div className="text-xs font-medium text-indigo-700 bg-indigo-50/80 px-3 py-1.5 rounded-lg border border-indigo-100 inline-block">
                      {step.detail}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-12 text-center">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold transition"
            >
              <span>Get Started Now</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
