# Profiles — small vs large

A project's **profile** decides how many gates Manara runs. It is proposed by Manara in
Step 1, confirmed/corrected by the user, and then **fixed for the project** (persisted to
`state.json`). It does not change task to task.

> **Hard rule that no profile relaxes:** guards are **always blocking**. Small projects run
> *fewer* gates, but every gate they do run still blocks on failure. "Small" buys you a
> shorter path, never a softer one.

---

## Small project — light path

For scripts, small tools, single-purpose extensions, throwaway-ish work.

**Skips / shortens:**
- Validation (grill-with-docs): optional. Offer it; don't force it.
- Formal Spec Kit (`specify`): skipped by default — too heavy for the size.
- PRD/issues: a lightweight plan instead of full to-prd + to-issues, unless the user asks.
- docs-guard, domain-modeling, codebase-design: skipped unless the work clearly warrants docs.

**Always runs (blocking):**
- The implementation guards on produced work: **clean-code-guard**, **test-guard**.
- diagnosing-bugs for fix-bug intent; the Review guards for review-pr intent.

Entry depth: build-mvp / add-feature enter close to **Implementation**.

---

## Large project — full path

For real products, multi-feature codebases, anything shipping to users (e.g. a SaaS or a
published extension).

**Runs the full ladder:**
- Validation: **grill-with-docs** before building.
- Specification: **to-prd** → **to-issues**, and **Spec Kit** (`specify`) when the work is
  complex enough to warrant a formal spec.
- Architecture vocabulary when designing modules: **codebase-design**, **domain-modeling**.
- Implementation: **tdd** approach, then **clean-code-guard** + **test-guard** (blocking),
  plus stack guards (wp-guard / woo-guard) and **docs-guard** on documented changes.

Entry depth: build-mvp enters at **Validation**; add-feature enters at **Specification**.

---

## Proposing the profile (Step 1)

Infer from the task description and project size, then **propose** — don't impose:

> "This looks like a **small** project — I'd run the light path (fewer gates, guards still
> blocking). OK, or treat it as large?"

Persist the confirmed profile with `state.py update --set profile=small|large`.
