"use client";

import React, { useEffect, useState, useRef } from "react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/lib/auth-context";
import { apiRequest } from "@/lib/api";
import {
  ShieldAlert,
  Users,
  Award,
  Briefcase,
  UploadCloud,
  Plus,
  CheckCircle2,
  AlertCircle,
  Activity,
  FileSpreadsheet,
  Trash2,
  Edit2,
  Search,
  Filter,
  FileText,
  Clock,
  BookOpen,
  Settings,
  X,
  ExternalLink,
  ChevronRight,
  UserCheck,
  UserX,
  Eye
} from "lucide-react";

export default function AdminPage() {
  const { user, token } = useAuth();
  const [activeTab, setActiveTab] = useState<
    "overview" | "users" | "jobs" | "applications" | "questions" | "resources" | "settings"
  >("overview");

  const [stats, setStats] = useState<any>(null);
  const [usersList, setUsersList] = useState<any[]>([]);
  const [jobsList, setJobsList] = useState<any[]>([]);
  const [applicationsList, setApplicationsList] = useState<any[]>([]);
  const [questions, setQuestions] = useState<any[]>([]);
  const [assessmentsList, setAssessmentsList] = useState<any[]>([]);
  const [assessmentsSubTab, setAssessmentsSubTab] = useState<"assessments" | "questions">("assessments");
  const [loading, setLoading] = useState(true);
  const [adminError, setAdminError] = useState<string | null>(null);

  // User Management State
  const [userSearch, setUserSearch] = useState("");
  const [userRoleFilter, setUserRoleFilter] = useState("all");
  const [selectedUserSummary, setSelectedUserSummary] = useState<any | null>(null);
  const [loadingUserSummary, setLoadingUserSummary] = useState(false);

  // New Job Form State
  const [newJob, setNewJob] = useState({
    title: "",
    company: "",
    opportunity_type: "Job",
    domain: "Frontend Development",
    location: "Remote",
    work_mode: "Remote",
    deadline: "",
    required_skills: "React, JavaScript",
    preferred_skills: "TypeScript",
    min_experience_years: 0,
    required_education: "Bachelor's",
    description: "",
    application_url: "",
  });
  const [jobCreating, setJobCreating] = useState(false);
  const [jobMessage, setJobMessage] = useState<string | null>(null);

  // Bulk CSV Upload State
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvImporting, setCsvImporting] = useState(false);
  const [importReport, setImportReport] = useState<any>(null);

  // Applications Review Modal State
  const [selectedApplication, setSelectedApplication] = useState<any | null>(null);
  const [appStatusUpdate, setAppStatusUpdate] = useState("Under Review");
  const [adminNotes, setAdminNotes] = useState("");
  const [updatingApp, setUpdatingApp] = useState(false);
  const [appFilterStatus, setAppFilterStatus] = useState("all");

  // Application Deletion State
  const [appToDelete, setAppToDelete] = useState<any | null>(null);
  const [deletingApp, setDeletingApp] = useState(false);
  const [deleteAppSuccess, setDeleteAppSuccess] = useState<string | null>(null);

  // Assessment Inspection & Filtering State
  const [selectedAssessmentDetail, setSelectedAssessmentDetail] = useState<any | null>(null);
  const [loadingAssessmentDetail, setLoadingAssessmentDetail] = useState(false);
  const [assessmentDomainFilter, setAssessmentDomainFilter] = useState("all");
  const [assessmentStatusFilter, setAssessmentStatusFilter] = useState("all");
  const [assessmentSearch, setAssessmentSearch] = useState("");

  const loadAdminData = async () => {
    setLoading(true);
    setAdminError(null);
    try {
      const [statsRes, usersRes, questionsRes, jobsRes, appsRes, assessRes] = await Promise.allSettled([
        apiRequest<any>("/admin/stats", { token }),
        apiRequest<any[]>("/admin/users", { token }),
        apiRequest<any[]>("/admin/questions", { token }),
        apiRequest<any[]>("/jobs", { token }),
        apiRequest<any[]>("/applications", { token }),
        apiRequest<any[]>("/admin/assessments", { token }),
      ]);

      const failedEndpoints: string[] = [];
      if (statsRes.status === "fulfilled") setStats(statsRes.value);
      else failedEndpoints.push("System Stats");

      if (usersRes.status === "fulfilled") setUsersList(usersRes.value || []);
      else failedEndpoints.push("User Directory");

      if (questionsRes.status === "fulfilled") setQuestions(questionsRes.value || []);
      else failedEndpoints.push("Question Bank");

      if (jobsRes.status === "fulfilled") setJobsList(jobsRes.value || []);
      else failedEndpoints.push("Jobs & Internships");

      if (appsRes.status === "fulfilled") setApplicationsList(appsRes.value || []);
      else failedEndpoints.push("Applications");

      if (assessRes.status === "fulfilled") setAssessmentsList(assessRes.value || []);
      else failedEndpoints.push("Student Assessments");

      if (failedEndpoints.length > 0) {
        setAdminError(`Unable to load data from: ${failedEndpoints.join(", ")}. Please check your permissions and server connection.`);
      }
    } catch (err: any) {
      console.error("Failed to load admin data:", err);
      setAdminError(err?.message || "Failed to load admin dashboard records");
    } finally {
      setLoading(false);
    }
  };

  const lastAdminFetchKeyRef = useRef<string>("");

  useEffect(() => {
    if (user && user.role === "admin") {
      const fetchKey = `${user.uid}_${token || ""}`;
      if (lastAdminFetchKeyRef.current === fetchKey) return;
      lastAdminFetchKeyRef.current = fetchKey;

      loadAdminData();
    }
  }, [user, token]);

  const handleToggleUserStatus = async (uid: string, currentActive: boolean) => {
    try {
      await apiRequest(`/admin/users/${uid}/status`, {
        method: "PATCH",
        token,
        body: JSON.stringify({ is_active: !currentActive }),
      });
      loadAdminData();
    } catch (err: any) {
      alert(`Status update failed: ${err.message}`);
    }
  };

  const handleRoleChange = async (uid: string, currentRole: string) => {
    const newRole = currentRole === "admin" ? "student" : "admin";
    try {
      await apiRequest(`/admin/users/${uid}/role`, {
        method: "PATCH",
        token,
        body: JSON.stringify({ role: newRole }),
      });
      loadAdminData();
    } catch (err: any) {
      alert(`Role change failed: ${err.message}`);
    }
  };

  const handleViewUserSummary = async (uid: string) => {
    setLoadingUserSummary(true);
    try {
      const summary = await apiRequest<any>(`/admin/users/${uid}/summary`, { token });
      setSelectedUserSummary(summary);
    } catch (err: any) {
      alert(`Failed to load student summary: ${err.message}`);
    } finally {
      setLoadingUserSummary(false);
    }
  };

  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    setJobCreating(true);
    setJobMessage(null);
    try {
      await apiRequest("/admin/jobs", {
        method: "POST",
        token,
        body: JSON.stringify({
          ...newJob,
          required_skills: newJob.required_skills.split(",").map((s) => s.trim()).filter(Boolean),
          preferred_skills: newJob.preferred_skills.split(",").map((s) => s.trim()).filter(Boolean),
        }),
      });
      setJobMessage("Opportunity listing published successfully!");
      setNewJob({
        title: "",
        company: "",
        opportunity_type: "Job",
        domain: "Frontend Development",
        location: "Remote",
        work_mode: "Remote",
        deadline: "",
        required_skills: "React, JavaScript",
        preferred_skills: "TypeScript",
        min_experience_years: 0,
        required_education: "Bachelor's",
        description: "",
        application_url: "",
      });
      loadAdminData();
    } catch (err: any) {
      setJobMessage(`Error: ${err.message}`);
    } finally {
      setJobCreating(false);
    }
  };

  const handleDeleteJob = async (jobId: string) => {
    if (!confirm("Are you sure you want to delete this listing?")) return;
    try {
      await apiRequest(`/admin/jobs/${jobId}`, {
        method: "DELETE",
        token,
      });
      loadAdminData();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const handleBulkCsvImport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!csvFile) return;

    setCsvImporting(true);
    setImportReport(null);
    const formData = new FormData();
    formData.append("file", csvFile);

    try {
      const rep = await apiRequest<any>("/admin/jobs/bulk-import", {
        method: "POST",
        token,
        body: formData,
      });
      setImportReport(rep);
      setCsvFile(null);
      loadAdminData();
    } catch (err: any) {
      alert(`Bulk import error: ${err.message}`);
    } finally {
      setCsvImporting(false);
    }
  };

  const handleOpenAppReview = (app: any) => {
    setSelectedApplication(app);
    setAppStatusUpdate(app.status || "Under Review");
    setAdminNotes(app.admin_notes || "");
  };

  const handleUpdateApplicationStatus = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedApplication) return;

    setUpdatingApp(true);
    try {
      await apiRequest(`/applications/${selectedApplication.id}/status`, {
        method: "PATCH",
        token,
        body: JSON.stringify({
          status: appStatusUpdate,
          admin_notes: adminNotes,
        }),
      });
      setSelectedApplication(null);
      loadAdminData();
    } catch (err: any) {
      alert(`Status update failed: ${err.message}`);
    } finally {
      setUpdatingApp(false);
    }
  };

  const handleDeleteApplication = async (hardDelete = false) => {
    if (!appToDelete) return;
    setDeletingApp(true);
    try {
      await apiRequest(`/applications/${appToDelete.id}?hard_delete=${hardDelete}`, {
        method: "DELETE",
        token,
      });
      setDeleteAppSuccess(
        hardDelete
          ? `Application ${appToDelete.id} permanently deleted.`
          : `Application ${appToDelete.id} successfully archived.`
      );
      setAppToDelete(null);
      await loadAdminData();
      setTimeout(() => setDeleteAppSuccess(null), 4000);
    } catch (err: any) {
      alert(`Failed to delete application: ${err.message}`);
    } finally {
      setDeletingApp(false);
    }
  };

  const handleInspectAssessment = async (assessmentId: string) => {
    setLoadingAssessmentDetail(true);
    try {
      const detail = await apiRequest<any>(`/admin/assessments/${assessmentId}`, { token });
      setSelectedAssessmentDetail(detail);
    } catch (err: any) {
      alert(`Failed to load assessment details: ${err.message}`);
    } finally {
      setLoadingAssessmentDetail(false);
    }
  };

  const filteredUsers = usersList.filter((u) => {
    if (userRoleFilter !== "all" && u.role !== userRoleFilter) return false;
    if (userSearch) {
      const q = userSearch.toLowerCase();
      const match = `${u.name || ""} ${u.email || ""}`.toLowerCase();
      return match.includes(q);
    }
    return true;
  });

  const filteredApplications = applicationsList.filter((a) => {
    if (appFilterStatus !== "all" && a.status !== appFilterStatus) return false;
    return true;
  });

  const filteredAssessments = assessmentsList.filter((att) => {
    if (assessmentStatusFilter !== "all" && att.status !== assessmentStatusFilter) return false;
    if (assessmentDomainFilter !== "all" && att.domain !== assessmentDomainFilter) return false;
    if (assessmentSearch) {
      const q = assessmentSearch.toLowerCase();
      const match = `${att.student_name || ""} ${att.student_email || ""} ${att.domain || ""} ${att.id || att.assessment_id || ""}`.toLowerCase();
      return match.includes(q);
    }
    return true;
  });

  if (user?.role !== "admin") {
    return (
      <AppShell title="Access Restricted">
        <div className="bg-white p-8 rounded-xl border border-slate-200 text-center space-y-4">
          <ShieldAlert className="w-12 h-12 text-rose-600 mx-auto" />
          <h2 className="text-xl font-bold text-slate-900">Administrator Credentials Required</h2>
          <p className="text-sm text-slate-600 max-w-md mx-auto">
            You are currently signed in as a student. To test administrator governance features, switch your active role using the profile dropdown.
          </p>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell
      title="Administrator Platform"
      description="System administration: student accounts, job listings, applications review, assessments, and learning resources."
    >
      <div className="space-y-6">
        {adminError && (
          <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
              <span>{adminError}</span>
            </div>
            <button
              onClick={() => loadAdminData()}
              className="px-2.5 py-1 bg-amber-200 hover:bg-amber-300 text-amber-900 font-semibold rounded text-xs transition"
            >
              Retry
            </button>
          </div>
        )}

        {/* Navigation Tabs (7 sections) */}
        <div className="flex border-b border-slate-200 gap-4 text-xs sm:text-sm font-semibold overflow-x-auto pb-1">
          {[
            { id: "overview", label: "Overview" },
            { id: "users", label: `User Management (${usersList.length})` },
            { id: "jobs", label: `Jobs & Internships (${jobsList.length})` },
            { id: "applications", label: `Applications (${applicationsList.length})` },
            { id: "questions", label: `Assessments (${assessmentsList.length}) & Questions (${questions.length})` },
            { id: "resources", label: "Learning Resources" },
            { id: "settings", label: "Settings" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`pb-3 whitespace-nowrap transition ${
                activeTab === tab.id
                  ? "border-b-2 border-purple-600 text-purple-600 font-bold"
                  : "text-slate-500 hover:text-slate-800"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* 1. OVERVIEW TAB */}
        {activeTab === "overview" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
                <span className="text-xs font-semibold text-slate-500 uppercase">
                  Total Registered Students
                </span>
                <div className="text-3xl font-extrabold text-slate-900 mt-1">
                  {stats?.total_registered_students ?? stats?.total_students ?? 0}
                </div>
                <span className="text-xs text-slate-400">Authentic student accounts</span>
              </div>

              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
                <span className="text-xs font-semibold text-slate-500 uppercase">
                  Active Jobs Managed
                </span>
                <div className="text-3xl font-extrabold text-purple-600 mt-1">
                  {stats?.total_active_jobs ?? 0}
                </div>
                <span className="text-xs text-slate-400">Published career positions</span>
              </div>

              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
                <span className="text-xs font-semibold text-slate-500 uppercase">
                  Active Internships
                </span>
                <div className="text-3xl font-extrabold text-blue-600 mt-1">
                  {stats?.total_active_internships ?? 0}
                </div>
                <span className="text-xs text-slate-400">Student internship opportunities</span>
              </div>

              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
                <span className="text-xs font-semibold text-slate-500 uppercase">
                  Total Applications
                </span>
                <div className="text-3xl font-extrabold text-emerald-600 mt-1">
                  {stats?.total_applications ?? applicationsList.length}
                </div>
                <span className="text-xs text-slate-400">Submitted by registered students</span>
              </div>

              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
                <span className="text-xs font-semibold text-slate-500 uppercase">
                  Applications Awaiting Review
                </span>
                <div className="text-3xl font-extrabold text-amber-600 mt-1">
                  {stats?.applications_awaiting_review ?? 0}
                </div>
                <span className="text-xs text-slate-400">Status: Submitted or Under Review</span>
              </div>

              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
                <span className="text-xs font-semibold text-slate-500 uppercase">
                  Assessments Completed
                </span>
                <div className="text-3xl font-extrabold text-indigo-600 mt-1">
                  {stats?.assessment_attempts_completed ?? stats?.total_assessments_taken ?? 0}
                </div>
                <span className="text-xs text-slate-400">
                  Average score: {stats?.average_assessment_score ?? 0}%
                </span>
              </div>
            </div>

            {/* Popular Career Domains */}
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-3">
              <h3 className="text-base font-bold text-slate-900">Popular Career Tracks</h3>
              <div className="space-y-2">
                {stats?.popular_career_domains?.map((p: any, idx: number) => (
                  <div key={idx} className="flex justify-between items-center text-xs p-3 rounded-lg bg-slate-50">
                    <span className="font-semibold text-slate-800">{p.domain}</span>
                    <span className="font-bold text-purple-600">{p.attempts} student attempts</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* 2. USER MANAGEMENT TAB */}
        {activeTab === "users" && (
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs space-y-4">
            <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
              <div>
                <h3 className="font-bold text-slate-900 text-sm">Registered User Directory</h3>
                <p className="text-xs text-slate-500">
                  Manage user accounts, toggle access, and inspect individual student records.
                </p>
              </div>

              <div className="flex gap-2 w-full sm:w-auto">
                <input
                  type="text"
                  placeholder="Search user..."
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                  className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
                <select
                  value={userRoleFilter}
                  onChange={(e) => setUserRoleFilter(e.target.value)}
                  className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-semibold bg-white text-slate-700"
                >
                  <option value="all">All Roles</option>
                  <option value="student">Students</option>
                  <option value="admin">Admins</option>
                </select>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-500 uppercase font-semibold border-b border-slate-200">
                  <tr>
                    <th className="p-3.5">User / Email</th>
                    <th className="p-3.5">Role</th>
                    <th className="p-3.5">Account Status</th>
                    <th className="p-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredUsers.map((u) => {
                    const isActive = u.is_active !== false;

                    return (
                      <tr key={u.uid} className="hover:bg-slate-50/50">
                        <td className="p-3.5">
                          <div className="font-bold text-slate-900">{u.name || "Student"}</div>
                          <div className="text-slate-500">{u.email}</div>
                        </td>
                        <td className="p-3.5">
                          <span
                            className={`px-2.5 py-0.5 rounded-full font-bold uppercase text-[10px] ${
                              u.role === "admin"
                                ? "bg-purple-100 text-purple-800"
                                : "bg-slate-100 text-slate-700"
                            }`}
                          >
                            {u.role}
                          </span>
                        </td>
                        <td className="p-3.5">
                          <span
                            className={`px-2 py-0.5 rounded-full font-semibold text-[11px] ${
                              isActive
                                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                : "bg-rose-50 text-rose-700 border border-rose-200"
                            }`}
                          >
                            {isActive ? "Active" : "Disabled"}
                          </span>
                        </td>
                        <td className="p-3.5 text-right space-x-2">
                          <button
                            onClick={() => handleViewUserSummary(u.uid)}
                            className="px-2.5 py-1 rounded-md border border-slate-300 text-slate-700 hover:bg-slate-100 font-semibold"
                          >
                            Summary
                          </button>
                          <button
                            onClick={() => handleToggleUserStatus(u.uid, isActive)}
                            className={`px-2.5 py-1 rounded-md text-xs font-semibold border transition ${
                              isActive
                                ? "border-rose-200 text-rose-700 hover:bg-rose-50"
                                : "border-emerald-200 text-emerald-700 hover:bg-emerald-50"
                            }`}
                          >
                            {isActive ? "Disable" : "Enable"}
                          </button>
                          <button
                            onClick={() => handleRoleChange(u.uid, u.role)}
                            className="px-2.5 py-1 rounded-md border border-purple-200 text-purple-700 hover:bg-purple-50 font-semibold"
                          >
                            Make {u.role === "admin" ? "Student" : "Admin"}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 3. JOBS & INTERNSHIPS TAB */}
        {activeTab === "jobs" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Create Listing Form */}
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4">
                <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
                  <Plus className="w-4 h-4 text-purple-600" />
                  <span>Create Job or Internship Listing</span>
                </h3>

                {jobMessage && (
                  <div className="p-3 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-semibold">
                    {jobMessage}
                  </div>
                )}

                <form onSubmit={handleCreateJob} className="space-y-3 text-xs">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">Opportunity Type</label>
                      <select
                        value={newJob.opportunity_type}
                        onChange={(e) => setNewJob({ ...newJob, opportunity_type: e.target.value })}
                        className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-purple-500"
                      >
                        <option value="Job">Job</option>
                        <option value="Internship">Internship</option>
                      </select>
                    </div>

                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">Career Domain</label>
                      <select
                        value={newJob.domain}
                        onChange={(e) => setNewJob({ ...newJob, domain: e.target.value })}
                        className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-purple-500"
                      >
                        <option value="Frontend Development">Frontend Development</option>
                        <option value="Backend Development">Backend Development</option>
                        <option value="Full-Stack Development">Full-Stack Development</option>
                        <option value="Data Science & Machine Learning">Data Science & ML</option>
                        <option value="Cloud and DevOps Engineering">Cloud and DevOps</option>
                        <option value="Cybersecurity">Cybersecurity</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Title</label>
                    <input
                      type="text"
                      required
                      value={newJob.title}
                      onChange={(e) => setNewJob({ ...newJob, title: e.target.value })}
                      placeholder="e.g. Junior Backend Engineer or SWE Intern"
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">Company</label>
                      <input
                        type="text"
                        required
                        value={newJob.company}
                        onChange={(e) => setNewJob({ ...newJob, company: e.target.value })}
                        placeholder="e.g. Stripe"
                        className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
                      />
                    </div>
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">Application Deadline</label>
                      <input
                        type="date"
                        value={newJob.deadline}
                        onChange={(e) => setNewJob({ ...newJob, deadline: e.target.value })}
                        className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">Location</label>
                      <input
                        type="text"
                        value={newJob.location}
                        onChange={(e) => setNewJob({ ...newJob, location: e.target.value })}
                        placeholder="e.g. San Francisco or Remote"
                        className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
                      />
                    </div>
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">Work Mode</label>
                      <select
                        value={newJob.work_mode}
                        onChange={(e) => setNewJob({ ...newJob, work_mode: e.target.value })}
                        className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-purple-500"
                      >
                        <option value="Remote">Remote</option>
                        <option value="Hybrid">Hybrid</option>
                        <option value="Onsite">Onsite</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">
                      Required Skills (Comma-Separated)
                    </label>
                    <input
                      type="text"
                      required
                      value={newJob.required_skills}
                      onChange={(e) => setNewJob({ ...newJob, required_skills: e.target.value })}
                      placeholder="Python, FastAPI, SQL"
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">
                      Preferred Skills (Comma-Separated)
                    </label>
                    <input
                      type="text"
                      value={newJob.preferred_skills}
                      onChange={(e) => setNewJob({ ...newJob, preferred_skills: e.target.value })}
                      placeholder="Docker, Kubernetes"
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Description & Requirements</label>
                    <textarea
                      rows={3}
                      required
                      value={newJob.description}
                      onChange={(e) => setNewJob({ ...newJob, description: e.target.value })}
                      placeholder="Role expectations and qualifications..."
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={jobCreating}
                    className="w-full py-2.5 rounded-lg bg-purple-600 hover:bg-purple-700 text-white font-semibold transition"
                  >
                    {jobCreating ? "Publishing..." : "Publish Opportunity Listing"}
                  </button>
                </form>
              </div>

              {/* Bulk CSV Import */}
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4">
                <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
                  <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
                  <span>Bulk CSV Import</span>
                </h3>
                <p className="text-xs text-slate-600 leading-relaxed">
                  Bulk import listings with columns: <code>title, company, opportunity_type, domain, required_skills, location, deadline</code>.
                </p>

                <form onSubmit={handleBulkCsvImport} className="space-y-3">
                  <input
                    type="file"
                    accept=".csv"
                    onChange={(e) => setCsvFile(e.target.files ? e.target.files[0] : null)}
                    className="w-full text-xs text-slate-600 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100 cursor-pointer"
                  />

                  <button
                    type="submit"
                    disabled={!csvFile || csvImporting}
                    className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold transition disabled:opacity-50"
                  >
                    {csvImporting ? "Processing CSV..." : "Validate & Import CSV"}
                  </button>
                </form>

                {importReport && (
                  <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-2">
                    <div className="font-bold text-slate-800">CSV Import Report:</div>
                    <div className="flex gap-4">
                      <span className="text-emerald-700 font-semibold">Imported: {importReport.imported_count}</span>
                      <span className="text-rose-700 font-semibold">Failed: {importReport.failed_count}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Existing Listings Table */}
            <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
              <div className="p-4 border-b border-slate-100 flex justify-between items-center">
                <h3 className="font-bold text-slate-900 text-sm">Active Opportunities ({jobsList.length})</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-500 uppercase font-semibold border-b border-slate-200">
                    <tr>
                      <th className="p-3.5">Title & Company</th>
                      <th className="p-3.5">Type</th>
                      <th className="p-3.5">Domain</th>
                      <th className="p-3.5">Location</th>
                      <th className="p-3.5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {jobsList.map((item: any) => {
                      const job = item.job || item;
                      return (
                        <tr key={job.id} className="hover:bg-slate-50/50">
                          <td className="p-3.5">
                            <span className="font-bold text-slate-900 block">{job.title}</span>
                            <span className="text-slate-500">{job.company}</span>
                          </td>
                          <td className="p-3.5">
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-50 text-purple-700 border border-purple-200">
                              {job.opportunity_type || "Job"}
                            </span>
                          </td>
                          <td className="p-3.5 text-slate-600">{job.domain}</td>
                          <td className="p-3.5 text-slate-600">{job.location} ({job.work_mode})</td>
                          <td className="p-3.5 text-right">
                            <button
                              onClick={() => handleDeleteJob(job.id)}
                              className="text-rose-600 hover:text-rose-800 p-1 rounded"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* 4. APPLICATIONS TAB */}
        {activeTab === "applications" && (
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs space-y-4">
            {deleteAppSuccess && (
              <div className="mx-4 mt-4 p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span className="font-semibold">{deleteAppSuccess}</span>
                </div>
                <button onClick={() => setDeleteAppSuccess(null)} className="text-emerald-700 hover:text-emerald-900">
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}

            <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
              <div>
                <h3 className="font-bold text-slate-900 text-sm">All Student Applications</h3>
                <p className="text-xs text-slate-500">
                  Review applicant profiles, evaluate cover letters, and manage hiring pipeline statuses.
                </p>
              </div>

              <select
                value={appFilterStatus}
                onChange={(e) => setAppFilterStatus(e.target.value)}
                className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-semibold bg-white text-slate-700"
              >
                <option value="all">All Statuses</option>
                <option value="Submitted">Submitted</option>
                <option value="Under Review">Under Review</option>
                <option value="Shortlisted">Shortlisted</option>
                <option value="Interview">Interview</option>
                <option value="Selected">Selected</option>
                <option value="Rejected">Rejected</option>
                <option value="Withdrawn">Withdrawn</option>
              </select>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-500 uppercase font-semibold border-b border-slate-200">
                  <tr>
                    <th className="p-3.5">Student</th>
                    <th className="p-3.5">Opportunity</th>
                    <th className="p-3.5">Type</th>
                    <th className="p-3.5">Applied Date</th>
                    <th className="p-3.5">Status</th>
                    <th className="p-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredApplications.map((app) => (
                    <tr key={app.id} className="hover:bg-slate-50/50">
                      <td className="p-3.5">
                        <span className="font-bold text-slate-900 block">{app.student_name || "Student"}</span>
                        <span className="text-slate-500">{app.student_email}</span>
                      </td>
                      <td className="p-3.5">
                        <span className="font-semibold text-slate-800 block">{app.job_title}</span>
                        <span className="text-slate-500">{app.company || app.company_name || "Company"}</span>
                      </td>
                      <td className="p-3.5">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700">
                          {app.opportunity_type || "Job"}
                        </span>
                      </td>
                      <td className="p-3.5 text-slate-600">
                        {new Date(app.submission_date).toLocaleDateString()}
                      </td>
                      <td className="p-3.5">
                        <span className="px-2.5 py-0.5 rounded-full font-bold text-[10px] bg-purple-50 text-purple-700 border border-purple-200">
                          {app.status}
                        </span>
                      </td>
                      <td className="p-3.5 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleOpenAppReview(app)}
                            className="px-3 py-1 rounded-md bg-purple-600 hover:bg-purple-700 text-white font-semibold text-xs"
                          >
                            Review & Update
                          </button>
                          <button
                            onClick={() => setAppToDelete(app)}
                            className="p-1.5 rounded-md text-rose-600 hover:bg-rose-50 hover:text-rose-800 transition"
                            title="Delete or Archive Application"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 5. ASSESSMENTS & QUESTIONS TAB */}
        {activeTab === "questions" && (
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs space-y-4">
            <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
              <div>
                <h3 className="font-bold text-slate-900 text-sm">Assessments & Question Bank</h3>
                <p className="text-xs text-slate-500">
                  Inspect student diagnostic performance records and manage standardized technical question items.
                </p>
              </div>

              {/* Sub-tabs */}
              <div className="flex bg-slate-100 p-1 rounded-lg text-xs font-semibold">
                <button
                  onClick={() => setAssessmentsSubTab("assessments")}
                  className={`px-3 py-1.5 rounded-md transition ${
                    assessmentsSubTab === "assessments"
                      ? "bg-white text-purple-700 shadow-xs"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  Student Attempts ({assessmentsList.length})
                </button>
                <button
                  onClick={() => setAssessmentsSubTab("questions")}
                  className={`px-3 py-1.5 rounded-md transition ${
                    assessmentsSubTab === "questions"
                      ? "bg-white text-purple-700 shadow-xs"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  Question Bank ({questions.length})
                </button>
              </div>
            </div>

            {/* Sub-view: Student Attempts */}
            {assessmentsSubTab === "assessments" && (
              <div className="space-y-4">
                {/* Search & Filter Controls */}
                <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex flex-wrap gap-3 items-center justify-between">
                  <div className="flex items-center gap-2 flex-1 min-w-[200px]">
                    <div className="relative w-full max-w-sm">
                      <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                      <input
                        type="text"
                        placeholder="Search student, email, domain, or ID..."
                        value={assessmentSearch}
                        onChange={(e) => setAssessmentSearch(e.target.value)}
                        className="w-full pl-9 pr-3 py-1.5 rounded-lg border border-slate-300 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                      />
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <select
                      value={assessmentDomainFilter}
                      onChange={(e) => setAssessmentDomainFilter(e.target.value)}
                      className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-semibold bg-white text-slate-700"
                    >
                      <option value="all">All Domains</option>
                      <option value="Frontend Development">Frontend Development</option>
                      <option value="Backend Development">Backend Development</option>
                      <option value="Full Stack Development">Full Stack Development</option>
                      <option value="Data Science & ML">Data Science & ML</option>
                      <option value="Cloud & DevOps">Cloud & DevOps</option>
                      <option value="Cybersecurity">Cybersecurity</option>
                    </select>

                    <select
                      value={assessmentStatusFilter}
                      onChange={(e) => setAssessmentStatusFilter(e.target.value)}
                      className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-semibold bg-white text-slate-700"
                    >
                      <option value="all">All Statuses</option>
                      <option value="completed">Completed Only</option>
                      <option value="in_progress">In Progress</option>
                    </select>

                    <button
                      onClick={() => loadAdminData()}
                      className="px-3 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-100 text-xs font-semibold text-slate-700"
                    >
                      Refresh
                    </button>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  {filteredAssessments.length === 0 ? (
                    <div className="p-8 text-center text-xs text-slate-500">
                      No matching student assessment attempts found. Once students complete assessments, records will appear here.
                    </div>
                  ) : (
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-50 text-slate-500 uppercase font-semibold border-b border-slate-200">
                        <tr>
                          <th className="p-3.5">Student</th>
                          <th className="p-3.5">Target Domain</th>
                          <th className="p-3.5">Questions</th>
                          <th className="p-3.5">Score</th>
                          <th className="p-3.5">Status</th>
                          <th className="p-3.5">Date</th>
                          <th className="p-3.5 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {filteredAssessments.map((att: any) => (
                          <tr key={att.id || att.assessment_id} className="hover:bg-slate-50/50">
                            <td className="p-3.5">
                              <span className="font-bold text-slate-900 block">{att.student_name || att.user_id}</span>
                              <span className="text-slate-500">{att.student_email || "N/A"}</span>
                            </td>
                            <td className="p-3.5 font-semibold text-slate-800">
                              {att.domain || att.track || "General"}
                            </td>
                            <td className="p-3.5 font-semibold text-slate-700">
                              {att.actual_question_count || att.question_count || (att.questions?.length) || 20} Qs
                            </td>
                            <td className="p-3.5">
                              <span className="font-bold text-indigo-700">
                                {att.total_score_percentage != null ? `${att.total_score_percentage}%` : "Pending"}
                              </span>
                            </td>
                            <td className="p-3.5">
                              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                att.status === "completed"
                                  ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                  : "bg-amber-50 text-amber-700 border border-amber-200"
                              }`}>
                                {att.status || "in_progress"}
                              </span>
                            </td>
                            <td className="p-3.5 text-slate-600">
                              {att.completed_at || att.created_at
                                ? new Date(att.completed_at || att.created_at).toLocaleDateString()
                                : "N/A"}
                            </td>
                            <td className="p-3.5 text-right">
                              <button
                                onClick={() => handleInspectAssessment(att.id || att.assessment_id)}
                                disabled={loadingAssessmentDetail}
                                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-purple-50 hover:bg-purple-100 text-purple-700 font-semibold text-xs transition"
                              >
                                <Eye className="w-3.5 h-3.5" />
                                <span>Inspect</span>
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>
            )}

            {/* Sub-view: Question Bank */}
            {assessmentsSubTab === "questions" && (
              <div className="divide-y divide-slate-100">
                {questions.length === 0 ? (
                  <div className="p-8 text-center text-xs text-slate-500">
                    No questions found in question bank.
                  </div>
                ) : (
                  questions.map((q) => (
                    <div key={q.id} className="p-4 space-y-2 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-purple-700">{q.domain} • Skill: {q.skill}</span>
                        <span className="font-bold text-slate-800">{q.points} Pts</span>
                      </div>
                      <p className="font-semibold text-slate-900 text-sm">{q.question_text}</p>
                      {q.correct_answer && (
                        <div className="p-2 bg-emerald-50 text-emerald-900 rounded font-semibold">
                          Correct Key: {String(q.correct_answer)}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        )}

        {/* 6. LEARNING RESOURCES TAB */}
        {activeTab === "resources" && (
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4">
            <h3 className="font-bold text-slate-900 text-base">Approved Learning Resources & Knowledge Base</h3>
            <p className="text-xs text-slate-600">
              Curated official engineering documentation used for RAG generation to prevent hallucinated URLs.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              {[
                { title: "React Official Docs", domain: "Frontend", url: "https://react.dev" },
                { title: "FastAPI Tutorial", domain: "Backend", url: "https://fastapi.tiangolo.com" },
                { title: "PostgreSQL Tutorial", domain: "Database", url: "https://www.postgresqltutorial.com" },
                { title: "Docker Guide", domain: "Cloud & DevOps", url: "https://docs.docker.com" },
                { title: "Python Scikit-Learn Docs", domain: "Machine Learning", url: "https://scikit-learn.org" },
                { title: "OWASP Top 10", domain: "Cybersecurity", url: "https://owasp.org" },
              ].map((res, idx) => (
                <div key={idx} className="p-3 rounded-lg border border-slate-200 bg-slate-50 flex justify-between items-center">
                  <div>
                    <span className="font-bold text-slate-800 block">{res.title}</span>
                    <span className="text-purple-600">{res.domain}</span>
                  </div>
                  <a href={res.url} target="_blank" rel="noreferrer" className="text-purple-600 hover:text-purple-800">
                    <ExternalLink className="w-4 h-4" />
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 7. SETTINGS TAB */}
        {activeTab === "settings" && (
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4 text-xs">
            <h3 className="font-bold text-slate-900 text-base">System Configuration & Integrations</h3>
            <div className="space-y-3">
              <div className="p-3.5 rounded-lg border border-emerald-200 bg-emerald-50/50 flex items-center justify-between">
                <div>
                  <span className="font-bold text-emerald-900 block">Database & Auth</span>
                  <span className="text-slate-600">Firebase Firestore & Secure Server Authentication Active</span>
                </div>
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              </div>

              <div className="p-3.5 rounded-lg border border-purple-200 bg-purple-50/50 flex items-center justify-between">
                <div>
                  <span className="font-bold text-purple-900 block">AI Engine Integration</span>
                  <span className="text-slate-600">Google Gemini API / Fallback Question Bank Configured</span>
                </div>
                <CheckCircle2 className="w-5 h-5 text-purple-600" />
              </div>

              <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50 flex items-center justify-between">
                <div>
                  <span className="font-bold text-slate-800 block">Vector Knowledge Base</span>
                  <span className="text-slate-600">Qdrant In-Memory Vector Store Initialized</span>
                </div>
                <CheckCircle2 className="w-5 h-5 text-slate-600" />
              </div>
            </div>
          </div>
        )}

        {/* APPLICATION REVIEW MODAL */}
        {selectedApplication && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-4 max-h-[90vh] overflow-y-auto text-xs">
              <div className="flex justify-between items-start border-b border-slate-100 pb-3">
                <div>
                  <span className="font-bold text-purple-600 uppercase text-[10px]">Application Governance</span>
                  <h3 className="text-base font-bold text-slate-900">{selectedApplication.job_title}</h3>
                  <p className="text-slate-500">Applicant: {selectedApplication.student_name} ({selectedApplication.student_email})</p>
                </div>
                <button onClick={() => setSelectedApplication(null)} className="text-slate-400 hover:text-slate-600">
                  <X className="w-5 h-5" />
                </button>
              </div>

              {selectedApplication.cover_letter && (
                <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1">
                  <span className="font-bold text-slate-800 block">Applicant's Cover Letter / Statement:</span>
                  <p className="text-slate-600 whitespace-pre-line">{selectedApplication.cover_letter}</p>
                </div>
              )}

              <form onSubmit={handleUpdateApplicationStatus} className="space-y-4">
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <label className="block font-semibold text-slate-700">Update Status</label>
                    <span className="text-[10px] text-slate-500">Current: <strong className="text-slate-800">{selectedApplication.status}</strong></span>
                  </div>
                  {["Selected", "Rejected", "Withdrawn"].includes(selectedApplication.status) ? (
                    <div className="p-2.5 rounded-lg bg-slate-100 border border-slate-200 text-slate-600 text-xs">
                      This application has reached a terminal state (<strong>{selectedApplication.status}</strong>) and cannot transition to a different status.
                    </div>
                  ) : (
                    <select
                      value={appStatusUpdate}
                      onChange={(e) => setAppStatusUpdate(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 font-semibold text-slate-800"
                    >
                      {selectedApplication.status === "Submitted" && (
                        <>
                          <option value="Submitted">Submitted (Current)</option>
                          <option value="Under Review">Under Review</option>
                          <option value="Shortlisted">Shortlisted</option>
                          <option value="Rejected">Rejected</option>
                        </>
                      )}
                      {selectedApplication.status === "Under Review" && (
                        <>
                          <option value="Under Review">Under Review (Current)</option>
                          <option value="Shortlisted">Shortlisted</option>
                          <option value="Interview">Interview</option>
                          <option value="Rejected">Rejected</option>
                        </>
                      )}
                      {selectedApplication.status === "Shortlisted" && (
                        <>
                          <option value="Shortlisted">Shortlisted (Current)</option>
                          <option value="Interview">Interview</option>
                          <option value="Selected">Selected</option>
                          <option value="Rejected">Rejected</option>
                        </>
                      )}
                      {selectedApplication.status === "Interview" && (
                        <>
                          <option value="Interview">Interview (Current)</option>
                          <option value="Selected">Selected</option>
                          <option value="Rejected">Rejected</option>
                        </>
                      )}
                    </select>
                  )}
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Internal Administrator Notes (Private to Admin)
                  </label>
                  <textarea
                    rows={3}
                    value={adminNotes}
                    onChange={(e) => setAdminNotes(e.target.value)}
                    placeholder="Enter internal hiring notes..."
                    className="w-full p-2.5 rounded-lg border border-slate-300 bg-white text-slate-900 placeholder:text-slate-400 text-xs focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setSelectedApplication(null)}
                    className="px-4 py-2 rounded-lg border border-slate-300 font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={updatingApp}
                    className="px-5 py-2 rounded-lg bg-purple-600 text-white font-semibold hover:bg-purple-700 disabled:opacity-50"
                  >
                    {updatingApp ? "Saving..." : "Save Status"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* STUDENT PROFILE & ASSESSMENT SUMMARY MODAL */}
        {selectedUserSummary && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-4 max-h-[90vh] overflow-y-auto text-xs">
              <div className="flex justify-between items-start border-b border-slate-100 pb-3">
                <div>
                  <span className="font-bold text-purple-600 uppercase text-[10px]">Student Record</span>
                  <h3 className="text-base font-bold text-slate-900">{selectedUserSummary.profile?.name}</h3>
                  <p className="text-slate-500">{selectedUserSummary.profile?.email}</p>
                </div>
                <button onClick={() => setSelectedUserSummary(null)} className="text-slate-400 hover:text-slate-600">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="p-3 bg-slate-50 rounded-lg">
                  <span className="text-base font-bold text-slate-900">{selectedUserSummary.assessments_count}</span>
                  <span className="block text-[10px] text-slate-500 uppercase">Assessments</span>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg">
                  <span className="text-base font-bold text-slate-900">{selectedUserSummary.applications_count}</span>
                  <span className="block text-[10px] text-slate-500 uppercase">Applications</span>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg">
                  <span className="text-base font-bold text-slate-900">{selectedUserSummary.resumes_count}</span>
                  <span className="block text-[10px] text-slate-500 uppercase">Resumes</span>
                </div>
              </div>

              <div className="space-y-2">
                <span className="font-bold text-slate-800 block">Assessment History:</span>
                {selectedUserSummary.assessments?.map((a: any, idx: number) => (
                  <div key={idx} className="p-2.5 rounded border border-slate-200 flex justify-between items-center">
                    <span>{a.domain}</span>
                    <span className="font-bold text-purple-600">{a.total_score_percentage}%</span>
                  </div>
                ))}
              </div>

              <div className="flex justify-end pt-2 border-t border-slate-100">
                <button
                  onClick={() => setSelectedUserSummary(null)}
                  className="px-4 py-2 rounded-lg bg-slate-800 text-white font-semibold"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}

        {/* APPLICATION DELETION CONFIRMATION MODAL */}
        {appToDelete && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
            <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4 text-xs">
              <div className="flex items-center gap-3 text-rose-600">
                <div className="p-2 bg-rose-50 rounded-xl">
                  <Trash2 className="w-6 h-6 text-rose-600" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">Delete Application Record</h3>
                  <span className="text-[11px] text-slate-500">ID: {appToDelete.id}</span>
                </div>
              </div>

              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-500 font-medium">Applicant:</span>
                  <span className="font-bold text-slate-800">{appToDelete.student_name || "Student"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500 font-medium">Email:</span>
                  <span className="font-medium text-slate-700">{appToDelete.student_email || "N/A"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500 font-medium">Position:</span>
                  <span className="font-bold text-purple-700">{appToDelete.job_title}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500 font-medium">Company:</span>
                  <span className="font-medium text-slate-700">{appToDelete.company || appToDelete.company_name || "Company"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500 font-medium">Current Status:</span>
                  <span className="px-2 py-0.5 rounded font-bold text-[10px] bg-purple-50 text-purple-700">
                    {appToDelete.status}
                  </span>
                </div>
              </div>

              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-900 space-y-1">
                <div className="font-bold flex items-center gap-1.5 text-amber-800">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>Data Integrity Guarantee</span>
                </div>
                <p className="text-[11px] text-amber-800 leading-relaxed">
                  Only this application record will be removed. The student&apos;s account, verified profile, resume data,
                  diagnostic assessment history, and the job listing remain completely intact and unaffected.
                </p>
              </div>

              <div className="flex flex-col sm:flex-row justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setAppToDelete(null)}
                  disabled={deletingApp}
                  className="px-4 py-2 rounded-lg border border-slate-300 font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => handleDeleteApplication(false)}
                  disabled={deletingApp}
                  className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-semibold shadow-xs disabled:opacity-50"
                >
                  {deletingApp ? "Archiving..." : "Archive Application"}
                </button>
                <button
                  type="button"
                  onClick={() => handleDeleteApplication(true)}
                  disabled={deletingApp}
                  className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-semibold shadow-xs disabled:opacity-50"
                >
                  {deletingApp ? "Deleting..." : "Permanently Delete"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ASSESSMENT DETAIL INSPECTION MODAL */}
        {selectedAssessmentDetail && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
            <div className="bg-white rounded-2xl max-w-3xl w-full p-6 shadow-2xl border border-slate-200 space-y-5 max-h-[90vh] overflow-y-auto text-xs">
              <div className="flex justify-between items-start border-b border-slate-100 pb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-purple-700 uppercase text-[10px] bg-purple-50 px-2 py-0.5 rounded-full border border-purple-200">
                      {selectedAssessmentDetail.domain || "Technical Assessment"}
                    </span>
                    <span className={`px-2 py-0.5 rounded-full font-bold text-[10px] ${
                      selectedAssessmentDetail.status === "completed"
                        ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                        : "bg-amber-50 text-amber-700 border border-amber-200"
                    }`}>
                      {selectedAssessmentDetail.status || "In Progress"}
                    </span>
                  </div>
                  <h3 className="text-lg font-bold text-slate-900 mt-1">
                    Assessment Attempt: {selectedAssessmentDetail.id}
                  </h3>
                  <p className="text-slate-500">
                    Student: <span className="font-semibold text-slate-700">{selectedAssessmentDetail.student_name || selectedAssessmentDetail.user_id}</span> ({selectedAssessmentDetail.student_email || "N/A"})
                  </p>
                </div>
                <button
                  onClick={() => setSelectedAssessmentDetail(null)}
                  className="text-slate-400 hover:text-slate-600 p-1"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Assessment Score Metrics */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
                  <span className="text-[10px] text-slate-500 uppercase font-semibold block">Total Score</span>
                  <span className="text-xl font-black text-indigo-700">
                    {selectedAssessmentDetail.total_score_percentage != null
                      ? `${selectedAssessmentDetail.total_score_percentage}%`
                      : "Pending"}
                  </span>
                </div>
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
                  <span className="text-[10px] text-slate-500 uppercase font-semibold block">Questions</span>
                  <span className="text-xl font-bold text-slate-900">
                    {selectedAssessmentDetail.actual_question_count || (selectedAssessmentDetail.questions?.length) || 20} Qs
                  </span>
                </div>
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
                  <span className="text-[10px] text-slate-500 uppercase font-semibold block">Time Allocated</span>
                  <span className="text-xl font-bold text-slate-900">
                    {selectedAssessmentDetail.duration_minutes || 20} Mins
                  </span>
                </div>
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
                  <span className="text-[10px] text-slate-500 uppercase font-semibold block">Completed Date</span>
                  <span className="text-sm font-bold text-slate-900 block truncate">
                    {selectedAssessmentDetail.completed_at
                      ? new Date(selectedAssessmentDetail.completed_at).toLocaleDateString()
                      : "In Progress"}
                  </span>
                </div>
              </div>

              {/* Strengths & Weaknesses if available */}
              {(selectedAssessmentDetail.strengths?.length > 0 || selectedAssessmentDetail.weaknesses?.length > 0) && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="p-3.5 bg-emerald-50/60 rounded-xl border border-emerald-200 space-y-1">
                    <span className="font-bold text-emerald-900 block text-[11px]">Identified Strengths:</span>
                    <ul className="list-disc list-inside space-y-0.5 text-emerald-800 text-[11px]">
                      {selectedAssessmentDetail.strengths?.map((s: string, idx: number) => (
                        <li key={idx}>{s}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="p-3.5 bg-amber-50/60 rounded-xl border border-amber-200 space-y-1">
                    <span className="font-bold text-amber-900 block text-[11px]">Identified Growth Areas:</span>
                    <ul className="list-disc list-inside space-y-0.5 text-amber-800 text-[11px]">
                      {selectedAssessmentDetail.weaknesses?.map((w: string, idx: number) => (
                        <li key={idx}>{w}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {/* Generated Questions & Student Answers */}
              <div className="space-y-3">
                <h4 className="font-bold text-slate-900 text-sm flex items-center justify-between">
                  <span>Questions & Answer Key Evaluation ({selectedAssessmentDetail.questions?.length || 0})</span>
                  <span className="text-[11px] text-slate-500 font-normal">Authorized Administrator Inspection</span>
                </h4>

                <div className="space-y-3">
                  {(selectedAssessmentDetail.questions || []).map((q: any, idx: number) => {
                    const studentAns =
                      selectedAssessmentDetail.answers?.[q.id] ||
                      selectedAssessmentDetail.saved_answers?.[q.id] ||
                      (selectedAssessmentDetail.answers && Array.isArray(selectedAssessmentDetail.answers)
                        ? selectedAssessmentDetail.answers.find((a: any) => a.question_id === q.id)?.answer
                        : null);

                    return (
                      <div key={q.id || idx} className="p-4 rounded-xl border border-slate-200 bg-white space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-purple-700">
                            Q{idx + 1}. Skill: {q.skill || "Technical Concept"}
                          </span>
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-600">
                            {q.points || 5} Pts
                          </span>
                        </div>

                        <p className="font-semibold text-slate-800 text-xs sm:text-sm">{q.question_text}</p>

                        {q.options && Array.isArray(q.options) && (
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 pt-1">
                            {q.options.map((opt: string, optIdx: number) => (
                              <div
                                key={optIdx}
                                className={`p-2 rounded-lg border text-[11px] ${
                                  studentAns === opt
                                    ? "border-purple-500 bg-purple-50 font-bold text-purple-900"
                                    : "border-slate-200 text-slate-600 bg-slate-50/50"
                                }`}
                              >
                                {opt}
                              </div>
                            ))}
                          </div>
                        )}

                        <div className="pt-2 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
                          <div className="p-2 rounded bg-slate-50">
                            <span className="text-slate-500 font-medium block">Candidate Submitted Answer:</span>
                            <span className="font-bold text-slate-800">
                              {studentAns != null ? String(studentAns) : "Unanswered"}
                            </span>
                          </div>
                          <div className="p-2 rounded bg-emerald-50 text-emerald-900">
                            <span className="text-emerald-700 font-medium block">Correct Key / Rubric:</span>
                            <span className="font-bold">{String(q.correct_answer || q.correct_key || "Validated")}</span>
                          </div>
                        </div>

                        {q.explanation && (
                          <p className="text-[11px] text-slate-500 italic pt-1">
                            Rationale: {q.explanation}
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="flex justify-end pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setSelectedAssessmentDetail(null)}
                  className="px-5 py-2 rounded-lg bg-slate-800 hover:bg-slate-900 text-white font-semibold transition"
                >
                  Close Inspection
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
