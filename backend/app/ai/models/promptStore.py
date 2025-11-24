"""
promptStore.py

Chứa các prompt dùng cho:
- Undefined Terms (EN-only endpoint)
- Unsupported Claims (EN-only endpoint)
- Unified Analysis EN (5 subtasks: spelling, unsupported claims,
  undefined terms, contradictions, logical jumps)
- Unified Analysis VI (5 subtasks tương tự, tiếng Việt)

Mục tiêu thiết kế (theo A2):

1️⃣ Tối ưu ĐỘ CHÍNH XÁC + TỐC ĐỘ:
   - Prompt không quá ngắn (dễ mơ hồ) cũng không quá dài (gây quá tải).
   - Số dòng ~vừa phải để Gemini hiểu rõ nhiệm vụ, không bị "tê liệt" vì prompt khổng lồ.

2️⃣ THỨ TỰ ƯU TIÊN 5 LỖI (tối ưu nhất về tốc độ + độ chính xác):
   1) Spelling Errors (EN + VI) – Ưu tiên số 1
   2) Unsupported Claims
   3) Undefined Terms
   4) Contradictions
   5) Logical Jumps

   → Trong unified prompt, luôn yêu cầu LLM:
     - Đọc & đánh dấu spelling trước.
     - Sau đó mới phân tích unsupported claims → undefined terms → contradictions → logical jumps.

3️⃣ KHÔNG DẠY CÁCH SỬA TỪNG BƯỚC
   - Không yêu cầu LLM đưa ra checklist / hướng dẫn chi tiết.
   - Chỉ cần trả JSON với:
        - spelling_errors: original, suggested (đáp án trực tiếp), reason ngắn.
        - unsupported_claims, undefined_terms, contradictions, logical_jumps: nêu lỗi + gợi ý ngắn, không "tutorial".

4️⃣ KHÔNG GỢI Ý CHUNG CHUNG, TRẢ VỀ “ĐÁP ÁN”
   - Spelling: luôn điền vào "suggested" dạng từ/cụm từ cuối cùng nên dùng.
   - Không yêu cầu giải thích kiểu “bạn nên làm A, B, C từng bước…”, chỉ nêu ngắn gọn lý do.

5️⃣ MIXED EN + VI
   - Spelling phải hiểu ngữ cảnh song ngữ, tránh nhầm:
       + typo → undefined_term
       + tên riêng / brand → spelling_errors
   - Undefined terms:
       + KHÔNG bắt những typo đã được gắn cờ trong spelling_errors.
       + KHÔNG bắt các từ tiếng Anh phổ thông xen trong câu tiếng Việt (nếu nghĩa quá rõ).

6️⃣ JSON OUTPUT
   - Unified prompt EN/VI phải trả đúng schema:
        {
          "analysis_metadata": {...},
          "contradictions": {...},
          "undefined_terms": {...},
          "unsupported_claims": {...},
          "logical_jumps": {...},
          "spelling_errors": {...},
          "summary": {...}
        }
   - Mọi trường total_found phải khớp với số lượng items.
"""

from typing import Dict, Any


# ==============================
# 1. UNDEFINED TERMS (EN ONLY)
# ==============================

