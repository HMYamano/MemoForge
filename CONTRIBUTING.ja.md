# MemoForge へのコントリビューション

[English version](./CONTRIBUTING.md)

MemoForge への関心をお持ちいただきありがとうございます。

## コントリビューションの方法

- [GitHub Issues](../../issues) でバグを報告する
- [GitHub Issues](../../issues) で機能を提案する
- バグ修正や改善のプルリクエストを送る
- ドキュメントを改善する

## 開発を始める

### 前提条件

- Docker と Docker Compose
- Python 3.11 以上（Docker を使わないローカル開発の場合）
- Git

### ローカル開発セットアップ

1. リポジトリをフォークしてクローンします。

```bash
git clone https://github.com/<your-username>/MemoForge.git
cd MemoForge
```

2. 環境設定テンプレートをコピーします。

```bash
cp .env.example .env
```

PowerShell の場合:

```powershell
Copy-Item .env.example .env
```

3. サービスを起動します。

```bash
docker compose up -d --build
```

4. モデルを取得します。

```bash
./scripts/pull_models.sh
# PowerShell の場合:
./scripts/pull_models.ps1
```

5. `http://localhost:8001` でダッシュボードが表示されれば OK です。

## 変更を送る

### ブランチ名

わかりやすいブランチ名を使ってください。

- `fix/pdf-extraction-unicode` — バグ修正
- `feat/vector-db-retrieval` — 新機能
- `docs/update-model-guide` — ドキュメント

### プルリクエストのガイドライン

- PR は一つの変更に絞ってください。
- 何を変更したか、なぜ変更したかを明確に記載してください。
- 関連する Issue がある場合は `Closes #<issue番号>` を記載してください。
- PR を出す前に Docker ビルドがローカルで通ることを確認してください。

### コミットメッセージ

短い命令形の件名を使ってください。

```
fix: 空の PDF テキスト抽出を適切に処理する
feat: .rst ファイルのサポートを追加
docs: モデル設定手順を明確化
```

## コードスタイル

- Python コードは [PEP 8](https://peps.python.org/pep-0008/) に従ってください。
- `ruff` が利用可能な場合は使用してください（`pip install ruff && ruff check services/memoforge/`）。
- 関数は一つの責務に絞り、必要以上の抽象化は避けてください。

## バグ報告

以下の情報を含めてください。

1. 再現手順
2. 期待する動作
3. 実際の動作
4. 環境（OS、Docker バージョン、モデル名、ハードウェア）
5. `docker compose logs memoforge` から得られる関連ログ

## セキュリティ上の問題

セキュリティの脆弱性は公開 Issue として報告しないでください。[SECURITY.md](./SECURITY.md) を参照してください。

## ライセンス

コントリビューションを送ることで、変更内容が [MIT License](./LICENSE) のもとでライセンスされることに同意したとみなします。
