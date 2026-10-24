import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "SkillPath AI — Adaptive Career Intelligence System",
  description:
    "SkillPath AI: An Adaptive Career Intelligence System Using Large Language Models and Retrieval-Augmented Generation for Skill Validation, Personalized Learning, and Job Matching.",
  keywords: [
    "career intelligence",
    "skill assessment",
    "AI learning roadmap",
    "job matching",
    "RAG",
    "resume analysis"
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className={`${inter.className} min-h-screen bg-slate-50 text-slate-900 flex flex-col antialiased`}>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
