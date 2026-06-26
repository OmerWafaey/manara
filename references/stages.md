# Stages — the ladder Manara reasons over

Manara models a task as a position on a **ladder of stages**. The job of Step 2
(stage decision) is to place the task on this ladder *explicitly* so it is obvious
when the placement is wrong.

> **Entry-point rule (do not always start at the top).**
> The default entry stage comes from the user's *intent*. But if `state.json` already
> has a `stage`, **that wins** — resume there, do not walk the ladder from the bottom.
> A fresh idea enters at Validation; a bug enters at Diagnosis; a half-built feature
> with saved state re-enters wherever it left off.

---

## The stages

### 1. Validation  (Idea → Validation)
Pressure-test the idea before building: who is it for, what's the smallest valuable
slice, what would make it fail. Output is a sharpened plan, not code.
- Canonical skill: **grill-with-docs** (relentless interview; emits ADRs + glossary).
- Small projects may skip or shorten this (see `profiles.md`). Large projects do not.

### 2. Specification  (Idea → Spec)
Turn the validated idea into something buildable: a PRD, a set of grabbable issues,
and — when warranted — a formal spec via Spec Kit.
- PRD: **to-prd** · Breakdown into issues: **to-issues**
- Formal spec (optional, large/complex): **Spec Kit** (`specify` CLI) — run *inside the
  target project*, never inside Manara's folder. If Spec Kit isn't wanted/installed,
  skip and say so.

### 3. Implementation  (Feature → Implementation)
Build the slice. Test-first where it fits, then the blocking guards run on the output.
- Approach: **tdd** (red-green-refactor) when building a feature/bugfix test-first.
- Blocking guards on produced work: **clean-code-guard** (production code),
  **test-guard** (test code). Domain-specific guards swap in by stack (see `routing.md`).

### 4. Diagnosis  (Bug → Diagnosis)
Reproduce, isolate, and fix a defect or regression. The *fix* then re-enters
Implementation's guards before it's accepted.
- Canonical skill: **diagnosing-bugs**.
- After the fix: **clean-code-guard** / **test-guard** on the change (blocking).

### 5. Review  (PR / change review)
Review existing changes (a PR or a working diff) without necessarily having authored them.
- **clean-code-guard** (code), **test-guard** (tests), **docs-guard** (docs).
- Guards are blocking here too: a failing review surfaces and stops the merge path.

---

## Intent → default entry stage

v1 supports four intents. Map the plain-language task to one, then enter at its stage
(unless saved `state.stage` overrides):

| Intent       | Phrases that signal it                              | Default entry stage |
|--------------|-----------------------------------------------------|---------------------|
| `build-mvp`  | "build the X MVP", "start a new app/tool", "from scratch" | Validation (large) / Specification (small) |
| `add-feature`| "add feature Y", "implement Z", "extend X"          | Specification (large) / Implementation (small) |
| `review-pr`  | "review this PR", "is this safe to merge", "audit this change" | Review |
| `fix-bug`    | "fix this bug", "X is broken/throwing/failing/slow", "diagnose" | Diagnosis |

The profile (small vs large) shifts the *entry depth* for build/feature intents:
small projects skip the upstream gates and enter closer to Implementation. Review and
fix-bug enter at the same stage regardless of profile. See `profiles.md`.

---

## Moving between stages

- Advance only one stage at a time, persisting state after each (Step 5).
- Implementation and Diagnosis **always** pass through their blocking guards before
  the stage is marked done. A user hint never skips a guard.
- When the ladder is finished (or the slice is shipped), write the report (Step 6).
