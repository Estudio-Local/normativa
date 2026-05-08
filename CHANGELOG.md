# Changelog

All notable changes to **Norma** (`Estudio-Local/normativa`) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.9.0] - 2026-05-08

### Added

- Anonymous skill-invocation telemetry. `/norma-analyze` and `/norma-informe` now run `scripts/track.py` as a final step, recording `event` + `skill_version` + a stable per-machine UUID + `ts` to `https://estudio-local.com/api/telemetry`. Machine UUID lives at `~/.config/estudio-local/machine-id`. Padrón numbers, envelope content, file paths, conversation content, hostname, username, and IP are deliberately not collected.
- README "Telemetry" section disclosing exactly what's collected, where it goes, and how to opt out.
- `scripts/track.py` (~80 lines, pure stdlib).

### Opt-out

Set `ESTUDIO_LOCAL_TELEMETRY=0` in your environment. No machine-id file is created when opted out; an existing one can be removed with `rm ~/.config/estudio-local/machine-id`.

### Why

The Mapa side of the funnel (parcel clicks, JSON downloads, prompt copies) was already instrumented at `estudio-local.com/mapa`. The plugin side was a black box: we couldn't see whether anyone who exported a `selection.v1.json` actually ran `/norma-analyze` on it, or whether anyone went all the way to `/norma-informe`. Two events fix that.

## [0.8.1] - 2026-05-08

### Added

- `CHANGELOG.md` (this file). Adopts the version-bump discipline codified in `AlpacaLabsLLC/skills-for-architects/PATTERNS.md` rule #6: every shipped change moves three artifacts together — JSON `version` field, git tag (`vX.Y.Z`), GitHub release with notes.

### Notes

- This is a doc-only release (no plugin or skill behavior changed). Patch bump because `CHANGELOG.md` is a marketplace-level addition.
- Backfilled `v0.8.0` tag + GitHub release out-of-band (`9ee6132` → tagged retroactively with the original commit body as release notes).

## [0.8.0] - 2026-05-08

Adopt layered plugin pattern (rules/ + hooks/ + lint + dispatcher).

Restructures the plugin to follow the same layered architecture used across larger plugin libraries: a routing skill at the entry point, sub-skills for the actual work, externalized cross-skill rules, a marker-driven hook for disclaimer enforcement, and a structural lint.

### Changed

- `/norma` is now a **dispatcher** skill (no work, just routing). Reads the user's task and hands off to the right sub-skill.
- `/norma-analyze` (was `/norma`) — envelope analysis from padrones / GIS JSON / `selection.v1.json`. Same workflow as before; folder renamed.
- End users keep typing `/norma <args>`; routing happens transparently. Sub-skills remain user-invocable directly for power users.
- Validator renamed: `skills/norma/norma-validate-envelope.py` → `skills/norma-analyze/normativa-v1-validate.py`. Validator named after the schema id (`estudio-local.normativa.v1`), not after the skill, so future skill renames don't reach into it.

### Added

- **`/norma-informe`** sub-skill (unchanged behavior; previously inline) — printable HTML report from `*.normativa.v1.json` envelopes.
- **`rules/`** — externalized cross-skill enforcement copy. Single edit propagates to every skill that cites them. Lint verifies citations resolve. Files: `envelope-contract.md`, `professional-disclaimer.md`, `units-and-measurements.md`, `terminology.md`, `code-citations.md`, `transparency.md`.
- **Marker-driven disclaimer hook** — `hooks/post-write-disclaimer-check.sh` enforces `norma:requires-disclaimer` markers on regulatory output. Replaces keyword-sniffing; eliminates false positives on docs that mention regulated terms in passing.
- **`scripts/lint.sh`** — structural lint (~200 lines) modeled on `architecture-studio`. Validates: each plugin has `plugin.json` + at least one skill; SKILL.md frontmatter has `name`/`description`/`allowed-tools`/`user-invocable`; skill folder name matches frontmatter name; `*-schema.md` and `*-validate.py` references resolve; `rules/*.md` citations exist; `marketplace.json` plugin entry version matches `plugin.json`; hooks are executable.

### Notes

- Install command unchanged: `/plugin marketplace add Estudio-Local/normativa` then `/plugin install norma@normativa`.
- Power users who scripted `/norma <padrones>` directly now hit the dispatcher (which still routes correctly to `/norma-analyze` when it sees padrones+locality).
- Hooks aren't auto-enabled by Claude Code; opt-in is explicit via `~/.claude/settings.json`. Self-tested: marker+disclaimer→exit 0, marker-only→exit 2, no marker or non-md path→exit 0.
