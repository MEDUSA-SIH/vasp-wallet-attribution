# Security Policy

## Reporting a vulnerability

Please report security issues **privately** by emailing the maintainers
listed in [`CODEOWNERS`](.github/CODEOWNERS). Do NOT file a public
GitHub issue for suspected vulnerabilities.

Include:

- A clear description of the issue.
- Reproduction steps.
- The expected impact.
- Any known mitigations.

We will acknowledge the report within 2 business days and aim to ship a
fix within 7 days for high-severity issues.

## Supported versions

Only the latest minor version on the `main` branch receives security
fixes. Older minors are not patched.

## Out of scope (current Stage 0.5)

The repository is a scaffold — authentication is stubbed, providers are
no-ops, and the API is not exposed beyond `127.0.0.1` by default. Until
those land, do not deploy this scaffold to a public network.