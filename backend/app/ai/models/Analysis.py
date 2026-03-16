"""
Analysis - Gộp 4 Subtasks + Spelling
========================================
1. Contradictions (Mâu thuẫn logic)
2. Undefined Terms (Thuật ngữ chưa định nghĩa)
3. Unsupported Claims (Luận điểm thiếu chứng cứ)
4. Logical Jumps (Nhảy logic)
5. Spelling Errors (Lỗi chính tả EN + VI)

Mục tiêu:
- Phân tích toàn diện văn bản trong một lần gọi API duy nhất.
- ƯU TIÊN: Spell & Term Normalization (Surface Quality) chạy trước,
  sau đó mới phân tích các vấn đề logic / khái niệm.
"""
import sys

def check_heavy_libraries():
    # Danh sách các thư viện bạn muốn loại bỏ hoàn toàn
    forbidden_libs = ['torch', 'transformers', 'sentence_transformers', 'numpy']
    
    found_libs = []
    for lib in forbidden_libs:
        if lib in sys.modules:
            found_libs.append(lib)
    
    if found_libs:
        print(f"❌ CẢNH BÁO: Thư viện nặng vẫn đang bị load: {found_libs}")
        return False
    else:
        print("✅ TUYỆT VỜI: Không có thư viện nặng nào được load trong RAM.")
        return True

# Chạy test này sau khi bạn đã thực hiện các lệnh import chính của project
# Ví dụ:
# from app.ai.models.Analysis import analyze_document
# check_heavy_libraries()
from typing import Dict, Any, List, Optional
import json
import os
from datetime import datetime

import google.generativeai as genai
from google.generativeai import GenerationConfig
from dotenv import load_dotenv

from .promptStore import prompt_analysis, prompt_analysis_vi
from .term_normalizer import NormalizationResult, normalize_text

# -------------------------------------------------------------------
# Gemini config: đọc từ biến môi trường (.env backend)
# -------------------------------------------------------------------

load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

genai.configure(api_key=GEMINI_API_KEY)

# -------------------------------------------------------------------
# JSON schema cho Gemini
# -------------------------------------------------------------------

RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "analysis_metadata": {
            "type": "object",
            "properties": {
                "analyzed_at": {"type": "string"},
                "writing_type": {"type": "string"},
                "total_paragraphs": {"type": "integer"},
                "total_sentences": {"type": "integer"},
            },
            "required": [
                "analyzed_at",
                "writing_type",
                "total_paragraphs",
                "total_sentences",
            ],
        },
        "contradictions": {
            "type": "object",
            "properties": {
                "total_found": {"type": "integer"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "sentence1": {"type": "string"},
                            "sentence2": {"type": "string"},
                            "sentence1_location": {"type": "string"},
                            "sentence2_location": {"type": "string"},
                            "contradiction_type": {"type": "string"},
                            "severity": {"type": "string"},
                            "explanation": {"type": "string"},
                            "suggestion": {"type": "string"},
                        },
                        "required": ["sentence1", "sentence2", "explanation"],
                    },
                },
            },
            "required": ["total_found", "items"],
        },
        "undefined_terms": {
            "type": "object",
            "properties": {
                "total_found": {"type": "integer"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "term": {"type": "string"},
                            "first_appeared": {"type": "string"},
                            "context_snippet": {"type": "string"},
                            "is_defined": {"type": "boolean"},
                            "reason": {"type": "string"},
                            "suggestion": {"type": "string"},
                        },
                        "required": ["term", "reason"],
                    },
                },
            },
            "required": ["total_found", "items"],
        },
        "unsupported_claims": {
            "type": "object",
            "properties": {
                "total_found": {"type": "integer"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "claim": {"type": "string"},
                            "location": {"type": "string"},
                            "status": {"type": "string"},
                            "claim_type": {"type": "string"},
                            "reason": {"type": "string"},
                            "surrounding_context": {"type": "string"},
                            "suggestion": {"type": "string"},
                        },
                        "required": ["claim", "reason"],
                    },
                },
            },
            "required": ["total_found", "items"],
        },
        "logical_jumps": {
            "type": "object",
            "properties": {
                "total_found": {"type": "integer"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "from_location": {"type": "string"},
                            "to_location": {"type": "string"},
                            "from_paragraph_summary": {"type": "string"},
                            "to_paragraph_summary": {"type": "string"},
                            "coherence_score": {"type": "number"},
                            "flag": {"type": "string"},
                            "severity": {"type": "string"},
                            "explanation": {"type": "string"},
                            "suggestion": {"type": "string"},
                        },
                        "required": [
                            "from_location",
                            "to_location",
                            "coherence_score",
                            "explanation",
                        ],
                    },
                },
            },
            "required": ["total_found", "items"],
        },
        # Spelling errors (EN + VI) do Gemini + rule-based trả về
        "spelling_errors": {
            "type": "object",
            "properties": {
                "total_found": {"type": "integer"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "original": {"type": "string"},
                            "suggested": {"type": "string"},
                            "start_pos": {"type": "integer"},
                            "end_pos": {"type": "integer"},
                            "language": {"type": "string"},
                            "reason": {"type": "string"},
                        },
                        "required": ["original", "suggested"],
                    },
                },
            },
            "required": ["total_found", "items"],
        },
        "summary": {
            "type": "object",
            "properties": {
                "total_issues": {"type": "integer"},
                "critical_issues": {"type": "integer"},
                "document_quality_score": {"type": "integer"},
                "key_recommendations": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": [
                "total_issues",
                "critical_issues",
                "document_quality_score",
                "key_recommendations",
            ],
        },
    },
    "required": [
        "analysis_metadata",
        "contradictions",
        "undefined_terms",
        "unsupported_claims",
        "logical_jumps",
        "spelling_errors",
        "summary",
    ],
}


