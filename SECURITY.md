# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest  | ✅        |

## Reporting a Vulnerability

**Do NOT open a public issue for security vulnerabilities.**

Email: security@cobweaverclaw.ai

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond within 48 hours and patch within 7 days.

## Security Architecture

CoBWeaverClaw is built security-first:

- **Sandbox**: Every plugin runs in an isolated sandbox
- **Trust Levels**: Actions require appropriate trust level (0-3)
- **No open WebSockets**: No external connections without explicit permission
- **TLS 1.3**: All connections encrypted
- **JWT signing**: HMAC-SHA256 for all tokens
- **Auto-audit**: `agent security audit` runs automatic checks
