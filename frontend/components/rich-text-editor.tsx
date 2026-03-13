"use client"

import { useEditor, EditorContent } from "@tiptap/react"
import type { ChainedCommands } from "@tiptap/react"
import StarterKit from "@tiptap/starter-kit"
import Highlight from "@tiptap/extension-highlight"
import Underline from "@tiptap/extension-underline"
import { TextStyle } from "@tiptap/extension-text-style"
import Color from "@tiptap/extension-color"
import FontFamily from "@tiptap/extension-font-family"
import Link from "@tiptap/extension-link"
import TaskList from "@tiptap/extension-task-list"
import TaskItem from "@tiptap/extension-task-item"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Bold,
  Italic,
  Undo2,
  Redo2,
  Underline as UnderlineIcon,
  Strikethrough,
  Link2,
  Highlighter,
  Palette,
  ChevronDown,
  List,
  ListOrdered,
  ListTodo,
  Type,
  Heading1,
  Heading2,
  Heading3,
  Minus,
} from "lucide-react"
import type { LucideIcon } from "lucide-react"
import React, {
  useEffect,
  useState,
  forwardRef,
  useImperativeHandle,
  type ForwardedRef,
} from "react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { cn } from "@/lib/utils"

export type AnalysisIssueType =
  | "spelling_error"
  | "undefined_term"
  | "unsupported_claim"
  | "logical_jump"
  | "contradiction"

export type AnalysisIssue = {
  id: string
  type: AnalysisIssueType
  startPos: number
  endPos: number
  text: string
  message?: string
  suggestion?: string
}

interface RichTextEditorProps {
  onContentChange?: (content: string) => void
  initialContent?: string
  analysisActive?: boolean
  analysisIssues?: AnalysisIssue[]
  onSuggestionAccept?: (issueId: string) => void
}

export type RichTextEditorHandle = {
  applyIssueFix: (issue: AnalysisIssue) => void
}

const issueTypeLabel: Record<AnalysisIssueType, string> = {
  spelling_error: "Spelling Error",
  undefined_term: "Undefined Term",
  unsupported_claim: "Unsupported Claim",
  logical_jump: "Logical Jump",
  contradiction: "Contradiction",
}

/**
 * Màu highlight cho từng loại lỗi – dùng inline style để chắc chắn không bị Tailwind / prose override
 */
const issueTypeStyle: Record<AnalysisIssueType, string> = {
  spelling_error:
    "background-color:#FEF3C7;color:#92400E;text-decoration:underline;text-decoration-color:#F59E0B;text-decoration-thickness:2px;",
  undefined_term:
    "background-color:#F3E8FF;color:#6B21A8;text-decoration:underline;text-decoration-color:#A855F7;text-decoration-thickness:2px;",
  unsupported_claim:
    "background-color:#FFE4E6;color:#9F1239;text-decoration:underline;text-decoration-color:#FB7185;text-decoration-thickness:2px;",
  logical_jump:
    "background-color:#DBEAFE;color:#1D4ED8;text-decoration:underline;text-decoration-color:#60A5FA;text-decoration-thickness:2px;",
  contradiction:
    "background-color:#FFEDD5;color:#C2410C;text-decoration:underline;text-decoration-color:#FB923C;text-decoration-thickness:2px;",
}

function escapeRegExp(str: string) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
}

