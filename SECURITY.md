# Security Policy

## Supported version

Security updates are applied to the latest commit on the `main` branch. Older
commits and deployment snapshots are not maintained separately.

## Reporting a vulnerability

Please do not disclose a suspected vulnerability in a public issue, pull
request, discussion, or commit.

Use GitHub's private vulnerability reporting for this repository:

1. Open the repository's **Security** tab.
2. Select **Advisories**.
3. Select **Report a vulnerability**.
4. Include the affected component, reproduction steps, potential impact, and
   any suggested mitigation.

Do not include real credentials, API keys, personal data, or production
database contents in the report. Use redacted logs and minimal test data.

The maintainer will acknowledge a complete report as soon as practical,
validate the issue, and coordinate a fix before public disclosure. Reports
that are not security-sensitive can be submitted through the regular issue
templates instead.

## Security expectations

- Store deployment secrets in environment variables or the hosting platform's
  secret manager, never in the repository.
- Keep the supported Python, Node.js, PostgreSQL, and Redis versions described
  in [README.md](README.md) and [CONTRIBUTING.md](CONTRIBUTING.md).
- Require the CI and CodeQL checks to pass before merging changes into `main`.
- Review automated dependency updates for runtime compatibility before
  merging them.
