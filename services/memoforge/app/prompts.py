from __future__ import annotations

# ── Japanese ──────────────────────────────────────────────────────────────────

_SYSTEM_SUPERVISOR_JA = """あなたはローカル研究メモ整理システムの司令役です。
目的は、雑多なメモ・PDF・図・画像・テキストを、再利用しやすい研究ノートへ整理することです。
出力は常に日本語。必要なとき以外は冗長にしないでください。
曖昧な点は推測しすぎず、『不明』『要確認』として残してください。
"""

_PLAN_PROMPT_JA = """以下の依頼とファイル一覧に基づき、最短で安定した処理計画を 3〜6 ステップで作ってください。
JSON で返し、キーは plan のみ。plan は文字列配列。

依頼:
{instruction}

ファイル:
{files}
"""

_STRUCTURE_PROMPT_JA = """以下の材料をもとに、依頼内容に合う最終出力を Markdown で作成してください。

最優先ルール:
- 依頼文に出力形式、見出し、順序、文体、粒度の指定があれば最優先で従う
- 一般的な研究メモ用テンプレートよりも、依頼文の具体的な指示を優先する
- 依頼文に明示がない場合だけ、内容に最も適した構成を自分で選ぶ
- 依頼で求められていない定型見出しは無理に追加しない

構成の指針:
- 特に指定がなければ、簡潔なタイトルから始めてよい
- 比較依頼なら表や比較軸ごとの整理、要約依頼なら短い要約中心、Q&A依頼なら問答形式、手順依頼なら番号付き手順を優先する
- 「次のアクション」は依頼で求められた場合、または内容上有益な場合にだけ含める

共通条件:
- 日本語で書く
- 図やPDF画像から得られた情報は『図から読み取れた点』として明示する
- 確信の弱いものは『要確認』と明示する
- 重要な記述は、どの資料に基づくか分かるようにファイル名や資料名を適宜添える
- Markdown の範囲で自然で読みやすい構成にする

依頼:
{instruction}

抽出結果:
{extracted}

関連ノート:
{related_notes}
"""

_REVIEW_PROMPT_JA = """以下の草案をレビューし、次の JSON を返してください。
{{
  "verdict": "accept" または "revise",
  "issues": ["..."],
  "revision_instruction": "..."
}}

レビュー観点:
- 依頼文で指定された出力形式、見出し、順序、文体に合っているか
- 依頼にない定型セクションを機械的に足していないか
- 曖昧な断定がないか
- ソースとの対応が見えるか
- 図由来の読み取りと本文由来の内容が混ざっていないか
- 『要確認』扱いにすべき箇所が適切に残されているか
- 依頼で求められた場合のみ、次の行動やTODOが具体的か

依頼:
{instruction}

草案:
{draft}
"""

_REVISION_PROMPT_JA = """次の草案を、依頼文とレビュー指示に従って修正してください。
Markdown のみ返してください。

修正方針:
- 依頼文で求められた出力形式を優先する
- 依頼に不要な定型見出しや冗長な節は削るか統合する
- 事実関係、出典対応、図由来/本文由来の区別は維持する

依頼:
{instruction}

レビュー指示:
{revision_instruction}

草案:
{draft}
"""

# ── English ───────────────────────────────────────────────────────────────────

_SYSTEM_SUPERVISOR_EN = """You are the orchestrator of a local research note organization system.
Your goal is to organize messy notes, PDFs, figures, images, and text into reusable research notes.
Always output in English. Be concise unless detail is necessary.
Leave uncertain points as 'Unknown' or 'To be verified' rather than guessing.
"""

_PLAN_PROMPT_EN = """Based on the following request and file list, create the shortest stable processing plan in 3-6 steps.
Return JSON with only the key 'plan'. plan is a string array.

Request:
{instruction}

Files:
{files}
"""

_STRUCTURE_PROMPT_EN = """Create the final Markdown output that best fits the request and the provided materials.

Highest-priority rules:
- If the request specifies an output format, headings, ordering, tone, or level of detail, follow that first
- Prefer the concrete instructions in the request over a generic research-note template
- Only choose the structure yourself when the request does not specify one
- Do not add boilerplate sections that the request does not call for

Formatting guidance:
- If no explicit format is requested, you may start with a concise title
- For comparison tasks, prefer tables or comparison axes; for summaries, keep the summary compact; for Q&A tasks, use question-answer format; for procedures, use numbered steps
- Include next actions only when the request asks for them or when they are clearly useful

Requirements:
- Write in English
- Clearly label information derived from figures or PDF images as 'From figures'
- Mark uncertain items as 'To be verified'
- Keep important claims traceable to file or material names
- Use natural, readable Markdown

Request:
{instruction}

Extracted content:
{extracted}

Related notes:
{related_notes}
"""

