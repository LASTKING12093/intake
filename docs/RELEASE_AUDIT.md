# Release verification — 2.0.1

The first public tree was prepared from the final application source, with a new, sanitized Git history. The existing local executable archive was not used as source code or reused as a release artifact.

## Security and privacy

- Inventory and SHA-256 review of the original development tree, including environments, caches, logs, previous binaries, generated files and media.
- Gitleaks 8.30.1 plus manual pattern searches for credentials, authentication data, private keys, private URLs, addresses and local paths.
- Allowlisted source export; local environments, logs, downloads, databases, browser state and build intermediates excluded.
- Review of the proposed Git index and complete new history, not only the working files.
- Byte and UTF-16 scans for the build host's profile, workspace and machine identifiers in the distribution; inspection of ZIP members and frozen Python code, including nested code objects and source filenames.
- Clean demo screenshots inspected visually; PNG metadata checked. No existing personal history or desktop capture was reused.
- Two scanner findings in upstream QtWebEngine development resources were excluded along with the unused development environments. Those resources are not shipped. Literal private-key parser markers in upstream libraries were distinguished from actual private-key material.
- The unmodified official Deno executable contains its upstream GitHub runner's generic profile prefix. The audit records a narrowly scoped baseline for that prefix in that exact SHA-256-verified artifact. Other paths and changed artifacts still fail; no INTAKE developer-machine path is exempted.

No known user credentials or personal build-machine information were found in the public source or release payload. This is a release-time review, not a guarantee against every future vulnerability.

## Packaging

The Windows build uses pinned Python packages and verified upstream helper hashes. The installer and portable archive are generated from that build. The application, PE version resource, package metadata and installer use version 2.0.1.

Local verification includes 69 automated tests; packaged UI startup; generation, download and inspection of original MP4 and MP3 fixtures; installer registration and Start Menu shortcut; installed-file comparison against the audited distribution; and uninstall with preservation of user data and media. The installer and application use the final INTAKE icon.

Tests ran on Windows 11 x64 in isolated application/data folders. A clean Windows VM was not available. The opt-in media smoke test uses an ephemeral loopback HTTP server solely for locally generated fixtures; no development server is required for normal use.

No code-signing certificate was configured. The release is unsigned and the README/release notes explain the possible SmartScreen warning. Checksums detect changes but are not a publisher signature.

## Third-party components

MIT applies to original INTAKE code. Separate dependency licenses, attributions, pinned binary origins, source-access references and Qt/Deno source manifests accompany the project. FFmpeg is a separate GPLv3 program; Qt/PySide libraries remain dynamically linked and replaceable. See [third-party notices](../THIRD_PARTY_NOTICES.md) and [dependency sources](DEPENDENCY_SOURCES.md).

## Automation

The Windows workflow scans Git history, builds, runs the tests, checks installation/uninstallation, audits the payload and uploads checksummed artifacts. Version tags publish a release only after the build job succeeds. Actions are pinned by commit; update proposals are handled by Dependabot.
