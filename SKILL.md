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

## Step 2b — Single-slice enforcement (no bundling)

The lesson behind this: SnapClean's worst day came from **bundling** — shapes and a shared
strength control were built together, they coupled, and the coupling caused the privacy leak.
Every later patch broke something else. What turned it around was strict **one-slice-at-a-time**
work with a commit between each. Manara enforces this instead of relying on the user (or the
model) to remember it — because the natural instinct is to say "let's do X *and* Y" in one go.

So **before routing to implementation**, check whether the request bundles more than one
independent piece of work. If it does, do **not** start building — stop and ask which single
slice to start with.

**Detect the bundle — a judgment call, not a keyword rule:**
- **Bundle** (split it): two or more pieces that are each *independently testable and
  committable* — distinct capabilities or behaviors that each deserve their own verify + commit.
  E.g. "add live-paint **and** a size slider", "fix the bug **and** add the new mode",
  "do shapes **and** strength".
- **NOT a bundle** (proceed): a single coherent piece with natural sub-parts — one testable
  behavior, even if it has parts (a commit plus its message; a function plus its test).
- When genuinely unsure, **lean toward asking** rather than assuming it's fine.

**The procedure (do this BEFORE Step 3 routing):**

1. **Stop and ask — wait for the user's choice.** List the slices you see and ask which **ONE**
   to start with. Do **not** auto-pick the order — the user decides what matters most. Example:
   *"That's two slices: (1) brush paints live, (2) brush size control. Which should I start with?
   I'll record the other in the plan."*

2. **Record the rest in the plan** so the unchosen slices aren't lost — use the existing state
   queue (the `--next` list), not a new mechanism:
   ```
   py -3 "<SKILL>/scripts/state.py" update --project "<PROJECT_ROOT>" \
     --next "slice: <chosen one> (building now)" \
     --next "slice: <unchosen> (queued — one at a time, verify+commit before next)"
   ```
   Queued slices are picked up **one at a time**, each verified + committed (Step 5b) before the
   next begins.

3. **Then proceed with only the chosen slice** through the normal flow — Step 3 routing →
   Step 3b behavior-spec if sensitive → TDD → guards (Step 4 loop) → verify → Step 5b auto-commit.

**Boundaries (keep this slice honest):**
- Don't auto-split and silently start — **always ASK** which slice first.
- It's **not** a rigid "contains the word *and*" rule — it's about whether the pieces are
  independently testable/committable.
- Don't force a split on a single coherent slice that merely has sub-parts.

This is **brain**, not plumbing — no new script; it only uses the existing `state.py` queue. It
does not change Slice 1 (Step 5b auto-commit) or Slice 2 (Step 3b behavior-spec), and it sits
inside the normal v1 stage/guard flow — it gates *entry* to routing when a request bundles work.

---

## Step 3 — Routing (replace auto-triggering; don't duplicate it)

Based on the stage, **explicitly invoke** the appropriate existing skill(s) via the Skill tool,
per `references/routing.md`. Manara **replaces** the skills' own auto-firing — you are the one
that calls them, so they don't double-fire. Use the **canonical** skill for each stage; only
fall to an alternate if the canonical one doesn't fit. Announce which skill you're invoking and
why before you call it.

---

## Step 3b — Behavior spec before code (sensitive slices only)

The lesson behind this: SnapClean's worst bug — a privacy leak where "solid" redaction
turned translucent and the hidden content showed through — happened because the tests
encoded a **wrong assumption** about correct behavior. Guards passed, tests were green,
the product still leaked. **Clean code that does the wrong thing is still wrong.** So on a
sensitive slice, state the invariants in plain language and get them confirmed *before*
writing tests or code — that is the moment to catch a wrong invariant before it becomes a test.

**When this applies — a judgment call, not a gate on every change:**
- **Applies** to: redaction/privacy logic, anything touching security or data safety,
  state/history mutation, anything where "looks clean but does the wrong thing" is a real
  risk, or any slice the user flags as sensitive.