_REVIEW_PROMPT_EN = """Review the following draft and return the following JSON.
{{
  "verdict": "accept" or "revise",
  "issues": ["..."],
  "revision_instruction": "..."
}}

Review criteria:
- It follows the requested output format, headings, ordering, tone, and emphasis
- It does not add irrelevant boilerplate sections
- No vague assertions
- Sources are traceable
- Figure-derived and text-derived information are not mixed
- Uncertain points are left as 'To be verified' when appropriate
- If next actions or TODOs are requested, they are concrete

Request:
{instruction}

Draft:
{draft}
"""

_REVISION_PROMPT_EN = """Revise the following draft according to the request and the review instructions.
Return Markdown only.

Revision goals:
- Prioritize the output format requested by the user
- Remove or merge boilerplate sections that are not needed
- Preserve factual accuracy, source traceability, and the separation between figure-derived and text-derived content

Request:
{instruction}

Review instructions:
{revision_instruction}

Draft:
{draft}
"""

_CHAT_SYSTEM_PROMPT_JA = """あなたは、1つの整理済み run に対する追質問へ答えるローカル研究アシスタントです。
事実として述べる内容は、必ず与えられた抜粋に根拠を置いてください。
推測や仮説を述べる場合は、推測であることを明示してください。
可能な限り [1] [2] のような引用番号を本文中に付けてください。
必ず JSON だけを返してください。
"""

_CHAT_PROMPT_JA = """以下は、整理済みの研究資料に対する追質問です。
次の JSON だけを返してください。
{{
  "answer": "...",
  "follow_ups": ["...", "..."],
  "citations": ["[1]", "[2]"]
}}

回答ルール:
- 回答言語は {response_language}
- mode が ask のときは、資料に基づく回答を優先する
- mode が discuss のときは、まず資料に基づく回答を述べ、その後に深掘りの観点や仮説を明示して加える
- 根拠が足りない場合は、足りないと明言する
- citations には、実際に使った抜粋番号だけを入れる

元の依頼:
{instruction}

整理済みノートの題名:
{note_title}

これまでの会話:
{history}

参照できる抜粋:
{context}

ユーザーの質問:
{message}
"""

_CHAT_SYSTEM_PROMPT_EN = """You are a local research assistant answering follow-up questions about one organized run.
Ground factual claims in the provided excerpts only.
If you add hypotheses or extrapolations, label them clearly as speculation.
Use inline citation markers like [1] and [2] when possible.
Return JSON only.
"""

_CHAT_PROMPT_EN = """Answer the user's follow-up question about the organized research run.
Return only this JSON:
{{
  "answer": "...",
  "follow_ups": ["...", "..."],
  "citations": ["[1]", "[2]"]
}}

Answer rules:
- Write in {response_language}
- When mode is ask, prioritize a grounded answer from the excerpts
- When mode is discuss, first answer from the excerpts, then add deeper angles or hypotheses and label them clearly
- If the excerpts are insufficient, say so plainly
- Only include citation ids that you actually used

Original instruction:
{instruction}

Organized note title:
{note_title}

Conversation so far:
{history}

Available excerpts:
{context}

User question:
{message}
"""

# ── Tag extraction ────────────────────────────────────────────────────────────

_TAG_PROMPT_JA = """以下の研究ノートを読み、内容を表す短いタグを 3〜8 個抽出してください。
タグは小文字・日本語可・英数字可・スペースなし・ハイフン区切り可とします。
JSON のみを返してください。キーは tags のみ、値は文字列配列。

ノート:
{markdown}
"""

_TAG_PROMPT_EN = """Read the following research note and extract 3–8 short tags that describe its content.
Tags should be lowercase, no spaces, hyphens allowed.
Return JSON only. The only key is 'tags'; value is a string array.

Note:
{markdown}
"""


def get_tag_prompt(lang: str = "ja") -> str:
    return _TAG_PROMPT_EN if lang == "en" else _TAG_PROMPT_JA


# ── Accessors ─────────────────────────────────────────────────────────────────


def get_system_supervisor(lang: str = "ja") -> str:
    return _SYSTEM_SUPERVISOR_EN if lang == "en" else _SYSTEM_SUPERVISOR_JA


def get_plan_prompt(lang: str = "ja") -> str:
    return _PLAN_PROMPT_EN if lang == "en" else _PLAN_PROMPT_JA


def get_structure_prompt(lang: str = "ja") -> str:
    return _STRUCTURE_PROMPT_EN if lang == "en" else _STRUCTURE_PROMPT_JA


def get_review_prompt(lang: str = "ja") -> str:
    return _REVIEW_PROMPT_EN if lang == "en" else _REVIEW_PROMPT_JA


def get_revision_prompt(lang: str = "ja") -> str:
    return _REVISION_PROMPT_EN if lang == "en" else _REVISION_PROMPT_JA


def get_chat_system_prompt(lang: str = "ja") -> str:
    return _CHAT_SYSTEM_PROMPT_EN if lang == "en" else _CHAT_SYSTEM_PROMPT_JA


def get_chat_prompt(lang: str = "ja") -> str:
    return _CHAT_PROMPT_EN if lang == "en" else _CHAT_PROMPT_JA
