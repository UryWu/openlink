---
name: version-bump
description: Bump version across the two versioned components of a typical FastAPI+Vue (or Python-backend + Node-frontend) project (backend / frontend; add a third in the bundled scripts to fit your project) by running scripts/bump_version.{sh,ps1}, regenerate lockfiles safely (uv lock / npm install — never sed them), update CHANGELOG.md in Keep-a-Changelog categories, and run the release commit/tag/push workflow. Ships pre-configured for Python+Vue projects; to swap toolchains (e.g. uv lock for cargo generate-lockfile), edit the bundled scripts. Use when the user says "升级版本" / "bump to vX.Y.Z" / "release vX.Y.Z" / "patch" / "minor" / "major", asks which SemVer bump to apply, reports a stale-version warning, asks about lockfile corruption (uv.lock / package-lock.json / Cargo.lock 404s), or is adding a new version-bearing file to the bump script.
---

# Version Bump (2-Component Project)

## Overview

A typical FastAPI+Vue (or other Python-backend + Node-frontend) project has **two versioned components** — a backend service and a frontend app. When a release happens, both components move together — but writing/sed-ing each version slot by hand reliably misses files.

This skill centralizes the bump in a single driver script that:
1. Reads each component's **source-of-truth** version file,
2. Computes the target version (literal `X.Y.Z` or `patch|minor|major` bump from current),
3. `sed` (or `.Replace` on PowerShell) updates every version-bearing file in each component,
4. regenerates lockfiles via the package manager's lock command (NEVER by sed),
5. verifies no stale version strings remain, and
6. prints a suggested commit/tag/push sequence.

> The bump driver intentionally does NOT do git operations (commit / tag / push stay manual) — auto-generated commit messages are almost never what you want, and tag subjects need real prose.

## Ships pre-configured for…

Out of the box, the bundled `scripts/bump_version.{sh,ps1}` are configured for **2 components** (Python backend + Vue 3 frontend):

