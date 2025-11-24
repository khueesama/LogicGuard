"use client"

import { useState, useEffect, useRef } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { useDocument } from "@/lib/document-context"
import { Button } from "@/components/ui/button"
import { Save, Download, ChevronLeft, Loader2, Check, Sparkles, X } from "lucide-react"
import {
  RichTextEditor,
  type AnalysisIssue,
  type RichTextEditorHandle,
} from "@/components/rich-text-editor"
import { ContextSetup } from "@/components/context-setup"
import { AnalysisIssuesOverlay } from "@/components/analysis-issues-overlay"
import { DocumentsAPI, EnhancedGoalsAPI } from "@/lib/api-service"
import type { GoalDetailResponse } from "@/lib/api-service"
import { getApiBaseUrlWithoutSuffix } from "@/lib/api-config"

interface ContextDataPayload {
  writingType: string
  goalRubrics: string[]
  keyConstraints: string[]
  goal: GoalDetailResponse
}

interface LogicAnalysisAPIResponse {
  analysis_metadata?: any
  contradictions?: {
    total_found: number
    items: any[]
  }
  undefined_terms?: {
    total_found: number
    items: any[]
  }
  unsupported_claims?: {
    total_found: number
    items: any[]
  }
  logical_jumps?: {
    total_found: number
    items: any[]
  }
  spelling_errors?: {
    total_found: number
    items: any[]
  }
  summary?: {
    total_issues: number
    critical_issues: number
    document_quality_score: number
    key_recommendations: string[]
  }
  metadata?: Record<string, any>
}