def analyze_document(
    context: Dict[str, Any],
    content: str,
    language: str = "en",
    mode: str = "fast",  # chỉ để log, không đổi model
) -> Dict[str, Any]:
    """
    Phân tích toàn diện văn bản với 5 subtasks trong một lần gọi.
    (4 logic + 1 spelling)

    Flow ưu tiên:
    1) Spell & Term Normalization (rule-based) → phát hiện lỗi chính tả rõ ràng trước.
    2) Gọi Gemini unified analysis (5 subtasks).
    3) Merge lỗi chính tả rule-based vào block spelling_errors của kết quả cuối.
    """

    selected_model = GEMINI_MODEL  # luôn dùng 1 model Gemini 2.5

    result: Dict[str, Any] = {
        "success": False,
        "content": content,  # giữ nguyên văn bản gốc cho FE
        "context": context,
        "analysis_metadata": {
            "analyzed_at": datetime.utcnow().isoformat(),
            "writing_type": context.get("writing_type", "Document") if context else "Document",
            "total_paragraphs": 0,
            "total_sentences": 0,
            "model": selected_model,
            "mode_used": mode,
        },
        "contradictions": {"total_found": 0, "items": []},
        "undefined_terms": {"total_found": 0, "items": []},
        "unsupported_claims": {"total_found": 0, "items": []},
        "logical_jumps": {"total_found": 0, "items": []},
        "spelling_errors": {"total_found": 0, "items": []},
        "summary": {
            "total_issues": 0,
            "critical_issues": 0,
            "document_quality_score": 0,
            "key_recommendations": [],
        },
        "metadata": {
            "error": None,
            "normalization": {},
            "spelling_errors_rule_based": [],
        },
    }

    try:
        # -------- Validate input --------
        if not content or not content.strip():
            result["metadata"]["error"] = "Content is empty"
            return result

        if not context or not isinstance(context, Dict):
            result["metadata"]["error"] = "Invalid context format"
            return result

        if language not in ["en", "vi"]:
            result["metadata"]["error"] = f"Invalid language '{language}'. Use 'en' or 'vi'."
            return result

        # -------- 1) SPELL & TERM NORMALIZATION (ưu tiên chạy TRƯỚC) --------
        norm: NormalizationResult = normalize_text(content, language=language)

        # Đưa thông tin normalization vào metadata
        result["metadata"]["normalization"] = {
            "changed": norm.normalized_text != norm.original_text,
            "total_spelling_corrections": len(getattr(norm, "spelling_corrections", [])),
            "total_term_mappings": len(getattr(norm, "term_mappings", [])),
        }
        result["metadata"]["spelling_errors_rule_based"] = getattr(
            norm, "spelling_corrections", []
        )

        if norm.normalized_text != norm.original_text:
            print(
                f"[Normalization] Text normalized (light) "
                f"(spelling_corrections={result['metadata']['normalization']['total_spelling_corrections']}, "
                f"term_mappings={result['metadata']['normalization']['total_term_mappings']})"
            )

        # DÙ đã normalize, vẫn feed VĂN BẢN GỐC vào Gemini
        normalized_content_for_llm = content

        # -------- 2) Build prompt theo ngôn ngữ --------
        if language == "vi":
            prompt = prompt_analysis_vi(context, normalized_content_for_llm)
            print("Sử dụng prompt tiếng Việt...")
        else:
            prompt = prompt_analysis(context, normalized_content_for_llm)
            print("Using English prompt...")

        result["analysis_metadata"]["language"] = language

        # -------- 3) Gọi Gemini với cấu hình phù hợp ngôn ngữ --------
        #
        # EN: dùng response_schema đầy đủ (ổn định, ít biến thể).
        # VI: bỏ response_schema để Gemini tự do trả thêm spelling_errors,
        #     vì tiếng Việt + mix EN-VI nhiều, schema cứng quá thì model hay skip block này.
