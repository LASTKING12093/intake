# Security policy

## Supported versions

Security fixes target the latest stable INTAKE release. Update the extractor separately when a site requires a compatibility fix.

## Report privately

Use [GitHub private vulnerability reporting](https://github.com/LASTKING12093/intake/security/advisories/new). Include the affected version, a minimal reproduction and the impact. Do not post credentials, private links, cookies, exploit details or unredacted logs in public issues.

If private reporting is temporarily unavailable, open an issue requesting a private contact method **without sensitive details**. No response-time guarantee is implied.

## Boundaries

INTAKE does not bypass DRM or use browser authentication. It runs bundled third-party media processors against user-supplied URLs and files; upstream vulnerabilities can affect it. Only use trusted release artifacts and verify SHA-256 checksums. User configuration can intentionally select alternative executables; treat those paths as trusted code.

Queue and library files contain local media metadata and links. Logs may contain filenames or local paths even when URLs are redacted. Review and sanitize all diagnostics before sharing.
