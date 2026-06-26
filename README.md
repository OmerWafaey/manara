# Manara 🗼

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.7+](https://img.shields.io/badge/Python-3.7%2B-blue.svg)](https://www.python.org/)
[![Built for Claude Code](https://img.shields.io/badge/Built%20for-Claude%20Code-d97757.svg)](https://claude.com/claude-code)

*Manara* (مَنارة) means **lighthouse** — something that tells you where you are and lights the next step.

---

## What this is, in plain terms

Manara is a helper for [Claude Code](https://claude.com/claude-code) that **keeps your project on track**.

You talk to it in normal language — *"build the login page,"* *"fix this bug,"* *"review my changes"* — and Manara figures out what to do next, runs the right tools in the right order, and **remembers where you left off** so you can pick up later without starting over.

### Why it helps

Working on a real project with Claude Code, two things tend to go wrong:

1. **You have to remember which tool to run, and when.** Should you write the spec first? Run the code reviewer now, or after the tests? Manara makes that call for you — and always tells you *why*.
2. **Long sessions lose their memory.** When a chat gets cleared or summarized, the next session forgets what you were doing and starts from scratch. Manara writes your progress to a small file inside your project, so a fresh session reads it and **continues where you were**.

Think of it as one front door (`/manara`) that quietly coordinates the tools you already have — it doesn't replace them, it just makes sure the right one runs at the right moment.

---

## Install

### Easy way (recommended)

Run one command. It downloads Manara into the right folder for you, and you can re-run it anytime to update.

#### macOS / Linux

```bash
curl -fsSL https://raw.githubusercontent.com/OmerWafaey/manara/main/install.sh | bash
```

#### Windows (PowerShell)

```powershell
irm https://raw.githubusercontent.com/OmerWafaey/manara/main/install.ps1 | iex
```

That's it — Manara installs to `~/.claude/skills/manara` so Claude Code finds it in **every** project.

### Manual way (fallback)

Manara is a Claude Code **skill**, not an npm package — `npm install` won't put it in the right place. To install by hand, just clone it into your user-skills folder:

```bash
git clone https://github.com/OmerWafaey/manara.git ~/.claude/skills/manara
```

On **Windows** that folder is `C:\Users\<you>\.claude\skills\manara\`.

**Requirements:** Python 3.7 or newer (for the small state/progress scripts). Nothing else to install — the scripts use only Python's built-in library.

> **Windows tip — use `py -3`, not `python`.**
> On a fresh Windows setup, typing `python` often opens the Microsoft Store instead of running Python. Manara avoids this by calling its scripts through the **`py -3`** launcher, which always finds the real Python 3. If `py -3 --version` prints a version number, you're good. (macOS/Linux users can use `python3` directly.)

---

## ⚠️ Important: run `/manara` from inside your project folder

> **Always run `/manara` from inside your project folder.** Manara reads the *current directory* to find your saved `.manara/` progress file. If you run it from the skills folder — or anywhere that isn't your project — it can't find your state, and it won't be able to resume.

This is the single most common mistake, and the fix is simple:

```bash
cd <your-project>     # the folder you're actually building
/manara               # now Manara can read and resume your progress
```

---

## How to use it

Open your project in Claude Code and run `/manara`. Here's a typical first run:

```bash
cd <your-project>
/manara
> "build the MVP — a tool that blurs sensitive info in screenshots before sharing"
```

Manara then works out loud, so you can see every decision:

1. **First run?** It sets up a fresh `.manara/` progress file for this project. (Next time, it instead reads that file and says *"We're at this stage, last we did X, next is Y — keep going?"*)
2. **Sizing up the work.** *"This looks like a small project — I'll take the light path with fewer checkpoints, but the quality checks still run. Sound good?"* You confirm.
3. **Deciding the next step** — and explaining the reasoning, not just the action.
4. **Running the right tools** — for example, building a feature test-first, then running the code and test reviewers before moving on. A failed quality check **stops and tells you**, rather than slipping through.
5. **Saving progress as it goes**, so a cleared chat mid-build is never a problem.
6. **A short report** — what ran, what it skipped and why, and where you are now.

Clear the chat, run `/manara` again in the same folder, and it picks right back up.

### The quality checks always run

Manara leans on a set of "guard" tools — code review, test review, and so on. You can hint *which* one runs, but **you can't switch a guard off**. That's on purpose: it's what keeps quality from quietly slipping. If a guard you need isn't installed, Manara points it out instead of silently skipping it.

---

## A note on Spec Kit (optional)

For larger, more complex projects, Manara can use [Spec Kit](https://github.com/github/spec-kit) (the `specify` tool) to write a formal spec first. This is **optional** — if you don't have it installed, Manara simply skips that step and tells you it did.

One rule worth knowing: Spec Kit always runs **inside your project**, never inside Manara's own folder. Three folders stay separate and never get mixed up:

| Folder | What it holds |
|--------|---------------|
| `~/.claude/skills/manara/` | Manara itself (you install it here, once) |
| `<your-project>/.manara/` | Your saved progress for that project |
| `<your-project>/specs/` | Spec Kit's output, if you use it |

---

## What Manara doesn't do (yet)

This is **v1**, intentionally small and careful:

- **It always checks in with you** before each decision — no silent auto-pilot.
- **One terminal at a time** — no coordinating parallel sessions.
- **Just enough memory to resume** — not a full long-term memory yet.
- **Quality checks can't be turned off** — a hint can pick *which* one runs, never whether it runs.

---

## Roadmap

**v2** — a smarter decision engine (when to research vs. prototype vs. refactor), optional semi-automatic and fully-automatic modes, review checkpoints, a proper on/off adapter for Spec Kit, and the ability to generate a missing tool on the spot.

**v3** — real long-term project memory (your product, design system, users, competitors, architecture), awareness across multiple projects, coordinating several terminals at once, handoffs between sessions, ready-made templates per project type (SaaS, browser extension, mobile, API), and the option to delegate work to other coding agents — with the quality checks still running on whatever they produce.

---

## License

[MIT](LICENSE) © 2026 Omar Wafaey
