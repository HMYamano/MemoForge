# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 1.0.x   | Yes       |

## Reporting a Vulnerability

**Do not open a public GitHub Issue for security vulnerabilities.**

Please report security issues by emailing the maintainers directly, or by using [GitHub's private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing/privately-reporting-a-security-vulnerability) feature if enabled on this repository.

Include:

- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested mitigations if you have them

You can expect an acknowledgement within 7 days and a status update within 30 days.

## Scope

MemoForge is designed for **local use only**. The following are known design constraints, not vulnerabilities:

- The MemoForge API has no authentication by default. Do not expose port 8001 to the internet.
- Open WebUI has its own authentication layer. Configure it appropriately for your environment.
- Models are fetched from Ollama's registry. Review model sourcing for sensitive environments.

Issues involving remote code execution, path traversal, or unexpected data exposure via the API are in scope for responsible disclosure.