- **Skip** for: trivial UI tweaks (a label, a color, a tooltip), pure refactors with no
  behavior change, or wiring with no logic. Forcing a spec on these is friction, not safety —
  proceed normally.
- **When unsure**, briefly ask: *"this one looks sensitive — want a behavior spec first?"*
  rather than guessing.

**The procedure (do this BEFORE invoking TDD or writing any code):**

1. **Read the relevant existing code first**, so the spec fits reality, not assumptions.

2. **Write a short behavior spec in plain language**, containing:
   - The **invariants** the slice must preserve (the things that must stay true no matter what).
   - What the slice **will** and **won't** do.

3. **MANDATORY for ANY redaction/privacy slice** — always state these safety invariants
   explicitly; never rely on remembering them, because this is the exact class of bug that
   caused the leak:
   - **Redaction fully hides content — never partially transparent.**
   - **Coverage is hard-edged** (a pixel is in or out; no soft/feathered leak at the boundary).
   - **Already-committed work is immutable** — never silently changed by a later control or action.

4. **Get explicit user confirmation of the spec** before writing any test or code. The user can
   correct an invariant that's wrong; **incorporate the correction before coding.**

5. **Then** proceed to the implementation (Step 4 → route to TDD): the tests must assert the
   confirmed invariants, so green tests actually mean correct behavior.

This is **brain**, not plumbing — no script. It does not change the Step 5b auto-commit flow,
and it sits inside the normal v1 stage/guard flow (it gates *entry* to implementation on a
sensitive slice; guards still run and still block afterward).

---

## Step 4 — Hint vs. delegate (user control)

- **User named a skill** ("use clean-code-guard"): treat it as a **hint** — confirm it actually
  fits the stage, then honor it.
- **User named nothing**: decide stage + skills autonomously and proceed.
- **In all cases, guards stay blocking.** A user hint never disables a guard.

On a **sensitive** slice, do not enter implementation until Step 3b's behavior spec is
written and user-confirmed — the confirmed invariants are what the tests must encode.

When a stage produces work that a guard covers, run the guard loop:
1. `py -3 "<SKILL>/scripts/run_guards.py" should-run --project "<PROJECT_ROOT>" --guard <name>`
   → if `allowed: false` (verdict `escalate`), stop and surface to the user.
2. If allowed, invoke the guard skill (Skill tool), read its pass/fail.
3. `py -3 "<SKILL>/scripts/run_guards.py" record --project "<PROJECT_ROOT>" --guard <name> --result pass|fail`
4. While `verdict` is `retry`, fix and loop. On `escalate`, **stop** — the cap (default 3) was hit.

A guard **fail blocks**: do not wave it through, do not proceed to the next stage.

---

## Step 4b — Delegate a stuck slice to Codex (guards on output + anti-loop stop)