# -------- 3) Gọi Gemini với cấu hình phù hợp --------
        # BẮT BUỘC dùng response_schema cho cả Tiếng Anh và Tiếng Việt 
        # để ép AI không được phép lười biếng và lướt qua các subtasks.
        
        generation_config = GenerationConfig(
            response_mime_type="application/json",
            response_schema=RESPONSE_SCHEMA,
        )

        model = genai.GenerativeModel(
            selected_model,
            generation_config=generation_config,
        )

        model = genai.GenerativeModel(
            selected_model,
            generation_config=generation_config,
        )

        lang_msg = (
            "Đang phân tích văn bản toàn diện (5 nhiệm vụ: 4 logic + spelling)..."
            if language == "vi"
            else "Analyzing document comprehensively (5 subtasks: 4 logic + spelling)..."
        )
        print(f"{lang_msg} | model={selected_model} | mode_flag={mode}")

        last_error: Optional[Exception] = None
        llm_result: Optional[Dict[str, Any]] = None
        response_text: str = ""

        for attempt in range(2):
            try:
                response = model.generate_content(prompt)
                response_text = (response.text or "").strip()
                llm_result = json.loads(response_text)
                break
            except json.JSONDecodeError as e:
                last_error = e
                print(f"❌ JSON Parse Error (attempt {attempt + 1}): {e}")
                print(f"Response text (first 500 chars): {response_text[:500]}...")

        if llm_result is None:
            result["metadata"]["error"] = (
                f"Failed to parse LLM response as JSON after retries: {last_error}"
            )
            return result

        result["success"] = True

        # -------- 4) Merge kết quả từ LLM vào result chuẩn --------

        # analysis_metadata
        if "analysis_metadata" in llm_result:
            result["analysis_metadata"].update(llm_result["analysis_metadata"])

        # contradictions
        if "contradictions" in llm_result:
            result["contradictions"] = llm_result["contradictions"] or {
                "total_found": 0,
                "items": [],
            }
            if "total_found" not in result["contradictions"]:
                result["contradictions"]["total_found"] = len(
                    result["contradictions"].get("items", []) or []
                )

        # undefined_terms
        if "undefined_terms" in llm_result:
            result["undefined_terms"] = llm_result["undefined_terms"] or {
                "total_found": 0,
                "items": [],
            }
            if "total_found" not in result["undefined_terms"]:
                result["undefined_terms"]["total_found"] = len(
                    result["undefined_terms"].get("items", []) or []
                )

        # unsupported_claims
        if "unsupported_claims" in llm_result:
            result["unsupported_claims"] = llm_result["unsupported_claims"] or {
                "total_found": 0,
                "items": [],
            }
            if "total_found" not in result["unsupported_claims"]:
                result["unsupported_claims"]["total_found"] = len(
                    result["unsupported_claims"].get("items", []) or []
                )

        # logical_jumps
        if "logical_jumps" in llm_result:
            result["logical_jumps"] = llm_result["logical_jumps"] or {
                "total_found": 0,
                "items": [],
            }
            if "total_found" not in result["logical_jumps"]:
                result["logical_jumps"]["total_found"] = len(
                    result["logical_jumps"].get("items", []) or []
                )

        # spelling_errors từ Gemini (có thể trống)
        if "spelling_errors" in llm_result:
            result["spelling_errors"] = llm_result["spelling_errors"] or {
                "total_found": 0,
                "items": [],
            }
            if "total_found" not in result["spelling_errors"]:
                result["spelling_errors"]["total_found"] = len(
                    result["spelling_errors"].get("items", []) or []
                )

        # ======================================================================
        # -------- 4.5) BỘ LỌC RANH GIỚI: Unsupported Claims vs Contradictions
        # Loại bỏ Unsupported Claim nếu nó đã nằm trong Contradictions
        # ======================================================================
        # if result["unsupported_claims"]["items"] and result["contradictions"]["items"]:
        #     valid_claims = []
            
        #     # Lấy tất cả các câu đã bị đánh lỗi mâu thuẫn
        #     contra_texts = []
        #     for c in result["contradictions"]["items"]:
        #         contra_texts.append(c.get("sentence1", "").strip())
        #         contra_texts.append(c.get("sentence2", "").strip())
                
        #     for claim_item in result["unsupported_claims"]["items"]:
        #         claim_text = claim_item.get("claim", "").strip()
                
        #         # Kiểm tra xem claim này có phải là một phần của câu mâu thuẫn không
        #         is_overlap = False
        #         for c_text in contra_texts:
        #             # Nếu luận điểm nằm trong câu mâu thuẫn, hoặc câu mâu thuẫn nằm trong luận điểm
        #             if claim_text and c_text and (claim_text in c_text or c_text in claim_text):
        #                 is_overlap = True
        #                 break
                
        #         # Chỉ giữ lại những claim KHÔNG bị trùng lặp với mâu thuẫn
        #         if not is_overlap:
        #             valid_claims.append(claim_item)
            
        #     # Cập nhật lại danh sách Unsupported Claims
        #     result["unsupported_claims"]["items"] = valid_claims
        #     result["unsupported_claims"]["total_found"] = len(valid_claims)
        # # ======================================================================

        # -------- 5) MERGE lỗi chính tả rule-based vào spelling_errors chính --------
        try:
            rb_corrections = norm.spelling_corrections or []
        except Exception:
            rb_corrections = []

        if rb_corrections:
            sp_block = result.get("spelling_errors") or {"total_found": 0, "items": []}
            items = sp_block.get("items") or []

            # Đã sửa: Chỉ lọc trùng dựa trên chữ gốc (original)
            seen_keys = {(it.get("original") or "").lower() for it in items}

            for corr in rb_corrections:
                original_text = (corr.get("original") or "").lower()
                if original_text in seen_keys:
                    continue

                items.append(
                    {
                        "original": corr.get("original", ""),
                        "suggested": corr.get("normalized", ""),
                        "start_pos": corr.get("start_pos", -1),
                        "end_pos": corr.get("end_pos", -1),
                        "language": language,
                        "reason": corr.get("reason", "rule_based_detection"),
                    }
                )
                seen_keys.add(original_text)

            sp_block["items"] = items
            sp_block["total_found"] = len(items)
            result["spelling_errors"] = sp_block

        # -------- 6) Summary: tính lại total_issues cho chắc ăn --------
        total_issues = (
            result["contradictions"]["total_found"]
            + result["undefined_terms"]["total_found"]
            + result["unsupported_claims"]["total_found"]
            + result["logical_jumps"]["total_found"]
            + result["spelling_errors"]["total_found"]
        )

        if not result.get("summary"):
            result["summary"] = {
                "total_issues": total_issues,
                "critical_issues": 0,
                "document_quality_score": 0,
                "key_recommendations": [],
            }
        else:
            result["summary"]["total_issues"] = total_issues
            result["summary"].setdefault("critical_issues", 0)
            result["summary"].setdefault("document_quality_score", 0)
            result["summary"].setdefault("key_recommendations", [])

        print(
            f"✅ Phân tích hoàn tất. "
            f"Tổng issues: {result['summary'].get('total_issues', 0)}"
        )

    except Exception as e:
        result["metadata"]["error"] = f"Error during analysis: {str(e)}"
        print(f"❌ Error in analyze_document: {e}")

    return result


