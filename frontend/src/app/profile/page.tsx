"use client";

import React, { useEffect, useState, useRef } from "react";
import { AppShell } from "@/components/AppShell";
import { apiRequest } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import {
  User,
  GraduationCap,
  Building,
  Calendar,
  Code,
  Briefcase,
  Heart,
  Save,
  CheckCircle2,
  FileText,
  AlertCircle
} from "lucide-react";

interface UserProfile {
  name: string;
  email?: string;
  education_level: string;
  degree: string;
  institution: string;
  graduation_year: number;
  technical_skills: string[];
  interests: string[];
  preferred_career_domains: string[];
  bio: string;
  completion_percentage: number;
  [key: string]: unknown;
}

export default function ProfilePage() {
  const { user, token } = useAuth();
  const [profile, setProfile] = useState<UserProfile>({
    name: "",
    education_level: "Bachelor's",
    degree: "",
    institution: "",
    graduation_year: 2025,
    technical_skills: [],
    interests: [],
    preferred_career_domains: [],
    bio: "",
    completion_percentage: 0,
  });
  const [skillInput, setSkillInput] = useState("");
  const [interestInput, setInterestInput] = useState("");
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const lastLoadedKeyRef = useRef<string>("");

  useEffect(() => {
    let isSubscribed = true;

    // Safely populate from cached storage after client mount
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("skillpath_user");
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          if (isSubscribed) {
            setProfile((prev: UserProfile) => ({
              ...prev,
              ...parsed,
              technical_skills: parsed.technical_skills || [],
              interests: parsed.interests || [],
              preferred_career_domains: parsed.preferred_career_domains || [],
            }));
          }
        } catch {
          // ignore
        }
      }
    }

    if (!user && !token) {
      setLoading(false);
      return;
    }

    const sessionKey = `${user?.uid || ""}_${token || ""}`;
    if (lastLoadedKeyRef.current === sessionKey) {
      setLoading(false);
      return;
    }
    lastLoadedKeyRef.current = sessionKey;

    async function loadProfile() {
      try {
        const data = await apiRequest<UserProfile>("/profiles/me", { token, silent: true });
        if (data && isSubscribed) {
          const updated: UserProfile = {
            ...data,
            technical_skills: data.technical_skills || [],
            interests: data.interests || [],
            preferred_career_domains: data.preferred_career_domains || [],
          };
          setProfile(updated);
          localStorage.setItem("skillpath_user", JSON.stringify(updated));
        }
      } catch (err: unknown) {
        console.warn("Background profile refresh note:", err);
        if (isSubscribed) {
          setMessage({
            type: "error",
            text: "Could not load cloud profile. You can still edit and save your information below.",
          });
        }
      } finally {
        if (isSubscribed) {
          setLoading(false);
        }
      }
    }

    loadProfile();

    return () => {
      isSubscribed = false;
    };
  }, [user, token]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const updated = await apiRequest<UserProfile>("/profiles/me", {
        method: "PUT",
        token,
        body: JSON.stringify(profile),
      });
      setProfile(updated);
      setMessage({ type: "success", text: "Profile details updated successfully!" });
    } catch (err: unknown) {
      const errorMsg = (err as Error)?.message || "Failed to update profile.";
      setMessage({ type: "error", text: errorMsg });
    } finally {
      setSaving(false);
    }
  };

  const addSkill = () => {
    if (skillInput.trim() && !profile.technical_skills.includes(skillInput.trim())) {
      setProfile({
        ...profile,
        technical_skills: [...profile.technical_skills, skillInput.trim()],
      });
      setSkillInput("");
    }
  };

  const removeSkill = (skill: string) => {
    setProfile({
      ...profile,
      technical_skills: profile.technical_skills.filter((s: string) => s !== skill),
    });
  };

  const addInterest = () => {
    if (interestInput.trim() && !profile.interests.includes(interestInput.trim())) {
      setProfile({
        ...profile,
        interests: [...profile.interests, interestInput.trim()],
      });
      setInterestInput("");
    }
  };

  const removeInterest = (item: string) => {
    setProfile({
      ...profile,
      interests: profile.interests.filter((i: string) => i !== item),
    });
  };

  return (
    <AppShell
      title="Student Profile & Qualifications"
      description="Maintain your authoritative academic background, technical claimed skills, and target engineering domains."
    >
      {loading ? (
        <div className="bg-white p-8 rounded-xl border border-slate-200 animate-pulse space-y-4">
          <div className="h-6 w-1/3 bg-slate-200 rounded-sm"></div>
          <div className="h-20 bg-slate-100 rounded-sm"></div>
        </div>
      ) : (
        <form onSubmit={handleSave} className="space-y-6">
          {message && (
            <div
              className={`p-4 rounded-xl text-sm flex items-center gap-2 ${
                message.type === "success"
                  ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                  : "bg-rose-50 text-rose-800 border border-rose-200"
              }`}
            >
              {message.type === "success" ? (
                <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-emerald-600" />
              ) : (
                <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-600" />
              )}
              <span>{message.text}</span>
            </div>
          )}

          {/* Profile Completion Bar */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-bold text-slate-800">Profile Completion Status</span>
              <span className="text-xs font-bold text-purple-600">{profile.completion_percentage || 0}% Complete</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2.5">
              <div
                className="bg-purple-600 h-2.5 rounded-full transition-all duration-500"
                style={{ width: `${profile.completion_percentage || 0}%` }}
              ></div>
            </div>
          </div>

          {/* Personal & Academic Credentials */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-5">
            <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
              <GraduationCap className="w-5 h-5 text-purple-600" />
              <h3 className="font-bold text-slate-900 text-base">Academic Credentials</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Full Legal Name</label>
                <input
                  type="text"
                  required
                  value={profile.name || ""}
                  onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 text-sm text-slate-900 bg-white placeholder:text-slate-400 focus:ring-2 focus:ring-purple-600 focus:border-purple-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Email Address</label>
                <input
                  type="email"
                  disabled
                  value={profile.email || user?.email || ""}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-slate-200 bg-slate-50 text-slate-500 text-sm cursor-not-allowed"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Degree Program</label>
                <input
                  type="text"
                  placeholder="e.g. B.Tech in Computer Science"
                  value={profile.degree || ""}
                  onChange={(e) => setProfile({ ...profile, degree: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 text-sm text-slate-900 bg-white placeholder:text-slate-400 focus:ring-2 focus:ring-purple-600 focus:border-purple-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Education Level</label>
                <select
                  value={profile.education_level || "Bachelor's"}
                  onChange={(e) => setProfile({ ...profile, education_level: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 text-sm text-slate-900 bg-white focus:ring-2 focus:ring-purple-600 focus:border-purple-600 focus:outline-none"
                >
                  <option value="High School">High School</option>
                  <option value="Associate">Associate Degree</option>
                  <option value="Bachelor's">Bachelor&apos;s Degree</option>
                  <option value="Master's">Master&apos;s Degree</option>
                  <option value="Doctorate">Doctorate (Ph.D.)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">University / Institution</label>
                <input
                  type="text"
                  placeholder="e.g. Stanford University"
                  value={profile.institution || ""}
                  onChange={(e) => setProfile({ ...profile, institution: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 text-sm text-slate-900 bg-white placeholder:text-slate-400 focus:ring-2 focus:ring-purple-600 focus:border-purple-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Expected Graduation Year</label>
                <input
                  type="number"
                  min={2020}
                  max={2035}
                  value={profile.graduation_year || 2025}
                  onChange={(e) => setProfile({ ...profile, graduation_year: parseInt(e.target.value) || 2025 })}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 text-sm text-slate-900 bg-white placeholder:text-slate-400 focus:ring-2 focus:ring-purple-600 focus:border-purple-600 focus:outline-none"
                />
              </div>
            </div>
          </div>

          {/* Technical Skills & Self-Reported Competencies */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
              <Code className="w-5 h-5 text-purple-600" />
              <h3 className="font-bold text-slate-900 text-base">Claimed Technical Skills</h3>
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Add skill (e.g. Python, React, Docker)"
                value={skillInput}
                onChange={(e) => setSkillInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addSkill();
                  }
                }}
                className="flex-1 px-3.5 py-2 rounded-lg border border-slate-300 text-sm text-slate-900 bg-white placeholder:text-slate-400 focus:ring-2 focus:ring-purple-600 focus:border-purple-600 focus:outline-none"
              />
              <button
                type="button"
                onClick={addSkill}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold rounded-lg transition"
              >
                Add Skill
              </button>
            </div>

            <div className="flex flex-wrap gap-2 pt-2">
              {profile.technical_skills?.map((s: string, idx: number) => (
                <span
                  key={idx}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-800 border border-slate-200"
                >
                  <span>{s}</span>
                  <button
                    type="button"
                    onClick={() => removeSkill(s)}
                    className="text-slate-400 hover:text-rose-600 font-bold"
                  >
                    ×
                  </button>
                </span>
              ))}
              {profile.technical_skills?.length === 0 && (
                <p className="text-xs text-slate-400 italic">No claimed skills added. You can also extract them by uploading your resume.</p>
              )}
            </div>
          </div>

          {/* Target Domains & Career Interests */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
              <Heart className="w-5 h-5 text-purple-600" />
              <h3 className="font-bold text-slate-900 text-base">Career Interests & Domains</h3>
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Add interest (e.g. Distributed Systems, Frontend Engineering, NLP)"
                value={interestInput}
                onChange={(e) => setInterestInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addInterest();
                  }
                }}
                className="flex-1 px-3.5 py-2 rounded-lg border border-slate-300 text-sm text-slate-900 bg-white placeholder:text-slate-400 focus:ring-2 focus:ring-purple-600 focus:border-purple-600 focus:outline-none"
              />
              <button
                type="button"
                onClick={addInterest}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold rounded-lg transition"
              >
                Add Interest
              </button>
            </div>

            <div className="flex flex-wrap gap-2 pt-2">
              {profile.interests?.map((item: string, idx: number) => (
                <span
                  key={idx}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-purple-50 text-purple-700 border border-purple-100"
                >
                  <span>{item}</span>
                  <button
                    type="button"
                    onClick={() => removeInterest(item)}
                    className="text-purple-400 hover:text-rose-600 font-bold"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-purple-600 hover:bg-purple-700 text-white font-semibold text-sm shadow-sm transition disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              <span>{saving ? "Saving Changes..." : "Save Profile Details"}</span>
            </button>
          </div>
        </form>
      )}
    </AppShell>
  );
}