const InnerRichTextEditor = (
  {
    onContentChange,
    initialContent,
    analysisActive = false,
    analysisIssues = [],
    onSuggestionAccept,
  }: RichTextEditorProps,
  ref: ForwardedRef<RichTextEditorHandle>,
) => {
  const [selectedBlock, setSelectedBlock] = useState("Text")
  const [selectedFont, setSelectedFont] = useState("Inter")
  const [selectedSize, setSelectedSize] = useState<FontSizeLabel>("Medium")
  const [fontColor, setFontColor] = useState("#37322F")

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: {
          levels: [1, 2, 3],
        },
      }),
      Highlight.configure({ multicolor: true }),
      Underline,
      TextStyle,
      Color.configure({ types: ["textStyle"] }),
      FontFamily.configure({ types: ["textStyle"] }),
      Link.configure({ openOnClick: false, autolink: true, linkOnPaste: true }),
      TaskList.configure({ HTMLAttributes: { class: "not-prose" } }),
      TaskItem.configure({ nested: true }),
    ],
    content: initialContent || "<p>Start typing your content here...</p>",
    immediatelyRender: false,
    onUpdate: ({ editor }) => {
      onContentChange?.(editor.getHTML())
    },
  })

  const fontSizes: Record<string, string> = {
    Smaller: "0.875rem",
    Small: "0.9375rem",
    Medium: "1rem",
    Large: "1.125rem",
    "Extra Large": "1.25rem",
  }

  type FontSizeLabel = keyof typeof fontSizes

  // Sync toolbar state
  useEffect(() => {
    if (!editor) return

    const syncToolbarState = () => {
      const nextBlockLabel = editor.isActive("heading", { level: 1 })
        ? "Heading 1"
        : editor.isActive("heading", { level: 2 })
          ? "Heading 2"
          : editor.isActive("heading", { level: 3 })
            ? "Heading 3"
            : editor.isActive("taskList")
              ? "Todo list"
            : editor.isActive("bulletList")
              ? "Bullet list"
              : editor.isActive("orderedList")
                ? "Numbered list"
                : "Text"

      setSelectedBlock(prev => (prev === nextBlockLabel ? prev : nextBlockLabel))

      const textStyleAttrs = editor.getAttributes("textStyle") as {
        fontFamily?: string
        fontSize?: string
        color?: string
      }

      const nextFont = textStyleAttrs.fontFamily || "Inter"
      setSelectedFont(prev => (prev === nextFont ? prev : nextFont))

      const fontSizeEntry = (Object.entries(fontSizes) as [FontSizeLabel, string][])
        .find(([, value]) => value === textStyleAttrs.fontSize)
      const nextSize = fontSizeEntry ? fontSizeEntry[0] : "Medium"
      setSelectedSize(prev => (prev === nextSize ? prev : nextSize))

      const nextColor = textStyleAttrs.color || "#37322F"
      setFontColor(prev => (prev === nextColor ? prev : nextColor))
    }

    editor.on("selectionUpdate", syncToolbarState)
    editor.on("transaction", syncToolbarState)
    syncToolbarState()

    return () => {
      editor.off("selectionUpdate", syncToolbarState)
      editor.off("transaction", syncToolbarState)
    }
  }, [editor])

  // Hàm dùng chung để apply sửa lỗi cho 1 issue (cho cả click trong editor & click ở sidebar)
  const applyIssueFix = (issue: AnalysisIssue) => {
    if (!editor) return

    let html = editor.getHTML()

    // Tìm span tương ứng với issue.id
    const spanRegex = new RegExp(
      `<span[^>]*class="[^"]*lg-issue[^"]*"[^>]*data-issue-id="${escapeRegExp(
        issue.id,
      )}"[^>]*>([\\s\\S]*?)<\\/span>`,
      "m",
    )

    const innerText = issue.text || ""

    const makeReplacement = () => {
      // nếu không có suggestion thì chỉ bỏ highlight, giữ nguyên text gốc
      if (!issue.suggestion || !innerText) {
        return innerText
      }

      switch (issue.type) {
        case "spelling_error":
          // thay luôn bằng từ đúng
          return issue.suggestion
        case "undefined_term":
          // thêm định nghĩa ngay sau từ
          return `${innerText} (${issue.suggestion})`
        case "unsupported_claim":
          // nối thêm câu dẫn chứng
          return `${innerText}. ${issue.suggestion}`
        case "logical_jump":
          // thêm câu nối logic
          return `${innerText}. ${issue.suggestion}`
        case "contradiction":
          // chỉnh lại bằng phiên bản gợi ý
          return issue.suggestion
        default:
          return innerText
      }
    }

    const replacement = makeReplacement()

    html = html.replace(spanRegex, replacement)
    editor.commands.setContent(html, false)
    onContentChange?.(html)
    onSuggestionAccept?.(issue.id)
  }

  // Expose method cho parent (CanvasPage) dùng
  useImperativeHandle(
    ref,
    () => ({
      applyIssueFix,
    }),
    [editor, onContentChange, onSuggestionAccept],
  )

  // Gắn highlight vào HTML khi có analysisActive
  useEffect(() => {
    if (!editor) return

    // Bỏ hết highlight cũ (span.lg-issue) trước – regex tolerant hơn
    const currentHTML = editor.getHTML()
    const cleaned = currentHTML.replace(
      /<span[^>]*class="[^"]*lg-issue[^"]*"[^>]*>([\s\S]*?)<\/span>/g,
      "$1",
    )

    if (cleaned !== currentHTML) {
      editor.commands.setContent(cleaned, false)
    }

    if (!analysisActive || !analysisIssues.length) {
      return
    }

    let html = editor.getHTML()

    // Sort để text dài thay trước, tránh lồng nhau
    const sortedIssues = [...analysisIssues].sort(
      (a, b) => (b.text?.length || 0) - (a.text?.length || 0),
    )

    sortedIssues.forEach(issue => {
      if (!issue.text) return
      const escaped = escapeRegExp(issue.text)
      const label = issueTypeLabel[issue.type]
      const style = issueTypeStyle[issue.type]
      const regex = new RegExp(`(${escaped})`, "g")

      // ❗ span này phải bắt đầu với `<span class="lg-issue...` để regex phía trên nhận ra
      html = html.replace(
        regex,
        `<span class="lg-issue issue-highlight cursor-pointer rounded px-0.5" data-issue-id="${issue.id}" data-issue-type="${label}" style="${style}">$1</span>`,
      )
    })

    editor.commands.setContent(html, false)
  }, [analysisActive, analysisIssues, editor])

  if (!editor) {
    return null
  }

  type ExtendedChain = ChainedCommands & {
    setFontFamily: (fontFamily: string) => ExtendedChain
    unsetFontFamily: () => ExtendedChain
    setTextStyle: (attributes: Record<string, string>) => ExtendedChain
    unsetTextStyle: () => ExtendedChain
    setColor: (color: string) => ExtendedChain
    toggleUnderline: () => ExtendedChain
    toggleTaskList: () => ExtendedChain
  }

  const focusChain = () => editor.chain().focus() as ExtendedChain

  const handleBlockSelect = (label: string, action: () => boolean) => {
    if (analysisActive) return
    const executed = action()
    if (executed) {
      setSelectedBlock(label)
    }
  }

  const handleFontFamilyChange = (family: string) => {
    if (analysisActive) return
    if (!family || family === "Inter") {
      focusChain().unsetFontFamily().run()
      setSelectedFont("Inter")
      return
    }

    focusChain().setFontFamily(family).run()
    setSelectedFont(family)
  }

  const handleFontSizeChange = (label: FontSizeLabel) => {
    if (analysisActive) return
    const value = fontSizes[label]
    focusChain().setTextStyle({ fontSize: value }).run()
    setSelectedSize(label)
  }

  const handleSetLink = () => {
    if (analysisActive) return
    const previousUrl = editor.getAttributes("link").href as string | undefined
    const url = window.prompt("Enter URL", previousUrl || "")
    if (url === null) return
    if (url === "") {
      editor.chain().focus().unsetLink().run()
      return
    }
    editor.chain().focus().extendMarkRange("link").setLink({ href: url }).run()
  }

  const renderBlockMenuItem = (label: string, Icon: LucideIcon, action: () => boolean) => (
    <DropdownMenuItem
      onClick={() => handleBlockSelect(label, action)}
      disabled={analysisActive}
      className={cn("flex items-center gap-2 text-sm", selectedBlock === label && "bg-muted")}
    >
      <Icon className="h-4 w-4" />
      <span>{label}</span>
    </DropdownMenuItem>
  )

  const handleColorChange = (value: string) => {
    if (analysisActive) return
    focusChain().setColor(value).run()
    setFontColor(value)
  }

  // Auto-fix khi click vào đoạn gạch chân trong editor
  const handleEditorClick = (e: any) => {
    const target = (e.target as HTMLElement).closest(".lg-issue") as HTMLElement | null
    if (!target) return

    const issueId = target.getAttribute("data-issue-id")
    if (!issueId) return

    const issue = analysisIssues.find(i => i.id === issueId)
    if (!issue) return

    applyIssueFix(issue)
  }

  return (
    <Card className="border-[rgba(55,50,47,0.12)] min-h-[600px] relative">
      <CardHeader className="border-b border-[rgba(55,50,47,0.12)]">
        <div className="flex items-center justify-between mb-4">
          <CardTitle className="text-lg">Document Editor</CardTitle>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {/* Block type */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                className="h-9 bg-transparent min-w-[120px] justify-between"
                disabled={analysisActive}
              >
                <span className="text-sm font-medium">{selectedBlock}</span>
                <ChevronDown className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-60">
              <DropdownMenuLabel className="text-[11px] tracking-wide text-muted-foreground">
                HIERARCHY
              </DropdownMenuLabel>
              {renderBlockMenuItem("Text", Type, () => focusChain().setParagraph().run())}
              {renderBlockMenuItem("Heading 1", Heading1, () => focusChain().toggleHeading({ level: 1 }).run())}
              {renderBlockMenuItem("Heading 2", Heading2, () => focusChain().toggleHeading({ level: 2 }).run())}
              {renderBlockMenuItem("Heading 3", Heading3, () => focusChain().toggleHeading({ level: 3 }).run())}

              <DropdownMenuSeparator />
              <DropdownMenuLabel className="text-[11px] tracking-wide text-muted-foreground">
                LISTS
              </DropdownMenuLabel>
              {renderBlockMenuItem("Bullet list", List, () => focusChain().toggleBulletList().run())}
              {renderBlockMenuItem("Numbered list", ListOrdered, () => focusChain().toggleOrderedList().run())}
              {renderBlockMenuItem("Todo list", ListTodo, () => focusChain().toggleTaskList().run())}

              <DropdownMenuSeparator />
              <DropdownMenuLabel className="text-[11px] tracking-wide text-muted-foreground">
                INSERT
              </DropdownMenuLabel>
              <DropdownMenuItem
                disabled={analysisActive}
                onClick={() => {
                  if (analysisActive) return
                  focusChain().setHorizontalRule().run()
                }}
                className="flex items-center gap-2 text-sm"
              >
                <Minus className="h-4 w-4" />
                <span>Divider</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Font family */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                className="h-9 bg-transparent min-w-[120px] justify-between"
                disabled={analysisActive}
              >
                <span className="text-sm font-medium">{selectedFont}</span>
                <ChevronDown className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-40">
              <DropdownMenuLabel>Sans Serif</DropdownMenuLabel>
              {["Inter", "Arial", "Helvetica"].map(font => (
                <DropdownMenuItem key={font} onClick={() => handleFontFamilyChange(font)}>
                  {font}
                </DropdownMenuItem>
              ))}
              <DropdownMenuSeparator />
              <DropdownMenuLabel>Serif</DropdownMenuLabel>
              {["Times New Roman", "Garamond", "Georgia"].map(font => (
                <DropdownMenuItem key={font} onClick={() => handleFontFamilyChange(font)}>
                  {font}
                </DropdownMenuItem>
              ))}
              <DropdownMenuSeparator />
              <DropdownMenuLabel>Monospace</DropdownMenuLabel>
              {["Courier", "Courier New"].map(font => (
                <DropdownMenuItem key={font} onClick={() => handleFontFamilyChange(font)}>
                  {font}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Font size */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                className="h-9 bg-transparent min-w-[120px] justify-between"
                disabled={analysisActive}
              >
                <span className="text-sm font-medium">{selectedSize}</span>
                <ChevronDown className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-36">
              {Object.keys(fontSizes).map(size => (
                <DropdownMenuItem
                  key={size}
                  onClick={() => handleFontSizeChange(size as FontSizeLabel)}
                >
                  {size}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          <div className="w-px bg-[rgba(55,50,47,0.12)]" />

          {/* Inline formatting */}
          <Button
            variant="outline"
            size="icon"
            className="h-9 w-9 bg-transparent"
            onClick={() => editor.chain().focus().toggleBold().run()}
            disabled={!editor.can().chain().focus().toggleBold().run() || analysisActive}
          >
            <Bold className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-9 w-9 bg-transparent"
            onClick={() => editor.chain().focus().toggleItalic().run()}
            disabled={!editor.can().chain().focus().toggleItalic().run() || analysisActive}
          >
            <Italic className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-9 w-9 bg-transparent"
            onClick={() => focusChain().toggleUnderline().run()}
            disabled={analysisActive}
          >
            <UnderlineIcon className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-9 w-9 bg-transparent"
            onClick={() => editor.chain().focus().toggleStrike().run()}
            disabled={analysisActive}
          >
            <Strikethrough className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-9 w-9 bg-transparent"
            onClick={() => editor.chain().focus().toggleHighlight().run()}
            disabled={analysisActive}
          >
            <Highlighter className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-9 w-9 bg-transparent"
            onClick={handleSetLink}
            disabled={analysisActive}
          >
            <Link2 className="h-4 w-4" />
          </Button>

          {/* Color picker */}
          <label
            className={cn(
              "relative h-9 w-9 cursor-pointer rounded-md border bg-white text-muted-foreground transition hover:bg-muted flex items-center justify-center",
              analysisActive && "pointer-events-none opacity-50",
            )}
          >
            <Palette className="h-4 w-4" />
            <input
              type="color"
              value={fontColor}
              onChange={event => handleColorChange(event.target.value)}
              className="absolute inset-0 opacity-0 cursor-pointer"
              disabled={analysisActive}
            />
          </label>

          {/* Undo / Redo */}
          <Button
            variant="outline"
            size="icon"
            className="h-9 w-9 bg-transparent"
            onClick={() => editor.chain().focus().undo().run()}
            disabled={!editor.can().chain().focus().undo().run() || analysisActive}
          >
            <Undo2 className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-9 w-9 bg-transparent"
            onClick={() => editor.chain().focus().redo().run()}
            disabled={!editor.can().chain().focus().redo().run() || analysisActive}
          >
            <Redo2 className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="p-6">
        <div
          className={cn(
            "min-h-[500px] p-4 rounded border focus-within:ring-2",
            analysisActive
              ? "bg-amber-50 border-amber-200 focus-within:ring-amber-300"
              : "bg-white border-[rgba(55,50,47,0.12)] focus-within:ring-[#37322F]/20",
          )}
          onClick={handleEditorClick}
        >
          <EditorContent editor={editor} className="prose prose-sm max-w-none text-[#37322F]" />
        </div>
      </CardContent>
    </Card>
  )
}

export const RichTextEditor = forwardRef<RichTextEditorHandle, RichTextEditorProps>(InnerRichTextEditor)
