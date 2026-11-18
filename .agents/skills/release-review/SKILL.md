---
name: release-review
description: Run a structured pre-release readiness audit against the production base branch and produce a Go/No-Go checklist and draft release notes.
---

# Release Readiness Audit

When invoked, perform a thorough pre-release check of the current branch against `origin/main` (or the repository's default production branch). Do not modify any repository files during this review.

## Step 1: Gather Context & Diff
1. Run `git fetch origin main` and inspect the net diff using `git diff origin/main...HEAD`.
2. Review the commit log (`git log origin/main..HEAD --oneline`) to understand the scope of the release.
3. Read the root `AGENTS.md` (if present) to ensure all project-specific rules are enforced.

## Step 2: Run Verification Checks
1. Run the project's existing test suite, linter, and type-checker/build command to verify zero regressions.
2. Note any failing checks or skipped tests.

## Step 3: Audit for Release Blockers
Inspect the diff specifically for:
- **P0/P1 Bugs & Regressions**: Unhandled edge cases, broken API contracts, or missing error handling.
- **Database & State Safety**: Destructive or non-reversible migrations, missing backfills, or schema mismatches.
- **Configuration & Secrets**: Hardcoded credentials, missing entries in `.env.example`, or unguarded feature flags.
- **Dependencies**: Unintended lockfile changes or newly added high-risk packages.

## Step 4: Output the Go/No-Go Report
Present your findings in this exact Markdown structure:

### 1. Verdict: [GO / NO-GO]
*One-sentence summary explaining why the branch is safe to ship or what blocks it.*

### 2. Release Blockers (Must Fix Before Merge)
*Bullet list of P0/P1 issues with exact `file:line` references. Write "None found" if clear.*

### 3. Deployment & Rollback Checklist
*Required environment variables, migration steps, or rollback notes for the person deploying.*

### 4. Draft Release Notes
*Clean, user-facing summary of changes grouped under **Features**, **Fixes**, and **Maintenance**.*