The lesson / the wish: on large projects some slices get **stuck** — the agent loops on a problem
and can't solve it, and the instinct is to hand it to another agent (Codex) for a correct result
from a different angle. But the real danger: Claude delegates → Codex returns a fix → Claude finds
a problem → delegates again → **forever**, the two circling each other and draining usage limits
(the Codex plugin's own docs warn its review-gate can create a long-running loop). So delegation is
allowed here, but it **must** have a hard stop and its output **must** still pass the gates.

Manara **orchestrates the existing `codex-plugin-cc`** — it does **not** reimplement delegation.
It escalates **cheap → expensive**: read-only `/codex:adversarial-review` first, only then the
work-doing `/codex:rescue`. Spend the cheap resource before the expensive one.

**Detect first (mirrors the Spec Kit detect / skip / tell pattern):**
- Check whether the Codex plugin/CLI is available. If it is **not**, tell the user how to install it
  — `/plugin install codex@openai-codex`, then `/codex:setup` — and **stop**. Never silent-install,
  never silently proceed without it. Manara orchestrates the plugin, so it must exist first.

**When delegation happens (never silent — always a stated decision with a reason):**
- **User asks** ("delegate this to Codex") → Manara delegates.
- **Manara proposes** it when a slice is genuinely stuck (repeated failures / a loop it can't break)
  → surface the suggestion **with the reason** and wait for the user's OK before delegating.

**How to delegate — escalate cheap → expensive (two stages):**

*Stage 1 — `/codex:adversarial-review` (read-only, cheap, up to 3 rounds, NOT counted).* Ask Codex
to critique the stuck code / diagnose why it's failing. It doesn't edit files — Manara reads the
critique and attempts the fix itself. Run up to **3 review rounds**; these do **not** count toward
the rescue cap. If a review + Manara's own fix solves it (guards pass, build clean, user verifies),
**stop here** — never escalate to rescue. State each round ("adversarial-review round 2 of 3,
uncounted").

*Stage 2 — `/codex:rescue <clear task description>` (Codex does the work, expensive, counted).* Only
after the cheap reviews are exhausted (or clearly won't get there), hand the task to Codex to fix.
State the task plainly so Codex has the context it needs. This is the stage the **hard cap** counts.
(`--background`/`--wait`/`--resume`/`--model`/`--effort` exist on the command if useful; delegation
stays on the **current branch** — no worktree in this slice.)

**Guards on Codex's output — it gets NO free pass:**
Codex executing the work never bypasses the gates. Treat its result exactly like any other work:
1. Run the **Step 4 guard loop** on what Codex produced — clean-code-guard + test-guard — plus
   typecheck/build.
2. If the slice is **sensitive**, the Step 3b behavior spec still applies (its invariants are what
   the tests must encode).
3. If the slice has a **UI surface**, present the Step 5a checklist before verify.
4. Only after guards pass **AND** the user verifies does it reach Step 5b (commit).

**The anti-loop stop — two independent conditions, whichever hits first ends the loop:**

1. **STOP IMMEDIATELY when solved (this has priority over everything, at any stage).** The moment the
   guards pass AND typecheck/build are clean AND the user verifies, the problem is solved → **stop at
   once.** This wins during Stage 1 too: if a cheap adversarial-review round gets it fixed, stop
   there and never escalate to rescue. Solving on the first rescue means stop at the first rescue.

2. **HARD CAP — 3 `/codex:rescue` attempts for a single slice** (Stage-2 only; Stage-1 reviews are
   uncounted and never trigger the cap). If it is *not* solved, Manara may re-rescue, but never
   beyond 3 rescues. **State and count each rescue out loud** ("rescue attempt 2 of 3"). If the
   **3rd** rescue still hasn't produced a guard-passing, user-verified result → **STOP and hand back
   to the user** with a clear summary ("3 adversarial reviews + 3 Codex rescues; still failing on X —
   here's what was tried; this needs your decision"). Never silently loop past the cap. The cap is a
   **ceiling, not a target** — condition 1 always wins first; every rescue costs Codex time and usage
   limits, so prefer the fewest that solve it.

**Attempt counting (minimal — existing plumbing, no new script):** track the per-slice **rescue**
count with the existing `state.py` — read the current value, increment, and write it back before
each rescue (Stage-2 only; the Stage-1 reviews are not counted toward the cap):
```
py -3 "<SKILL>/scripts/state.py" update --project "<PROJECT_ROOT>" \
  --set codex_rescue_attempts=2 --set last_decision="Codex rescue (attempt 2 of 3): <why>"
```
Reset `codex_rescue_attempts=0` when a **new** slice starts, so the cap is per-slice.

**Boundaries (keep this slice honest):**
- Orchestrate the existing `codex-plugin-cc` — don't reimplement delegation.
- Escalate cheap → expensive: read-only `/codex:adversarial-review` (≤3, uncounted) before
  `/codex:rescue` (≤3, counted). Don't jump straight to rescue.
- Detect, then ask — never install the Codex plugin/CLI silently.
- Never let Codex's (or Manara's post-review) output skip the guards, the Step 3b behavior spec (if
  sensitive), the user verify, or the Step 5b commit.
- Never delegate silently — always a stated decision with a reason.
- Never loop past the 3-rescue cap; stop-and-hand-back instead.
- Always stop the moment it's solved, regardless of stage or attempt count.
- Current branch only — no branch/worktree management here (that's a later, v3 slice).
- Don't change Slices 1–4.

This is **brain**, not plumbing — no new script; the attempt counter reuses `state.py`. It sits
inside the normal stage/guard flow: Codex's output re-enters the Step 4 guard loop, then Step 5a
(if UI) → Step 5b, exactly like any other work.

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

## Step 5a — UX verification checklist (UI slices only — guides review, doesn't gate)

The lesson behind this: the code guards (clean-code-guard, test-guard) check code *quality* —
they **cannot** catch visual or interactive defects. A rectangle that drags stiffly, a square
that sizes wrong, a "solid" redaction that leaks, a preview that doesn't match the commit —
throughout SnapClean those were caught ONLY by a human looking in a real browser, and several
nearly slipped past because nothing prompted a *structured* check; the review was ad-hoc
"eyeball it and hope." So on a UI slice, **before** the Step 5b verify/commit, present a short
checklist of slice-specific things to verify in the browser. This **guides** the human review;
it never replaces it. UX cannot be auto-judged — the human eye stays the final gate.

**When this applies — a judgment call, like Step 3b:**
- **Applies** to slices with a **visual/interactive surface** (UI): redaction/preview, drag/shape,
  a control/slider, layout, anything the user sees or manipulates.
- **Skip** for non-visual slices — pure logic, refactors, wiring, config. A checklist there is
  noise, not safety; proceed straight to Step 5b.
- When genuinely unsure whether a slice has a meaningful visual surface, lean toward presenting a
  short checklist rather than skipping.

**The procedure (do this BEFORE Step 5b, after the slice is built and guards are clean):**

1. **Generate the checklist from what the slice actually touched** — adaptive, not a fixed list
   bolted onto every slice. Name the things most likely to break *for this specific slice*.
   Guidance by kind (examples, not an exhaustive menu):
   - **Redaction/privacy slice** → "zoom in and confirm content is fully hidden (no leak); the
     edge is hard with no faint halo; the fill covers exactly what the preview showed."
   - **Drag/shape slice** → "drag in every direction; the shape tracks the cursor smoothly; the
     committed result matches the preview exactly (no stray pixels)."
   - **Control/slider slice** → "the default value looks unchanged from before; the control's
     effect is visible; committed work doesn't change when you move it afterward."
   - **Plus, for ANY UI slice:** "previously committed work is unchanged."

2. **Present it as a suggestion and ask the user to review in the browser.** Show the few items
   and invite the user to verify them. Do **not** turn it into a mandatory tick-box and do **not**
   require ticking each item — a forced tick-gate invites mechanical "yes" answers without really
   looking, which is worse than guiding.

3. **Then proceed to the normal Step 5b verify+commit, unchanged.** The checklist guides the
   verification the user already does; it does **not** add a second mandatory gate. Step 5b's
   trigger is still exactly "blocking guards passed AND the user explicitly verified/approved."

**Boundaries (keep this slice honest):**
- It's a **suggestion that guides review**, never a hard gate — don't block the commit on ticking items.
- Don't replace human review with an auto-pass — Manara cannot judge UX itself.
- Adaptive to what the slice touched, not a rigid fixed list on every slice.
- No checklist on non-UI slices (no noise).
- Don't change Slice 1 (Step 5b auto-commit), Slice 2 (Step 3b behavior-spec), or Slice 3
  (Step 2b single-slice) behavior.

This is **brain**, not plumbing — no new script. It sits just before the Step 5b verify/commit on
UI slices and leaves that commit trigger untouched.

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
for the full list): **using-git-worktrees**, **dispatching-parallel-agents**,
**skill-creator**, semi/auto modes, review gates, and self-modification (`archive.py` stays a
stub). Manara may *detect and suggest*, but never auto-generate or self-modify in v1.

(Codex delegation is **no longer deferred** — it's enabled in v2 via Step 4b, orchestrating the
`codex-plugin-cc` (cheap `/codex:adversarial-review` → `/codex:rescue`) with guards on the output
and the 3-rescue anti-loop cap.)
