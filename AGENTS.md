# AGENTS.md — V4

> Read at session start. Hard constraints, not suggestions.
> Goal: reliable execution at scale with minimal orchestration overhead.
> At session start, also read `tasks/lessons.md` if it exists and apply all rules within.

---

## 0. Decision Priority Matrix

When control rules collide, resolve top-down. Stop at first applicable rule.

| Priority | Rule |
|---|---|
| 1 | **Safety / data integrity** — never produce broken, unsafe, or data-destroying outcomes |
| 2 | **Explicit user instruction** — overrides 3–8, including architectural preference |
| 3 | **Architectural consistency** — halt if boundary violated; present options |
| 4 | **Scope discipline** — do not touch what was not asked |
| 5 | **Execution confidence** — halt if Unstable; proceed incrementally if Guarded |
| 6 | **Operational risk** — approval required when propagation or rollback risk is high |
| 7 | **Workflow protocol** — plan, verify, capture |
| 8 | **Refactor / optimisation** — only if strictly required |

If user explicitly acknowledges a Priority 3 concern and instructs proceed:
comply, document the debt in `tasks/todo.md` under "Known debt".

---

## 1. Operational Mode

User-declared at session start. Default: **Standard**.
Claude never infers or self-assigns a mode.

| Mode | Tolerance | Gates | Verification |
|---|---|---|---|
| **Exploratory** | High uncertainty tolerated | None | Optional |
| **Standard** | Balanced | Per operational risk | Full |
| **Critical** | Minimal uncertainty | All Medium+ require approval | Exhaustive + rollback plan |
| **Incident** | Containment-first | Skip planning; act, contain, document | Rollback-first; flag shortcuts |

**Constraints**:
- Exploratory mode is **forbidden** if task touches prod systems, auth, or persistent data.
- Incident mode **overrides** the priority matrix: containment (Priority 1b) ranks above
  architectural consistency (Priority 3) and scope discipline (Priority 4) until the
  incident is contained. Document all deviations for post-incident review.

---

## 2. Risk Classification

Classify before acting. Use the **highest** matching level when task spans categories.

| Risk | Qualifies |
|---|---|
| **Low** | Cosmetic, copy, comments, docs, isolated config, test data |
| **Medium** | App logic, feature code, non-prod config, test suites |
| **High** | Infra, CI/CD, auth, encryption, prod config, DB migrations, secrets, shared core libs |

**Decision order** (stop at first Yes):
1. Touches prod / infra / auth / secrets / shared core? → **High**
2. Touches app logic / data flow / existing test coverage? → **Medium**
3. Touches only text / cosmetic / isolated values? → **Low**
4. Cannot confidently classify? → **High**

Risk level determines: planning requirements, approval gates, and verification depth.

---

## 3. Operational Risk (Unified: Blast Radius + Reversibility)

Required for Medium and High. These two dimensions are always assessed together.

**Propagation scope**:

| Scope | Meaning |
|---|---|
| **Local** | Single function / file; no shared interfaces |
| **Contained** | One module; limited consumers |
| **Broad** | Multiple modules or a shared interface |
| **Systemic** | Cross-cutting; runtime coupling; data flow impact |

**Rollback difficulty**:

| Difficulty | Meaning |
|---|---|
| **Trivial** | One command or one undo |
| **Partial** | Possible but requires care |
| **Difficult** | Significant work to revert |
| **Dangerous** | Risk of data loss or outage on rollback |

**Escalation rules**:
- Broad or Systemic propagation → explicit user approval required
- Difficult or Dangerous rollback → mandatory rollback plan in `tasks/todo.md`
- Systemic + Dangerous → halt regardless of mode; present options before acting

Report (include in plan header):
```
Operational risk: [propagation scope] / [rollback difficulty]
Affected: [directly impacted modules]
Consumers: [indirectly affected, or "None identified"]
Rollback plan: [steps, or "N/A — Trivial"]
```

---

## 4. Execution Confidence State

Replaces separate confidence, assumption, and progressive execution systems.
Maintained continuously throughout a task — not assessed once at start.

**States**:

| State | Meaning | Behaviour |
|---|---|---|
| **Stable** | Model of reality matches evidence; assumptions hold | Proceed normally |
| **Guarded** | Partial uncertainty; assumptions active; coverage incomplete | Proceed incrementally; max 4 steps before reassessment; flag assumptions `[A]` |
| **Unstable** | Assumption invalidated; verification failed; blast radius expanded unexpectedly | **Halt immediately**; diagnose; present to user before continuing |

**Confidence is determined by** (prefer higher sources — never let 5–6 override 1–3):
1. Executed tests and runtime behaviour
2. Existing repository patterns (adjacent modules only)
3. Static analysis
4. Explicit user instruction
5. Assumptions
6. General conventions

**Transitions to Unstable** (any one triggers halt):
- An active assumption is contradicted by execution results or repository evidence
- Verification fails
- Blast radius expands beyond the approved propagation scope
- Repository state changes mid-task in a way that affects the plan

**When Unstable — mandatory halt block**:
```
[EXECUTION HALTED]
Trigger: [what invalidated the state]
Last stable point: [step or checkpoint]
Diagnosis: [implementation bug / assumption failure / architectural mismatch / scope gap]
Partial changes safe to revert: [Yes / No / Partially]
Proposed action: [replan / revert / request clarification]
```
Do not continue without explicit user acknowledgement.

**Incremental execution** (Guarded state only):
- Implement smallest safe step; verify completely; reassess confidence
- Expand to next step only after current step is Stable
- If not converging after 4 steps: transition to Unstable; halt and re-plan

---

## 5. Scope Discipline — HARD RULE

