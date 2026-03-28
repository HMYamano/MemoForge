# Contributing to MemoForge

[日本語版はこちら](./CONTRIBUTING.ja.md)

Thank you for your interest in contributing to MemoForge.

## Ways to Contribute

- Report bugs via [GitHub Issues](../../issues)
- Suggest features via [GitHub Issues](../../issues)
- Submit pull requests for bug fixes or improvements
- Improve documentation

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development without Docker)
- Git

### Local Development Setup

1. Fork the repository and clone your fork.

```bash
git clone https://github.com/<your-username>/MemoForge.git
cd MemoForge
```

2. Copy the environment template.

```bash
cp .env.example .env
```

3. Start the services.

```bash
docker compose up -d --build
```

4. Pull the models.

```bash
./scripts/pull_models.sh
# or on PowerShell:
./scripts/pull_models.ps1
```

5. Open the dashboard at `http://localhost:8001` to verify everything works.

## Submitting Changes

### Branch Naming

Use descriptive branch names:

- `fix/pdf-extraction-unicode` — for bug fixes
- `feat/vector-db-retrieval` — for new features
- `docs/update-model-guide` — for documentation

### Pull Request Guidelines

- Keep PRs focused on a single concern.
- Include a clear description of what changed and why.
- Reference related issues with `Closes #<issue-number>` if applicable.
- Make sure the Docker build succeeds locally before opening the PR.

### Commit Messages

Use short, imperative subject lines:

```
fix: handle empty PDF text extraction gracefully
feat: add support for .rst files
docs: clarify model configuration steps
```

## Code Style

- Python code should follow [PEP 8](https://peps.python.org/pep-0008/).
- Use `ruff` for linting if available (`pip install ruff && ruff check services/memoforge/`).
- Keep functions focused and avoid adding abstractions beyond what the task requires.

## Reporting Bugs

Please include:

1. Steps to reproduce
2. Expected behavior
3. Actual behavior
4. Your environment (OS, Docker version, model names, hardware)
5. Relevant logs from `docker compose logs memoforge`

## Security Issues

Do **not** open a public issue for security vulnerabilities. See [SECURITY.md](./SECURITY.md).

## License

By submitting a contribution you agree that your changes will be licensed under the [MIT License](./LICENSE).
