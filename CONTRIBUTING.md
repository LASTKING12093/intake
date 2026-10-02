# Contributing

Thanks for helping improve INTAKE. Start with a focused issue describing the problem or the change you want to make.

1. Follow [BUILDING.md](BUILDING.md) to create a local environment.
2. Make a focused change that preserves the native Windows workflow.
3. Run the relevant tests, then the complete suite before requesting review.
4. Explain the behavior change and validation in your pull request. Include a clean screenshot for visible changes.

Use Python 3.12-compatible code, explicit UTF-8 for text files and subprocess argument lists instead of shell interpolation. Keep UI work on Qt's main thread. Do not add telemetry, browser-cookie access or new credentials without discussing the design first.

Use original or explicitly licensed fixtures. Keep downloaded media, personal paths, logs, caches and secrets out of commits and screenshots. Do not bundle dependencies without retaining their licenses and source-access information.

Report ordinary bugs using the issue form. Report vulnerabilities through [SECURITY.md](SECURITY.md), not public issues. Contributions to original project code are under the project's MIT license; retain third-party attribution.