def prompt_undefined_terms(context: Dict[str, Any], content: str) -> str:
    """
    Prompt phân tích THUẬT NGỮ CHƯA ĐỊNH NGHĨA (Undefined Terms) – tiếng Anh.
    Dùng riêng khi muốn gọi API chỉ cho undefined terms.

    Lưu ý:
    - Không đánh spelling ở đây (spelling đã làm ở chỗ khác).
    - KHÔNG coi lỗi chính tả / typo là undefined_terms.
    - Tập trung vào:
        + Tên mô hình, hệ thống, sản phẩm, module.
        + Từ viết tắt, acronym, metric lạ, khái niệm domain-specific.
    """

    writing_type = context.get("writing_type", "Document")
    main_goal = context.get("main_goal", "")
    criteria = context.get("criteria", [])
    constraints = context.get("constraints", [])

    ctx_lines = [f"Writing Type: {writing_type}"]
    if main_goal:
        ctx_lines.append(f"Main Goal: {main_goal}")
    if criteria:
        ctx_lines.append("Criteria:")
        ctx_lines.extend(f"  - {c}" for c in criteria)
    if constraints:
        ctx_lines.append("Constraints:")
        ctx_lines.extend(f"  - {c}" for c in constraints)
    ctx_block = "\n".join(ctx_lines)

    prompt = f"""
You are LogicGuard, an expert technical writing analyst specialized in identifying undefined terminology in {writing_type} documents.

Your single task in this endpoint:
- Detect technical terms, metrics, acronyms, product names, system names, or domain-specific concepts
  that are important for understanding the document BUT are NOT clearly defined when they first appear.

DO NOT perform spelling analysis here. Spelling is handled elsewhere.

---------------------------
CONTEXT
{ctx_block}

---------------------------
DOCUMENT CONTENT
<<<BEGIN DOCUMENT>>>
{content}
<<<END DOCUMENT>>>

---------------------------
DEFINITION & SCOPE

Treat something as a candidate technical term ONLY IF:
- It looks like: model name, framework/module name, product/system name, domain-specific metric,
  technical acronym, or specialized concept.
- It is important for understanding the main arguments, results, or architecture.

A term is considered CLEARLY DEFINED if:
- The text explicitly defines it near first occurrence:
    - "X is...", "X is defined as...", "X means..."
    - "X (short for ...)", "X, also known as ..."
    - Parenthetical explanation right after the term.
- OR the meaning is obviously clear for the expected expert audience (e.g., "CPU", "RAM" in a CS paper).

IMPORTANT: DO NOT mark plain typos or obvious misspellings as undefined terms.
Examples that should NOT be returned as undefined_terms:
- "deeplearnnig" instead of "deep learning"
- "algoritm" instead of "algorithm"
- "databaes" instead of "database"
- "platfomr" instead of "platform"
If a token clearly looks like a spelling mistake for a common English word, IGNORE it here.

---------------------------
MIXED-LANGUAGE HANDLING

If the document contains Vietnamese + English mixed:
- Do NOT mark common English words like "system", "model", "accuracy", "dataset" as undefined terms
  when they are used in a natural way.
- Only mark as undefined term if:
    - It is a special metric, method, or name that the reader cannot guess from context, AND
    - It is not a simple translation of a normal word.

---------------------------
OUTPUT FORMAT

Return ONLY valid JSON with this structure:

{{
  "total_terms_found": <int>,
  "undefined_terms": [
    {{
      "term": "Quantum Efficiency Score",
      "first_appeared": "Paragraph 2, Sentence 1",
      "context_snippet": "Short excerpt showing where the term appears...",
      "is_defined": false,
      "reason": "Metric is used as a key result but never explained or defined.",
      "suggestion": "Add a short definition the first time this score is mentioned."
    }}
  ],
  "defined_terms": [
    {{
      "term": "gradient clipping",
      "first_appeared": "Paragraph 3, Sentence 2",
      "context_snippet": "We apply gradient clipping, which means limiting the gradient norm...",
      "is_defined": true,
      "definition_found": "limiting the gradient norm to stabilize training."
    }}
  ]
}}

Rules:
- total_terms_found = len(undefined_terms) + len(defined_terms)
- Always include both undefined_terms and defined_terms (can be empty lists).
- All strings must be plain text, no markdown.

Return ONLY the JSON object. No markdown, no extra commentary.
"""
    return prompt


# =======================================
# 2. UNSUPPORTED CLAIMS (EN ONLY)
# =======================================