| Component | Source of truth | Synced files (sed'd by driver) |
|---|---|---|
| `backend`   (Python/FastAPI) | `<project>/backend/pyproject.toml`            | `backend/VERSION`, `backend/app/main.py`, `backend/app/schemas/types.py`, `backend/app/api/endpoints/health.py` |
| `frontend`  (Vue 3)           | `<project>/frontend/package.json`             | — |

### Adding a third component (or adapting to a different stack)

To add a third component to this 2-comp skill (e.g. a browser extension, a CLI tool, a worker):

1. **Append an entry** in:
   - `COMPONENT_FILES[<name>]`, `COMPONENT_READ[<name>]`, `COMPONENT_SYNC[<name>]` arrays in `scripts/bump_version.sh`
   - `$Components[$name] = @{ ... }` block in `scripts/bump_version.ps1`
   - The `for comp in ...` and `foreach ($name in ...) { ... }` loops
   - The override-var / switch-case logic (param, OVERRIDE_BACKEND="", `case --<name>`, `'<name>' { $override = $<Name> }`)
2. **Add a `read_version_<name>()` function** (shell) / **a `Reader` scriptblock** (PowerShell) that prints the current version to stdout.
3. **Add a `sync_lock_<name>()` function** / **a `Sync` scriptblock** matching your toolchain.
4. **Bump the count checks**: `[[ ${#NEW_VERSIONS[@]} -eq 2 ]]` → 3 in shell, `$changedCount -eq 2` → 3 in PowerShell.
5. **Dry-run**: `./scripts/bump_version.sh patch` should print `already at X.Y.Z (skip)` for unchanged components.

To swap toolchains without adding components, edit just `sync_lock_backend` (`uv lock` → e.g. `cargo generate-lockfile`) and `sync_lock_frontend` (`npm install` → e.g. `yarn install --frozen-lockfile`).

## Bundled resources

This skill carries copies of three files for self-containment; **the project canonical copies are the single source of truth** — keep them in sync by running `<project>/scripts/sync_skill_copies.sh` after every edit. (That helper is not bundled; recreate it from the "Adding a new version-bearing file" pattern.)

- `scripts/bump_version.sh` — bundled bash bump driver. For execution, use the project copy at `<project>/scripts/bump_version.sh`; this copy is a reference snapshot.
- `scripts/bump_version.ps1` — bundled PowerShell bump driver. Same pattern, PS-cased param names (`-Backend` not `--backend`).
- `references/version-bumping.md` — bundled long-form docs (lockfile rationale, SemVer judgment, full release flow).

## When to invoke

Triggers that should pull this skill in:
- "升级版本到 vX.Y.Z", "bump to X.Y.Z", "release vX.Y.Z"
- "patch" / "minor" / "major" as a verb
- "为什么上次漏改了", "stale references" warning from the script
- "uv sync 报 404", "uv.lock 坏了" / "package-lock.json corrupted" / "Cargo.lock version drift" → root cause was a sed, this skill explains why
- adding a new file that carries `__version__`
- questions about whether this version should be patch / minor / major

## Decide the version type

Apply SemVer mentally BEFORE running the script:

| Change since last release | Bump type |
|---|---|
| Bug fix only, no new feature | `patch` (1.1.1 → 1.1.2) |
| New backward-compatible feature, no breaking change | `minor` (1.1.1 → 1.2.0) |
| Breaking change (API, config, removed feature) | `major` (1.1.1 → 2.0.0) |

A period of **all new features and zero bug fixes** correctly jumps 1.1.1 → 1.2.0 directly. Don't pad patch numbers.

Override individual components for hot-fixes:
```bash
# Linux/macOS / Git Bash (PowerShell: --backend → -Backend, etc.)
./scripts/bump_version.sh 1.2.0 --backend 1.1.5    # backend sticks; others → 1.2.0
./scripts/bump_version.sh patch --frontend minor   # backend +=patch, frontend +=minor
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
2. Compute target per component (literal `X.Y.Z` or `patch|minor|major` from current).
3. `sed` (or `.Replace`) the version-bearing files — NOT lockfiles (see Pitfalls).
4. Run the configured package-manager lock command per moved component (e.g. `uv lock` / `npm install`) to regenerate lockfiles.
5. Grep for stale references; exit 1 if any non-lockfile file still contains the old version.
6. Print `git diff --stat` (version files only) and a suggested commit message.

## ⚠️ Update CHANGELOG.md (do NOT skip)

> This is the most commonly forgotten step in a release. After the bump script succeeds but **before** committing, write the new version's section in the project's changelog file (commonly `CHANGELOG.md`).

Required behavior, matching the existing layout in your changelog:

1. Replace the `## [Unreleased]` heading (and its empty body) with a new `## [X.Y.Z] - YYYY-MM-DD` heading. Leave a fresh empty `## [Unreleased]` above for the next cycle.
2. Move (don't duplicate) any leftover `[Unreleased]` content into the new dated section.
3. Categorize fresh notes under Keep-a-Changelog headings (`### Added` / `### Fixed` / `### Changed` / `### Removed`, plus `### Security` only when relevant).
4. Bullet style — each line starts `- **bold heading**:` followed by the change, often referencing the file path in backticks. Indent continuation lines by two spaces.
5. One bullet per file-change is the norm; do not collapse multi-file features into a single mega-bullet.
6. Order within each section: most user-visible first; critical bugs and breaking changes near the top.

When uncertain about what landed since the last tag, cross-check with:
```bash
git log --oneline vX.Y.Z~..vX.Y.Z
# or, for a wider net:
git diff vX.Y.Z~ -- ':!CHANGELOG.md' ':!*.lock' ':!*package-lock.json' | head
```

For a **pure patch** (single bug fix), one `### Fixed` bullet is enough.

After editing, eyeball `git diff <changelog-file>` to confirm:
- Date is today's local date in `YYYY-MM-DD`.
- Heading is exactly `## [X.Y.Z] - YYYY-MM-DD` (square brackets, single space, hyphen, single space, date).
- No leftover populated `## [Unreleased]` block.

## Release: commit, tag, push

After both the script edits AND the changelog are staged:

```bash
git status                                 # bump files + lockfiles + CHANGELOG.md
git diff --stat                            # (script already printed stat for version files only)
git diff <changelog-file>                  # eyeball before committing

git add -A
git commit -m "chore: 升级版本到 v1.2.0"
# If only some components moved, the script's suggested message looks like:
#   "chore: 升级版本 (<comp1>:1.1.5→1.1.6) (<comp2>:1.1.1→1.2.0)"

git tag -a v1.2.0 -m "v1.2.0 — <one-line description of the headline change>"
git push origin main
git push origin v1.2.0                     # always push tag and main in the same batch
```

Optional but recommended — make the GitHub/GitLab Release page actually show the new section:
```bash
gh release view v1.2.0 --repo <owner>/<repo> --json body,isDraft,publishedAt
# If body is empty / stale / release missing, recreate:
sed -n '/^## \[1\.2\.0\]/,/^## \[/p' CHANGELOG.md | sed '$d' > /tmp/v1.2.0-notes.md
gh release create v1.2.0 --draft \
  --title "v1.2.0" \
  --notes-file /tmp/v1.2.0-notes.md \
  --repo <owner>/<repo>
gh release edit v1.2.0 --draft=false --repo <owner>/<repo>   # publish
```

## Pitfalls

- **Lockfile corruption** — never `sed s/1.1.1/1.2.0/g` over a lockfile (`uv.lock`, `package-lock.json`, `Cargo.lock`, etc.). It will turn a transitive dep's version into a nonexistent one and the next install command will 404. Always let the package manager regenerate (`uv lock`, `npm install`, `cargo generate-lockfile`, etc.).
- **Missed file** — if you add a file carrying the version string, the script's grep verify will fail with "stale references". Update both the shell script's `COMPONENT_FILES[<component>]` and the PowerShell script's `Files = @(...)` array, then run `<project>/scripts/sync_skill_copies.sh` (if you have one) to push into the skill's bundled copies. See [`references/version-bumping.md`](references/version-bumping.md) §"加新文件时怎么同步".
- **Tag pushed later than main** — `git push origin main` without `git push origin vX.Y.Z` makes installs of the new tag fail. Always push both in the same batch.
- **Bumping without CHANGELOG** — the GitHub Release body comes out empty or stale; downstream consumers won't know what changed.
- **Pre-release versions** — the bundled script regex `^\d+\.\d+\.\d+$` rejects `1.2.0-beta.1`. If you need pre-release tags, relax the regex (in both shell and PowerShell scripts) or accept that this skill won't auto-handle it.

## Adding a new version-bearing file

> Always edit the **project canonical** scripts first, then run `<project>/scripts/sync_skill_copies.sh` (if you have one) to push project → skill copies in one shot. Bundled copies are reference snapshots; project canonical wins.

1. Pick the component (one of your project's versioned components).
2. In `<project>/scripts/bump_version.sh` (canonical), append `path|plain` or `path|json` on a new line in `COMPONENT_FILES[<component>]`.
3. Mirror in `<project>/scripts/bump_version.ps1` (canonical): add `@{ Path = "..."; Mode = 'plain' }` or `'json'` to the `Files = @(...)` array.
4. Run `./scripts/sync_skill_copies.sh` to push both edits into the skill's bundled copies.
5. Smoke test: `./scripts/bump_version.sh patch` from project root should print `already at X.Y.Z (skip)` for unchanged components and exit 0.
6. Real test: edit one existing file's version by hand, then re-run `./scripts/bump_version.sh patch` — confirm the new file is also touched.

## Reference

For deeper context — `lockfile` design rationale, full release flow, related helper scripts (build / deploy) — see [`references/version-bumping.md`](references/version-bumping.md).
