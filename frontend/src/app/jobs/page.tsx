"use client";

import React, { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/lib/auth-context";
import { apiRequest } from "@/lib/api";
import {
  Briefcase,
  Search,
  Filter,
  MapPin,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  Building,
  GraduationCap,
  Calendar,
  Send,
  Clock,
  Sparkles,
  ChevronRight,
  X,
  FileText
} from "lucide-react";

export default function JobsPage() {
  const { user, token } = useAuth();
  const [activeTab, setActiveTab] = useState<"opportunities" | "applications">("opportunities");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const urlParams = new URLSearchParams(window.location.search);
      if (urlParams.get("tab") === "applications") {
        setActiveTab("applications");
      }
    }
  }, []);

  // Opportunities state
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [opportunityTypeFilter, setOpportunityTypeFilter] = useState("all");
  const [domainFilter, setDomainFilter] = useState("all");
  const [workModeFilter, setWorkModeFilter] = useState("all");

  // Applications state
  const [myApplications, setMyApplications] = useState<any[]>([]);
  const [loadingApps, setLoadingApps] = useState(false);
  const [withdrawingId, setWithdrawingId] = useState<string | null>(null);

  // Application modal state
  const [selectedJob, setSelectedJob] = useState<any | null>(null);
  const [coverLetter, setCoverLetter] = useState("");
  const [applying, setApplying] = useState(false);
  const [applySuccess, setApplySuccess] = useState<string | null>(null);
  const [applyError, setApplyError] = useState<string | null>(null);

  const loadJobs = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (search) params.append("q", search);
      if (opportunityTypeFilter !== "all") params.append("opportunity_type", opportunityTypeFilter);
      if (domainFilter !== "all") params.append("domain", domainFilter);
      if (workModeFilter !== "all") params.append("work_mode", workModeFilter);

      const data = await apiRequest<any[]>(`/jobs?${params.toString()}`, { token });
      setJobs(data || []);
    } catch (err) {
      console.error("Failed to load jobs:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadMyApplications = async () => {
    if (!user) return;
    setLoadingApps(true);
    try {
      const data = await apiRequest<any[]>("/applications/my", { token });
      setMyApplications(data || []);
    } catch (err) {
      console.error("Failed to load my applications:", err);
    } finally {
      setLoadingApps(false);
    }
  };

  const lastFetchKeyRef = useRef<string>("");

  useEffect(() => {
    if (user) {
      const fetchKey = `${user.uid}_${token || ""}_${opportunityTypeFilter}_${domainFilter}_${workModeFilter}`;
      if (lastFetchKeyRef.current === fetchKey) return;
      lastFetchKeyRef.current = fetchKey;

      loadJobs();
      loadMyApplications();
    }
  }, [user, token, opportunityTypeFilter, domainFilter, workModeFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadJobs();
  };

  const handleOpenApplyModal = (job: any) => {
    setSelectedJob(job);
    setCoverLetter("");
    setApplySuccess(null);
    setApplyError(null);
  };

  const handleCloseModal = () => {
    setSelectedJob(null);
    setCoverLetter("");
    setApplySuccess(null);
    setApplyError(null);
  };

  const handleSubmitApplication = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedJob) return;

    setApplying(true);
    setApplyError(null);
    try {
      await apiRequest("/applications/apply", {
        method: "POST",
        token,
        body: JSON.stringify({
          job_id: selectedJob.id,
          cover_letter: coverLetter,
        }),
      });
      setApplySuccess("Application submitted successfully! Track status in My Applications.");
      await loadMyApplications();
      setTimeout(() => {
        handleCloseModal();
      }, 1500);
    } catch (err: any) {
      setApplyError(err.message || "Failed to submit application.");
    } finally {
      setApplying(false);
    }
  };

  const handleWithdraw = async (applicationId: string) => {
    if (!confirm("Are you sure you want to withdraw this application?")) return;
    setWithdrawingId(applicationId);
    try {
      await apiRequest(`/applications/${applicationId}/withdraw`, {
        method: "PATCH",
        token,
      });
      await loadMyApplications();
    } catch (err: any) {
      alert(`Withdrawal failed: ${err.message}`);
    } finally {
      setWithdrawingId(null);
    }
  };

  const appliedJobIds = new Set(myApplications.map((a) => a.job_id));
  const getApplicationForJob = (jobId: string) => myApplications.find((a) => a.job_id === jobId);

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
      title="Jobs & Internships"
      description="Discover active engineering jobs and internships. Apply directly and track your application progress."
    >
      <div className="space-y-6">
        {/* Navigation Tabs */}
        <div className="flex border-b border-slate-200 gap-6 text-sm font-semibold">
          <button
            onClick={() => setActiveTab("opportunities")}
            className={`pb-3 transition flex items-center gap-2 ${
              activeTab === "opportunities"
                ? "border-b-2 border-purple-600 text-purple-600 font-bold"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            <Briefcase className="w-4 h-4" />
            <span>Discover Opportunities</span>
            <span className="px-2 py-0.5 rounded-full text-xs bg-slate-100 text-slate-700">
              {jobs.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab("applications")}
            className={`pb-3 transition flex items-center gap-2 ${
              activeTab === "applications"
                ? "border-b-2 border-purple-600 text-purple-600 font-bold"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            <FileText className="w-4 h-4" />
            <span>My Applications</span>
            <span className="px-2 py-0.5 rounded-full text-xs bg-purple-100 text-purple-700 font-bold">
              {myApplications.length}
            </span>
          </button>
        </div>

        {/* TAB 1: OPPORTUNITIES */}
        {activeTab === "opportunities" && (
          <div className="space-y-6">
            {/* Search & Filter Bar */}
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-3">
              <form onSubmit={handleSearchSubmit} className="flex flex-col lg:flex-row gap-3">
                <div className="relative flex-1">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                  <input
                    type="text"
                    placeholder="Search by job title, company, skill, or keyword..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="w-full pl-9 pr-4 py-2 rounded-lg border border-slate-300 text-sm text-slate-900 bg-white placeholder:text-slate-400 focus:ring-2 focus:ring-purple-600 focus:border-purple-600 focus:outline-none"
                  />
                </div>

                <div className="flex flex-wrap gap-2">
                  <select
                    value={opportunityTypeFilter}
                    onChange={(e) => setOpportunityTypeFilter(e.target.value)}
                    className="px-3 py-2 rounded-lg border border-slate-300 text-xs font-semibold bg-white text-slate-700"
                  >
                    <option value="all">All Opportunity Types</option>
                    <option value="Job">Jobs Only</option>
                    <option value="Internship">Internships Only</option>
                  </select>

                  <select
                    value={domainFilter}
                    onChange={(e) => setDomainFilter(e.target.value)}
                    className="px-3 py-2 rounded-lg border border-slate-300 text-xs font-semibold bg-white text-slate-700"
                  >
                    <option value="all">All Domains</option>
                    <option value="Frontend">Frontend</option>
                    <option value="Backend">Backend</option>
                    <option value="Full-Stack">Full-Stack</option>
                    <option value="Data Science">Data Science</option>
                    <option value="Machine Learning">Machine Learning / AI</option>
                    <option value="DevOps">Cloud / DevOps</option>
                    <option value="Cybersecurity">Cybersecurity</option>
                  </select>

                  <select
                    value={workModeFilter}
                    onChange={(e) => setWorkModeFilter(e.target.value)}
                    className="px-3 py-2 rounded-lg border border-slate-300 text-xs font-semibold bg-white text-slate-700"
                  >
                    <option value="all">All Work Modes</option>
                    <option value="Remote">Remote</option>
                    <option value="Hybrid">Hybrid</option>
                    <option value="Onsite">Onsite</option>
                  </select>

                  <button
                    type="submit"
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold rounded-lg transition"
                  >
                    Filter
                  </button>
                </div>
              </form>
            </div>

            {/* Opportunities List */}
            {loading ? (
              <div className="space-y-4 animate-pulse">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-44 bg-slate-200 rounded-xl"></div>
                ))}
              </div>
            ) : jobs.length > 0 ? (
              <div className="space-y-4">
                {jobs.map((item: any) => {
                  const job = item.job || item;
                  const isEligible = item.eligibility_met !== undefined ? item.eligibility_met : true;
                  const matchScore = item.match_score !== undefined ? item.match_score : null;
                  const hasApplied = appliedJobIds.has(job.id);
                  const existingApp = hasApplied ? getApplicationForJob(job.id) : null;
                  const oppType = job.opportunity_type || "Job";

                  return (
                    <div
                      key={job.id}
                      className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-4 hover:border-purple-200 transition"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 pb-3 border-b border-slate-100">
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <h3 className="text-lg font-bold text-slate-900">{job.title}</h3>
                            <span
                              className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${
                                oppType === "Internship"
                                  ? "bg-purple-50 text-purple-700 border border-purple-200"
                                  : "bg-blue-50 text-blue-700 border border-blue-200"
                              }`}
                            >
                              {oppType}
                            </span>
                            <span
                              className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${
                                isEligible
                                  ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                  : "bg-rose-50 text-rose-700 border border-rose-200"
                              }`}
                            >
                              {isEligible ? "Eligible" : "Eligibility Criteria Unmet"}
                            </span>
                          </div>

                          <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 mt-1">
                            <span className="font-semibold text-slate-700">{job.company}</span>
                            <span>•</span>
                            <span className="text-purple-700 font-medium">{job.domain}</span>
                            <span>•</span>
                            <span className="flex items-center gap-1">
                              <MapPin className="w-3.5 h-3.5 text-slate-400" />
                              {job.location} ({job.work_mode})
                            </span>
                            <span>•</span>
                            <span className="flex items-center gap-1">
                              <GraduationCap className="w-3.5 h-3.5 text-slate-400" />
                              Min: {job.required_education || "Bachelor's"}
                            </span>
                            {job.deadline && (
                              <>
                                <span>•</span>
                                <span className="flex items-center gap-1 text-slate-600">
                                  <Calendar className="w-3.5 h-3.5 text-slate-400" />
                                  Deadline: {job.deadline}
                                </span>
                              </>
                            )}
                          </div>
                        </div>

                        {item.match_status === "assessment_required" ? (
                          <div className="text-right flex-shrink-0">
                            <Link
                              href="/career-assessment"
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-xs font-bold hover:bg-amber-100 transition"
                            >
                              <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
                              <span>Complete your skill assessment</span>
                            </Link>
                            <span className="block text-[10px] text-slate-400 mt-1">
                              Confirmed skills needed
                            </span>
                          </div>
                        ) : item.match_status === "match_unavailable" ? (
                          <div className="text-right flex-shrink-0">
                            <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-100 border border-slate-200 text-slate-600 text-xs font-bold">
                              Match unavailable
                            </span>
                            <span className="block text-[10px] text-slate-400 mt-1">
                              No requirements listed
                            </span>
                          </div>
                        ) : matchScore !== null ? (
                          <div className="text-right flex-shrink-0">
                            <div
                              className={`text-2xl font-extrabold ${
                                matchScore >= 60
                                  ? "text-emerald-600"
                                  : matchScore > 0
                                  ? "text-purple-600"
                                  : "text-slate-500"
                              }`}
                            >
                              {matchScore}%
                            </div>
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                              Skill Match
                            </span>
                          </div>
                        ) : null}
                      </div>

                      <p className="text-xs text-slate-600 leading-relaxed">{job.description}</p>

                      {/* Match Explanation & Alignment */}
                      {item.explanation && item.match_status !== "assessment_required" && item.match_status !== "match_unavailable" && (
                        <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-600">
                          <span className="font-semibold text-slate-700 block mb-0.5">Match Breakdown:</span>
                          <span>{item.explanation}</span>
                        </div>
                      )}

                      {/* Skills Alignment */}
                      <div className="space-y-2 text-xs">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="font-bold text-slate-700 mr-1">Required Skills:</span>
                          {job.required_skills?.map((s: string, idx: number) => {
                            const isMatched = item.matched_required_skills?.includes(s);
                            return (
                              <span
                                key={idx}
                                className={`px-2 py-0.5 rounded-md border text-[11px] font-medium ${
                                  isMatched
                                    ? "bg-emerald-50 border-emerald-300 text-emerald-800 font-semibold"
                                    : "bg-slate-100 border-slate-200 text-slate-700"
                                }`}
                              >
                                {isMatched ? "✓ " : ""}{s}
                              </span>
                            );
                          })}
                        </div>

                        {job.preferred_skills && job.preferred_skills.length > 0 && (
                          <div className="flex flex-wrap items-center gap-1.5">
                            <span className="font-bold text-slate-500 mr-1">Preferred Skills:</span>
                            {job.preferred_skills.map((s: string, idx: number) => {
                              const isMatched = item.matched_preferred_skills?.includes(s);
                              return (
                                <span
                                  key={idx}
                                  className={`px-2 py-0.5 rounded-md border text-[11px] ${
                                    isMatched
                                      ? "bg-purple-50 border-purple-300 text-purple-800 font-semibold"
                                      : "bg-slate-50 border-slate-200 text-slate-500"
                                  }`}
                                >
                                  {isMatched ? "✓ " : ""}{s}
                                </span>
                              );
                            })}
                          </div>
                        )}
                      </div>

                      {/* Card Actions */}
                      <div className="pt-2 flex items-center justify-between border-t border-slate-100">
                        <div>
                          {hasApplied && existingApp && (
                            <div className="flex items-center gap-2">
                              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                              <span className="text-xs font-semibold text-slate-700">
                                Applied:
                              </span>
                              <span
                                className={`text-xs px-2.5 py-0.5 rounded-full font-bold border ${getStatusBadge(
                                  existingApp.status
                                )}`}
                              >
                                {existingApp.status}
                              </span>
                            </div>
                          )}
                        </div>

                        <div className="flex gap-2">
                          {hasApplied ? (
                            <button
                              onClick={() => setActiveTab("applications")}
                              className="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition"
                            >
                              View Status
                            </button>
                          ) : (
                            <button
                              onClick={() => handleOpenApplyModal(job)}
                              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-700 text-white font-semibold text-xs shadow-xs transition"
                            >
                              <Send className="w-3.5 h-3.5" />
                              <span>Apply Now</span>
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="bg-white p-12 rounded-xl border border-slate-200 text-center space-y-3">
                <Briefcase className="w-10 h-10 text-slate-300 mx-auto" />
                <h3 className="text-base font-bold text-slate-800">No Listings Found</h3>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  No active listings match your current filters. Try selecting All Opportunity Types or All Domains.
                </p>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: MY APPLICATIONS */}
        {activeTab === "applications" && (
          <div className="space-y-4">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex justify-between items-center">
              <div>
                <h3 className="font-bold text-slate-900 text-sm">Submitted Applications</h3>
                <p className="text-xs text-slate-500">
                  Track the review and interview stages of your submitted job and internship applications.
                </p>
              </div>
              <button
                onClick={loadMyApplications}
                className="px-3 py-1.5 text-xs font-semibold text-purple-600 bg-purple-50 rounded-lg hover:bg-purple-100 transition"
              >
                Refresh
              </button>
            </div>

            {loadingApps ? (
              <div className="space-y-4 animate-pulse">
                {[1, 2].map((i) => (
                  <div key={i} className="h-32 bg-slate-200 rounded-xl"></div>
                ))}
              </div>
            ) : myApplications.length > 0 ? (
              <div className="space-y-3">
                {myApplications.map((app) => {
                  const canWithdraw = ["Submitted", "Under Review", "Shortlisted", "Interview"].includes(
                    app.status
                  );

                  return (
                    <div
                      key={app.id}
                      className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-3 hover:border-slate-300 transition"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <h4 className="font-bold text-base text-slate-900">{app.job_title}</h4>
                            <span
                              className={`text-xs px-2.5 py-0.5 rounded-full font-bold border ${getStatusBadge(
                                app.status
                              )}`}
                            >
                              {app.status}
                            </span>
                          </div>
                          <div className="flex items-center gap-3 text-xs text-slate-500 mt-1">
                            <span className="font-semibold text-slate-700">{app.company_name}</span>
                            <span>•</span>
                            <span className="flex items-center gap-1">
                              <Clock className="w-3.5 h-3.5 text-slate-400" />
                              Submitted: {new Date(app.submission_date).toLocaleDateString()}
                            </span>
                          </div>
                        </div>

                        <div>
                          {canWithdraw && (
                            <button
                              onClick={() => handleWithdraw(app.id)}
                              disabled={withdrawingId === app.id}
                              className="px-3 py-1.5 rounded-lg border border-rose-300 text-rose-700 hover:bg-rose-50 text-xs font-semibold transition disabled:opacity-50"
                            >
                              {withdrawingId === app.id ? "Withdrawing..." : "Withdraw Application"}
                            </button>
                          )}
                        </div>
                      </div>

                      {app.cover_letter && (
                        <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs text-slate-600">
                          <span className="font-semibold text-slate-700 block mb-1">
                            Your Statement of Interest / Cover Letter:
                          </span>
                          <p className="whitespace-pre-line">{app.cover_letter}</p>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="bg-white p-12 rounded-xl border border-slate-200 text-center space-y-3">
                <FileText className="w-10 h-10 text-slate-300 mx-auto" />
                <h3 className="text-base font-bold text-slate-800">No Applications Yet</h3>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  You haven't submitted any applications. Switch to Discover Opportunities to find roles matching your skills.
                </p>
                <button
                  onClick={() => setActiveTab("opportunities")}
                  className="px-4 py-2 bg-purple-600 text-white text-xs font-semibold rounded-lg hover:bg-purple-700 transition"
                >
                  Browse Opportunities
                </button>
              </div>
            )}
          </div>
        )}

        {/* APPLICATION MODAL */}
        {selectedJob && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-4 max-h-[90vh] overflow-y-auto">
              <div className="flex justify-between items-start border-b border-slate-100 pb-3">
                <div>
                  <span className="text-xs font-bold text-purple-600 uppercase tracking-wider">
                    {selectedJob.opportunity_type || "Job"} Application
                  </span>
                  <h3 className="text-lg font-bold text-slate-900">{selectedJob.title}</h3>
                  <p className="text-xs text-slate-500">
                    {selectedJob.company} • {selectedJob.location} ({selectedJob.work_mode})
                  </p>
                </div>
                <button
                  onClick={handleCloseModal}
                  className="text-slate-400 hover:text-slate-600 p-1 rounded-md"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {applySuccess ? (
                <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
                  <span>{applySuccess}</span>
                </div>
              ) : (
                <form onSubmit={handleSubmitApplication} className="space-y-4 text-xs">
                  {applyError && (
                    <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 font-semibold flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
                      <span>{applyError}</span>
                    </div>
                  )}

                  <div className="bg-purple-50/50 p-3.5 rounded-xl border border-purple-100 space-y-2">
                    <div className="font-semibold text-slate-800">Application Confirmation:</div>
                    <p className="text-slate-600 leading-relaxed">
                      Your authenticated student profile ({user?.name || user?.email}) and validated skill record will be shared directly with the hiring administrator for {selectedJob.company}.
                    </p>
                    <div className="text-[11px] text-slate-500">
                      Required Education: {selectedJob.required_education || "Bachelor's"} • Required Skills: {selectedJob.required_skills?.join(", ")}
                    </div>
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">
                      Statement of Interest / Cover Letter (Optional)
                    </label>
                    <textarea
                      rows={4}
                      value={coverLetter}
                      onChange={(e) => setCoverLetter(e.target.value)}
                      placeholder="Highlight relevant projects, technologies, and why you are excited about this opportunity..."
                      className="w-full p-3 rounded-lg border border-slate-300 text-xs text-slate-900 bg-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-600 focus:border-purple-600"
                    />
                  </div>

                  <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                    <button
                      type="button"
                      onClick={handleCloseModal}
                      className="px-4 py-2 rounded-lg border border-slate-300 text-slate-700 font-semibold hover:bg-slate-50 transition"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={applying}
                      className="inline-flex items-center gap-1.5 px-5 py-2 rounded-lg bg-purple-600 hover:bg-purple-700 text-white font-semibold shadow-xs transition disabled:opacity-50"
                    >
                      <Send className="w-3.5 h-3.5" />
                      <span>{applying ? "Submitting..." : "Confirm Application"}</span>
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
