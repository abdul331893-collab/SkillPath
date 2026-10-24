"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function ResumeAssessmentRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/career-assessment");
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="flex flex-col items-center gap-3">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
        <p className="text-xs text-slate-500">Redirecting to Career Assessment...</p>
      </div>
    </div>
  );
}
