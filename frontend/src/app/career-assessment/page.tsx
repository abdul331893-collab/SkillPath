"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/lib/auth-context";
import { apiRequest } from "@/lib/api";
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  ArrowRight,
  ArrowLeft,
  Plus,
  Trash2,
  Edit2,
  Send,
  BookOpen,
  Briefcase,
  Layers,
  BarChart2,
  Target,
  ExternalLink,
  ChevronRight,
  RefreshCw,
  FolderGit2,
  Award,
  Check,
  X,
  Sliders,
  Settings2,
  HelpCircle,
  CheckSquare,
  ListOrdered,
  Play
} from "lucide-react";

interface SkillItem {
  name: string;
  source: "resume-claimed" | "student-added";
}

interface ProjectItem {
  title: string;
  description: string;
  technologies: string[];
}

export default function CareerAssessmentPage() {
  const { user, token } = useAuth();

  // Active step: 1 to 7
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [loadingInitial, setLoadingInitial] = useState(true);

  // Step 1: Upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [resumeData, setResumeData] = useState<any | null>(null);

  // Step 2: Review & Edit state
  const [skillsList, setSkillsList] = useState<SkillItem[]>([]);
  const [projectsList, setProjectsList] = useState<ProjectItem[]>([]);
  const [newSkillInput, setNewSkillInput] = useState("");
  const [newProject, setNewProject] = useState({ title: "", description: "", technologies: "" });
  const [confirmingSkills, setConfirmingSkills] = useState(false);
  const [confirmSuccess, setConfirmSuccess] = useState(false);

  // Step 3: Assessment state
  const [generatingTest, setGeneratingTest] = useState(false);
  const [assessmentQuestions, setAssessmentQuestions] = useState<any[]>([]);
  const [currentQIdx, setCurrentQIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [timeRemaining, setTimeRemaining] = useState(1200);
  const [testStarted, setTestStarted] = useState(false);
  const [submittingTest, setSubmittingTest] = useState(false);
  const [targetDomain, setTargetDomain] = useState("Frontend Development");

  // Assessment Configuration state (20, 30, 50 questions)
  const [questionCount, setQuestionCount] = useState<number>(20);
  const [assessmentFocus, setAssessmentFocus] = useState<"all_skills" | "selected_skills" | "project_based">("all_skills");
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [difficulty, setDifficulty] = useState<"adaptive" | "beginner" | "intermediate" | "advanced">("adaptive");
  const [questionTypes, setQuestionTypes] = useState<"combination" | "mcq" | "short_answer">("combination");
  const [durationMinutes, setDurationMinutes] = useState<number>(20);
  const [assessmentId, setAssessmentId] = useState<string | null>(null);
  const [actualGeneratedCount, setActualGeneratedCount] = useState<number>(0);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<"saved" | "saving" | "unsaved">("saved");
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [showPalette, setShowPalette] = useState(false);
  const [generationProgressMessage, setGenerationProgressMessage] = useState<string>(
    "Preparing your personalized assessment..."
  );
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  // Step 4: Assessment Report state
  const [assessmentResult, setAssessmentResult] = useState<any | null>(null);
  const [assessmentHistory, setAssessmentHistory] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [showHistoryModal, setShowHistoryModal] = useState(false);

  // Step 5: Learning Roadmap state
  const [roadmap, setRoadmap] = useState<any | null>(null);
  const [loadingRoadmap, setLoadingRoadmap] = useState(false);

  // Step 6: Career Domain Recommendations
  const [careerRecs, setCareerRecs] = useState<any[]>([]);
  const [loadingCareers, setLoadingCareers] = useState(false);

  // Step 7: Recommended Jobs & Internships
  const [recommendedJobs, setRecommendedJobs] = useState<any[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(false);

  // Quick apply modal in Step 7
  const [quickApplyJob, setQuickApplyJob] = useState<any | null>(null);
  const [quickCoverLetter, setQuickCoverLetter] = useState("");
  const [quickApplying, setQuickApplying] = useState(false);
  const [quickApplySuccess, setQuickApplySuccess] = useState<string | null>(null);

  const hasFetchedInitialRef = useRef<string | null>(null);

  // Initial load - Fetch independent state in parallel
  useEffect(() => {
    let isSubscribed = true;

    async function loadInitialState() {
      const activeToken = token || (typeof window !== "undefined" ? localStorage.getItem("skillpath_token") : null);
      if (!activeToken) {
        if (isSubscribed) setLoadingInitial(false);
        return;
      }

      const requestKey = `${user?.uid || "user"}_${activeToken}`;
      if (hasFetchedInitialRef.current === requestKey) {
        if (isSubscribed) setLoadingInitial(false);
        return;
      }
      hasFetchedInitialRef.current = requestKey;

      if (isSubscribed) setLoadingInitial(true);
      try {
        const [resDataRes, profileDataRes, latestAssessmentRes, savedRecsRes, savedRoadmapRes, historyRes] =
          await Promise.allSettled([
            apiRequest<{ resume: any | null }>("/resumes/latest", { token: activeToken, silent: true }),
            apiRequest<any>("/profiles/me", { token: activeToken, silent: true }),
            apiRequest<any>("/assessments/latest", { token: activeToken, silent: true }),
            apiRequest<any[]>("/careers/recommendations", { token: activeToken, silent: true }),
            apiRequest<any>("/roadmaps/latest", { token: activeToken, silent: true }),
            apiRequest<any[]>("/assessments/history", { token: activeToken, silent: true }),
          ]);

        if (!isSubscribed) return;

        let hasResume = false;
        if (resDataRes.status === "fulfilled" && resDataRes.value?.resume) {
          const res = resDataRes.value.resume;
          setResumeData(res);
          populateSkillsAndProjects(res);
          hasResume = true;
          setCurrentStep(2);
        }

        if (profileDataRes.status === "fulfilled" && profileDataRes.value) {
          const profileData = profileDataRes.value;
          if (!hasResume) {
            const profileSkills: SkillItem[] = [
              ...(profileData.technical_skills || []).map((s: string) => ({ name: s, source: "student-added" as const })),
              ...(profileData.claimed_skills || []).map((s: string) => ({ name: s, source: "resume-claimed" as const })),
            ];
            if (profileSkills.length > 0) {
              setSkillsList(profileSkills);
              setCurrentStep(2);
            }
            if (profileData.projects && profileData.projects.length > 0) {
              setProjectsList(profileData.projects);
            }
          }
        }

        let hasCompletedAssessment = false;
        if (latestAssessmentRes.status === "fulfilled" && latestAssessmentRes.value) {
          const latest = latestAssessmentRes.value;
          setAssessmentResult(latest);
          if (latest.total_score_percentage !== undefined) {
            hasCompletedAssessment = true;
            if (latest.domain) {
              setTargetDomain(latest.domain);
            }
          }
        }

        if (savedRecsRes.status === "fulfilled" && Array.isArray(savedRecsRes.value) && savedRecsRes.value.length > 0) {
          setCareerRecs(savedRecsRes.value);
        }

        if (historyRes.status === "fulfilled" && Array.isArray(historyRes.value)) {
          setAssessmentHistory(historyRes.value);
        }

        const initialRoadmap = savedRoadmapRes.status === "fulfilled" ? savedRoadmapRes.value : null;
        if (initialRoadmap) {
          if (hasCompletedAssessment && initialRoadmap.requires_assessment) {
            setRoadmap(null);
          } else {
            setRoadmap(initialRoadmap);
          }
        }

        // If student already has a completed assessment report, default to Step 4 so results are immediately visible
        if (hasCompletedAssessment) {
          setCurrentStep(4);
          if (!initialRoadmap || initialRoadmap.requires_assessment) {
            loadRoadmapData(false);
          }
        } else {
          // Check for in-flight assessment generation job
          try {
            const activeJob = await apiRequest<any>("/assessments/jobs/active", { token: activeToken, silent: true });
            if (activeJob && (activeJob.status === "queued" || activeJob.status === "processing")) {
              setGeneratingTest(true);
              setGenerationProgressMessage(activeJob.progress_message || "Preparing your personalized assessment...");
              setCurrentStep(3);
              startPollingJob(activeJob.job_id, activeToken);
            }
          } catch {
            // No active job, proceed normally
          }
        }
      } catch (err) {
        console.warn("Initial state load note:", err);
      } finally {
        if (isSubscribed) {
          setLoadingInitial(false);
        }
      }
    }

    if (user || (typeof window !== "undefined" && localStorage.getItem("skillpath_token"))) {
      loadInitialState();
    } else {
      setLoadingInitial(false);
    }

    return () => {
      isSubscribed = false;
    };
  }, [user, token]);

  const fetchAssessmentHistory = async () => {
    const activeToken = token || (typeof window !== "undefined" ? localStorage.getItem("skillpath_token") : null);
    if (!activeToken) return;
    setLoadingHistory(true);
    setHistoryError(null);
    try {
      const list = await apiRequest<any[]>("/assessments/history", { token: activeToken });
      setAssessmentHistory(Array.isArray(list) ? list : []);
    } catch (err: any) {
      console.error("Failed to load assessment history:", err);
      setHistoryError(err?.message || "Failed to load assessment history. Please retry.");
    } finally {
      setLoadingHistory(false);
    }
  };

  const populateSkillsAndProjects = (resume: any) => {
    const rawSkills = resume.extracted_data?.claimed_skills || [];
    const initialSkills: SkillItem[] = rawSkills.map((s: string) => ({
      name: s,
      source: "resume-claimed" as const,
    }));
    setSkillsList(initialSkills);

    const initialProjects: ProjectItem[] = (resume.extracted_data?.projects || []).map((p: any) => ({
      title: typeof p === "string" ? p : p.title || "Project",
      description: p.description || "Project implementation details",
      technologies: Array.isArray(p.technologies) ? p.technologies : [],
    }));
    setProjectsList(initialProjects);
  };

  // Timer for Step 3
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (testStarted && timeRemaining > 0 && !assessmentResult) {
      interval = setInterval(() => {
        setTimeRemaining((prev) => prev - 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [testStarted, timeRemaining, assessmentResult]);

  // STEP 1 HANDLERS
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setUploadError(null);
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const ext = file.name.split(".").pop()?.toLowerCase();
      if (ext !== "pdf" && ext !== "docx") {
        setUploadError("Only PDF and DOCX documents are supported.");
        setSelectedFile(null);
        return;
      }
      if (file.size === 0) {
        setUploadError("The selected file is empty (0 bytes).");
        setSelectedFile(null);
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        setUploadError("File size exceeds the 10MB limit.");
        setSelectedFile(null);
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleUploadResume = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || uploading) return;

    setUploading(true);
    setUploadError(null);
    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const activeAuthToken = token || (typeof window !== "undefined" ? localStorage.getItem("skillpath_token") : null);
      const result = await apiRequest<any>("/resumes/upload", {
        method: "POST",
        token: activeAuthToken,
        body: formData,
        timeoutMs: 60000,
      });
      setResumeData(result);
      populateSkillsAndProjects(result);
      setCurrentStep(2);
    } catch (err: any) {
      setUploadError(err.message || "Failed to parse document. Please check the file.");
    } finally {
      setUploading(false);
    }
  };

  // STEP 2 HANDLERS: EDIT & CONFIRM
  const handleAddSkill = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = newSkillInput.trim();
    if (!trimmed) return;
    if (!skillsList.some((s) => s.name.toLowerCase() === trimmed.toLowerCase())) {
      setSkillsList([...skillsList, { name: trimmed, source: "student-added" }]);
    }
    setNewSkillInput("");
  };

  const handleRemoveSkill = (skillName: string) => {
    setSkillsList(skillsList.filter((s) => s.name !== skillName));
  };

  const handleAddProject = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProject.title.trim()) return;
    const techs = newProject.technologies
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    setProjectsList([
      ...projectsList,
      {
        title: newProject.title.trim(),
        description: newProject.description.trim() || "Technical project implementation",
        technologies: techs,
      },
    ]);
    setNewProject({ title: "", description: "", technologies: "" });
  };

  const handleRemoveProject = (index: number) => {
    setProjectsList(projectsList.filter((_, idx) => idx !== index));
  };

  const handleConfirmSkills = async () => {
    setConfirmingSkills(true);
    try {
      if (resumeData?.id) {
        await apiRequest(`/resumes/${resumeData.id}/confirmed`, {
          method: "PUT",
          token,
          body: JSON.stringify({
            skills: skillsList,
            projects: projectsList,
          }),
        });
      }
      setConfirmSuccess(true);
      setTimeout(() => {
        setCurrentStep(3);
      }, 500);
    } catch (err: any) {
      alert(`Confirmation failed: ${err.message}`);
    } finally {
      setConfirmingSkills(false);
    }
  };

  // Cancel polling on component unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, []);

  const startPollingJob = (jobId: string, activeToken: string) => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }

    let pollAttempts = 0;
    const maxPollAttempts = 90; // 90 * 2s = 180 seconds maximum

    pollingRef.current = setInterval(async () => {
      pollAttempts++;
      if (pollAttempts > maxPollAttempts) {
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
        setGeneratingTest(false);
        setGenerationError(
          "Assessment generation is taking longer than expected. If the server is still processing, please refresh in a moment."
        );
        return;
      }

      try {
        const job = await apiRequest<any>(`/assessments/jobs/${jobId}`, {
          token: activeToken,
          silent: true,
        });

        if (!job) return;

        if (job.progress_message) {
          setGenerationProgressMessage(job.progress_message);
        }

        if (job.status === "completed") {
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }
          setGeneratingTest(false);
          if (job.assessment) {
            const assm = job.assessment;
            const qList = Array.isArray(assm.questions) ? assm.questions : [];
            setAssessmentId(assm.id || null);
            setAssessmentQuestions(qList);
            setActualGeneratedCount(qList.length);
            setCurrentQIdx(0);
            setAnswers(assm.saved_answers || {});
            setTimeRemaining((durationMinutes || questionCount) * 60);
            setTestStarted(false); // Let student review and confirm settings before starting!
          }
        } else if (job.status === "failed") {
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }
          setGeneratingTest(false);
          setGenerationError(job.error_message || "Assessment generation failed. Please try again.");
        }
      } catch (err) {
        console.warn("Assessment job polling check note:", err);
      }
    }, 2000);
  };

  // STEP 3 HANDLERS: PERSONALIZED ASSESSMENT
  const handleGenerateAssessment = async () => {
    if (skillsList.length === 0) {
      alert("Please confirm at least one skill before generating an assessment.");
      return;
    }
    if (assessmentFocus === "project_based" && projectsList.length === 0) {
      alert("Project-based assessment requires at least one project. Please add a project in Step 2.");
      return;
    }
    if (assessmentFocus === "selected_skills" && selectedSkills.length === 0) {
      alert("Please select at least one skill to assess.");
      return;
    }

    setGeneratingTest(true);
    setGenerationError(null);
    setGenerationProgressMessage(`Submitting generation request for ${questionCount} questions...`);

    try {
      const activeToken = token || (typeof window !== "undefined" ? localStorage.getItem("skillpath_token") : null);
      if (!activeToken) throw new Error("Authentication token required.");

      const payload = {
        domain: targetDomain,
        confirmed_skills: skillsList.map((s) => s.name),
        selected_skills: assessmentFocus === "selected_skills" ? selectedSkills : undefined,
        projects: projectsList,
        question_count: questionCount,
        focus: assessmentFocus,
        difficulty,
        question_types: questionTypes,
        duration_minutes: durationMinutes,
      };

      // Asynchronous, persisted generation job workflow (HTTP 202 Accepted)
      const startRes = await apiRequest<any>("/assessments/generate/start", {
        method: "POST",
        token: activeToken,
        body: JSON.stringify(payload),
      });

      if (startRes?.job_id) {
        setGenerationProgressMessage(startRes.progress_message || "Preparing your personalized assessment...");
        startPollingJob(startRes.job_id, activeToken);
      } else {
        throw new Error("Backend did not return a valid generation job ID.");
      }
    } catch (err: any) {
      console.error("Failed to start assessment generation:", err);
      setGeneratingTest(false);
      setGenerationError(err.message || "Failed to start assessment generation. Please try again.");
    }
  };

  const handleStartAssessment = () => {
    setTestStarted(true);
  };

  const handleAnswerChange = (qId: string, val: string) => {
    const updated = { ...answers, [qId]: val };
    setAnswers(updated);
    setSaveStatus("saving");

    if (assessmentId) {
      apiRequest(`/assessments/${assessmentId}/answers`, {
        method: "PUT",
        token,
        body: JSON.stringify({
          answers: updated,
          time_remaining_seconds: timeRemaining,
        }),
        silent: true,
      })
        .then(() => setSaveStatus("saved"))
        .catch(() => setSaveStatus("unsaved"));
    }
  };

  const handleSubmitAssessment = async () => {
    setSubmittingTest(true);
    setSubmissionError(null);
    try {
      const activeToken = token || (typeof window !== "undefined" ? localStorage.getItem("skillpath_token") : null);
      const submissionPayload = {
        domain: targetDomain,
        assessment_id: assessmentId,
        answers: Object.entries(answers).map(([qId, ans]) => ({
          question_id: qId,
          answer: ans,
        })),
        time_taken_seconds: ((durationMinutes || questionCount) * 60) - timeRemaining,
      };

      const url = assessmentId ? `/assessments/${assessmentId}/submit` : "/assessments/submit";
      const report = await apiRequest<any>(url, {
        method: "POST",
        token: activeToken,
        body: JSON.stringify(submissionPayload),
      });

      setAssessmentResult(report);
      setTestStarted(false);
      setShowSubmitModal(false);
      setRoadmap(null);
      setCurrentStep(4);
      if (typeof window !== "undefined") {
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
      // Pre-load evidence-based roadmap calibrated to this submission
      loadRoadmapData(true);
    } catch (err: any) {
      console.error("Assessment submission error:", err);
      setSubmissionError(err.message || "Failed to submit assessment. Please check your connection and retry.");
    } finally {
      setSubmittingTest(false);
    }
  };

  // STEP 5 LOADER
  const loadRoadmapData = async (replaceExisting: boolean = false) => {
    setLoadingRoadmap(true);
    try {
      const activeToken = token || (typeof window !== "undefined" ? localStorage.getItem("skillpath_token") : null);
      if (!replaceExisting) {
        try {
          const existing = await apiRequest<any>("/roadmaps/latest", { token: activeToken, silent: true });
          if (existing && existing.id && !existing.requires_assessment) {
            setRoadmap(existing);
            setLoadingRoadmap(false);
            return;
          }
        } catch {
          // If no existing roadmap found or error, fall through to generation
        }
      }

      // Generate roadmap targeted to weaknesses
      const data = await apiRequest<any>("/roadmaps/generate", {
        method: "POST",
        token: activeToken,
        body: JSON.stringify({
          target_career_domain: targetDomain,
          weekly_hours_available: 12,
          replace_existing: replaceExisting,
        }),
      });
      setRoadmap(data);
    } catch (err) {
      console.error("Roadmap generation error:", err);
    } finally {
      setLoadingRoadmap(false);
    }
  };

  const handleToggleRoadmapTopic = async (topicId: string, currentStatus: string | boolean) => {
    if (!roadmap) return;
    let nextStatus = "In Progress";
    if (currentStatus === "Completed" || currentStatus === true) {
      nextStatus = "Not Started";
    } else if (currentStatus === "In Progress") {
      nextStatus = "Completed";
    } else {
      nextStatus = "In Progress";
    }
    try {
      const updated = await apiRequest<any>(`/roadmaps/${roadmap.id}/progress`, {
        method: "PATCH",
        token,
        body: JSON.stringify({
          topic_id: topicId,
          progress_status: nextStatus,
          completed: nextStatus === "Completed",
        }),
      });
      setRoadmap(updated);
    } catch (err) {
      console.error("Failed to update topic progress:", err);
    }
  };

  // STEP 6 LOADER
  const loadCareerRecommendations = async (forceRegenerate = false) => {
    setLoadingCareers(true);
    try {
      const activeToken = token || (typeof window !== "undefined" ? localStorage.getItem("skillpath_token") : null);
      const endpoint = forceRegenerate ? "/careers/recommendations/regenerate" : "/careers/recommendations";
      const data = await apiRequest<any[]>(endpoint, {
        method: forceRegenerate ? "POST" : "GET",
        token: activeToken,
      });
      if (Array.isArray(data) && data.length > 0) {
        setCareerRecs(data);
      }
    } catch (err) {
      console.error("Career recommendations error:", err);
      // Preserve existing careerRecs on failure
    } finally {
      setLoadingCareers(false);
    }
  };

  // STEP 7 LOADER
  const loadRecommendedJobs = async () => {
    setLoadingJobs(true);
    try {
      const data = await apiRequest<any[]>("/jobs", { token });
      setRecommendedJobs(data || []);
    } catch (err) {
      console.error("Recommended jobs error:", err);
    } finally {
      setLoadingJobs(false);
    }
  };

  const handleOpenQuickApply = (job: any) => {
    setQuickApplyJob(job);
    setQuickCoverLetter("");
    setQuickApplySuccess(null);
  };

  const handleQuickSubmitApplication = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickApplyJob) return;
    setQuickApplying(true);
    try {
      await apiRequest("/applications/apply", {
        method: "POST",
        token,
        body: JSON.stringify({
          job_id: quickApplyJob.id,
          cover_letter: quickCoverLetter,
        }),
      });
      setQuickApplySuccess("Application successfully submitted to hiring administrator!");
      setTimeout(() => {
        setQuickApplyJob(null);
      }, 1500);
    } catch (err: any) {
      alert(`Application failed: ${err.message}`);
    } finally {
      setQuickApplying(false);
    }
  };

  // Step Switcher trigger
  const goToStep = (stepNumber: number) => {
    setCurrentStep(stepNumber);
    if (stepNumber === 5 && (!roadmap || roadmap.requires_assessment)) {
      loadRoadmapData();
    }
    if (stepNumber === 6 && careerRecs.length === 0) {
      loadCareerRecommendations();
    }
    if (stepNumber === 7 && recommendedJobs.length === 0) {
      loadRecommendedJobs();
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
  };

  const currentQ = assessmentQuestions[currentQIdx];

  const stepsMeta = [
    { num: 1, label: "Upload Resume" },
    { num: 2, label: "Review & Edit Skills" },
    { num: 3, label: "Personalized Test" },
    { num: 4, label: "Skill Assessment Report" },
    { num: 5, label: "Learning Roadmap" },
    { num: 6, label: "Career Recommendation" },
    { num: 7, label: "Relevant Jobs" },
  ];

  return (
    <AppShell
      title="Skill Assessment & Career Guidance"
      description="The central AI-guided student workflow: extract skills, calibrate through adaptive technical tests, obtain learning roadmaps, and receive explainable domain recommendations."
    >
      <div className="space-y-6">
        {/* Step Progression Header */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs overflow-x-auto">
          <div className="flex items-center min-w-[700px] justify-between">
            {stepsMeta.map((s, idx) => {
              const isCurrent = currentStep === s.num;
              const isPassed = currentStep > s.num;

              return (
                <div key={s.num} className="flex items-center flex-1">
                  <button
                    onClick={() => goToStep(s.num)}
                    className="flex items-center gap-2 text-left focus:outline-none"
                  >
                    <div
                      className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition ${
                        isCurrent
                          ? "bg-purple-600 text-white shadow-xs ring-4 ring-purple-100"
                          : isPassed
                          ? "bg-emerald-600 text-white"
                          : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {isPassed ? <Check className="w-3.5 h-3.5" /> : s.num}
                    </div>
                    <span
                      className={`text-xs whitespace-nowrap font-semibold ${
                        isCurrent
                          ? "text-purple-700 font-bold"
                          : isPassed
                          ? "text-slate-800"
                          : "text-slate-400"
                      }`}
                    >
                      {s.label}
                    </span>
                  </button>
                  {idx < stepsMeta.length - 1 && (
                    <div className="flex-1 mx-3 border-t border-slate-200"></div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* ========================================================================= */}
        {/* STEP 1: UPLOAD RESUME OR CV */}
        {/* ========================================================================= */}
        {currentStep === 1 && (
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-5">
            <div>
              <span className="text-xs font-bold text-purple-600 uppercase tracking-wider">
                Step 1 of 7
              </span>
              <h2 className="text-xl font-bold text-slate-900">Upload Your Resume or CV</h2>
              <p className="text-xs text-slate-600 mt-1">
                Upload your engineering resume in PDF or DOCX format (Max: 10MB). Our parser will extract your technical skills, programming languages, libraries, tools, and projects.
              </p>
            </div>

            <form onSubmit={handleUploadResume} className="space-y-4">
              <div className="border-2 border-dashed border-slate-300 rounded-xl p-8 text-center hover:bg-slate-50/50 transition">
                <UploadCloud className="w-10 h-10 text-purple-600 mx-auto mb-3" />
                <div className="text-sm font-semibold text-slate-800">
                  {selectedFile ? selectedFile.name : "Select or drag your PDF/DOCX resume"}
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Supported formats: PDF, DOCX • Maximum file size: 10MB
                </p>

                <label
                  className={`mt-4 inline-block px-4 py-2 rounded-lg text-xs font-semibold cursor-pointer border transition ${
                    uploading
                      ? "bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed"
                      : "bg-purple-50 text-purple-700 hover:bg-purple-100 border-purple-200"
                  }`}
                >
                  {selectedFile ? "Choose Different File" : "Browse Local File"}
                  <input
                    type="file"
                    accept=".pdf,.docx"
                    disabled={uploading}
                    onChange={handleFileChange}
                    className="hidden"
                  />
                </label>
              </div>

              {uploadError && (
                <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2.5">
                  <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-600 mt-0.5" />
                  <div>
                    <span className="font-bold block">Extraction Alert</span>
                    <span>{uploadError}</span>
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-3 items-center pt-2">
                {selectedFile && !uploading && (
                  <span className="text-xs text-slate-500 font-medium">
                    Ready to parse: {(selectedFile.size / 1024).toFixed(1)} KB
                  </span>
                )}
                <button
                  type="submit"
                  disabled={!selectedFile || uploading}
                  className="px-6 py-2.5 rounded-lg bg-purple-600 hover:bg-purple-700 text-white font-semibold text-xs shadow-xs transition disabled:opacity-50 flex items-center gap-2"
                >
                  {uploading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Parsing & Extracting Skills...</span>
                    </>
                  ) : (
                    <>
                      <span>Upload & Extract Information</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* ========================================================================= */}
        {/* STEP 2: REVIEW AND EDIT EXTRACTED INFORMATION */}
        {/* ========================================================================= */}
        {currentStep === 2 && (
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-3 border-b border-slate-100">
              <div>
                <span className="text-xs font-bold text-purple-600 uppercase tracking-wider">
                  Step 2 of 7
                </span>
                <h2 className="text-xl font-bold text-slate-900">Review & Edit Extracted Information</h2>
                <p className="text-xs text-slate-600 mt-1">
                  Validate the extracted data before taking your assessment. Clearly distinction: <span className="font-semibold text-slate-700">Resume-Claimed</span> vs <span className="font-semibold text-purple-700">Student-Added</span>.
                </p>
              </div>

              <button
                onClick={() => setCurrentStep(1)}
                className="text-xs text-purple-600 hover:text-purple-800 font-semibold self-start sm:self-auto"
              >
                Upload Different File
              </button>
            </div>

            {/* Skills Review Section */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-800">
                  Confirmed Skills for Assessment ({skillsList.length})
                </h3>
              </div>

              {/* Add New Skill Input */}
              <form onSubmit={handleAddSkill} className="flex gap-2">
                <input
                  type="text"
                  placeholder="Add a missing skill (e.g., Docker, TypeScript, PyTorch)..."
                  value={newSkillInput}
                  onChange={(e) => setNewSkillInput(e.target.value)}
                  className="flex-1 px-3 py-2 rounded-lg border border-slate-300 text-slate-900 bg-white placeholder:text-slate-400 text-xs focus:ring-2 focus:ring-purple-500 focus:outline-none"
                />
                <button
                  type="submit"
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 transition"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add Skill</span>
                </button>
              </form>

              {/* Skills Tags List */}
              <div className="flex flex-wrap gap-2 pt-1">
                {skillsList.map((skill, idx) => (
                  <div
                    key={idx}
                    className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-semibold ${
                      skill.source === "student-added"
                        ? "bg-purple-50 border-purple-200 text-purple-900"
                        : "bg-slate-50 border-slate-200 text-slate-800"
                    }`}
                  >
                    <span>{skill.name}</span>
                    <span className="text-[10px] font-normal uppercase opacity-60">
                      ({skill.source === "student-added" ? "Added" : "Claimed"})
                    </span>
                    <button
                      type="button"
                      onClick={() => handleRemoveSkill(skill.name)}
                      className="text-slate-400 hover:text-rose-600"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Projects Review Section */}
            <div className="space-y-4 pt-4 border-t border-slate-100">
              <h3 className="text-sm font-bold text-slate-800">
                Projects for Question Customization ({projectsList.length})
              </h3>
              <p className="text-xs text-slate-500">
                Assessment questions will be generated from the specific architectures and technologies mentioned in your projects.
              </p>

              {/* List of existing projects */}
              <div className="space-y-3">
                {projectsList.map((proj, idx) => (
                  <div
                    key={idx}
                    className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2 relative"
                  >
                    <button
                      onClick={() => handleRemoveProject(idx)}
                      className="absolute top-3 right-3 text-slate-400 hover:text-rose-600"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                    <h4 className="font-bold text-sm text-slate-900">{proj.title}</h4>
                    <p className="text-xs text-slate-600">{proj.description}</p>
                    {proj.technologies?.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {proj.technologies.map((t, tIdx) => (
                          <span
                            key={tIdx}
                            className="px-2 py-0.5 rounded-md bg-white border border-slate-200 text-slate-700 text-[10px] font-medium"
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Add New Project Form */}
              <div className="p-4 rounded-xl border border-purple-100 bg-purple-50/40 space-y-3">
                <span className="text-xs font-bold text-purple-900 block">
                  Add Additional Project:
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <input
                    type="text"
                    placeholder="Project Title (e.g. Distributed Task Queue)"
                    value={newProject.title}
                    onChange={(e) => setNewProject({ ...newProject, title: e.target.value })}
                    className="p-2.5 rounded-lg border border-slate-300 bg-white text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                  <input
                    type="text"
                    placeholder="Technologies (comma-separated, e.g. Python, Redis, Docker)"
                    value={newProject.technologies}
                    onChange={(e) => setNewProject({ ...newProject, technologies: e.target.value })}
                    className="p-2.5 rounded-lg border border-slate-300 bg-white text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>
                <textarea
                  rows={2}
                  placeholder="Project description and key technical features..."
                  value={newProject.description}
                  onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                  className="w-full p-2.5 rounded-lg border border-slate-300 bg-white text-slate-900 placeholder:text-slate-400 text-xs focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
                <button
                  type="button"
                  onClick={handleAddProject}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold rounded-lg transition"
                >
                  Add Project
                </button>
              </div>
            </div>

            {/* Target Assessment Domain Selector & Confirmation */}
            <div className="pt-4 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Primary Domain to Assess:
                </label>
                <select
                  value={targetDomain}
                  onChange={(e) => setTargetDomain(e.target.value)}
                  className="px-3 py-2 rounded-lg border border-slate-300 text-xs font-semibold bg-white text-slate-800"
                >
                  <option value="Frontend Development">Frontend Development</option>
                  <option value="Backend Development">Backend Development</option>
                  <option value="Full-Stack Development">Full-Stack Development</option>
                  <option value="Data Science & Machine Learning">Data Science & Machine Learning</option>
                  <option value="Cloud and DevOps Engineering">Cloud and DevOps Engineering</option>
                  <option value="Cybersecurity">Cybersecurity</option>
                </select>
              </div>

              <button
                onClick={handleConfirmSkills}
                disabled={confirmingSkills || skillsList.length === 0}
                className="px-6 py-2.5 rounded-lg bg-purple-600 hover:bg-purple-700 text-white font-semibold text-xs shadow-xs transition flex items-center gap-2 self-end disabled:opacity-50"
              >
                {confirmingSkills ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Saving Profile Information...</span>
                  </>
                ) : (
                  <>
                    <span>Confirm Profile & Configure Assessment</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* STEP 3: PERSONALIZED ASSESSMENT (20, 30, 50 QUESTIONS) */}
        {/* ========================================================================= */}
        {currentStep === 3 && (
          <div className="space-y-6">
            {/* If Generating: Full Progress State */}
            {generatingTest && (
              <div className="bg-white p-12 rounded-2xl border border-purple-200 shadow-md text-center space-y-4">
                <div className="relative w-16 h-16 mx-auto">
                  <div className="absolute inset-0 rounded-full border-4 border-purple-100"></div>
                  <div className="absolute inset-0 rounded-full border-4 border-purple-600 border-t-transparent animate-spin"></div>
                  <Sparkles className="w-6 h-6 text-purple-600 absolute inset-0 m-auto" />
                </div>
                <h3 className="text-xl font-bold text-slate-900">
                  Preparing Your Personalized Assessment ({questionCount} Questions)
                </h3>
                <div className="inline-block px-4 py-2 bg-purple-50 text-purple-800 rounded-xl font-medium text-xs sm:text-sm border border-purple-200">
                  {generationProgressMessage}
                </div>
                <p className="text-xs sm:text-sm text-slate-600 max-w-lg mx-auto">
                  Creating and validating questions based on your confirmed skills ({skillsList.map((s) => s.name).join(", ")}).
                </p>
                <div className="flex flex-wrap items-center justify-center gap-3 pt-2 text-xs font-semibold text-purple-700">
                  <span className="flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-emerald-500" /> Skill relevance validation</span>
                  <span className="flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-emerald-500" /> Structure & schema checks</span>
                  <span className="flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-emerald-500" /> Difficulty calibration</span>
                </div>
              </div>
            )}

            {/* Error Message if generation failed */}
            {!generatingTest && generationError && (
              <div className="bg-red-50 border border-red-200 text-red-800 p-5 rounded-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <h4 className="text-sm font-bold text-red-900">Assessment Generation Error</h4>
                    <p className="text-xs text-red-700 mt-1">{generationError}</p>
                    <p className="text-xs text-red-600 mt-1">
                      Please check your connection and retry. If the issue persists, review your selected skills and try again.
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleGenerateAssessment}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded-lg transition shrink-0 flex items-center gap-1.5"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Retry Generation</span>
                </button>
              </div>
            )}

            {/* STATE A: Configuration Section (Before Generation) */}
            {!generatingTest && assessmentQuestions.length === 0 && (
              <div className="bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-xs space-y-7">
                {assessmentHistory.length > 0 && (
                  <div className="p-4 rounded-xl border border-purple-200 bg-purple-50/70 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                    <div className="flex items-center gap-2.5">
                      <Award className="w-5 h-5 text-purple-600 shrink-0" />
                      <div>
                        <p className="font-bold text-purple-950">
                          You have {assessmentHistory.length} completed assessment {assessmentHistory.length === 1 ? "record" : "records"} on file
                        </p>
                        <p className="text-purple-700">
                          You can view past evaluation marks or configure a new assessment below.
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setShowHistoryModal(true);
                        fetchAssessmentHistory();
                      }}
                      className="px-3.5 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-700 text-white font-semibold shrink-0 transition"
                    >
                      View Past Assessments
                    </button>
                  </div>
                )}

                <div>
                  <div className="flex items-center gap-2 text-purple-600 text-xs font-bold uppercase tracking-wider mb-1">
                    <Sliders className="w-4 h-4" />
                    <span>Assessment Configuration</span>
                  </div>
                  <h2 className="text-2xl font-bold text-slate-900">
                    Configure Your Technical Assessment
                  </h2>
                  <p className="text-xs sm:text-sm text-slate-600 mt-1">
                    Select your assessment size, focus area, difficulty level, and format. Questions are generated dynamically based on your verified skills and practical experience.
                  </p>
                </div>

                {/* 1. Question Count Selector */}
                <div className="space-y-3">
                  <label className="block text-xs font-bold text-slate-800 uppercase tracking-wider">
                    1. Select Assessment Size (Question Count):
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {[
                      { count: 20, label: "20 Questions", tag: "Quick Diagnostic", desc: "Comprehensive calibration of core concepts & practical implementations." },
                      { count: 30, label: "30 Questions", tag: "In-Depth Evaluation", desc: "Detailed evaluation covering architecture, problem solving, and trade-offs." },
                      { count: 50, label: "50 Questions", tag: "Complete Mastery", desc: "Exhaustive technical assessment evaluating end-to-end expertise." },
                    ].map((item) => {
                      const isSelected = questionCount === item.count;
                      return (
                        <button
                          key={item.count}
                          type="button"
                          onClick={() => {
                            setQuestionCount(item.count);
                            setDurationMinutes(item.count);
                          }}
                          className={`p-4 rounded-xl border text-left transition relative ${
                            isSelected
                              ? "border-purple-600 bg-purple-50/70 shadow-xs ring-2 ring-purple-500/20"
                              : "border-slate-200 hover:border-slate-300 bg-white"
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1.5">
                            <span className="text-base font-bold text-slate-900">{item.label}</span>
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                              isSelected ? "bg-purple-600 text-white" : "bg-slate-100 text-slate-600"
                            }`}>
                              {item.tag}
                            </span>
                          </div>
                          <p className="text-xs text-slate-600">{item.desc}</p>
                          <div className="mt-2.5 flex items-center gap-1.5 text-xs font-semibold text-slate-500">
                            <Clock className="w-3.5 h-3.5 text-slate-400" />
                            <span>Estimated {item.count} mins</span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* 2. Assessment Focus */}
                <div className="space-y-3">
                  <label className="block text-xs font-bold text-slate-800 uppercase tracking-wider">
                    2. Assessment Focus:
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {[
                      { id: "all_skills", title: "All Skills", desc: `Proportionally evaluates all ${skillsList.length} confirmed skills.` },
                      { id: "selected_skills", title: "Selected Skills", desc: "Choose specific skills from your profile to test." },
                      { id: "project_based", title: "Project-Based", desc: "Emphasizes practical project architecture & real implementation trade-offs." },
                    ].map((f) => {
                      const isSelected = assessmentFocus === f.id;
                      return (
                        <button
                          key={f.id}
                          type="button"
                          onClick={() => setAssessmentFocus(f.id as any)}
                          className={`p-3.5 rounded-xl border text-left transition ${
                            isSelected
                              ? "border-purple-600 bg-purple-50/70 ring-2 ring-purple-500/20"
                              : "border-slate-200 hover:border-slate-300 bg-white"
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-sm font-bold text-slate-900">{f.title}</span>
                            {isSelected && <Check className="w-4 h-4 text-purple-600" />}
                          </div>
                          <p className="text-xs text-slate-500">{f.desc}</p>
                        </button>
                      );
                    })}
                  </div>

                  {/* If Selected Skills chosen, show chips to select skills */}
                  {assessmentFocus === "selected_skills" && (
                    <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                      <span className="text-xs font-bold text-slate-700 block">
                        Select skills to include in this assessment:
                      </span>
                      <div className="flex flex-wrap gap-2">
                        {skillsList.map((s) => {
                          const isChecked = selectedSkills.includes(s.name);
                          return (
                            <button
                              key={s.name}
                              type="button"
                              onClick={() => {
                                if (isChecked) {
                                  setSelectedSkills(selectedSkills.filter((x) => x !== s.name));
                                } else {
                                  setSelectedSkills([...selectedSkills, s.name]);
                                }
                              }}
                              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
                                isChecked
                                  ? "bg-purple-600 text-white shadow-xs"
                                  : "bg-white border border-slate-300 text-slate-700 hover:bg-slate-100"
                              }`}
                            >
                              <span>{s.name}</span>
                              {isChecked && <Check className="w-3.5 h-3.5" />}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>

                {/* 3. Difficulty Level & Question Types (Two columns) */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Difficulty */}
                  <div className="space-y-2">
                    <label className="block text-xs font-bold text-slate-800 uppercase tracking-wider">
                      3. Difficulty Level:
                    </label>
                    <select
                      value={difficulty}
                      onChange={(e) => setDifficulty(e.target.value as any)}
                      className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-xs font-semibold bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-purple-500"
                    >
                      <option value="adaptive">Adaptive (Auto-scales from beginner to advanced)</option>
                      <option value="beginner">Beginner (Core fundamentals & syntax)</option>
                      <option value="intermediate">Intermediate (Standard engineering implementation)</option>
                      <option value="advanced">Advanced (Architectural design & concurrency)</option>
                    </select>
                  </div>

                  {/* Question Types */}
                  <div className="space-y-2">
                    <label className="block text-xs font-bold text-slate-800 uppercase tracking-wider">
                      4. Question Types:
                    </label>
                    <select
                      value={questionTypes}
                      onChange={(e) => setQuestionTypes(e.target.value as any)}
                      className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-xs font-semibold bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-purple-500"
                    >
                      <option value="combination">Combination (Multiple Choice + Short Answer)</option>
                      <option value="mcq">Multiple Choice Questions (MCQ only)</option>
                      <option value="short_answer">Short Answer / Descriptive only</option>
                    </select>
                  </div>
                </div>

                {/* 5. Summary of Profile to be Assessed */}
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <span className="text-xs font-bold text-slate-700 block">Assessment Target Scope:</span>
                    <p className="text-xs text-slate-600 mt-0.5">
                      Domain: <span className="font-semibold text-purple-700">{targetDomain}</span> • {questionCount} Questions ({durationMinutes} mins)
                    </p>
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {(assessmentFocus === "selected_skills" ? selectedSkills : skillsList.map((s) => s.name)).slice(0, 8).map((name) => (
                        <span key={name} className="px-2 py-0.5 rounded-md bg-white border border-slate-200 text-[11px] font-medium text-slate-700">
                          {name}
                        </span>
                      ))}
                      {skillsList.length > 8 && (
                        <span className="px-2 py-0.5 rounded-md bg-slate-200 text-[11px] font-medium text-slate-600">
                          +{skillsList.length - 8} more
                        </span>
                      )}
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={handleGenerateAssessment}
                    disabled={generatingTest || skillsList.length === 0}
                    className="px-6 py-3 rounded-xl bg-purple-600 hover:bg-purple-700 text-white font-bold text-xs sm:text-sm shadow-sm transition flex items-center justify-center gap-2 flex-shrink-0 disabled:opacity-50"
                  >
                    <Sparkles className="w-4 h-4" />
                    <span>Generate Personalized Assessment</span>
                  </button>
                </div>
              </div>
            )}

            {/* STATE B: Assessment Generated, Ready for Confirmation & Start */}
            {!generatingTest && assessmentQuestions.length > 0 && !testStarted && (
              <div className="bg-white p-6 sm:p-8 rounded-2xl border border-emerald-200 shadow-sm space-y-6">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-xl bg-emerald-100 flex items-center justify-center text-emerald-600">
                    <CheckCircle2 className="w-7 h-7" />
                  </div>
                  <div>
                    <span className="text-xs font-bold text-emerald-600 uppercase tracking-wider">
                      Assessment Successfully Generated
                    </span>
                    <h2 className="text-2xl font-bold text-slate-900">
                      {actualGeneratedCount || assessmentQuestions.length} Questions Ready
                    </h2>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Your personalized assessment has been generated and validated against your confirmed profile.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="text-[11px] text-slate-500 font-medium block">Total Questions</span>
                    <span className="text-lg font-bold text-slate-900">{actualGeneratedCount || assessmentQuestions.length} Questions</span>
                  </div>
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="text-[11px] text-slate-500 font-medium block">Allocated Time</span>
                    <span className="text-lg font-bold text-slate-900">{durationMinutes} Minutes</span>
                  </div>
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="text-[11px] text-slate-500 font-medium block">Difficulty</span>
                    <span className="text-lg font-bold text-slate-900 capitalize">{difficulty}</span>
                  </div>
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="text-[11px] text-slate-500 font-medium block">Domain</span>
                    <span className="text-lg font-bold text-purple-700 truncate block">{targetDomain}</span>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-purple-50 border border-purple-100 space-y-2">
                  <h4 className="text-xs font-bold text-purple-900 uppercase">Assessment Instructions:</h4>
                  <ul className="text-xs text-purple-800 space-y-1 list-disc list-inside">
                    <li>Navigate freely between questions using Previous and Next buttons or the Question Palette.</li>
                    <li>Answers are automatically synchronized with the backend as you type or select options.</li>
                    <li>For MCQs, pick the single best option. For Short Answers, detail key technical principles.</li>
                    <li>Click &quot;Submit Final Assessment&quot; once you have completed all questions to receive your performance report.</li>
                  </ul>
                </div>

                <div className="flex items-center justify-between pt-2">
                  <button
                    type="button"
                    onClick={() => setAssessmentQuestions([])}
                    className="px-4 py-2 rounded-lg border border-slate-300 text-slate-700 text-xs font-semibold hover:bg-slate-50 transition"
                  >
                    Reconfigure Settings
                  </button>
                  <button
                    type="button"
                    onClick={handleStartAssessment}
                    className="px-8 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold shadow-md transition flex items-center gap-2"
                  >
                    <Play className="w-4 h-4 fill-white" />
                    <span>Start Assessment Now</span>
                  </button>
                </div>
              </div>
            )}

            {/* STATE C: Test in Progress (Paginated Multi-Question UI) */}
            {!generatingTest && testStarted && currentQ && (
              <div className="space-y-5">
                {/* Header: Progress, Timer & Autosave Status */}
                <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-bold px-2.5 py-1 rounded-md bg-purple-50 text-purple-700 uppercase">
                        {targetDomain}
                      </span>
                      <span className="text-sm font-bold text-slate-800">
                        Question {currentQIdx + 1} of {assessmentQuestions.length}
                      </span>
                      <span className="text-xs text-slate-500 font-medium">
                        ({Object.keys(answers).filter((k) => answers[k]?.trim()).length} of {assessmentQuestions.length} answered)
                      </span>
                    </div>

                    <div className="flex items-center gap-3">
                      {/* Autosave status indicator */}
                      <span className="text-[11px] text-slate-500 font-medium flex items-center gap-1">
                        {saveStatus === "saving" ? (
                          <>
                            <RefreshCw className="w-3 h-3 animate-spin text-purple-600" />
                            <span>Saving...</span>
                          </>
                        ) : saveStatus === "saved" ? (
                          <>
                            <Check className="w-3 h-3 text-emerald-600" />
                            <span>Progress saved</span>
                          </>
                        ) : (
                          <span className="text-amber-600">Unsaved changes</span>
                        )}
                      </span>

                      {/* Timer */}
                      <div className="flex items-center gap-1.5 text-xs font-bold text-purple-700 bg-purple-50 px-3 py-1.5 rounded-lg border border-purple-200">
                        <Clock className="w-4 h-4 text-purple-600" />
                        <span>{formatTime(timeRemaining)}</span>
                      </div>

                      {/* Question Palette Toggle */}
                      <button
                        type="button"
                        onClick={() => setShowPalette(!showPalette)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition flex items-center gap-1.5 ${
                          showPalette
                            ? "bg-slate-900 text-white border-slate-900"
                            : "bg-white text-slate-700 border-slate-300 hover:bg-slate-50"
                        }`}
                      >
                        <ListOrdered className="w-3.5 h-3.5" />
                        <span>Question Palette</span>
                      </button>
                    </div>
                  </div>

                  {/* Top Continuous Progress Bar */}
                  <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-purple-600 h-2 rounded-full transition-all duration-300 ease-out"
                      style={{ width: `${Math.round(((currentQIdx + 1) / assessmentQuestions.length) * 100)}%` }}
                    ></div>
                  </div>

                  {/* Question Palette Dropdown / Strip */}
                  {showPalette && (
                    <div className="pt-3 border-t border-slate-100 space-y-2">
                      <div className="flex items-center justify-between text-xs text-slate-500">
                        <span className="font-semibold text-slate-700">Quick Question Navigator:</span>
                        <div className="flex items-center gap-3 text-[11px]">
                          <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span> Answered</span>
                          <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-purple-600"></span> Current</span>
                          <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-slate-200"></span> Unanswered</span>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto p-1">
                        {assessmentQuestions.map((q, idx) => {
                          const isAnswered = Boolean(answers[q.id]?.trim());
                          const isCur = idx === currentQIdx;
                          return (
                            <button
                              key={q.id || idx}
                              type="button"
                              onClick={() => {
                                setCurrentQIdx(idx);
                                setShowPalette(false);
                              }}
                              className={`w-8 h-8 rounded-lg text-xs font-bold transition flex items-center justify-center ${
                                isCur
                                  ? "bg-purple-600 text-white ring-2 ring-purple-400 ring-offset-1"
                                  : isAnswered
                                  ? "bg-emerald-100 text-emerald-800 border border-emerald-300 hover:bg-emerald-200"
                                  : "bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-200"
                              }`}
                            >
                              {idx + 1}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>

                {/* Question Box */}
                <div className="bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-xs space-y-6">
                  {/* Question Meta Tags */}
                  <div className="flex flex-wrap items-center justify-between gap-2 pb-4 border-b border-slate-100">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-purple-50 text-purple-700 border border-purple-200">
                        Skill: {currentQ.skill}
                      </span>
                      <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 capitalize">
                        Difficulty: {currentQ.difficulty || "intermediate"}
                      </span>
                      {currentQ.related_project && (
                        <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-blue-50 text-blue-700 border border-blue-200 flex items-center gap-1">
                          <FolderGit2 className="w-3 h-3" />
                          <span>Project: {currentQ.related_project}</span>
                        </span>
                      )}
                      {currentQ.source_reference && (
                        <span className="text-xs font-medium px-2 py-0.5 rounded-sm bg-slate-50 text-slate-500">
                          Ref: {currentQ.source_reference}
                        </span>
                      )}
                    </div>
                    <span className="text-xs font-bold text-purple-600 px-2 py-1 rounded-md bg-purple-50">
                      {currentQ.points || 10} Points
                    </span>
                  </div>

                  {/* Question Title */}
                  <div className="space-y-2">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
                      Question {currentQIdx + 1} of {assessmentQuestions.length}
                    </span>
                    <h3 className="text-lg sm:text-xl font-bold text-slate-900 leading-relaxed">
                      {currentQ.question_text}
                    </h3>
                  </div>

                  {/* Multiple Choice Options */}
                  {currentQ.question_type === "mcq" && currentQ.options && (
                    <div className="space-y-3 pt-2">
                      {currentQ.options.map((opt: string, optIdx: number) => {
                        const isSelected = answers[currentQ.id] === opt;
                        const optionLetters = ["A", "B", "C", "D"];
                        return (
                          <button
                            key={optIdx}
                            type="button"
                            onClick={() => handleAnswerChange(currentQ.id, opt)}
                            className={`w-full p-4 rounded-xl border text-left text-xs sm:text-sm transition flex items-center justify-between ${
                              isSelected
                                ? "border-purple-600 bg-purple-50 text-purple-950 font-semibold shadow-xs ring-2 ring-purple-500/20"
                                : "border-slate-200 hover:border-slate-300 hover:bg-slate-50/70 text-slate-700 bg-white"
                            }`}
                          >
                            <div className="flex items-center gap-3">
                              <span className={`w-6 h-6 rounded-md flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                                isSelected ? "bg-purple-600 text-white" : "bg-slate-100 text-slate-600"
                              }`}>
                                {optionLetters[optIdx] || optIdx + 1}
                              </span>
                              <span>{opt}</span>
                            </div>
                            {isSelected && (
                              <CheckCircle2 className="w-5 h-5 text-purple-600 flex-shrink-0 ml-2" />
                            )}
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {/* Short Answer / Descriptive Field */}
                  {(currentQ.question_type === "descriptive" || currentQ.question_type === "short_answer") && (
                    <div className="pt-2 space-y-2">
                      <label className="block text-xs font-semibold text-slate-700">
                        Provide your concise technical explanation or architectural solution:
                      </label>
                      <textarea
                        rows={6}
                        value={answers[currentQ.id] || ""}
                        onChange={(e) => handleAnswerChange(currentQ.id, e.target.value)}
                        placeholder="Detail your solution, core trade-offs, edge case handling, and implementation steps..."
                        className="w-full p-4 rounded-xl border border-slate-300 text-slate-900 bg-white placeholder:text-slate-400 text-xs sm:text-sm focus:ring-2 focus:ring-purple-500 focus:outline-none"
                      />
                      <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1">
                        <span>Short answer responses are evaluated against technical rubric benchmarks.</span>
                        <span>{answers[currentQ.id]?.length || 0} characters</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Bottom Navigation and Submission Buttons */}
                <div className="flex items-center justify-between pt-2">
                  <button
                    type="button"
                    onClick={() => setCurrentQIdx((prev) => Math.max(0, prev - 1))}
                    disabled={currentQIdx === 0}
                    className="px-5 py-2.5 rounded-xl border border-slate-300 bg-white text-slate-700 text-xs font-semibold hover:bg-slate-50 transition disabled:opacity-40 flex items-center gap-2"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    <span>Previous Question</span>
                  </button>

                  <div className="flex items-center gap-3">
                    {currentQIdx < assessmentQuestions.length - 1 ? (
                      <button
                        type="button"
                        onClick={() => setCurrentQIdx((prev) => prev + 1)}
                        className="px-6 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold transition flex items-center gap-2 shadow-xs"
                      >
                        <span>Next Question</span>
                        <ArrowRight className="w-4 h-4" />
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setShowSubmitModal(true)}
                        disabled={submittingTest}
                        className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-sm transition flex items-center gap-2 disabled:opacity-50"
                      >
                        <Send className="w-4 h-4" />
                        <span>Submit Final Assessment</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Submission Confirmation & Evaluation Modal */}
                {showSubmitModal && (
                  <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
                    <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4">
                      {submittingTest ? (
                        <div className="py-6 text-center space-y-4">
                          <div className="w-14 h-14 rounded-full bg-purple-50 text-purple-600 flex items-center justify-center mx-auto border border-purple-200 shadow-xs">
                            <RefreshCw className="w-7 h-7 animate-spin" />
                          </div>
                          <div className="space-y-1.5">
                            <h3 className="text-base font-bold text-slate-900">Evaluating Your Assessment</h3>
                            <p className="text-xs text-slate-600 max-w-xs mx-auto leading-relaxed">
                              Scoring multiple-choice questions & evaluating descriptive responses against skill benchmarks. Validating competencies in your student profile...
                            </p>
                          </div>
                          <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                            <div className="bg-purple-600 h-1.5 rounded-full animate-pulse w-3/4"></div>
                          </div>
                          <p className="text-[11px] text-slate-400">Please keep this window open while your report is generated.</p>
                        </div>
                      ) : (
                        <>
                          <div className="flex items-center justify-between">
                            <h3 className="text-base font-bold text-slate-900">Confirm Assessment Submission</h3>
                            <button
                              type="button"
                              onClick={() => {
                                setShowSubmitModal(false);
                                setSubmissionError(null);
                              }}
                              className="text-slate-400 hover:text-slate-600"
                            >
                              <X className="w-5 h-5" />
                            </button>
                          </div>

                          {submissionError && (
                            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 text-xs flex items-center gap-2">
                              <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-600" />
                              <span>{submissionError}</span>
                            </div>
                          )}

                          <div className="text-xs text-slate-600 space-y-2">
                            <p>
                              You have answered <span className="font-bold text-slate-900">{Object.keys(answers).filter((k) => answers[k]?.trim()).length}</span> out of{" "}
                              <span className="font-bold text-slate-900">{assessmentQuestions.length}</span> questions.
                            </p>
                            {assessmentQuestions.length - Object.keys(answers).filter((k) => answers[k]?.trim()).length > 0 && (
                              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 flex items-center gap-2">
                                <AlertCircle className="w-4 h-4 flex-shrink-0 text-amber-600" />
                                <span>
                                  You have {assessmentQuestions.length - Object.keys(answers).filter((k) => answers[k]?.trim()).length} unanswered questions.
                                </span>
                              </div>
                            )}
                            <p>
                              Once submitted, your answers will be evaluated and your validated profile proficiencies will be updated.
                            </p>
                          </div>

                          <div className="flex items-center justify-end gap-3 pt-2">
                            <button
                              type="button"
                              onClick={() => {
                                setShowSubmitModal(false);
                                setSubmissionError(null);
                              }}
                              className="px-4 py-2 rounded-lg border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                            >
                              Return to Test
                            </button>
                            <button
                              type="button"
                              onClick={handleSubmitAssessment}
                              disabled={submittingTest}
                              className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition flex items-center gap-1.5 shadow-xs"
                            >
                              <Send className="w-4 h-4" />
                              <span>Confirm & Submit</span>
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* STEP 4: GENERATE A SKILL ASSESSMENT REPORT */}
        {/* ========================================================================= */}
        {currentStep === 4 && (
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-4 border-b border-slate-100 gap-4">
              <div>
                <span className="text-xs font-bold text-purple-600 uppercase tracking-wider">
                  Step 4 of 7 • Skill Assessment Report
                </span>
                <h2 className="text-2xl font-bold text-slate-900">
                  {assessmentResult?.domain || targetDomain} Evaluation
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                  Categorized by verified performance thresholds (Strong: ≥70%, Moderate: 40-69%, Needs Improvement: &lt;40%).
                </p>
              </div>

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowHistoryModal(true);
                    fetchAssessmentHistory();
                  }}
                  className="px-3.5 py-2 rounded-lg border border-purple-200 bg-purple-50 hover:bg-purple-100 text-purple-700 text-xs font-semibold flex items-center gap-1.5 transition"
                >
                  <Clock className="w-3.5 h-3.5" />
                  <span>Assessment History {assessmentHistory.length > 0 ? `(${assessmentHistory.length})` : ""}</span>
                </button>
                <div className="text-right flex-shrink-0">
                  <div className="text-3xl font-extrabold text-purple-600">
                    {assessmentResult?.total_score_percentage || 0}%
                  </div>
                  <span className="text-xs text-slate-500 font-medium">
                    {assessmentResult?.total_earned_points || 0} /{" "}
                    {assessmentResult?.total_available_points || 100} Points
                  </span>
                </div>
              </div>
            </div>

            {/* Overall Feedback */}
            {assessmentResult?.overall_feedback && (
              <div className="p-4 rounded-xl bg-purple-50/60 border border-purple-100 text-xs text-purple-950 leading-relaxed">
                <span className="font-bold block mb-1">Executive Assessment Summary:</span>
                {assessmentResult.overall_feedback}
              </div>
            )}

            {/* Performance Level Breakdown Cards */}
            <div>
              <h3 className="text-sm font-bold text-slate-900 mb-3">
                Skill Competency Breakdown & Visual Performance Chart
              </h3>

              <div className="space-y-3">
                {assessmentResult?.skill_breakdown?.map((item: any, idx: number) => {
                  const score = item.score_percentage || 0;
                  const level = item.performance_level || item.proficiency_level || "Moderate";

                  const levelBadge =
                    level === "Strong"
                      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                      : level === "Moderate"
                      ? "bg-amber-50 text-amber-700 border-amber-200"
                      : level === "Needs Improvement"
                      ? "bg-rose-50 text-rose-700 border-rose-200"
                      : "bg-slate-100 text-slate-600 border-slate-200";

                  return (
                    <div
                      key={idx}
                      className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-900 text-sm">{item.skill}</span>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${levelBadge}`}>
                            {level}
                          </span>
                        </div>
                        <div className="flex items-center gap-3">
                          <div className="w-28 bg-slate-200 rounded-full h-2">
                            <div
                              className={`h-2 rounded-full ${
                                score >= 70
                                  ? "bg-emerald-600"
                                  : score >= 40
                                  ? "bg-amber-500"
                                  : "bg-rose-500"
                              }`}
                              style={{ width: `${Math.min(100, score)}%` }}
                            ></div>
                          </div>
                          <span className="text-xs font-bold text-slate-900 w-10 text-right">
                            {score}%
                          </span>
                        </div>
                      </div>

                      {/* Evidence & Suggestions */}
                      {item.evidence && (
                        <p className="text-xs text-slate-600 pt-1">
                          <strong>Evidence from answers:</strong> {item.evidence}
                        </p>
                      )}
                      {item.improvement_suggestion && (
                        <p className="text-xs text-purple-700 font-medium">
                          💡 <strong>Improvement Suggestion:</strong> {item.improvement_suggestion}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Next Step Action */}
            <div className="pt-4 border-t border-slate-100 flex justify-end">
              <button
                onClick={() => goToStep(5)}
                className="px-6 py-2.5 rounded-lg bg-purple-600 hover:bg-purple-700 text-white font-semibold text-xs shadow-xs transition flex items-center gap-2"
              >
                <span>Proceed to Step 5: Learning Roadmap</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* STEP 5: PERSONALIZED LEARNING ROADMAP */}
        {/* ========================================================================= */}
        {currentStep === 5 && (
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-4 border-b border-slate-100 gap-4">
              <div>
                <span className="text-xs font-bold text-purple-600 uppercase tracking-wider">
                  Step 5 of 7 • Personalized Learning Roadmap
                </span>
                <h2 className="text-2xl font-bold text-slate-900">
                  Targeted Gap Remediation Roadmap
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                  Curriculum synthesized specifically from your weak assessment areas, paired with approved learning resources and hands-on mini-projects.
                </p>
              </div>

              {roadmap && (
                <div className="text-right">
                  <div className="text-2xl font-extrabold text-purple-600">
                    {roadmap.completion_percentage}%
                  </div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    Roadmap Completed
                  </span>
                </div>
              )}
            </div>

            {loadingRoadmap ? (
              <div className="space-y-4 animate-pulse">
                <div className="h-28 bg-slate-200 rounded-xl"></div>
                <div className="h-64 bg-slate-200 rounded-xl"></div>
              </div>
            ) : (roadmap?.requires_assessment && !assessmentResult) ? (
              <div className="bg-amber-50 border border-amber-200 rounded-2xl p-8 text-center space-y-4">
                <div className="w-12 h-12 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center mx-auto">
                  <AlertCircle className="w-6 h-6" />
                </div>
                <div className="space-y-1">
                  <h3 className="text-base font-bold text-amber-900">Skill Assessment Required</h3>
                  <p className="text-xs text-amber-800 max-w-md mx-auto leading-relaxed">
                    {roadmap.message || "To generate a genuinely personalized roadmap based on measured evidence rather than generic steps, you must first complete the technical skill assessment."}
                  </p>
                </div>
                <div>
                  <button
                    onClick={() => goToStep(3)}
                    className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold shadow-xs transition"
                  >
                    <Sparkles className="w-4 h-4" />
                    <span>Go to Skill Assessment (Step 3)</span>
                  </button>
                </div>
              </div>
            ) : (!roadmap || roadmap.requires_assessment) && assessmentResult ? (
              <div className="bg-purple-50/60 border border-purple-100 rounded-2xl p-8 text-center space-y-4">
                <div className="w-12 h-12 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center mx-auto">
                  <Sparkles className="w-6 h-6" />
                </div>
                <div className="space-y-1">
                  <h3 className="text-base font-bold text-purple-900">Synthesizing Your Evidence-Based Roadmap</h3>
                  <p className="text-xs text-purple-700 max-w-md mx-auto leading-relaxed">
                    Your assessment results have been recorded. Click below to load your personalized remediation curriculum.
                  </p>
                </div>
                <div>
                  <button
                    onClick={() => loadRoadmapData(true)}
                    className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold shadow-xs transition"
                  >
                    <RefreshCw className="w-4 h-4" />
                    <span>Generate Evidence-Based Roadmap</span>
                  </button>
                </div>
              </div>
            ) : roadmap ? (
              <div className="space-y-6">
                {/* Priority Gaps & Regeneration Bar */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between p-4 rounded-xl bg-purple-50/60 border border-purple-100 gap-3">
                  <div className="space-y-1">
                    <span className="text-[11px] font-bold text-purple-900 block uppercase tracking-wider">
                      Measured Assessment Skill Gaps:
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {roadmap.priority_skill_gaps?.map((gap: string, gIdx: number) => (
                        <span
                          key={gIdx}
                          className="px-2.5 py-0.5 rounded-full bg-white border border-purple-200 text-purple-800 text-[11px] font-semibold"
                        >
                          {gap}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-start sm:self-auto">
                    <button
                      onClick={() => {
                        if (confirm("Regenerate roadmap with your latest assessment performance? This will replace the existing schedule.")) {
                          loadRoadmapData(true);
                        }
                      }}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-purple-300 bg-white hover:bg-purple-50 text-purple-700 text-xs font-semibold transition shadow-2xs"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                      <span>Regenerate Roadmap</span>
                    </button>
                  </div>
                </div>

                {/* Roadmap Phases */}
                <div className="space-y-5">
                  {roadmap.phases?.map((phase: any) => (
                    <div
                      key={phase.phase_number}
                      className="p-6 rounded-2xl border border-slate-200 bg-white space-y-4 shadow-2xs"
                    >
                      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                        <div className="flex items-center gap-3">
                          <span className="w-8 h-8 rounded-xl bg-purple-600 text-white flex items-center justify-center font-bold text-xs shadow-2xs">
                            P{phase.phase_number}
                          </span>
                          <div>
                            <h4 className="font-bold text-sm text-slate-900">{phase.title}</h4>
                            <p className="text-xs text-slate-500">{phase.description}</p>
                          </div>
                        </div>
                        <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
                          {phase.estimated_weeks} Weeks
                        </span>
                      </div>

                      {/* Phased Topics */}
                      <div className="space-y-4 pt-1">
                        {phase.topics?.map((topic: any) => {
                          const status = topic.progress_status || (topic.is_completed ? "Completed" : "Not Started");
                          const isDone = status === "Completed";
                          const isInProgress = status === "In Progress";

                          return (
                            <div
                              key={topic.id}
                              className={`p-4 rounded-xl border text-xs space-y-3 transition ${
                                isDone
                                  ? "bg-emerald-50/40 border-emerald-200"
                                  : isInProgress
                                  ? "bg-purple-50/40 border-purple-200"
                                  : "bg-slate-50/50 border-slate-200"
                              }`}
                            >
                              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-2 border-b border-slate-100">
                                <div className="flex items-center gap-2">
                                  <button
                                    onClick={() => handleToggleRoadmapTopic(topic.id, status)}
                                    title="Click to advance status"
                                    className={`px-2.5 py-1 rounded-md text-[11px] font-bold border transition flex items-center gap-1.5 ${
                                      isDone
                                        ? "bg-emerald-100 text-emerald-800 border-emerald-300"
                                        : isInProgress
                                        ? "bg-purple-100 text-purple-800 border-purple-300"
                                        : "bg-white text-slate-600 border-slate-300 hover:bg-slate-100"
                                    }`}
                                  >
                                    {isDone ? <Check className="w-3 h-3 text-emerald-700" /> : <Clock className="w-3 h-3 text-purple-600" />}
                                    <span>{status}</span>
                                  </button>
                                  <span className={`font-bold text-sm ${isDone ? "text-emerald-900 line-through" : "text-slate-900"}`}>
                                    {topic.title}
                                  </span>
                                  <span className="px-2 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-600 text-[10px] font-semibold">
                                    {topic.skill}
                                  </span>
                                </div>

                                <div className="flex items-center gap-2 text-xs">
                                  {topic.current_level && topic.target_level && (
                                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700">
                                      Level: {topic.current_level} → {topic.target_level}
                                    </span>
                                  )}
                                  <span className="text-[11px] font-semibold text-slate-500">
                                    {topic.estimated_duration || "Estimated: 8 hours"}
                                  </span>
                                </div>
                              </div>

                              {/* Why it needs improvement - Assessment Evidence */}
                              {topic.why_improvement_needed && (
                                <div className="p-3 rounded-lg bg-amber-50/60 border border-amber-100 text-slate-700 space-y-0.5">
                                  <span className="font-bold text-amber-900 text-[11px] block">
                                    Why Improvement is Needed (Assessment Evidence):
                                  </span>
                                  <p className="leading-relaxed">{topic.why_improvement_needed}</p>
                                </div>
                              )}

                              <p className="text-slate-700 leading-relaxed">{topic.objective}</p>

                              {/* Ordered Learning Steps */}
                              {topic.ordered_steps && topic.ordered_steps.length > 0 && (
                                <div className="space-y-1.5 pt-1">
                                  <span className="font-bold text-slate-800 block text-[11px]">
                                    Ordered Learning Steps:
                                  </span>
                                  <ol className="list-decimal list-inside space-y-1 text-slate-600 pl-1">
                                    {topic.ordered_steps.map((st: string, sIdx: number) => (
                                      <li key={sIdx}>{st}</li>
                                    ))}
                                  </ol>
                                </div>
                              )}

                              {/* Practical Exercise */}
                              {topic.exercise && (
                                <div className="p-2.5 rounded-lg bg-white border border-slate-200 text-slate-700">
                                  <span className="font-semibold text-purple-700 block mb-0.5">
                                    Practical Exercise / Mini-Project:
                                  </span>
                                  <span>{topic.exercise}</span>
                                </div>
                              )}

                              {/* Measurable Completion Criterion */}
                              {topic.measurable_criterion && (
                                <div className="text-[11px] text-slate-500 flex items-center gap-1.5 pt-0.5">
                                  <CheckSquare className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
                                  <span><strong>Completion Criterion:</strong> {topic.measurable_criterion}</span>
                                </div>
                              )}

                              {/* Verified Resources */}
                              {topic.resources?.length > 0 && (
                                <div className="flex flex-wrap gap-2 pt-1 border-t border-slate-100">
                                  {topic.resources.map((r: any, rIdx: number) => (
                                    <a
                                      key={rIdx}
                                      href={r.url || "#"}
                                      target={r.url ? "_blank" : undefined}
                                      rel="noreferrer"
                                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white border border-purple-200 text-purple-700 text-[11px] font-semibold hover:bg-purple-50 transition"
                                    >
                                      <BookOpen className="w-3 h-3 text-purple-600" />
                                      <span>{r.title}</span>
                                      <ExternalLink className="w-3 h-3 text-purple-400" />
                                    </a>
                                  ))}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>

                      {phase.mini_project && (
                        <div className="p-3.5 rounded-xl border border-purple-200 bg-purple-50/50 text-xs">
                          <span className="font-bold text-purple-900 block mb-0.5">
                            Phase Milestone: {phase.mini_project.title}
                          </span>
                          <p className="text-slate-700 leading-relaxed">{phase.mini_project.description}</p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                <div className="pt-4 border-t border-slate-100 flex justify-end">
                  <button
                    onClick={() => goToStep(6)}
                    className="px-6 py-2.5 rounded-lg bg-purple-600 hover:bg-purple-700 text-white font-semibold text-xs shadow-xs transition flex items-center gap-2"
                  >
                    <span>Proceed to Step 6: Career Domain Recommendations</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <button
                  onClick={() => loadRoadmapData(false)}
                  className="px-5 py-2.5 rounded-lg bg-purple-600 text-white font-semibold text-xs shadow-xs"
                >
                  Generate Roadmap Now
                </button>
              </div>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* STEP 6: RECOMMEND THE MOST SUITABLE CAREER DOMAIN */}
        {/* ========================================================================= */}
        {currentStep === 6 && (
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-6">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
              <div>
                <span className="text-xs font-bold text-purple-600 uppercase tracking-wider">
                  Step 6 of 7 • Explainable Career Recommendations
                </span>
                <h2 className="text-2xl font-bold text-slate-900">
                  Transparent Career Domain Recommendations
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                  Calculated using validated assessment scores, project technologies, and algorithmic matching.
                </p>
              </div>
              <button
                onClick={() => loadCareerRecommendations(true)}
                disabled={loadingCareers}
                className="px-3.5 py-2 text-xs font-semibold rounded-lg bg-purple-50 text-purple-700 hover:bg-purple-100 border border-purple-200 transition flex items-center gap-1.5"
              >
                <span>{loadingCareers ? "Recalculating..." : "Regenerate Recommendations"}</span>
              </button>
            </div>

            {loadingCareers ? (
              <div className="space-y-4 animate-pulse">
                {[1, 2].map((i) => (
                  <div key={i} className="h-44 bg-slate-200 rounded-xl"></div>
                ))}
              </div>
            ) : careerRecs.length > 0 ? (
              <div className="space-y-5">
                {careerRecs.map((rec, idx) => (
                  <div
                    key={idx}
                    className="p-5 rounded-xl border border-slate-200 bg-white shadow-xs space-y-4"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 pb-3 border-b border-slate-100">
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <h3 className="text-lg font-bold text-slate-900">{rec.title}</h3>
                          <span
                            className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${
                              rec.eligibility_met
                                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                : "bg-rose-50 text-rose-700 border border-rose-200"
                            }`}
                          >
                            {rec.eligibility_met ? "Eligible" : "Prerequisites Unmet"}
                          </span>
                        </div>
                        <p className="text-xs text-slate-600 mt-1">{rec.description}</p>
                      </div>

                      <div className="text-right flex-shrink-0">
                        <div>
                          <div className="text-3xl font-extrabold text-purple-600">
                            {rec.match_score !== null && rec.match_score !== undefined
                              ? `${rec.match_score}%`
                              : "0%"}
                          </div>
                          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                            Deterministic Match Score
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Explaining: "Why is this career domain suitable for me?" */}
                    <div className="p-3.5 rounded-xl bg-purple-50/60 border border-purple-100 text-xs space-y-1 text-slate-800">
                      <span className="font-bold text-purple-900 flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5 text-purple-600" />
                        Why is this career domain recommended?
                      </span>
                      <p className="leading-relaxed">
                        {rec.reason_for_recommendation ||
                          rec.ai_explanation ||
                          "Your demonstrated performance on technical assessments and project history indicate a strong foundation for this engineering domain."}
                      </p>
                    </div>

                    {/* Transparent Formula & Calculation Method */}
                    {rec.formula_explanation && (
                      <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-1">
                        <span className="font-bold text-slate-800 flex items-center gap-1.5">
                          <HelpCircle className="w-3.5 h-3.5 text-slate-500" />
                          Scoring Formula & Criteria:
                        </span>
                        <p className="text-[11px] text-slate-600 font-mono bg-white p-2 rounded border border-slate-200">
                          {rec.formula_explanation}
                        </p>
                      </div>
                    )}

                    {/* Comparative Analysis */}
                    {rec.comparative_analysis && (
                      <div className="p-3 rounded-lg bg-indigo-50/50 border border-indigo-100 text-xs space-y-1">
                        <span className="font-bold text-indigo-900 flex items-center gap-1.5">
                          <Layers className="w-3.5 h-3.5 text-indigo-600" />
                          Comparative Domain Analysis:
                        </span>
                        <p className="text-[11px] text-indigo-900 leading-relaxed">
                          {rec.comparative_analysis}
                        </p>
                      </div>
                    )}

                    {/* Skills & Project Evidence Grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                      <div className="p-3 rounded-lg bg-emerald-50/50 border border-emerald-100 space-y-1.5">
                        <span className="font-bold text-emerald-800 block">
                          Supporting Skills & Validated Evidence:
                        </span>
                        {rec.matching_skills?.length > 0 ? (
                          <div className="space-y-1.5 pt-1">
                            {rec.matching_skills.map((s: any, sIdx: number) => (
                              <div
                                key={sIdx}
                                className="p-2 rounded bg-white border border-emerald-200 text-emerald-900"
                              >
                                <div className="flex items-center justify-between font-semibold text-[11px]">
                                  <span>{s.skill || s}</span>
                                  <span className="px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px]">
                                    {s.score !== undefined ? `${s.score}% score` : "Confirmed"}
                                  </span>
                                </div>
                                {s.evidence && (
                                  <p className="text-[10px] text-slate-500 mt-0.5 italic">
                                    Evidence: {s.evidence}
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        ) : (
                          <span className="text-slate-400 italic">No validated skills recorded yet.</span>
                        )}
                      </div>

                      <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5">
                        <span className="font-bold text-slate-700 block">
                          Missing or Weak Skills to Master:
                        </span>
                        {rec.missing_required_skills?.length > 0 ? (
                          <div className="flex flex-wrap gap-1.5 pt-1">
                            {rec.missing_required_skills.map((s: string, sIdx: number) => (
                              <span
                                key={sIdx}
                                className="px-2 py-1 rounded bg-white border border-slate-300 text-slate-700 text-[11px] font-medium"
                              >
                                {s}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-emerald-700 font-semibold">
                            All mandatory competencies validated!
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Steps required to become job-ready */}
                    {rec.job_ready_steps && rec.job_ready_steps.length > 0 && (
                      <div className="pt-2 text-xs space-y-1.5">
                        <span className="font-bold text-slate-800 block">
                          What to Learn Next (Action Plan):
                        </span>
                        <ul className="space-y-1">
                          {rec.job_ready_steps.map((st: string, stIdx: number) => (
                            <li key={stIdx} className="flex items-start gap-2 text-slate-600">
                              <CheckCircle2 className="w-3.5 h-3.5 text-purple-600 flex-shrink-0 mt-0.5" />
                              <span className="text-[11px]">{st}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Suggested Projects to Build Portfolio Experience */}
                    {rec.suggested_projects && rec.suggested_projects.length > 0 && (
                      <div className="pt-2 text-xs space-y-2">
                        <span className="font-bold text-slate-800 flex items-center gap-1.5">
                          <FolderGit2 className="w-3.5 h-3.5 text-purple-600" />
                          Suggested Projects to Build Domain Experience:
                        </span>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                          {rec.suggested_projects.map((proj: any, pIdx: number) => (
                            <div
                              key={pIdx}
                              className="p-3 rounded-lg border border-slate-200 bg-slate-50/70 space-y-1.5"
                            >
                              <div className="font-bold text-slate-900 text-[12px]">{proj.title}</div>
                              <p className="text-[11px] text-slate-600 leading-snug">{proj.description}</p>
                              {proj.technologies && proj.technologies.length > 0 && (
                                <div className="flex flex-wrap gap-1 pt-1">
                                  {proj.technologies.map((t: string, tIdx: number) => (
                                    <span
                                      key={tIdx}
                                      className="px-1.5 py-0.5 bg-white border border-slate-200 rounded text-[10px] font-medium text-slate-700"
                                    >
                                      {t}
                                    </span>
                                  ))}
                                </div>
                              )}
                              {proj.portfolio_impact && (
                                <div className="text-[10px] text-purple-700 font-medium pt-1">
                                  Impact: {proj.portfolio_impact}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Related Active Opportunities */}
                    {rec.related_opportunities && rec.related_opportunities.length > 0 && (
                      <div className="pt-2 text-xs space-y-2">
                        <span className="font-bold text-slate-800 flex items-center gap-1.5">
                          <Briefcase className="w-3.5 h-3.5 text-purple-600" />
                          Related Active Listings ({rec.related_opportunities.length} available):
                        </span>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                          {rec.related_opportunities.slice(0, 4).map((opp: any, oIdx: number) => (
                            <div
                              key={oIdx}
                              className="p-3 rounded-lg border border-slate-200 bg-white hover:border-purple-300 transition shadow-2xs space-y-1.5"
                            >
                              <div className="flex items-start justify-between gap-2">
                                <div>
                                  <h4 className="font-bold text-slate-900 text-[12px]">{opp.title}</h4>
                                  <p className="text-[10px] text-slate-500">{opp.company} • {opp.location}</p>
                                </div>
                                <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-purple-50 text-purple-700 capitalize">
                                  {opp.job_type || "internship"}
                                </span>
                              </div>
                              {opp.stipend && (
                                <div className="text-[10px] font-medium text-emerald-700">
                                  {opp.stipend}
                                </div>
                              )}
                              <div className="pt-1">
                                <Link
                                  href={`/jobs?search=${encodeURIComponent(opp.title)}`}
                                  className="text-[11px] font-bold text-purple-600 hover:text-purple-700 inline-flex items-center gap-1"
                                >
                                  View details & match score →
                                </Link>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Disclaimer */}
                    <div className="pt-2 border-t border-slate-100 text-[10px] text-slate-400 italic">
                      {rec.disclaimer ||
                        "Career domain recommendations represent measured skill alignment based on student evidence. They do not guarantee job offers or employment outcomes."}
                    </div>
                  </div>
                ))}

                <div className="pt-4 border-t border-slate-100 flex justify-end">
                  <button
                    onClick={() => goToStep(7)}
                    className="px-6 py-2.5 rounded-lg bg-purple-600 hover:bg-purple-700 text-white font-semibold text-xs shadow-xs transition flex items-center gap-2"
                  >
                    <span>Proceed to Step 7: Relevant Jobs & Internships</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <button
                  onClick={() => loadCareerRecommendations()}
                  className="px-5 py-2.5 rounded-lg bg-purple-600 text-white font-semibold text-xs shadow-xs"
                >
                  Generate Domain Recommendations
                </button>
              </div>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* STEP 7: RECOMMEND RELEVANT JOBS AND INTERNSHIPS */}
        {/* ========================================================================= */}
        {currentStep === 7 && (
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-4 border-b border-slate-100 gap-4">
              <div>
                <span className="text-xs font-bold text-purple-600 uppercase tracking-wider">
                  Step 7 of 7 • Relevant Opportunities
                </span>
                <h2 className="text-2xl font-bold text-slate-900">
                  Recommended Jobs & Internships
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                  Active administrator-published listings matched directly against your assessed skills and career domain.
                </p>
              </div>

              <Link
                href="/jobs"
                className="px-4 py-2 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 text-xs font-semibold transition"
              >
                Go to Full Jobs Page →
              </Link>
            </div>

            {loadingJobs ? (
              <div className="space-y-4 animate-pulse">
                {[1, 2].map((i) => (
                  <div key={i} className="h-36 bg-slate-200 rounded-xl"></div>
                ))}
              </div>
            ) : recommendedJobs.length > 0 ? (
              <div className="space-y-4">
                {recommendedJobs.map((item: any) => {
                  const job = item.job || item;
                  const oppType = job.opportunity_type || "Job";
                  const isEligible = item.eligibility_met !== undefined ? item.eligibility_met : true;
                  const matchScore = item.match_score !== undefined ? item.match_score : null;
                  const matchStatus = item.match_status;

                  return (
                    <div
                      key={job.id}
                      className="p-5 rounded-xl border border-slate-200 bg-white space-y-3 hover:border-purple-200 transition"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <h4 className="font-bold text-base text-slate-900">{job.title}</h4>
                            <span
                              className={`text-xs px-2.5 py-0.5 rounded-full font-bold border ${
                                oppType === "Internship"
                                  ? "bg-purple-50 text-purple-700 border-purple-200"
                                  : "bg-blue-50 text-blue-700 border-blue-200"
                              }`}
                            >
                              {oppType}
                            </span>
                            <span
                              className={`text-xs px-2.5 py-0.5 rounded-full font-bold border ${
                                isEligible
                                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                  : "bg-rose-50 text-rose-700 border-rose-200"
                              }`}
                            >
                              {isEligible ? "Eligible" : "Eligibility Unmet"}
                            </span>
                          </div>

                          <div className="flex items-center gap-3 text-xs text-slate-500 mt-1">
                            <span className="font-semibold text-slate-700">{job.company}</span>
                            <span>•</span>
                            <span>{job.location} ({job.work_mode})</span>
                            <span>•</span>
                            <span>Domain: {job.domain}</span>
                          </div>
                        </div>

                        {matchStatus === "assessment_required" ? (
                          <div className="text-right flex-shrink-0">
                            <button
                              type="button"
                              onClick={() => goToStep(3)}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-xs font-bold hover:bg-amber-100"
                            >
                              <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
                              <span>Complete your skill assessment</span>
                            </button>
                          </div>
                        ) : matchStatus === "match_unavailable" ? (
                          <div className="text-right flex-shrink-0">
                            <span className="px-2.5 py-1 rounded-lg bg-slate-100 border border-slate-200 text-slate-600 text-xs font-bold">
                              Match unavailable
                            </span>
                          </div>
                        ) : matchScore !== null ? (
                          <div className="text-right flex-shrink-0">
                            <div
                              className={`text-2xl font-extrabold ${
                                matchScore >= 60 ? "text-emerald-600" : matchScore > 0 ? "text-purple-600" : "text-slate-500"
                              }`}
                            >
                              {matchScore}%
                            </div>
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                              Match Score
                            </span>
                          </div>
                        ) : null}
                      </div>

                      <p className="text-xs text-slate-600">{job.description}</p>

                      <div className="pt-2 flex items-center justify-between border-t border-slate-100">
                        <div className="text-xs text-slate-500">
                          Required: {job.required_skills?.join(", ")}
                        </div>

                        <button
                          onClick={() => handleOpenQuickApply(job)}
                          className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-700 text-white font-semibold text-xs transition flex items-center gap-1.5"
                        >
                          <Send className="w-3.5 h-3.5" />
                          <span>Apply Now</span>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-8">
                <button
                  onClick={loadRecommendedJobs}
                  className="px-5 py-2.5 rounded-lg bg-purple-600 text-white font-semibold text-xs shadow-xs"
                >
                  Load Verified Job Matches
                </button>
              </div>
            )}
          </div>
        )}

        {/* QUICK APPLY MODAL FOR STEP 7 */}
        {quickApplyJob && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-4">
              <div className="flex justify-between items-start border-b border-slate-100 pb-3">
                <div>
                  <span className="text-xs font-bold text-purple-600 uppercase">
                    {quickApplyJob.opportunity_type || "Job"} Application
                  </span>
                  <h3 className="text-lg font-bold text-slate-900">{quickApplyJob.title}</h3>
                  <p className="text-xs text-slate-500">{quickApplyJob.company}</p>
                </div>
                <button
                  onClick={() => setQuickApplyJob(null)}
                  className="text-slate-400 hover:text-slate-600"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {quickApplySuccess ? (
                <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  <span>{quickApplySuccess}</span>
                </div>
              ) : (
                <form onSubmit={handleQuickSubmitApplication} className="space-y-4 text-xs">
                  <div className="bg-purple-50 p-3 rounded-lg text-slate-700">
                    Applying with your authenticated student profile ({user?.name || user?.email}) and validated skill scores.
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">
                      Statement of Interest (Optional)
                    </label>
                    <textarea
                      rows={3}
                      value={quickCoverLetter}
                      onChange={(e) => setQuickCoverLetter(e.target.value)}
                      placeholder="Why are you a great fit for this role?"
                      className="w-full p-2.5 rounded-lg border border-slate-300 bg-white text-slate-900 placeholder:text-slate-400 text-xs focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                  </div>

                  <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                    <button
                      type="button"
                      onClick={() => setQuickApplyJob(null)}
                      className="px-4 py-2 rounded-lg border border-slate-300 text-slate-700 font-semibold"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={quickApplying}
                      className="px-5 py-2 rounded-lg bg-purple-600 text-white font-semibold transition disabled:opacity-50"
                    >
                      {quickApplying ? "Submitting..." : "Confirm Application"}
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        )}
        {/* Assessment History Modal */}
        {showHistoryModal && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 max-h-[85vh] flex flex-col animate-in fade-in zoom-in-95 duration-150">
              <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                <div className="flex items-center gap-2.5">
                  <div className="w-9 h-9 rounded-xl bg-purple-100 text-purple-700 flex items-center justify-center">
                    <Award className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900">Your Assessment History & Marks</h3>
                    <p className="text-xs text-slate-500">
                      Permanent records stored in Cloud Firestore for your authenticated account
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setShowHistoryModal(false)}
                  className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 transition"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto py-4 space-y-3">
                {loadingHistory ? (
                  <div className="py-12 text-center text-slate-500 text-xs flex flex-col items-center justify-center gap-3">
                    <RefreshCw className="w-6 h-6 animate-spin text-purple-600" />
                    <p>Retrieving your saved assessment attempts from Firestore...</p>
                  </div>
                ) : historyError ? (
                  <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex flex-col gap-2">
                    <div className="flex items-center gap-2 font-bold text-rose-900">
                      <AlertCircle className="w-4 h-4 text-rose-600" />
                      <span>Failed to retrieve assessment history</span>
                    </div>
                    <p>{historyError}</p>
                    <button
                      type="button"
                      onClick={fetchAssessmentHistory}
                      className="self-start px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-semibold transition"
                    >
                      Retry
                    </button>
                  </div>
                ) : assessmentHistory.length === 0 ? (
                  <div className="py-12 text-center text-slate-500 text-xs space-y-2">
                    <BookOpen className="w-8 h-8 text-slate-300 mx-auto" />
                    <p className="font-semibold text-slate-700">No completed assessments recorded yet.</p>
                    <p className="text-slate-500 max-w-sm mx-auto">
                      Generate and complete an assessment to record your verified skills and receive a comprehensive proficiency breakdown.
                    </p>
                  </div>
                ) : (
                  assessmentHistory.map((item: any, idx: number) => {
                    const score = Number(item.total_score_percentage || 0);
                    const formattedDate = item.submitted_at
                      ? new Date(item.submitted_at).toLocaleDateString(undefined, {
                          year: "numeric",
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })
                      : "Completed Record";

                    return (
                      <div
                        key={item.attempt_id || item.id || idx}
                        className="p-4 rounded-xl border border-slate-200 hover:border-purple-300 bg-slate-50/50 hover:bg-purple-50/20 transition space-y-3"
                      >
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-sm text-slate-900">
                                {item.domain || "Technical"} Assessment
                              </span>
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                                Completed
                              </span>
                            </div>
                            <div className="flex items-center gap-1.5 text-[11px] text-slate-500 mt-0.5">
                              <Clock className="w-3 h-3 text-slate-400" />
                              <span>{formattedDate}</span>
                            </div>
                          </div>

                          <div className="flex items-center gap-3">
                            <div className="text-right">
                              <span
                                className={`text-lg font-extrabold ${
                                  score >= 70
                                    ? "text-emerald-600"
                                    : score >= 40
                                    ? "text-purple-600"
                                    : "text-rose-600"
                                }`}
                              >
                                {score}%
                              </span>
                              <p className="text-[10px] text-slate-500 font-medium">
                                {item.total_earned_points ?? score} / {item.total_available_points ?? 100} Marks
                              </p>
                            </div>

                            <button
                              type="button"
                              onClick={() => {
                                setAssessmentResult(item);
                                if (item.domain) setTargetDomain(item.domain);
                                setCurrentStep(4);
                                setShowHistoryModal(false);
                              }}
                              className="px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold shadow-xs transition"
                            >
                              View Report
                            </button>
                          </div>
                        </div>

                        {/* Skill badges */}
                        {Array.isArray(item.skill_breakdown) && item.skill_breakdown.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 pt-1 border-t border-slate-100">
                            {item.skill_breakdown.map((s: any, sIdx: number) => {
                              const sScore = Number(s.score_percentage || 0);
                              return (
                                <span
                                  key={sIdx}
                                  className={`px-2 py-0.5 rounded-md text-[10px] font-semibold border ${
                                    sScore >= 70
                                      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                      : sScore >= 40
                                      ? "bg-amber-50 text-amber-700 border-amber-200"
                                      : "bg-rose-50 text-rose-700 border-rose-200"
                                  }`}
                                >
                                  {s.skill}: {sScore}%
                                </span>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                <span>Total records: {assessmentHistory.length}</span>
                <button
                  type="button"
                  onClick={() => setShowHistoryModal(false)}
                  className="px-4 py-2 rounded-lg border border-slate-300 hover:bg-slate-50 font-semibold text-slate-700 transition"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