def get_analysis_summary(analysis_result: Dict[str, Any]) -> str:
    """
    Tạo text summary từ kết quả phân tích (debug / log).
    """
    if not analysis_result.get("success"):
        return f"Analysis failed: {analysis_result.get('metadata', {}).get('error', 'Unknown error')}"

    lines: List[str] = []
    lines.append("=" * 80)
    lines.append("DOCUMENT ANALYSIS SUMMARY")
    lines.append("=" * 80)

    meta = analysis_result.get("analysis_metadata", {})
    lines.append(f"\nWriting Type: {meta.get('writing_type', 'N/A')}")
    lines.append(f"Mode Flag: {meta.get('mode_used', 'N/A')}")
    lines.append(f"Model: {meta.get('model', 'N/A')}")
    lines.append(f"Total Paragraphs: {meta.get('total_paragraphs', 0)}")
    lines.append(f"Total Sentences: {meta.get('total_sentences', 0)}")
    lines.append(f"Analyzed At: {meta.get('analyzed_at', 'N/A')}")

    summary = analysis_result.get("summary", {})
    lines.append(
        f"\n📊 OVERALL QUALITY SCORE: {summary.get('document_quality_score', 0)}/100"
    )
    lines.append(f"Total Issues Found: {summary.get('total_issues', 0)}")
    lines.append(f"Critical Issues: {summary.get('critical_issues', 0)}")

    # Contradictions
    contra = analysis_result.get("contradictions", {})
    lines.append(f"\n🔴 CONTRADICTIONS: {contra.get('total_found', 0)} found")
    if contra.get("items"):
        for item in contra["items"][:3]:
            lines.append(
                f"  - {item.get('sentence1', '')[:60]}... ↔ "
                f"{item.get('sentence2', '')[:60]}..."
            )

    # Undefined Terms
    terms = analysis_result.get("undefined_terms", {})
    lines.append(f"\n📚 UNDEFINED TERMS: {terms.get('total_found', 0)} found")
    if terms.get("items"):
        for item in terms["items"][:5]:
            lines.append(f"  - {item.get('term', 'N/A')}")

    # Unsupported Claims
    claims = analysis_result.get("unsupported_claims", {})
    lines.append(f"\n⚠️  UNSUPPORTED CLAIMS: {claims.get('total_found', 0)} found")
    if claims.get("items"):
        for item in claims["items"][:3]:
            lines.append(f"  - {item.get('claim', 'N/A')[:70]}...")

    # Logical Jumps
    jumps = analysis_result.get("logical_jumps", {})
    lines.append(f"\n🔀 LOGICAL JUMPS: {jumps.get('total_found', 0)} found")
    if jumps.get("items"):
        for item in jumps["items"]:
            lines.append(
                f"  - {item.get('from_location', '?')} → "
                f"{item.get('to_location', '?')} "
                f"(coherence: {item.get('coherence_score', 0)})"
            )

    # Spelling errors
    spell = analysis_result.get("spelling_errors", {})
    lines.append(f"\n✏️  SPELLING ERRORS: {spell.get('total_found', 0)} found")
    if spell.get("items"):
        for item in spell["items"][:5]:
            lines.append(
                f"  - {item.get('original', '')} → {item.get('suggested', '')} "
                f"({item.get('language', 'unknown')})"
            )

    # Key Recommendations
    if summary.get("key_recommendations"):
        lines.append("\n💡 KEY RECOMMENDATIONS:")
        for i, rec in enumerate(summary["key_recommendations"], 1):
            lines.append(f"  {i}. {rec}")

    lines.append("\n" + "=" * 80)
    return "\n".join(lines)