---
name: openlink-version-bump
description: Bump OpenLink project version across backend / frontend / extension components via scripts/bump_version.{sh,ps1}, regenerate lockfiles safely (uv lock / npm install — never sed them), update CHANGELOG.md in Keep-a-Changelog categories, and run the release commit/tag/push workflow. Use when the user says "升级版本" / "bump to vX.Y.Z" / "release vX.Y.Z" / "patch" / "minor" / "major", asks which SemVer bump to apply, reports a stale-version warning, asks about uv.lock / package-lock.json 404s after a bump, or is adding a new version-bearing file to the bump script.
---

# OpenLink Version Bump

## Overview

OpenLink has three components, each with its own version slot:

| Component | Source of truth | Synced files (sed'd by bump script) |
|---|---|---|
| **backend** (Python/FastAPI) | `backend/pyproject.toml` | `backend/VERSION`, `backend/app/main.py`, `backend/app/schemas/types.py`, `backend/app/api/endpoints/health.py` |
| **frontend** (Vue 3) | `frontend/package.json` | — |
| **extension** (Chrome MV3) | `extension/public/manifest.json` | `extension/package.json` |

Past manual edits missed files. `scripts/bump_version.{sh,ps1}` centralizes the bump so all 8 source-of-truth + synced slots move together.

> The bump script intentionally does NOT do git operations (commit / tag / push stay manual) — auto-generated commit messages are almost never what you want, and tag subjects need real prose.

## Bundled resources

This skill carries copies of three project files for self-containment; **the project copies at `<project>/scripts/bump_version.{sh,ps1}` and `<project>/docs/version-bumping.md` remain canonical** — keep both copies in sync by running [`<project>/scripts/sync_skill_copies.sh`](../../../scripts/sync_skill_copies.sh) after every edit (it pushes project → skill in one direction; `--check` mode reports drift, `--verbose` logs every file).

- `scripts/bump_version.sh` — bundled bash bump script (use the project copy at `<project>/scripts/bump_version.sh` for execution; this copy is a reference snapshot)
- `scripts/bump_version.ps1` — bundled PowerShell bump script (use the project copy at `<project>/scripts/bump_version.ps1` for execution; this copy is a reference snapshot)
- `references/version-bumping.md` — bundled long-form docs (lockfile rationale, SemVer judgment, full release flow, `build.sh` / `deploy-extension.sh` pointers)

## When to invoke

Triggers that should pull this skill in:
- "升级版本到 vX.Y.Z", "bump to X.Y.Z", "release vX.Y.Z"
- "patch" / "minor" / "major" as a verb
- "为什么上次漏改了", "stale references" warning from the script
- "uv sync 报 404", "uv.lock 坏了" → root cause was a sed, this skill explains why
- adding a new file that carries `__version__`
- questions about whether this version should be patch / minor / major

## Decide the version type

Apply SemVer mentally BEFORE running the script:

| Change since last release | Bump type |
|---|---|
| Bug fix only, no new feature | `patch` (1.1.1 → 1.1.2) |
| New backward-compatible feature, no breaking change | `minor` (1.1.1 → 1.2.0) |
| Breaking change (API, config, removed feature) | `major` (1.1.1 → 2.0.0) |

A period of **all new features and zero bug fixes** correctly jumps 1.1.1 → 1.2.0 directly. Don't pad patch numbers (`1.1.2 / 1.1.3`) just to feel incremental.

Override individual components for hot-fixes:
```bash
# Linux/macOS / Git Bash (PowerShell: --backend → -Backend, etc.)
./scripts/bump_version.sh 1.2.0 --backend 1.1.5    # backend sticks; others → 1.2.0
./scripts/bump_version.sh patch --frontend minor   # backend/extension +=patch, frontend +=minor
```

## Run the bump

From repo root:

```bash
# Linux/macOS / Git Bash
./scripts/bump_version.sh 1.2.0
./scripts/bump_version.sh patch

# Windows PowerShell (capitalized param names per PS convention)
.\scripts\bump_version.ps1 1.2.0
.\scripts\bump_version.ps1 patch -Frontend minor
```

The script will, in order:
1. Read each component's current version from its source-of-truth file.
2. Compute target per component (literal X.Y.Z or `patch|minor|major` from current).
3. `sed` the version-bearing files — NOT lockfiles (see Pitfalls).
4. Run `uv lock` (backend) / `npm install` (frontend + extension) per moved component to regen lockfiles.
5. Grep for stale references; exit 1 if any non-lockfile file still contains the old version.
6. Print `git diff --stat` (version files only) and a suggested commit message.

## ⚠️ Update CHANGELOG.md (do NOT skip)

> This is the most commonly forgotten step in a release. After the bump script succeeds but **before** committing, write the new version's section in [`CHANGELOG.md`](../../CHANGELOG.md).

Required behavior, matching the existing layout at `CHANGELOG.md:10-82`:

1. Replace the `## [Unreleased]` heading and its (empty) body with a new `## [X.Y.Z] - YYYY-MM-DD` heading for this release. Then leave a fresh empty `## [Unreleased]` above it for the next cycle.
2. Move (don't duplicate) any leftover `[Unreleased]` content into the new dated section.
3. Categorize fresh notes under Keep-a-Changelog headings (`### Added` / `### Fixed` / `### Changed` / `### Removed`, plus `### Security` only when relevant).
4. Bullet style — each line starts `- **bold heading**:` followed by the change, often referencing the file path in backticks. Indent continuation lines by two spaces. See existing entries for the exact format.
5. One bullet per file-change is the norm; do not collapse multi-file features into a single mega-bullet.
6. Order within each section: most user-visible first; critical bugs and breaking changes near the top of their section.

When uncertain about what landed since the last tag, cross-check with:
```bash
git log --oneline vX.Y.Z~..vX.Y.Z
# or, for a wider net:
git diff vX.Y.Z~ -- ':!CHANGELOG.md' ':!*.lock' ':!*package-lock.json' | head
```

For a **pure patch** (single bug fix), one `### Fixed` bullet is enough — no need to invent Added/Changed/Removed content.

After editing, eyeball `git diff CHANGELOG.md` to confirm:
- Date is today's local date in `YYYY-MM-DD`.
- Heading is exactly `## [X.Y.Z] - YYYY-MM-DD` (square brackets, single space, hyphen, single space, date).
- No leftover populated `## [Unreleased]` block.

## Release: commit, tag, push

After both the script edits AND the CHANGELOG are staged:

```bash
git status                                 # bump files + lockfiles + CHANGELOG.md
git diff --stat                            # (script already printed stat for version files only)
git diff CHANGELOG.md                      # eyeball before committing

git add -A
git commit -m "chore: 升级版本到 v1.2.0"
# If only some components moved, the script's suggested message looks like:
#   "chore: 升级版本 (backend:1.1.5→1.1.6) (frontend:1.1.1→1.2.0)"

git tag -a v1.2.0 -m "v1.2.0 — <one-line description of the headline change>"
git push origin main
git push origin v1.2.0                     # always push tag and main in the same batch
```

To make the GitHub Release page actually show the new section:

```bash
gh release view v1.2.0 --repo UryWu/openlink --json body,isDraft,publishedAt
# If body is empty / stale / release missing, recreate:
sed -n '12,82p' CHANGELOG.md > /tmp/v1.2.0-notes.md   # skip the ## [X.Y.Z] header
gh release create v1.2.0 --draft \
  --title "v1.2.0" \
  --notes-file /tmp/v1.2.0-notes.md \
  --repo UryWu/openlink
gh release edit v1.2.0 --draft=false --repo UryWu/openlink   # publish
```

## Pitfalls

- **Lockfile corruption** — never `sed s/1.1.1/1.2.0/g` over `uv.lock` / `package-lock.json`. `pathspec 1.1.1` (mypy transitive) would turn into nonexistent `1.2.0`, then `uv sync` 404s. Always let `uv lock` / `npm install` regenerate.
- **Missed file** — if you add a file carrying the version string, the script's grep verify will fail with "stale references". Update both `COMPONENT_FILES[<component>]` (shell, project `scripts/bump_version.sh`) and `Files = @(...)` (PowerShell, project `scripts/bump_version.ps1`), then run `./scripts/sync_skill_copies.sh` to push into the skill's bundled copies. See [`references/version-bumping.md`](references/version-bumping.md) §"加新文件时怎么同步".
- **Tag pushed later than main** — `git push origin main` without `git push origin vX.Y.Z` makes installs of the new tag fail. Always push both in the same batch.
- **Bumping without CHANGELOG** — the GitHub Release body comes out empty or stale; downstream consumers won't know what changed.
- **Pre-release versions** — the bump regex `^\d+\.\d+\.\d+$` rejects `1.2.0-beta.1`. If you need a pre-release tag, relax the regex in both scripts or accept that this skill won't auto-handle it.

## Adding a new version-bearing file

> Always edit the **project canonical** first, then run `./scripts/sync_skill_copies.sh` (project canonical) to push project → skill copies. The skill's sync helper knows the 3-file map and updates all bundled copies in one shot — no manual `cp` needed.

1. Pick the component (`backend` / `frontend` / `extension`).
2. In `<project>/scripts/bump_version.sh` (canonical), append `path|plain` or `path|json` on a new line in `COMPONENT_FILES[<component>]`.
3. Mirror in `<project>/scripts/bump_version.ps1` (canonical): add `@{ Path = "..."; Mode = 'plain' }` or `'json'` to the `Files = @(...)` array.
4. Run `./scripts/sync_skill_copies.sh` to push both edits into the skill's bundled copies.
5. Smoke test: `./scripts/bump_version.sh patch` from project root should print `already at X.Y.Z (skip)` for unchanged components and exit 0.
6. Real test: edit one existing file's version by hand, then run `.\scripts\bump_version.ps1 patch` from project root — confirm the new file is also touched.

If you forget step 4, the bump script will still work (it uses project canonical), but future triggers of this skill will read stale bundled copies and may suggest outdated steps.

## Reference

For deeper context — `lockfile` design rationale, full release flow, related scripts (`build.sh`, `deploy-extension.sh`) — see [`references/version-bumping.md`](references/version-bumping.md) (bundled with this skill; canonical copy at [`docs/version-bumping.md`](../../docs/version-bumping.md) in this repo).
