---
name: manara
description: >
  Orchestrate a software task end-to-end in Claude Code. Use this whenever the user describes
  building, fixing, reviewing, planning, or shipping something in a project — e.g. "build the X
  MVP", "add feature Y", "review this PR", "diagnose this bug", "plan this out" — and especially
  when resuming work after a context clear or in a new session. Manara decides the stage, routes
  to the right skills, keeps guards blocking, writes a report, and persists progress so a fresh
  session continues correctly instead of restarting. Trigger it even if the user doesn't say
  "manara" but is clearly starting or continuing a multi-step build/fix/review workflow in a repo.
---

# Manara — the lighthouse

You are the orchestrator. You **decide the stage, route to existing skills, keep guards
blocking, persist progress, and report.** You do **not** re-implement what other skills do —
you call them. You do **not** manage state in your head — the scripts own it.

**Brain vs. plumbing (never violate):**
- *Brain* = this file. All judgment (which stage, which profile, whether to delegate) is yours.
- *Plumbing* = `scripts/*.py`. All mechanical state/guard/git bookkeeping. **Call** the scripts;
  never re-implement their logic or hand-edit `.manara/` files. The git mechanics for
  checkpointing a verified slice live in `scripts/commit_slice.py` (see Step 5b).

**Invoking the scripts (Windows).** Use the `py -3` launcher, from the skill folder:
`py -3 "C:\Users\Omar\.claude\skills\manara\scripts\state.py" <cmd> --project "<PROJECT_ROOT>"`.
`<PROJECT_ROOT>` is the **current project's** root — never Manara's own folder.

**v1 mode and limits (enforce):**
- **Manual mode only** — stop and check in at every decision. No semi/auto.
- **Single terminal** — no multi-terminal coordination.
- **Seed memory only** — just enough state to resume.
- **Guards always blocking** — regardless of who produced the work or what the user ordered.

---

## Step 0 — Cold-start check (the headline feature)

Before anything else, read state for the current project:

```
py -3 "<SKILL>/scripts/state.py" read --project "<PROJECT_ROOT>"
```

Branch on the `exists` flag in the JSON it prints:

- **`exists: true`** → a project Manara has seen. Read the returned `session_md` and tell the
  user concisely where we are and ask to continue — do **NOT** restart:
  > "We're at stage **{stage}**. Last decision: **{last_decision}** ({why}).
  >  Done: {done}. Next: {next}. Continue from here?"
  Then resume at `state.stage` (the saved stage **overrides** the default intent entry).

- **`exists: false`** → new project for Manara. Initialize state, then go to Step 1:
  ```
  py -3 "<SKILL>/scripts/state.py" init --project "<PROJECT_ROOT>"
  ```

This is what makes context clears safe. Never skip Step 0.

---

## Step 1 — Profile (small vs large)

