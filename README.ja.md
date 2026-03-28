# MemoForge

[English README](./README.md)

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Release](https://img.shields.io/github/v/release/HMYamano/MemoForge)](../../releases)
[![CI](https://github.com/HMYamano/MemoForge/actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)

完全ローカルで動かす研究メモ整理システムです。PDF、画像、Markdown、テキストを材料にして、Markdown 形式の再利用しやすい研究ノートを生成します。

- UI 1: Open WebUI (`http://localhost:3000`)
- UI 2: MemoForge Dashboard (`http://localhost:8001`)
- LLM 実行: Ollama
- 既定の整理モデル: `qwen3:30b`
- 既定の図解釈モデル: `gemma3:27b`

## 特長

- ローカル完結で研究メモを整理
- PDF の本文抽出と、ページ画像ベースの補助解釈を組み合わせ
- 既存 `notes/` を BM25 で検索し、関連ノートを文脈として再利用
- Open WebUI から OpenAI-compatible provider として接続可能
- 出力はそのまま再編集しやすい Markdown

## 構成

- `ollama`: ローカル LLM / VLM 実行
- `open-webui`: 通常チャットとモデル操作用 UI
- `memoforge`: 研究メモ整理用の FastAPI + LangGraph ワークフロー

## クイックスタート

### 1. 必要条件

- Docker / Docker Compose
- Ollama モデルを保持できる十分なディスク容量
- 大きめのモデルを使う場合は相応の GPU / RAM

### 1.1 推奨PC要件

以下はローカル利用向けの実用的な目安です。実際の必要性能は、モデルの量子化方式、資料サイズ、同時に動かしているアプリ数によって変わります。

標準構成: `qwen3:30b` + `gemma3:27b`

- OS: Docker が動作する Windows 11 / macOS / Linux
- CPU: 8 コア以上を推奨
- メインメモリ: 64 GB 以上を推奨
- GPU: VRAM 24 GB 以上を推奨
- 空きストレージ: Docker データと Ollama モデル用に 120 GB 以上を推奨

軽量構成: `qwen3:14b` + `gemma3:12b`

- メインメモリ: 32 GB 以上を推奨
- GPU: VRAM 12 GB から 16 GB 以上を推奨
- 空きストレージ: 60 GB 以上を推奨

CPU のみでも小さめのモデルで試すことはできますが、標準構成では応答がかなり遅くなりやすいため、あまりおすすめしません。

### 2. 任意で `.env` を作る

```bash
cp .env.example .env
```

PowerShell の場合:

```powershell
Copy-Item .env.example .env
```

### 3. コンテナ起動

```bash
docker compose up -d --build
```

### 4. モデルを取得

macOS / Linux / Git Bash:

```bash
./scripts/pull_models.sh
```

PowerShell:

```powershell
./scripts/pull_models.ps1
```

### 5. 画面を開く

- MemoForge Dashboard: `http://localhost:8001`
- Open WebUI: `http://localhost:3000`

## インストール後の開始方法と終了方法

### 開始方法

初回セットアップと必要なモデル取得が終わっていれば、普段の起動は次で行えます。

```bash
docker compose up -d
```

起動後は次を開きます。

- MemoForge Dashboard: `http://localhost:8001`
- Open WebUI: `http://localhost:3000`

`.env` でモデル設定を変更した場合も、保存後に同じコマンドを実行すれば新しい環境変数が反映されます。

### 終了方法

ノート、Ollama モデル、Open WebUI の状態などのローカルデータを残したままコンテナだけ停止する場合:

```bash
docker compose stop
```

コンテナを停止して削除する場合:

```bash
docker compose down
```

どちらのコマンドでも、ローカルの bind mount ディレクトリにある保存データは残ります。`down` はコンテナを削除し、`stop` は停止のみです。

## 使い方

### MemoForge Dashboard

1. `http://localhost:8001` を開く
2. 依頼文を書く
3. PDF / PNG / JPG / MD / TXT などを添付する
4. 実行する
5. `notes/` に Markdown メモが保存される

### Open WebUI から使う

- Ollama のモデルを直接使った通常チャットも可能
- 必要なら `memoforge` を OpenAI-compatible provider として追加可能
- API URL: `http://memoforge:8001/v1`（Docker 内）
- 別環境の Open WebUI から見に行く場合: `http://host.docker.internal:8001/v1`
- API Key: 空で可

## モデル設定

既定値は精度寄りです。重い場合は `.env` で切り替えてください。

```env
REASONING_MODEL=qwen3:14b
VISION_MODEL=gemma3:12b
EMBEDDING_MODEL=embeddinggemma
```

### モデルを変更する方法

1. まだ作成していなければ `.env.example` を `.env` にコピーします。
2. `.env` 内のモデル名を書き換えます。

```env
REASONING_MODEL=qwen3:14b
VISION_MODEL=gemma3:12b
EMBEDDING_MODEL=embeddinggemma
```

3. 使いたいモデルを取得します。

macOS / Linux / Git Bash:

```bash
./scripts/pull_models.sh
```

PowerShell:

```powershell
./scripts/pull_models.ps1
```

4. 新しい環境変数を反映するため、コンテナを再起動または再作成します。

```bash
docker compose up -d
```

現在のモデル設定はダッシュボード上部にも表示されます。このプロジェクトでは、`REASONING_MODEL` がメモ生成とレビュー、`VISION_MODEL` が画像や PDF ページの解釈、`EMBEDDING_MODEL` がローカル検索系の機能向けとして使われます。

## 実装メモ

- 関連ノート検索はローカル Markdown に対する BM25 ベースです
- PDF 本文抽出は `pypdf`、PDF ページ画像化は `pypdfium2` を利用しています
- 画像や PDF ページの視覚情報は Vision モデルに短く要約させています
- 将来的にベクトル DB や別のドキュメント処理系に差し替えやすい構成です

## リポジトリ内のデータについて

以下はランタイム生成物なので、Git には含めない前提です。

- `data/`
- `notes/`
- `incoming/`
- `__pycache__/`

各ディレクトリにはプレースホルダのみ置いてあります。実行時に Docker やアプリがローカルデータを作成します。

## セキュリティと運用上の注意

- このリポジトリはローカル利用前提です
- MemoForge API はローカルネットワークや自分の端末内で使う想定です
- インターネットへ直接公開する前提ではありません
- 機密文書を扱う場合は、モデル取得元や Open WebUI 側の設定も含めて運用を確認してください

## コントリビューション

コントリビューションを歓迎します。プルリクエストを送る前に [CONTRIBUTING.ja.md](./CONTRIBUTING.ja.md) をお読みください。

## 変更履歴

リリース履歴は [CHANGELOG.md](./CHANGELOG.md) を参照してください。

## ライセンス

このリポジトリ内のソースコードは `MIT License` です。商用利用、改変、再配布が可能です。

ただし、同梱していない外部コンポーネントやモデルはそれぞれ別ライセンス / 別規約です。特に次は README とは別に各 upstream を確認してください。

- Ollama: MIT
- Open WebUI: 現行版は branding 関連の条項を含むライセンス体系
- Qwen3: Apache-2.0
- Gemma / EmbeddingGemma: Gemma Terms of Use

このリポジトリの MIT ライセンスは、上記外部要素のライセンス条件を上書きしません。
