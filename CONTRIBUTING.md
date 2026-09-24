# Contributing

- Keep agent-facing instructions and source documentation in English. Human UI labels belong in the bilingual string table.
- Add a harness to discovery separately from its mission adapter. Do not claim automatic prompt submission until the actual CLI interface has been verified.
- Test quoting, spaces, multiline objectives, unavailable profiles and default-profile handling.
- Do not add workstation paths, device IDs, login state, credentials or provider usage data to fixtures.
- Use a temporary `AI_DEV_DATA_DIR` for tests. Never run paid agents in automated tests.
- Run `python -m unittest discover -s tests -v` and the source exporter before submitting changes.
