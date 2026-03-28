from __future__ import annotations

SYSTEM_SUPERVISOR = """あなたはローカル研究メモ整理システムの司令役です。
目的は、雑多なメモ・PDF・図・画像・テキストを、再利用しやすい研究ノートへ整理することです。
出力は常に日本語。必要なとき以外は冗長にしないでください。
曖昧な点は推測しすぎず、『不明』『要確認』として残してください。
"""

PLAN_PROMPT = """以下の依頼とファイル一覧に基づき、最短で安定した処理計画を 3〜6 ステップで作ってください。
JSON で返し、キーは plan のみ。plan は文字列配列。

依頼:
{instruction}

ファイル:
{files}
"""

STRUCTURE_PROMPT = """以下の材料をもとに、研究メモを Markdown で整理してください。
必ず次の見出しをこの順番で含めてください。
# Title
## One-line summary
## Background / Context
## Key points
## Evidence from files
## Open questions
## Next actions
## Related notes
## Raw source list

条件:
- 日本語で書く
- 図やPDF画像から得られた情報は『図から読み取れた点』として明示
- 確信の弱いものは『要確認』と明示
- 次の行動は具体的に 3〜7 個
- タイトルは簡潔に

依頼:
{instruction}

抽出結果:
{extracted}

関連ノート:
{related_notes}
"""

REVIEW_PROMPT = """以下の研究メモ草案をレビューし、次の JSON を返してください。
{{
  "verdict": "accept" または "revise",
  "issues": ["..."],
  "revision_instruction": "..."
}}

レビュー観点:
- 曖昧な断定がないか
- 次の行動が具体的か
- ソースとの対応が見えるか
- 図由来の読み取りと本文由来の内容が混ざっていないか
- タイトルが内容を表しているか

草案:
{draft}
"""

REVISION_PROMPT = """次の研究メモ草案を、レビュー指示に従って修正してください。
Markdown のみ返してください。

レビュー指示:
{revision_instruction}

草案:
{draft}
"""
