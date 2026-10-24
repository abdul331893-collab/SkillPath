"use client";

import React, { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/lib/auth-context";
import { apiRequest } from "@/lib/api";
import {
  Briefcase,
  Clock,
  CheckCircle2,
  AlertCircle,
  Building,
  MapPin,
  ExternalLink,
  ChevronRight,
  FileText,
  Calendar,
  XCircle,
  RefreshCw,
  ArrowLeft
} from "lucide-react";

export default function ApplicationsPage() {
  const { user, token } = useAuth();
  const [applications, setApplications] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [withdrawingId, setWithdrawingId] = useState<string | null>(null);
  const [selectedApp, setSelectedApp] = useState<any | null>(null);

  const loadApplications = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await apiRequest<any[]>("/applications/my", { token });
      setApplications(data || []);
    } catch (err: any) {
      console.error("Failed to load applications:", err);
    } finally {
      setLoading(false);
    }
  };

  const lastAppFetchKeyRef = useRef<string>("");

  useEffect(() => {
    if (user && token) {
      const fetchKey = `${user.uid}_${token}`;
      if (lastAppFetchKeyRef.current === fetchKey) return;
      lastAppFetchKeyRef.current = fetchKey;

      loadApplications();
    }
  }, [user, token]);

  const handleWithdraw = async (appId: string) => {
    if (!confirm("Are you sure you want to withdraw this application? This action cannot be undone.")) {
      return;
    }
    setWithdrawingId(appId);
    try {
      await apiRequest(`/applications/${appId}/withdraw`, {
        method: "PATCH",
        token,
      });
      await loadApplications();
    } catch (err: any) {
      alert(`Withdrawal failed: ${err.message}`);
    } finally {
      setWithdrawingId(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "Submitted":
        return "bg-blue-50 text-blue-700 border-blue-200";
      case "Under Review":
        return "bg-amber-50 text-amber-700 border-amber-200";
      case "Shortlisted":
        return "bg-purple-50 text-purple-700 border-purple-200";
      case "Interview":
        return "bg-indigo-50 text-indigo-700 border-indigo-200";
      case "Selected":
        return "bg-emerald-50 text-emerald-700 border-emerald-200";
      case "Rejected":
        return "bg-rose-50 text-rose-700 border-rose-200";
      case "Withdrawn":
        return "bg-slate-100 text-slate-600 border-slate-300";
      default:
        return "bg-slate-50 text-slate-700 border-slate-200";
    }
  };

  return (
    <AppShell
      title="My Job & Internship Applications"
      description="Track the real-time review stages, interview schedules, and submission history of all your applications."
    >
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div>
            <h2 className="text-base font-bold text-slate-900">Submitted Applications ({applications.length})</h2>
            <p className="text-xs text-slate-500">
              Persistent tracking across sessions, verified by server-side Firebase Authentication.
            </p>
          </div>
          <div className="flex gap-2">
            <Link
              href="/jobs"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
            >
              <Briefcase className="w-3.5 h-3.5" />
              <span>Browse More Opportunities</span>
            </Link>
            <button
              onClick={loadApplications}
              disabled={loading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-purple-50 border border-purple-200 text-xs font-semibold text-purple-700 hover:bg-purple-100 transition"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {loading ? (
          <div className="space-y-4 animate-pulse">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-32 bg-slate-200 rounded-xl"></div>
            ))}
          </div>
        ) : applications.length > 0 ? (
          <div className="space-y-4">
            {applications.map((app) => (
              <div
                key={app.id}
                className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4 hover:border-purple-200 transition"
              >
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-bold text-slate-900 text-base">{app.job_title}</h3>
                      <span
                        className={`text-xs px-2.5 py-0.5 rounded-full font-bold border ${getStatusBadge(
                          app.status
                        )}`}
                      >
                        {app.status}
                      </span>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                        {app.opportunity_type || "Job"}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-y-1 gap-x-3 text-xs text-slate-500 mt-1.5">
                      <span className="flex items-center gap-1 font-semibold text-slate-700">
                        <Building className="w-3.5 h-3.5 text-slate-400" />
                        {app.company || app.company_name}
                      </span>
                      <span>•</span>
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3.5 h-3.5 text-slate-400" />
                        {app.location || "Remote"} ({app.work_mode || "Remote"})
                      </span>
                      <span>•</span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-slate-400" />
                        Applied: {new Date(app.submission_date).toLocaleDateString()}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {app.status !== "Withdrawn" && app.status !== "Selected" && app.status !== "Rejected" && (
                      <button
                        onClick={() => handleWithdraw(app.id)}
                        disabled={withdrawingId === app.id}
                        className="px-3 py-1.5 rounded-lg border border-slate-300 hover:bg-rose-50 hover:text-rose-700 hover:border-rose-200 text-xs font-semibold text-slate-600 transition"
                      >
                        {withdrawingId === app.id ? "Withdrawing..." : "Withdraw"}
                      </button>
                    )}
                  </div>
                </div>

                {/* Candidate cover letter preview */}
                {app.cover_letter && (
                  <div className="p-3 rounded-lg bg-slate-50 border border-slate-100 text-xs text-slate-600">
                    <span className="font-bold text-slate-700 block mb-0.5">Your Statement of Interest:</span>
                    <p className="whitespace-pre-line line-clamp-3">{app.cover_letter}</p>
                  </div>
                )}

                {/* Status history audit trail */}
                {app.status_history && app.status_history.length > 0 && (
                  <div className="pt-2 border-t border-slate-100">
                    <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-2">
                      Review Progress Timeline
                    </span>
                    <div className="space-y-1.5 text-xs">
                      {app.status_history.map((h: any, idx: number) => (
                        <div key={idx} className="flex items-center justify-between text-slate-600">
                          <div className="flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-purple-600"></span>
                            <span className="font-semibold text-slate-800">{h.status}</span>
                            {h.notes && <span className="text-slate-500">— {h.notes}</span>}
                          </div>
                          <span className="text-[10px] text-slate-400">
                            {new Date(h.timestamp).toLocaleString()}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-white p-12 rounded-xl border border-slate-200 text-center space-y-3">
            <Briefcase className="w-10 h-10 text-slate-300 mx-auto" />
            <h3 className="text-base font-bold text-slate-800">No Applications Submitted Yet</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              You haven't submitted applications yet. Browse recommended opportunities matched to your verified competencies and apply.
            </p>
            <div className="pt-2">
              <Link
                href="/jobs"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold transition"
              >
                <span>Browse Opportunities</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