export default function CanvasPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { selectedDocumentId, selectedDocument } = useDocument()

  const [editorContent, setEditorContent] = useState("")
  const [currentDoc, setCurrentDoc] = useState<{ title: string; content: string; goalId?: string | null } | null>(null)
  const [currentGoal, setCurrentGoal] = useState<GoalDetailResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [analysisActive, setAnalysisActive] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisIssues, setAnalysisIssues] = useState<AnalysisIssue[]>([])
  const [appliedSuggestions, setAppliedSuggestions] = useState<string[]>([])
  const [showAnalysisToast, setShowAnalysisToast] = useState(false)

  const initialContentRef = useRef<string>("")
  const editorRef = useRef<RichTextEditorHandle | null>(null)

  const docId = searchParams?.get("docId") ?? selectedDocumentId ?? null

  useEffect(() => {
    if (docId) {
      void fetchDocument(docId)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docId])

  // Track unsaved changes
  useEffect(() => {
    if (initialContentRef.current && editorContent !== initialContentRef.current) {
      setHasUnsavedChanges(true)
    } else {
      setHasUnsavedChanges(false)
    }
  }, [editorContent])

  // Warn before leaving page with unsaved changes
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        e.preventDefault()
        e.returnValue = ""
        return ""
      }
    }

    window.addEventListener("beforeunload", handleBeforeUnload)
    return () => window.removeEventListener("beforeunload", handleBeforeUnload)
  }, [hasUnsavedChanges])

  const handleNavigation = (path: string) => {
    if (hasUnsavedChanges) {
      const confirmed = window.confirm(
        "Bạn có thay đổi chưa được lưu. Bạn có chắc muốn rời đi mà không lưu không?",
      )
      if (!confirmed) return
    }
    router.push(path)
  }

  const fetchDocument = async (documentId: string) => {
    setIsLoading(true)
    setError(null)
    setCurrentGoal(null)
    try {
      const doc = await DocumentsAPI.getById(documentId)
      const content = doc.content_full || ""
      setCurrentDoc({
        title: doc.title,
        content,
        goalId: doc.goal_id,
      })
      setEditorContent(content)
      initialContentRef.current = content
      setHasUnsavedChanges(false)

      if (doc.goal_id) {
        await loadGoal(doc.goal_id)
      }
    } catch (err: unknown) {
      const e = err as Error
      setError(e.message || "Failed to load document")
      if (selectedDocument) {
        const content = selectedDocument.content || ""
        setCurrentDoc({
          title: selectedDocument.title,
          content,
          goalId: undefined,
        })
        setEditorContent(content)
        initialContentRef.current = content
      }
    } finally {
      setIsLoading(false)
    }
  }

  const loadGoal = async (goalId: string) => {
    try {
      const goalData = await EnhancedGoalsAPI.getById(goalId)
      setCurrentGoal(goalData)
    } catch (err: unknown) {
      const e = err as Error
      setError(e.message || "Failed to load goal data")
    }
  }

  const handleSave = async () => {
    if (!docId) return

    setIsSaving(true)
    setSaveSuccess(false)
    setError(null)

    try {
      await DocumentsAPI.update(docId, {
        content_full: editorContent,
      })

      initialContentRef.current = editorContent
      setHasUnsavedChanges(false)
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 2000)
    } catch (err: unknown) {
      const e = err as Error
      setError(e.message || "Failed to save document")
    } finally {
      setIsSaving(false)
    }
  }

  const handleExport = () => {
    if (!currentDoc) return

    const blob = new Blob([editorContent], { type: "text/html" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = `${currentDoc.title}.html`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const handleContextApply = async (contextData: ContextDataPayload) => {
    if (!docId || !contextData.goal) return

    try {
      if (!currentDoc?.goalId || currentDoc.goalId !== contextData.goal.id) {
        await DocumentsAPI.update(docId, {
          goal_id: contextData.goal.id,
        })

        setCurrentDoc(prev => (prev ? { ...prev, goalId: contextData.goal.id } : prev))
      }

      setCurrentGoal(contextData.goal)
    } catch (err: unknown) {
      const e = err as Error
      setError(e.message || "Failed to link goal to document")
    }
  }

  const handleAnalyze = async () => {
    // nếu đang bật thì tắt
    if (analysisActive) {
      setAnalysisIssues([])
      setAnalysisActive(false)
      setAppliedSuggestions([])
      return
    }

    setAnalysisActive(true)
    setIsAnalyzing(true)
    setError(null)
    setShowAnalysisToast(false)

    try {
      const content = editorContent || currentDoc?.content || ""

      if (!content.trim()) {
        setError("Không có nội dung để phân tích")
        setAnalysisIssues([])
        setAnalysisActive(false)
        setIsAnalyzing(false)
        return
      }

      let token: string | null = null

      if (typeof window !== "undefined") {
        token =
          localStorage.getItem("access_token") ||
          localStorage.getItem("accessToken") ||
          localStorage.getItem("token") ||
          sessionStorage.getItem("access_token") ||
          sessionStorage.getItem("accessToken") ||
          sessionStorage.getItem("token")

        console.log("[Canvas] token found?", !!token)
      }

      if (!token) {
        setError("Bạn chưa đăng nhập hoặc phiên đăng nhập đã hết hạn.")
        setAnalysisIssues([])
        setAnalysisActive(false)
        setIsAnalyzing(false)
        return
      }

      const mainGoalTitle = currentGoal
        ? "Analyze document for current goal"
        : "Analyze document for logical issues"

      const contextPayload = {
        writing_type: "Document",
        main_goal: mainGoalTitle,
        criteria: [],
        constraints: [],
      }

      const baseUrl = getApiBaseUrlWithoutSuffix()

      const res = await fetch(`${baseUrl}/api/logic-checks/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        credentials: "include",
        body: JSON.stringify({
          context: contextPayload,
          content,
          language: "vi", // hoặc "en" tuỳ nội dung
          mode: "fast",
        }),
      })

      if (res.status === 401 || res.status === 403) {
        const text = await res.text()
        console.error("[Canvas] Unauthorized/Forbidden:", res.status, text)
        setError("Bạn chưa đăng nhập hoặc không có quyền sử dụng tính năng phân tích.")
        setAnalysisIssues([])
        setAnalysisActive(false)
        setIsAnalyzing(false)
        return
      }

      if (!res.ok) {
        const text = await res.text()
        console.error("[Canvas] Analysis API error:", res.status, text)
        setError("Phân tích thất bại từ server")
        setAnalysisIssues([])
        setAnalysisActive(false)
        setIsAnalyzing(false)
        return
      }

      const data: LogicAnalysisAPIResponse = await res.json()

      const spellingItems = data.spelling_errors?.items ?? []
      const undefinedItems = data.undefined_terms?.items ?? []
      const unsupportedItems = data.unsupported_claims?.items ?? []
      const jumpsItems = data.logical_jumps?.items ?? []
      const contraItems = data.contradictions?.items ?? []

      const mapped: AnalysisIssue[] = []

      // 1. Spelling
      spellingItems.forEach((it: any, idx: number) => {
        mapped.push({
          id: `spell_${idx + 1}`,
          type: "spelling_error",
          startPos: it.start_pos ?? 0,
          endPos: it.end_pos ?? 0,
          text: it.original ?? "",
          message: it.reason ?? "",
          suggestion: it.suggested ?? "",
        })
      })

      // 2. Undefined terms
      undefinedItems.forEach((it: any, idx: number) => {
        mapped.push({
          id: `undef_${idx + 1}`,
          type: "undefined_term",
          startPos: 0,
          endPos: 0,
          text: it.term ?? it.text ?? "",
          message: it.reason ?? "",
          suggestion: it.suggestion ?? "",
        })
      })

      // 3. Unsupported claims
      unsupportedItems.forEach((it: any, idx: number) => {
        mapped.push({
          id: `claim_${idx + 1}`,
          type: "unsupported_claim",
          startPos: 0,
          endPos: 0,
          text: it.claim ?? it.text ?? "",
          message: it.reason ?? "",
          suggestion: it.suggestion ?? "",
        })
      })

      // 4. Logical jumps
      jumpsItems.forEach((it: any, idx: number) => {
        mapped.push({
          id: `jump_${idx + 1}`,
          type: "logical_jump",
          startPos: 0,
          endPos: 0,
          text: `${it.from_paragraph} → ${it.to_paragraph}`,
          message: it.explanation ?? "",
          suggestion: it.suggestion ?? "",
        })
      })

      // 5. Contradictions
      contraItems.forEach((it: any, idx: number) => {
        mapped.push({
          id: `contra_${idx + 1}`,
          type: "contradiction",
          startPos: 0,
          endPos: 0,
          text: `${it.sentence1 ?? ""} ↔ ${it.sentence2 ?? ""}`,
          message: it.explanation ?? "",
          suggestion: it.suggestion ?? "",
        })
      })

      console.log("[Canvas] mapped issues:", mapped.length)
      setAnalysisIssues(mapped)
      setIsAnalyzing(false)
      setShowAnalysisToast(true)
      setTimeout(() => setShowAnalysisToast(false), 2000)
    } catch (err: unknown) {
      console.error("[Canvas] Analysis failed:", err)
      if (err instanceof Error) {
        setError(err.message || "Phân tích thất bại")
      } else {
        setError("Phân tích thất bại")
      }
      setAnalysisIssues([])
      setAnalysisActive(false)
      setIsAnalyzing(false)
    }
  }

  // ✅ GIỜ: click bên Issues Found sẽ gọi editor.applyIssueFix(issue)
  const handleSuggestionClick = (issue: AnalysisIssue) => {
    editorRef.current?.applyIssueFix(issue)
  }

  // Được gọi từ RichTextEditor sau khi đã sửa xong trong content
  const handleSuggestionAccept = (issueId: string) => {
    setAppliedSuggestions(prev => [...prev, issueId])
    setAnalysisIssues(prev => prev.filter(i => i.id !== issueId))
  }

  if (!docId) {
    return (
      <div className="p-8 space-y-6 text-center">
        <div>
          <h1 className="text-3xl font-semibold text-[#37322F] mb-2">Writing Canvas</h1>
          <p className="text-[#605A57] mb-6">Please select a document to start writing</p>
          <Button
            onClick={() => handleNavigation("/dashboard/documents")}
            className="bg-[#37322F] hover:bg-[#37322F]/90"
          >
            <ChevronLeft className="h-4 w-4 mr-2" />
            Back to Documents
          </Button>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="p-8 space-y-6 flex justify-center items-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-[#37322F]" />
      </div>
    )
  }

  return (
    <div className="p-8 space-y-6">
      {isAnalyzing && (
        <div className="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Đang phân tích văn bản của bạn, vui lòng chờ...</span>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Toast thông báo đã phân tích xong */}
      {showAnalysisToast && (
        <div className="fixed bottom-6 right-6 z-50 flex items-start gap-3 rounded-lg border bg-white px-4 py-3 shadow-lg text-sm max-w-sm">
          <div className="mt-0.5">
            <Sparkles className="h-4 w-4 text-emerald-600" />
          </div>
          <div className="flex-1">
            <p className="font-medium text-[#37322F]">Phân tích hoàn tất</p>
            
          </div>
          <button
            className="ml-2 text-gray-400 hover:text-gray-600"
            onClick={() => setShowAnalysisToast(false)}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-[#37322F] mb-2">Writing Canvas</h1>
          <p className="text-[#605A57]">
            Editing: <span className="font-medium">{currentDoc?.title}</span>
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            className="gap-2 bg-transparent"
            onClick={handleSave}
            disabled={isSaving || !hasUnsavedChanges}
          >
            {isSaving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : saveSuccess ? (
              <Check className="h-4 w-4 text-green-600" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            {isSaving ? "Saving..." : saveSuccess ? "Saved!" : "Save Draft"}
          </Button>
          <Button
            onClick={handleAnalyze}
            disabled={isAnalyzing}
            className={`gap-2 ${
              analysisActive ? "bg-blue-600 hover:bg-blue-700" : "bg-[#37322F] hover:bg-[#37322F]/90"
            }`}
          >
            {isAnalyzing ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                {analysisActive ? "Analysis Active" : "Analyze"}
              </>
            )}
          </Button>
          <Button className="gap-2 bg-[#37322F] hover:bg-[#37322F]/90" onClick={handleExport}>
            <Download className="h-4 w-4" />
            Export
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <RichTextEditor
            ref={editorRef}
            onContentChange={setEditorContent}
            initialContent={currentDoc?.content || ""}
            analysisActive={analysisActive}
            analysisIssues={analysisIssues}
            onSuggestionAccept={handleSuggestionAccept}
          />
        </div>

        <div className="space-y-4">
          {analysisActive && analysisIssues.length > 0 ? (
            <AnalysisIssuesOverlay issues={analysisIssues} onSuggestionClick={handleSuggestionClick} />
          ) : (
            <ContextSetup goal={currentGoal} onApply={handleContextApply} />
          )}
        </div>
      </div>
    </div>
  )
}