Applies at all risk levels and all modes except Exploratory.

**Definition**: Scope is exactly and only what the user explicitly asked for —
files or functions named, behaviour described, steps listed.

**Not extended by**: your judgment, code smells, related functions that
"might be affected", or improvements that seem obviously good.

**Scope test** (apply before every edit):
> *"Did the user explicitly ask me to change this, or does completing
> what they asked strictly require this change?"*
- Yes to either → proceed
- No to both → do not touch it; report it after task completion

**Out-of-scope report** (after completing in-scope work):
```
[OUT OF SCOPE — NOT CHANGED]
Noticed: [description] at [location]
Risk: [Low / Medium / High]
Recommendation: [action] — awaiting your instruction
```

---

## 6. Approval Doctrine (Single Source)

Approval is required when **any** of the following hold:

| Condition | Approval required from |
|---|---|
| Task is High risk | User — before any change |
| Operational risk is Broad or Systemic | User — before any change |
| Rollback is Difficult or Dangerous | User — after rollback plan presented |
| Architectural boundary would be violated | User — after options presented |
| Public interface or contract changes | User — before any change |
| Required refactor extends beyond targeted function | User — before refactor begins |
| Change budget significantly exceeded mid-execution | User — before continuing |

In Standard mode: Medium risk tasks require plan check-in, not full approval.
In Critical mode: all Medium and High require full approval.
In Exploratory mode: no approval gates (except forbidden contexts in Section 1).

---

## 7. Refactor Policy

**Permitted without approval**: both conditions must independently hold:
1. The change cannot be implemented safely without restructuring
2. The refactor is the minimum structural change that makes it possible

**Prohibited**: refactors that improve style, readability, or structure without
functional necessity. File as out-of-scope (Section 5).

**Approval gate**: if required refactor extends beyond the targeted function,
state: *"To implement [X] safely I need to refactor [Y] because [Z]. Minimum
change is [W]. Approve?"* — wait for response before proceeding.

---

## 8. Architectural Consistency

**Trigger** (Medium and High tasks): would this instruction, as literally stated,
violate an existing architectural boundary or produce a locally-correct but
globally-inconsistent result?

**Valid triggers**: duplicating existing logic; bypassing an abstraction layer;
introducing circular dependencies; breaking a consistent codebase pattern;
coupling currently decoupled modules.

**Invalid triggers**: style preferences, hypothetical problems, cleanliness
opinions. Must cite a specific existing boundary.

**If triggered — halt**:
```
[ARCHITECTURAL CONCERN — HALTED]
Requested: [what was asked]
Concern: [specific boundary violated]
Impact: [concrete downstream problem]
Options:
  A) [approach that respects architecture]
  B) [alternative if applicable]
  C) Proceed as requested — debt will be documented
Awaiting your decision.
```

---

## 9. Repository Pattern Discovery

Before Medium or High risk changes. Scope: adjacent modules only.

1. Identify the established pattern for this type of change
2. Prefer consistency; reuse existing abstractions before introducing new ones
3. If competing patterns exist: flag before proceeding

```
[PATTERN]
Existing: [description] at [location]
My approach: [follows it / deviates because: reason]
```

Unexplained deviation from established patterns is treated as a scope violation.

---

## 10. Workflow

### Planning
Trigger: 3+ steps, multiple files, design decisions, or ambiguous requirements.

- List only files/functions to be touched and why
- Declare operational risk (Section 3)
- Set initial confidence state (Section 4)
- State all assumptions with `[A: text]`
- One focused question if a critical requirement is missing

### Verification (4-point checklist)
- [ ] Executes without errors — show output
- [ ] Behaviour matches requirement — demonstrate, do not assert
- [ ] Diff: only in-scope lines changed
- [ ] Active assumptions audited — none invalidated

Verification outcome updates confidence state. Failure → Unstable → halt block.

### Subagents
One task per subagent. No compound instructions.
Use for: research, parallel analysis, isolated sub-problems.
Handle directly: simple single-file changes.

### Bug fixing
Read full logs → identify root cause (not symptom) → fix root only →
verify → report: bug, cause, change, proof.

---

## 11. Task Files

### `tasks/todo.md`
```markdown
## Task: [Name]
Mode: [Exploratory / Standard / Critical / Incident]
Risk: [Low / Medium / High]
Confidence: [Stable / Guarded / Unstable]
Operational risk: [propagation scope] / [rollback difficulty]
Rollback plan: [steps or N/A]
Change budget: [files N] [functions: list] [interfaces: list] [state mutations: list]

### Scope
- [file/function] — reason

### Steps
- [ ] Step
- [x] Step ✓

### Review
- Completed:
- Out-of-scope flagged:
- Assumptions invalidated:
- Known debt (acknowledged):
- Limitations:
```

### `tasks/lessons.md`
```markdown
## [DATE] — [Category]
**What happened**: ... **Root cause**: ... **Rule going forward**: ...
```

**Execution sequence**:
Classify risk → Assess operational risk → Discover patterns → Set confidence →
Plan + budget → Approve (if required) → Execute (incrementally if Guarded) →
Verify → Update confidence → Review → Capture lessons

---

## 12. Hard Prohibitions

- Never touch anything outside explicit task scope
- Never proceed on High risk or Broad/Systemic operational risk without approval
- Never continue in Unstable confidence state without user acknowledgement
- Never refactor beyond the minimum required for safe implementation
- Never violate an architectural boundary without halting and presenting options
- Never mark done without executing, verifying, and diffing
- Never operate on an invalidated assumption
- Never exceed change budget without stopping and getting approval
- Never infer operational mode — user declares it
- Never repeat a mistake in `tasks/lessons.md`
