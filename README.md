# Manara 🗼

**One orchestrator skill for Claude Code: describe a task in plain language, and Manara decides
the stage, routes to the right skills, keeps the guards blocking, writes a report — and remembers
where you are across context clears so a fresh session resumes instead of restarting.**

*Manara* (مَنارة) means **lighthouse**: it tells you where you are on the path and lights the next step.

---

## The problem it solves

Two everyday pains with a big skill catalog:

1. **You have to remember which skill to run.** Was this a `to-prd` moment? Should `clean-code-guard`
   fire now or after tests? Manara makes that call for you and tells you *why*.
2. **You lose context on every clear.** Long builds get summarized or cleared, and the next session
   starts over. Manara persists progress to a per-project `.manara/` folder, so a fresh session reads
   where you were and continues from there.

`/manara` is the **single entry point**. It reads state, decides the stage, and *invokes* your
existing skills — it does not absorb or rewrite them. It's a coordinator over your catalog, not a
monolith.

---

## Install

Manara lives in your **user-level** skills directory, so Claude Code finds it in **every** project:

```
# clone (or copy) into your user skills folder
git clone <repo-url> ~/.claude/skills/manara
```

On **Windows** that path is:

```
C:\Users\<you>\.claude\skills\manara\
```

Source = install location = one place. Once it's there, just `cd` into any project and run `/manara`.

**Requirements:** Python 3 for the state/guard scripts. No other runtime — the scripts use only the
standard library (`pathlib`, `json`, `argparse`).

> **Windows install note — use `py -3`, not `python`.**
> On a default Windows setup, typing `python` or `python3` opens the Microsoft Store stub
> ("Python was not found; run without arguments to install from the Microsoft Store…") instead of
> running Python — even when Python is installed. Manara therefore invokes its scripts through the
> **`py -3`** launcher, which resolves the real interpreter. Two things to know:
> - Run the scripts as `py -3 "...\scripts\state.py" ...` (this is what `SKILL.md` does).
> - The `py -3` form also sidesteps a related gotcha: `py` alone honors a script's
>   `#!/usr/bin/env python3` shebang and re-resolves to the same Store stub; `-3` forces the real
>   Python 3 regardless. If `py -3 --version` prints a version, you're set.
>
> macOS/Linux users can use `python3` directly.

---

## Dependencies — layered, so nobody faces a long install list

### Required — the guard skills Manara routes to
These are the gates Manara keeps **blocking**. Install the ones for your work:
- `clean-code-guard` — production-code review (the canonical code gate)
- `test-guard` — test-code review
- `diagnosing-bugs` — the bug/perf diagnosis loop
- `to-prd`, `to-issues` — PRD + issue breakdown
- `grill-with-docs` — idea validation interview
- *(by stack)* `wp-guard` / `woo-guard`, and `docs-guard` for documented changes

If a routed skill is missing, Manara **detects and suggests** it — it never silently skips a guard.

### Optional — Spec Kit
Used only at the Specification stage, for large/complex work. **If it isn't installed, Manara skips
that stage and says so.** Never forced. (See the Spec Kit section below — read it before first use.)

### Self-bootstrapping (roadmap, v2)
When a needed skill is missing, Manara will be able to **offer** to generate it via `skill-creator`.
**In v1 it only detects and suggests — it does not auto-generate.**

---

## Spec Kit — read this before first use

Spec Kit (the `specify` CLI) is **optional** and lives in **its own territory**. The most common
setup mistake is running it in the wrong place — so the rule is simple and absolute:

> **Manara runs `specify init` *inside the target project*, when a formal spec is warranted —
> NEVER inside Manara's own skill folder.** And Manara **never writes into Spec Kit's own folders**
> (e.g. `specs/`); it may *decide to invoke* Spec Kit, but it does not manage Spec Kit's files.

Three locations stay distinct, and Spec Kit only ever touches the project's:

| Location | What it is | Manara's relationship |
|----------|-----------|----------------------|
| `~/.claude/skills/manara/` | Manara's source **and** install location | Manara's own folder — Spec Kit never runs here |
| `<project>/.manara/` | Per-project Manara state (resume file) | Manara reads/writes this, via its scripts only |
| `<project>/specs/` (Spec Kit) | Spec Kit's own output | Manara *invokes* `specify`, never writes here |

If Spec Kit isn't installed or isn't wanted, Manara skips the Specification stage and notes the skip
in its report. It is never a hard dependency.

---

## Usage — one end-to-end example (SnapClean)

```
cd path/to/SnapClean          # the target project
/manara                       # single entry point
> "build the SnapClean MVP — blur and redact sensitive info in screenshots before sharing"
```

What Manara does, out loud and inspectable:

1. **Cold-start check.** No `.manara/` yet → initializes one from the template. (On a later run it
   would instead read `.manara/session.md` and say *"We're at stage X, last decision Y, next Z —
   continue?"* instead of starting over.)
2. **Profile.** *"Looks like a small project — light path, fewer gates (guards still blocking). OK?"*
   You confirm → persisted to `state.json`.
3. **Stage decision.** Intent = `build-mvp`, small profile → enters at **Implementation**, skipping
   upstream gates. It states the decision **and the reason**.
4. **Routing.** Invokes `tdd` to build the slice test-first, then runs the blocking guards —
   `clean-code-guard` then `test-guard` — through `run_guards.py` (cap 3; a fail blocks and surfaces).
5. **Persist after each step.** `state.json` + `session.md` updated throughout, so a context clear
   mid-build is safe.
6. **Report.** *What ran, what was skipped and why* (e.g. "skipped Spec Kit: small profile"), guard
   results, and where you are now.

Clear the context, run `/manara` again in the same folder, and it resumes from the saved state.

---

## What Manara does *not* do in v1

- **Manual mode only** — it stops and checks in at every decision. No semi-auto or full-auto.
- **Single terminal** — no multi-terminal/worktree coordination.
- **Seed memory only** — just enough state to resume, not a full memory system.
- **Guards always blocking** — a user hint can pick *which* skill runs, but never disables a guard.

---

## Roadmap

### v2
Decision Engine proper (deep-research / architecture / prototype / MVP / refactor / tests decision
points); semi-auto and full-auto modes; review gates; a Spec Kit adapter (run/skip); skill
auto-generation via `skill-creator`; an override log that feeds learning.

### v3
Full project memory (brand, design system, target users, competitors, risks, architecture);
multi-project awareness; multi-terminal coordination via git worktrees (one terminal = one worktree
= one claimed issue; merge is always a gate, and **guards re-run on the merged result**);
cross-session / cross-project handoffs (reusing the `handoff` skill); per-project-type templates
(SaaS, Extension, Mobile, API); a Codex delegate (Codex executes, but guards still run on its output
before anything is accepted; self-modification only ever happens **after** the report and **with user
approval**, never mid-task).

---

## License

MIT (placeholder — confirm before publishing).
