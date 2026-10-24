"use client";

import React from "react";
import Link from "next/link";
import { Compass, Shield, CheckCircle2, Sparkles, BookOpen, Briefcase, Award } from "lucide-react";

export const Footer: React.FC = () => {
  return (
    <footer className="mt-auto bg-white border-t border-slate-200 py-12 text-sm text-slate-600">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div className="md:col-span-1">
            <Link href="/" className="flex items-center gap-2 mb-3">
              <div className="w-8 h-8 rounded-lg bg-purple-600 flex items-center justify-center text-white">
                <Compass className="w-4 h-4" />
              </div>
              <span className="font-bold text-slate-900 tracking-tight">
                SkillPath <span className="text-purple-600">AI</span>
              </span>
            </Link>
            <p className="text-xs text-slate-500 leading-relaxed">
              AI-Powered Career Intelligence System for authentic skill validation, personalized learning roadmaps, and verified job matching.
            </p>
          </div>

          <div>
            <h4 className="font-semibold text-slate-900 mb-3 text-xs uppercase tracking-wider">Platform</h4>
            <ul className="space-y-2 text-xs">
              <li><Link href="/career-assessment" className="hover:text-purple-600 transition">Skill Assessments</Link></li>
              <li><Link href="/resume-assessment" className="hover:text-purple-600 transition">Resume Analysis</Link></li>
              <li><Link href="/roadmap" className="hover:text-purple-600 transition">Adaptive Roadmaps</Link></li>
              <li><Link href="/career-domains" className="hover:text-purple-600 transition">Career Domains</Link></li>
              <li><Link href="/jobs" className="hover:text-purple-600 transition">Verified Job Matches</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-slate-900 mb-3 text-xs uppercase tracking-wider">Career Domains</h4>
            <ul className="space-y-2 text-xs">
              <li><Link href="/career-domains" className="hover:text-purple-600 transition">Frontend Engineering</Link></li>
              <li><Link href="/career-domains" className="hover:text-purple-600 transition">Backend Architecture</Link></li>
              <li><Link href="/career-domains" className="hover:text-purple-600 transition">Full-Stack Development</Link></li>
              <li><Link href="/career-domains" className="hover:text-purple-600 transition">Data Science & AI</Link></li>
              <li><Link href="/career-domains" className="hover:text-purple-600 transition">Cloud & DevOps</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-slate-900 mb-3 text-xs uppercase tracking-wider">Product Capabilities</h4>
            <div className="space-y-2 text-xs text-slate-500">
              <div className="flex items-center gap-1.5">
                <Award className="w-3.5 h-3.5 text-purple-600" />
                <span>Skill Assessments</span>
              </div>
              <div className="flex items-center gap-1.5">
                <BookOpen className="w-3.5 h-3.5 text-purple-600" />
                <span>Resume Analysis</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-purple-600" />
                <span>Personalized Roadmaps</span>
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-purple-600" />
                <span>Career Recommendations</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Briefcase className="w-3.5 h-3.5 text-purple-600" />
                <span>Verified Job Listings</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-purple-600" />
                <span>Secure Student Profiles</span>
              </div>
              <p className="text-[11px] text-slate-400 pt-2 border-t border-slate-100">
                All numerical scores are deterministically calculated. AI models provide rubric evaluation and contextual explanations.
              </p>
            </div>
          </div>
        </div>

        <div className="mt-8 pt-8 border-t border-slate-100 flex flex-col sm:flex-row justify-between items-center text-xs text-slate-400 gap-4">
          <p>© 2026 SkillPath AI. Production-Oriented Career Intelligence Platform.</p>
          <div className="flex space-x-6">
            <span>Deterministic Scoring</span>
            <span>Rubric Grounding</span>
            <span>Verified Alignment</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
