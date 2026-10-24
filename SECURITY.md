# Security Policy

## Supported Versions

MathWeave Studio is under active development. Security updates are applied to the latest stable release line.

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1.0 | :x:                |

## Reporting a Vulnerability

We take the security of MathWeave Studio seriously. If you discover a security vulnerability, we appreciate your help in disclosing it responsibly.

### How to report

1. **Do not disclose the issue publicly** in open GitHub issues, pull requests, or public forums.
2. Please report security issues via GitHub's **Private Vulnerability Reporting** feature on the repository:
   - Navigate to the repository's **Security** tab.
   - Select **Report a vulnerability**.
3. Alternatively, if private vulnerability reporting is unavailable, reach out to the project maintainers via the email address listed in `pyproject.toml` (`92263302+TqvNoCode@users.noreply.github.com`).

### Information to include in your report

To help us investigate and triage effectively, please include:
- A clear description of the vulnerability and its potential impact.
- Step-by-step instructions or a minimal Proof of Concept (PoC) expression/input demonstrating the issue.
- Operating system, Python version, and dependency versions.
- Any suggested remediation or patch if available.

### Handling and resolution process

- Maintainers will acknowledge receipt of the report and review the vulnerability in an isolated environment.
- If verified, a patch will be developed, tested against regression suites, and published in a subsequent release.
- A security advisory will be published upon release crediting the reporter if desired.