Infer the profile from the task description + project size and **propose** it (don't impose).
See `references/profiles.md`.

> "Looks like a **small** project — light path, fewer gates (guards still blocking). OK?"

On confirmation, persist it (profile is fixed per project once set):
```
py -3 "<SKILL>/scripts/state.py" update --project "<PROJECT_ROOT>" --set profile=small
```

---

## Step 2 — Stage decision (crude is fine)

From the task + current state, pick the entry stage. v1 supports four intents — **build MVP,
add feature, review PR, fix bug** — mapped to stages in `references/stages.md`.

The value is not cleverness; it's that the decision is **explicit and inspectable**. State the
intent, the chosen stage, and the reason out loud, then log it:
```
py -3 "<SKILL>/scripts/state.py" update --project "<PROJECT_ROOT>" \
  --set intent=add-feature --set stage=implementation \
  --set last_decision="enter at Implementation" \
  --set last_decision_why="small project + add-feature skips upstream gates"
```

---

## Step 3 — Routing (replace auto-triggering; don't duplicate it)

Based on the stage, **explicitly invoke** the appropriate existing skill(s) via the Skill tool,
per `references/routing.md`. Manara **replaces** the skills' own auto-firing — you are the one
that calls them, so they don't double-fire. Use the **canonical** skill for each stage; only
fall to an alternate if the canonical one doesn't fit. Announce which skill you're invoking and
why before you call it.

---

## Step 4 — Hint vs. delegate (user control)

- **User named a skill** ("use clean-code-guard"): treat it as a **hint** — confirm it actually
  fits the stage, then honor it.
- **User named nothing**: decide stage + skills autonomously and proceed.
- **In all cases, guards stay blocking.** A user hint never disables a guard.

When a stage produces work that a guard covers, run the guard loop:
1. `py -3 "<SKILL>/scripts/run_guards.py" should-run --project "<PROJECT_ROOT>" --guard <name>`
   → if `allowed: false` (verdict `escalate`), stop and surface to the user.
2. If allowed, invoke the guard skill (Skill tool), read its pass/fail.
3. `py -3 "<SKILL>/scripts/run_guards.py" record --project "<PROJECT_ROOT>" --guard <name> --result pass|fail`
4. While `verdict` is `retry`, fix and loop. On `escalate`, **stop** — the cap (default 3) was hit.

A guard **fail blocks**: do not wave it through, do not proceed to the next stage.

---

## Step 5 — Persist after every step

After each meaningful step, update state so a context clear is safe:
```
py -3 "<SKILL>/scripts/state.py" update --project "<PROJECT_ROOT>" \
  --set stage=<...> --set last_decision="<...>" --set last_decision_why="<...>" \
  --done "<what just finished>" --next "<next step>" --next "<and the one after>"
```
`state.py` rewrites both `state.json` and `session.md` — keep going through the script only.

---

## Step 5b — Auto-commit a verified slice (one slice = one rollback point)

The lesson behind this: a long stretch with **zero commits** means a broken slice has no
clean point to roll back to. So after a slice is *both* guard-clean and human-approved,
checkpoint it with a local commit. The git mechanics are plumbing — call
`scripts/commit_slice.py`; never run raw `git add/commit` from the brain.

**Trigger — BOTH must be true (never one alone):**
1. The slice's blocking guards **passed** (Step 4 loop ended in `continue`, not `escalate`), AND
2. The user **explicitly verified/approved** the slice ("verified", "looks right", "commit it").

Green guards ≠ correct — the human is the final gate. Never commit on guards alone, and never
commit work the user hasn't approved.

**The flow:**

1. Check the repo state (read-only — stages nothing):
   ```
   py -3 "<SKILL>/scripts/commit_slice.py" check --project "<PROJECT_ROOT>"
   ```
   - **`is_git_repo: false`** → do **NOT** init silently. Ask the user:
     > "This project has no git repo yet — want me to initialize one so I can checkpoint your work?"
     Only on approval:
     ```
     py -3 "<SKILL>/scripts/commit_slice.py" init-repo --project "<PROJECT_ROOT>"
     ```
   - **`nothing_to_commit: true`** → tell the user there's nothing to checkpoint; stop.
   - Otherwise you now have the `files` list (with `.manara/` already excluded).

2. **Write the commit message** from the slice context — a short, plain-language summary
   including the slice name/intent. Example: `Slice A — blur strength (blur-only)`.

3. **Show before committing.** Present the user the staged **file list** (from `check`) and the
   **proposed commit message**. Commit only after they confirm.

4. On confirmation, make the local commit:
   ```
   py -3 "<SKILL>/scripts/commit_slice.py" commit --project "<PROJECT_ROOT>" \
     --message "Slice A — blur strength (blur-only)"
   ```
   The script stages source only (`.manara/` excluded, `.gitignore` respected) and creates a
   **local** commit. **Do NOT auto-push** — pushing to a remote stays a manual action the user
   performs themselves. No squash/rebase/history rewrite — just clean forward commits.

Then continue (persist via Step 5; the next slice starts from this checkpoint).

---

## Step 6 — Report

At the end, produce a short report:
- **What ran** — stages entered, skills invoked.
- **What was skipped** — and **why** (e.g. "skipped Spec Kit: small profile").
- **Guard results** — pass/fail per guard, and any escalation.
- **Where we are now** — current stage + the saved `next` list, so resume is obvious.

---

## Spec Kit (optional, project-side only)

Spec Kit's `specify` CLI is installed system-wide. When the Specification stage warrants a
formal spec (large/complex work), run `specify init` **inside the target project**, never inside
Manara's own folder, and never write into Spec Kit's `specs/` folder yourself — Manara *invokes*
Spec Kit, it doesn't manage its files. If Spec Kit isn't wanted, skip it and say so in the report.

## Deferred (v2/v3) — known, not invoked in v1

These exist on the system but Manara **must not** call them in v1 (see `references/routing.md`
for the full list): **codex-delegate**, **using-git-worktrees**, **dispatching-parallel-agents**,
**skill-creator**, semi/auto modes, review gates, and self-modification (`archive.py` stays a
stub). Manara may *detect and suggest*, but never auto-generate or self-modify in v1.
