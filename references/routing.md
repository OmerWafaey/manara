# Routing — stage → skill(s) to call

This is the catalog Manara chooses from in Step 3. It is built from the skills **actually
installed** on this system, not assumptions. Manara **replaces** the skills' own auto-firing:
it is the single caller, so skills never double-fire.

**One canonical skill per stage.** Where several skills overlap, exactly one is *canonical*
(the one Manara fires). The rest are *alternates* — used only if the canonical one plainly
doesn't fit, or when the user explicitly hints one (Step 4). Guards (⛔) are **blocking** and
run through `scripts/run_guards.py` (cap 3); a fail is never waved through.

---

## Stage → canonical skill

| Stage | Canonical skill (Manara fires) | Alternate / fallback | When / notes |
|-------|--------------------------------|----------------------|--------------|
| Validation (Idea→Validation) | `grill-with-docs` | — | Relentless interview to sharpen the plan; emits ADRs + glossary. Large profile; optional for small. |
| Specification — PRD | `to-prd` | — | Synthesize the conversation into a PRD on the issue tracker. |
| Specification — breakdown | `to-issues` | — | Break a plan/PRD into grabbable tracer-bullet issues. |
| Specification — formal spec | Spec Kit (`specify` CLI) | skip | Run `specify init` **inside the target project**. Optional; large/complex only. Never write Spec Kit's `specs/` yourself. |
| Architecture (designing modules, large) | `codebase-design` | `domain-modeling` | Deep-module vocabulary; `domain-modeling` for ubiquitous language / ADRs. |
| Implementation — approach | `tdd` | `superpowers:test-driven-development` | Test-first red-green-refactor when building a feature/bugfix. |
| Implementation — code guard ⛔ | `clean-code-guard` | `/code-review`, `coderabbit`, `/simplify` | The blocking code gate. Alternates are manual review commands, not the gate. |
| Implementation — test guard ⛔ | `test-guard` | — | Reviews produced test code. Distinct role from `tdd` (which writes tests). |
| Implementation — docs guard ⛔ | `docs-guard` | — | Only when a change documents behavior (READMEs, API docs, docstrings). |
| Implementation — stack guard ⛔ | `wp-guard` / `woo-guard` | — | Swap in by stack: `wp-guard` for WordPress, `woo-guard` for WooCommerce. |
| Diagnosis (Bug→Diagnosis) | `diagnosing-bugs` | `superpowers:systematic-debugging` | Canonical bug/perf loop. The fix then re-enters the code/test guards. |
| Review (PR / diff) ⛔ | `clean-code-guard` + `test-guard` + `docs-guard` | `/code-review`, `coderabbit` | Guards blocking here too; a failing review stops the merge path. |

---

## Overlap resolutions (canonical vs alternates)

These collisions are resolved deliberately so Manara never double-fires:

1. **Bug diagnosis** — canonical **`diagnosing-bugs`** (installed user skill).
   Fallback: `superpowers:systematic-debugging`. Fire one, not both.
2. **Code review/quality** — canonical **`clean-code-guard`** (the actual blocking gate).
   Alternates `/code-review`, `coderabbit`, `/simplify` are manual review *commands*; Manara
   does not auto-fire them — only on an explicit user hint.
3. **Test-first vs test review** — **not** an either/or. `tdd` is the *implementation approach*
   (writes tests first); **`test-guard`** is the *blocking review* of the resulting test code.
   Different stages, different artifacts — both kept, neither double-fires.
4. **Docs** — `docs-guard` is the canonical docs gate; it runs only when a change actually
   documents behavior, so it does not collide with the code/test guards on the same artifact.

---

## Intent → stage → skills (quick reference)

| Intent | Entry stage (see `stages.md`) | Skills fired (in order) |
|--------|-------------------------------|-------------------------|
| `build-mvp` | Validation (large) / Specification (small) | grill-with-docs → to-prd → to-issues → [Spec Kit] → tdd → clean-code-guard ⛔ → test-guard ⛔ |
| `add-feature` | Specification (large) / Implementation (small) | [to-prd → to-issues] → tdd → clean-code-guard ⛔ → test-guard ⛔ → [docs-guard ⛔] |
| `review-pr` | Review | clean-code-guard ⛔ → test-guard ⛔ → [docs-guard ⛔] |
| `fix-bug` | Diagnosis | diagnosing-bugs → clean-code-guard ⛔ → test-guard ⛔ |

`[ ]` = conditional on profile / whether the work touches that artifact (see `profiles.md`).

---

## Available but DEFERRED to v2/v3 — Manara knows, does NOT invoke in v1

These powerful skills are installed but belong to later versions. v1 may **detect and suggest**
them, but must **not** call them:

| Skill | Belongs to | Why deferred |
|-------|-----------|--------------|
| `codex-delegate` | v3 | Delegate implementation to Codex; guards must still run on its output before acceptance. Not in v1. |
| `superpowers:using-git-worktrees` | v3 | One terminal = one worktree = one claimed issue. v1 is single-terminal only. |
| `superpowers:dispatching-parallel-agents` | v3 | Multi-agent parallelism. v1 is manual, single-track. |
| `skill-creator` | v2 | Auto-generate a missing skill. v1 only detects/suggests a gap; never auto-generates. |

Also installed but **not** part of task routing in v1:
- `handoff` — cross-session handoff document (v3 cross-session/cross-project handoffs).
- `setup-pre-commit`, `git-guardrails-claude-code` — environment setup, not task-stage routing.
- `teach` — tutoring, outside the build/fix/review flow.

Self-modification stays a stub (`scripts/archive.py`): Manara does not edit its own folder in v1.