def prompt_unsupported_claims(context: Dict[str, Any], content: str) -> str:
    """
    Prompt phân tích LUẬN ĐIỂM THIẾU CHỨNG CỨ (Unsupported Claims) – tiếng Anh.
    Dùng riêng khi muốn gọi API chỉ cho unsupported claims.

    Focus:
    - Tìm câu khẳng định (claims) thiếu data / example / citation / reasoning.
    - Không đánh spelling, không bắt undefined term ở đây.
    """

    writing_type = context.get("writing_type", "Document")
    main_goal = context.get("main_goal", "")
    criteria = context.get("criteria", [])
    constraints = context.get("constraints", [])

    ctx_lines = [f"Writing Type: {writing_type}"]
    if main_goal:
        ctx_lines.append(f"Main Goal: {main_goal}")
    if criteria:
        ctx_lines.append("Criteria:")
        ctx_lines.extend(f"  - {c}" for c in criteria)
    if constraints:
        ctx_lines.append("Constraints:")
        ctx_lines.extend(f"  - {c}" for c in constraints)
    ctx_block = "\n".join(ctx_lines)

    prompt = f"""
You are LogicGuard, an expert writing analyst specialized in identifying unsupported claims in {writing_type} documents.

Your single task in this endpoint:
- Detect claims / statements that require evidence but are NOT properly supported in the text.

Do NOT do spelling or undefined term detection here.

---------------------------
CONTEXT
{ctx_block}

---------------------------
DOCUMENT CONTENT
<<<BEGIN DOCUMENT>>>
{content}
<<<END DOCUMENT>>>

---------------------------
WHAT IS A CLAIM?

Treat a sentence (or clause) as a claim if it:
- Asserts something about facts, trends, comparisons, predictions, or causal relations.
- Example types:
    - Absolute statements: "X always works", "No one fails with this method".
    - Comparative: "X is faster than Y".
    - Causal: "X causes Y", "Using our system will double revenue".
    - Quantitative: "97% of users prefer this tool".

WHAT COUNTS AS EVIDENCE?

A claim is considered supported ONLY IF the document provides nearby:
- Data or statistics.
- Concrete examples or case studies.
- Citations to credible sources.
- Clear logical reasoning that links prior facts to the claim.

We use an "evidence proximity rule":
- Evidence must appear in:
    - the same sentence, OR
    - within ±2 sentences around the claim, OR
    - clearly in the same paragraph with explicit connection.

---------------------------
OUTPUT FORMAT

Return ONLY valid JSON with this structure:

{{
  "total_claims_found": <int>,
  "unsupported_claims": [
    {{
      "claim": "97% of all professionals worldwide prefer this software.",
      "location": "Paragraph 2, Sentence 1",
      "status": "unsupported",  // or "weak" or "partially_supported"
      "claim_type": "absolute", // "absolute" | "comparative" | "causal" | "predictive" | ...
      "reason": "High, precise percentage is given without any data, citation, or reference.",
      "surrounding_context": "Short excerpt around the claim...",
      "suggestion": "Either provide concrete survey or market research data, or rewrite the sentence to be less absolute."
    }}
  ],
  "supported_claims": [
    {{
      "claim": "According to Smith (2023), the model achieves 85% accuracy.",
      "location": "Paragraph 1, Sentence 2",
      "status": "supported",
      "evidence_type": "citation_with_data",
      "evidence": "Cites a specific source and provides a clear numeric result."
    }}
  ]
}}

Rules:
- total_claims_found = len(unsupported_claims) + len(supported_claims)
- "suggestion" should be short and direct (no long tutorial).
- Return ONLY the JSON object, no markdown, no extra text.
"""
    return prompt


# =======================================
# 3. UNIFIED ANALYSIS – ENGLISH (A2)
# =======================================

