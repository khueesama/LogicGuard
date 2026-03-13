"use client"

import React from "react"
import type { AnalysisIssue } from "@/components/rich-text-editor"
import { cn } from "@/lib/utils"

interface Props {
  issues: AnalysisIssue[]
  onSuggestionClick?: (issue: AnalysisIssue) => void
}

const typeLabel: Record<AnalysisIssue["type"], string> = {
  spelling_error: "Spelling Error",
  undefined_term: "Undefined Term",
  unsupported_claim: "Unsupported Claim",
  logical_jump: "Logical Jump",
  contradiction: "Contradiction",
}

const typeBadgeClass: Record<AnalysisIssue["type"], string> = {
  spelling_error: "bg-yellow-100 text-yellow-800",
  undefined_term: "bg-purple-100 text-purple-800",
  unsupported_claim: "bg-rose-100 text-rose-800",
  logical_jump: "bg-blue-100 text-blue-800",
  contradiction: "bg-orange-100 text-orange-800",
}

export function AnalysisIssuesOverlay({ issues, onSuggestionClick }: Props) {
  return (
    <div className="border border-[rgba(55,50,47,0.12)] rounded-xl bg-white h-full flex flex-col">
      {/* Header luôn cố định, không cuộn */}
      <div className="px-4 pt-4 pb-3 border-b border-[rgba(55,50,47,0.12)] sticky top-0 bg-white z-10">
        <h2 className="text-sm font-semibold text-[#37322F]">Issues Found</h2>
        <p className="text-xs text-[#807B78] mt-1">
          Bạn có thể click vào lỗi bên dưới hoặc click trực tiếp vào đoạn gạch chân trong văn bản để tự động sửa.
        </p>
      </div>

      {/* Danh sách lỗi cuộn bên dưới */}
      <div className="px-4 pb-4 pt-2 space-y-3 overflow-y-auto max-h-[540px]">
        {issues.map(issue => (
          <button
            key={issue.id}
            type="button"
            onClick={() => onSuggestionClick?.(issue)}
            className="w-full text-left rounded-lg border border-[rgba(55,50,47,0.12)] px-3 py-2.5 hover:bg-[rgba(55,50,47,0.02)] transition"
          >
            <div className="flex items-center justify-between gap-2 mb-1.5">
              <span
                className={cn(
                  "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide",
                  typeBadgeClass[issue.type],
                )}
              >
                {typeLabel[issue.type]}
              </span>
              <span className="text-[11px] text-[#A39D9A]">Click để sửa</span>
            </div>
            <p className="text-xs font-medium text-[#37322F] line-clamp-2">{issue.text}</p>
            {issue.suggestion && (
              <p className="mt-1.5 text-[11px] text-[#605A57]">
                <span className="font-semibold">Suggestion:&nbsp;</span>
                {issue.suggestion}
              </p>
            )}
          </button>
        ))}

        {issues.length === 0 && (
          <p className="text-xs text-[#807B78] italic">Không có lỗi nào được phát hiện.</p>
        )}
      </div>
    </div>
  )
}
