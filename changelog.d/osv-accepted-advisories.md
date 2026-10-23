### Fixed

- **The security scans pass again for the test tools of Home Assistant:** Home Assistant 2026.10 pins Pillow 12.3.0 and uv 0.12.23 for the tests of every integration, and no update of the tests can fix their advisories until Home Assistant moves on, so the OSV-Scanner and Findings checks failed on every change. `osv-scanner.toml` now accepts every advisory of exactly these two versions, with the reason and until 2026-11-22. Nothing that you install changes: the integration ships neither of them.