def prompt_analysis(context: Dict[str, Any], content: str) -> str:
    """
    Unified English prompt (A2):
    - Runs 5 subtasks in one call, với thứ tự ưu tiên:
      1) Spelling Errors (EN + VI, trong văn bản)
      2) Unsupported Claims
      3) Undefined Terms
      4) Contradictions
      5) Logical Jumps

    Mục tiêu:
    - Ưu tiên phát hiện spelling chính xác và nhanh.
    - Sau đó lần lượt xử lý các lỗi logic khác.
    - Trả về JSON A2 (final answers, không hướng dẫn từng bước).
    """

    writing_type = context.get("writing_type", "Document")
    main_goal = context.get("main_goal", "")
    criteria = context.get("criteria", [])
    constraints = context.get("constraints", [])

    ctx_lines = [f"Writing Type: {writing_type}"]
    if main_goal:
        ctx_lines.append(f"Main Goal: {main_goal}")
    if criteria:
        ctx_lines.append("Criteria:")
        ctx_lines.extend(f"  - {c}" for c in criteria)
    if constraints:
        ctx_lines.append("Constraints:")
        ctx_lines.extend(f"  - {c}" for c in constraints)
    ctx_block = "\n".join(ctx_lines)

    prompt = f"""
You are LogicGuard, an AI assistant specialized in logical and structural analysis of {writing_type} documents.

You MUST analyze the document along 5 dimensions, in this PRIORITY ORDER:
1) Spelling Errors (English + Vietnamese)
2) Unsupported Claims
3) Undefined Terms
4) Contradictions
5) Logical Jumps

You receive:
- CONTEXT: high-level info about the writing task.
- CONTENT: the full original document string (possibly mixed EN + VI).

GLOBAL JSON RULES:
- Return EXACTLY ONE JSON object.
- The JSON MUST be valid (no trailing commas, no comments).
- Do NOT wrap JSON in markdown fences.
- Do NOT output any explanation text outside the JSON.
- Every section must be present:
    - analysis_metadata
    - contradictions
    - undefined_terms
    - unsupported_claims
    - logical_jumps
    - spelling_errors
    - summary
- If no issues in a section, set total_found = 0 and items = [].

INDEXING RULES FOR SPELLING:
- start_pos, end_pos are 0-based character indices on the ORIGINAL CONTENT.
- end_pos is exclusive (Python slicing style: content[start_pos:end_pos]).

BRAND / MODEL NAMES:
- Do NOT treat brand names, product names, or clearly invented model names as spelling errors
  (e.g., "iPhone", "YouTube", "Z-Trax", "NeuroLearn-X", "LogicGuard").

---------------------------
CONTEXT
{ctx_block}

---------------------------
DOCUMENT (CONTENT STRING TO ANALYSE)
<<<BEGIN DOCUMENT>>>
{content}
<<<END DOCUMENT>>>

You MUST always refer to THIS exact content string for:
- All substring positions in spelling_errors.
- All sentences and paragraphs used in logical and factual analysis.

---------------------------
STEP 1 – SPELLING ERRORS (HIGHEST PRIORITY)

Goal:
- First, scan the entire content for obvious spelling mistakes in English AND Vietnamese.
- This reduces noise so later tasks do not confuse typos with undefined terms or unsupported claims.

Rules:
- Only flag a spelling error if you are at least ~70% confident it is wrong in context.
- Check at least 1–3 words before and after the token/phrase to understand context.
- If the token is a proper noun, brand, or likely name → do NOT mark it as error.
- If the token is a mixed EN+VI phrase but still makes sense for bilingual readers,
  do NOT mark it as error unless it is clearly misspelled.

Examples that SHOULD be flagged:
- EN:
    - "smple" → "simple"
    - "speling" → "spelling"
    - "erors" → "errors"
- VI:
    - "nghien cúu" → "nghiên cứu"
    - "cơ thễ" → "cơ thể"
    - "bằng trứng khoa học" → "bằng chứng khoa học"

For each spelling error item:
- original: exact substring from CONTENT (respect casing & accents).
- suggested: the final corrected form (short phrase or word) → direct answer, no step-by-step.
- start_pos, end_pos: character span in CONTENT.
- language: "en" or "vi" (best guess).
- reason: very short explanation why this is a spelling error in this context.

IMPORTANT:
- Perform spelling detection FIRST.
- Later subtasks MUST NOT treat a substring already clearly handled as a spelling error
  as an undefined term or part of unsupported_claims.

---------------------------
STEP 2 – UNSUPPORTED CLAIMS

After spelling is identified:
- Detect claims that require evidence but have no adequate support nearby.

Claims:
- Statements about facts, predictions, comparisons, causal links, or strong opinions presented as facts.

Evidence:
- Data, statistics, examples, citations, or strong reasoning.

A claim is considered supported ONLY IF there is evidence:
- In the same sentence, OR
- Within ±2 sentences, OR
- Clearly in the same paragraph and explicitly connected.

For each unsupported claim item:
- claim: main sentence or clause.
- location: "Paragraph X, Sentence Y".
- status: "unsupported" | "weak" | "partially_supported".
- claim_type: "absolute" | "comparative" | "causal" | "predictive" | ...
- reason: why the support is missing or weak.
- surrounding_context: short nearby snippet.
- suggestion: short, direct hint (e.g., "Add concrete data or citation").

---------------------------
STEP 3 – UNDEFINED TERMS

Next, look for undefined important terminology.

Rules:
- DO NOT mark plain typos (especially words that should be in spelling_errors) as undefined terms.
- Ignore common English words used naturally in Vietnamese sentences (e.g., "AI system", "model accuracy"),
  unless they are clearly special metrics or names.

For each undefined term item:
- term: exact substring from CONTENT.
- first_appeared: "Paragraph X, Sentence Y".
- context_snippet: short snippet around first occurrence.
- is_defined: true/false depending on whether a definition is provided close to first use.
- reason: why it is unclear or missing a definition.
- suggestion: short recommendation (e.g., "Add a one-line definition the first time it appears.").

---------------------------
STEP 4 – CONTRADICTIONS

Then, detect contradictions between statements.

Definition:
- Two statements cannot both be true in the same context if they disagree on:
    - Facts, numbers, dates, outcomes, or strong evaluations.

For each contradiction item:
- sentence1, sentence2: full sentences from CONTENT.
- sentence1_location, sentence2_location: e.g., "Paragraph 1, Sentence 2".
- contradiction_type: "factual" | "numerical" | "temporal" | "logical".
- severity: "high" | "medium" | "low".
- explanation: short description of the conflict.
- suggestion: short hint on how to resolve or clarify (no long tutorial).

---------------------------
STEP 5 – LOGICAL JUMPS (LOWEST PRIORITY)

Finally, check transitions between paragraphs.

Logical jump:
- The topic or reasoning changes abruptly without a clear bridge,
  explanation, or justification.

For each item:
- from_paragraph: 1-based index of source paragraph.
- to_paragraph: 1-based index of target paragraph.
- from_paragraph_summary: 1–2 sentence summary of source paragraph.
- to_paragraph_summary: 1–2 sentence summary of target paragraph.
- coherence_score: float 0–1 (1 = very coherent, 0 = no connection).
- flag: short label, e.g., "abrupt_topic_shift", "missing_explanation".
- severity: "high" | "medium" | "low".
- explanation: why the jump feels abrupt.
- suggestion: short hint on how to add a bridge or restructure.

Only include logical_jumps items where coherence_score < 0.7.

---------------------------
STRICT JSON OUTPUT FORMAT (A2)

Return JSON with exactly this structure and field names:

{{
  "analysis_metadata": {{
    "analyzed_at": "ISO timestamp",
    "writing_type": "{writing_type}",
    "total_paragraphs": <int>,
    "total_sentences": <int>
  }},

  "contradictions": {{
    "total_found": <int>,
    "items": [
      {{
        "id": 1,
        "sentence1": "Full text of first statement",
        "sentence2": "Full text of contradicting statement",
        "sentence1_location": "Paragraph X, Sentence Y",
        "sentence2_location": "Paragraph A, Sentence B",
        "contradiction_type": "factual|numerical|temporal|logical",
        "severity": "high|medium|low",
        "explanation": "Short explanation of why these statements conflict.",
        "suggestion": "Short hint on how to resolve or clarify."
      }}
    ]
  }},

  "undefined_terms": {{
    "total_found": <int>,
    "items": [
      {{
        "term": "gradient clipping",
        "first_appeared": "Paragraph 3, Sentence 1",
        "context_snippet": "Short excerpt where the term appears...",
        "is_defined": false,
        "reason": "Term is important but never explained.",
        "suggestion": "Add a brief definition on first use."
      }}
    ]
  }},

  "unsupported_claims": {{
    "total_found": <int>,
    "items": [
      {{
        "claim": "AI can perfectly predict human emotions.",
        "location": "Paragraph 2, Sentence 3",
        "status": "unsupported",
        "claim_type": "absolute",
        "reason": "No data or citation is provided.",
        "surrounding_context": "Short excerpt around the claim...",
        "suggestion": "Provide concrete data, citation, or soften the claim."
      }}
    ]
  }},

  "logical_jumps": {{
    "total_found": <int>,
    "items": [
      {{
        "from_paragraph": 5,
        "to_paragraph": 6,
        "from_paragraph_summary": "Short summary of paragraph 5...",
        "to_paragraph_summary": "Short summary of paragraph 6...",
        "coherence_score": 0.32,
        "flag": "abrupt_topic_shift",
        "severity": "high|medium|low",
        "explanation": "Why this transition feels abrupt.",
        "suggestion": "Add a linking sentence or explanation."
      }}
    ]
  }},

  "spelling_errors": {{
    "total_found": <int>,
    "items": [
      {{
        "original": "speling",
        "suggested": "spelling",
        "start_pos": 32,
        "end_pos": 39,
        "language": "en",
        "reason": "\"speling\" is a common misspelling of \"spelling\"."
      }}
    ]
  }},

  "summary": {{
    "total_issues": <int>,
    "critical_issues": <int>,
    "document_quality_score": <int>,
    "key_recommendations": [
      "Short key recommendation 1",
      "Short key recommendation 2",
      "Short key recommendation 3"
    ]
  }}
}}

- total_issues ≈ contradictions.total_found
                 + undefined_terms.total_found
                 + unsupported_claims.total_found
                 + logical_jumps.total_found
                 + spelling_errors.total_found

Return ONLY this JSON object. No markdown, no extra text.
"""
    return prompt


# =======================================
# 4. UNIFIED ANALYSIS – VIETNAMESE (A2)
# =======================================

def prompt_analysis_vi(context: Dict[str, Any], content: str) -> str:
    """
    Unified Vietnamese prompt (A2) – 5 nhiệm vụ, với thứ tự ưu tiên:
    1) Lỗi chính tả (spelling_errors – VI + EN trong văn bản)
    2) Luận điểm thiếu chứng cứ (unsupported_claims)
    3) Thuật ngữ chưa định nghĩa (undefined_terms)
    4) Mâu thuẫn logic (contradictions)
    5) Nhảy logic (logical_jumps)

    Mục tiêu:
    - Ưu tiên phát hiện lỗi chính tả chính xác, tránh nhầm với undefined_terms.
    - Không hướng dẫn từng bước, chỉ trả JSON kết quả cuối.
    - Hỗ trợ cả văn bản thuần VI và mixed VI + EN.
    """

    writing_type = context.get("writing_type", "Văn bản")
    main_goal = context.get("main_goal", "")
    criteria = context.get("criteria", [])
    constraints = context.get("constraints", [])

    ctx_lines = [f"Loại văn bản: {writing_type}"]
    if main_goal:
        ctx_lines.append(f"Mục tiêu chính: {main_goal}")
    if criteria:
        ctx_lines.append("Tiêu chí đánh giá:")
        ctx_lines.extend(f"  - {c}" for c in criteria)
    if constraints:
        ctx_lines.append("Ràng buộc:")
        ctx_lines.extend(f"  - {c}" for c in constraints)
    ctx_block = "\n".join(ctx_lines)

    prompt = f"""
Bạn là LogicGuard – AI phân tích logic và cấu trúc cho các tài liệu {writing_type} (tiếng Việt, có thể xen tiếng Anh).

Bạn PHẢI phân tích văn bản theo 5 loại vấn đề, theo THỨ TỰ ƯU TIÊN sau:
1) Lỗi chính tả (Spelling Errors – tiếng Việt + tiếng Anh)
2) Luận điểm thiếu chứng cứ (Unsupported Claims)
3) Thuật ngữ chưa định nghĩa (Undefined Terms)
4) Mâu thuẫn logic (Contradictions)
5) Nhảy logic (Logical Jumps)

Bạn nhận được:
- CONTEXT: thông tin nhiệm vụ viết.
- CONTENT: toàn bộ văn bản gốc dạng chuỗi (có thể VI + EN xen lẫn).

QUY TẮC CHUNG VỀ JSON:
- Chỉ trả về DUY NHẤT một object JSON.
- Không có markdown, không có giải thích ngoài JSON.
- Mỗi phần phải tồn tại:
    - analysis_metadata
    - contradictions
    - undefined_terms
    - unsupported_claims
    - logical_jumps
    - spelling_errors
    - summary
- Nếu không có lỗi ở một loại, để:
    - total_found = 0
    - items = []

QUY TẮC VỊ TRÍ (spelling_errors):
- start_pos, end_pos là index ký tự 0-based trên chuỗi CONTENT gốc.
- end_pos là exclusive, như Python slicing: content[start_pos:end_pos].

---------------------------
NGỮ CẢNH
{ctx_block}

---------------------------
VĂN BẢN GỐC (CONTENT)
<<<BẮT ĐẦU VĂN BẢN>>>
{content}
<<<KẾT THÚC VĂN BẢN>>>

Mọi phân tích bên dưới PHẢI dựa trên chính xác chuỗi CONTENT này.

---------------------------
BƯỚC 1 – LỖI CHÍNH TẢ (ƯU TIÊN CAO NHẤT)

Mục tiêu:
- Tìm lỗi chính tả rõ ràng trong cả tiếng Việt và tiếng Anh.
- Giảm nhiễu cho các bước sau (tránh nhầm typo thành thuật ngữ hoặc luận điểm).

Hướng dẫn:
- Đọc toàn văn bản, kiểm tra từ/cụm từ trong NGỮ CẢNH.
- Ít nhất phải nhìn 1–3 từ TRƯỚC và 1–3 từ SAU để hiểu ngữ cảnh.
- Nếu từ/cụm từ gần như chắc chắn là sai chính tả trong ngữ cảnh → gắn cờ lỗi.

Ví dụ nên gắn cờ:
- "compaeny" → "company" (EN)
- "repoort" → "report" (EN)
- "nghien cúu" → "nghiên cứu" (VI)
- "cơ thễ" → "cơ thể" (VI)
- "bằng trứng khoa học" → "bằng chứng khoa học" (VI)

QUY TẮC QUAN TRỌNG:
- KHÔNG sửa tên thương hiệu, tên riêng, tên sản phẩm/mô hình nếu có vẻ cố ý:
  Ví dụ: "Zindra", "Tinh Vân Định Chuẩn", "Tâm Linh Omega".
- Nếu không chắc ≥ 70% rằng từ đó sai → BỎ QUA, KHÔNG gắn cờ.
- Với câu VI + EN xen lẫn, chỉ đánh lỗi chính tả nếu:
  - Từ đó sai trong ngôn ngữ của nó (EN/VI), VÀ
  - Khi sửa, cụm trở nên tự nhiên hơn rõ rệt.

Mỗi item trong spelling_errors:
- original: chuỗi gốc bị sai chính tả.
- suggested: phiên bản đúng cuối cùng (đáp án trực tiếp, không từng bước).
- start_pos: index bắt đầu (0-based) trong CONTENT.
- end_pos: index kết thúc dạng exclusive.
- language: "vi" hoặc "en".
- reason: giải thích ngắn vì sao đây là lỗi trong ngữ cảnh.

Bước này phải thực hiện TRƯỚC. Các bước sau KHÔNG được coi các typo này là undefined_terms.

---------------------------
BƯỚC 2 – LUẬN ĐIỂM THIẾU CHỨNG CỨ (UNSUPPORTED CLAIMS)

Sau khi xử lý chính tả, bạn tìm:
- Các câu/mệnh đề khẳng định điều gì đó (sự thật, xu hướng, hiệu quả, dự đoán, so sánh, quan hệ nhân quả)
  mà KHÔNG có dữ liệu, ví dụ, trích dẫn hoặc lập luận đủ mạnh.

Một luận điểm chỉ được xem là CÓ CHỨNG CỨ nếu:
- Có bằng chứng trong cùng câu, HOẶC
- Trong khoảng ±2 câu lân cận, HOẶC
- Trong cùng đoạn với liên kết rõ ràng.

Mỗi item:
- claim: câu hoặc mệnh đề chứa luận điểm.
- location: ví dụ "Đoạn 2, Câu 3".
- status: "unsupported" | "weak" | "partially_supported".
- claim_type: "absolute" | "comparative" | "causal" | "predictive" | ...
- reason: giải thích ngắn vì sao thiếu chứng cứ.
- surrounding_context: trích đoạn ngắn xung quanh.
- suggestion: gợi ý ngắn (ví dụ: "Bổ sung số liệu hoặc dẫn chứng nghiên cứu").

---------------------------
BƯỚC 3 – THUẬT NGỮ CHƯA ĐỊNH NGHĨA (UNDEFINED TERMS)

Tiếp theo, bạn tìm:
- Thuật ngữ kỹ thuật, tên mô hình, tên hệ thống, metric lạ, từ viết tắt quan trọng
  nhưng không được giải thích rõ ở lần xuất hiện đầu.

Lưu ý:
- KHÔNG coi các lỗi chính tả đã thuộc spelling_errors là thuật ngữ.
- KHÔNG đánh dấu các từ tiếng Anh phổ thông (system, model, accuracy, data, ...) là undefined_terms
  nếu dùng tự nhiên trong câu tiếng Việt.

Mỗi item:
- term: đúng chuỗi xuất hiện trong CONTENT.
- first_appeared: ví dụ "Đoạn 3, Câu 1".
- context_snippet: trích đoạn ngắn quanh lần xuất hiện đầu.
- is_defined: true/false (có được giải thích gần đó hay không).
- reason: vì sao xem là chưa định nghĩa / khó hiểu.
- suggestion: khuyến nghị ngắn (ví dụ: "Thêm 1 câu định nghĩa ngắn cho thuật ngữ này").

---------------------------
BƯỚC 4 – MÂU THUẪN LOGIC (CONTRADICTIONS)

Sau đó, bạn tìm các cặp câu không thể cùng đúng.

Ví dụ:
- Cùng nói về một chương trình thử nghiệm:
  - Câu A: "thử nghiệm thất bại hoàn toàn".
  - Câu B: "thử nghiệm là một thành công vang dội".

Mỗi item:
- sentence1, sentence2: nguyên văn hai câu mâu thuẫn.
- sentence1_location, sentence2_location: ví dụ "Đoạn 1, Câu 2".
- contradiction_type: "factual" | "numerical" | "temporal" | "logical".
- severity: "high" | "medium" | "low".
- explanation: 1–2 câu giải thích xung đột.
- suggestion: gợi ý ngắn để làm rõ hoặc thống nhất quan điểm.

---------------------------
BƯỚC 5 – NHẢY LOGIC (LOGICAL JUMPS)

Cuối cùng, xem xét mạch nối giữa các đoạn.

Nhảy logic xảy ra khi:
- Chủ đề hoặc lập luận đổi hướng đột ngột,
- Thiếu câu nối hoặc giải thích tại sao chuyển ý.

Mỗi item:
- from_paragraph: số đoạn nguồn (bắt đầu từ 1).
- to_paragraph: số đoạn đích (bắt đầu từ 1).
- from_paragraph_summary: tóm tắt ngắn 1–2 câu nội dung đoạn nguồn.
- to_paragraph_summary: tóm tắt ngắn 1–2 câu nội dung đoạn đích.
- coherence_score: số thực 0–1 (1 = rất mạch lạc, 0 = hầu như không liên quan).
- flag: nhãn ngắn, ví dụ "abrupt_topic_shift", "missing_explanation".
- severity: "high" | "medium" | "low".
- explanation: vì sao xem đây là nhảy logic.
- suggestion: gợi ý ngắn để thêm câu chuyển ý hoặc cấu trúc lại.

Chỉ đưa vào các item có coherence_score < 0.7.

---------------------------
ĐỊNH DẠNG JSON ĐẦU RA (A2, CHUẨN)

Bạn PHẢI trả về JSON với cấu trúc:

{{
  "analysis_metadata": {{
    "analyzed_at": "Timestamp ISO",
    "writing_type": "{writing_type}",
    "total_paragraphs": <số nguyên>,
    "total_sentences": <số nguyên>
  }},

  "contradictions": {{
    "total_found": <số nguyên>,
    "items": [ ... ]
  }},

  "undefined_terms": {{
    "total_found": <số nguyên>,
    "items": [ ... ]
  }},

  "unsupported_claims": {{
    "total_found": <số nguyên>,
    "items": [ ... ]
  }},

  "logical_jumps": {{
    "total_found": <số nguyên>,
    "items": [ ... ]
  }},

  "spelling_errors": {{
    "total_found": <số nguyên>,
    "items": [ ... ]
  }},

  "summary": {{
    "total_issues": <tổng số vấn đề>,
    "critical_issues": <số vấn đề mức high>,
    "document_quality_score": <0-100>,
    "key_recommendations": [
      "Khuyến nghị quan trọng 1",
      "Khuyến nghị quan trọng 2",
      "Khuyến nghị quan trọng 3"
    ]
  }}
}}

Trong đó:
- total_issues ≈ tổng số mục trong:
  contradictions.items
  + undefined_terms.items
  + unsupported_claims.items
  + logical_jumps.items
  + spelling_errors.items

Trả về DUY NHẤT object JSON này.
KHÔNG dùng markdown, KHÔNG giải thích ngoài JSON.
"""
    return prompt
