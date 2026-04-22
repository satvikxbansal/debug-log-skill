# Roadmap

Phase 1 is shipped in v2.0 (below). Phases 2–8 are scoped here with honest trade-offs — what each phase buys, what it costs, and whether it changes the skill's shape in a good or a bad way. If you skim one section, skim the "Evaluation" under each phase.

## Guiding principles

These are the guardrails every future phase has to respect; we have seen other projects in this space drift because they forgot one of them.

1. **Prose first, tool second.** The log is a Markdown file a human can read end-to-end without any tool installed. Every automation layer we add must keep that property — the skill must remain useful on a laptop with no Python, no MCP server, no CLI. Everything downstream is additive.
2. **Discipline cannot be delegated to tools.** The most valuable act in this skill is the *author's think-before-coding* moment. Any CLI subcommand that shortcuts past that (a chatty `dls append` wizard, an auto-generated entry) is an anti-feature even if it feels helpful.
3. **One schema source of truth.** `scripts/debug_log_schema.py` is the vocabulary. Every validator, every CLI, every MCP tool, every test fixture reads from it. Adding a second source (JSON schema, YAML config, hard-coded list in the MCP server) re-introduces the drift we just fixed.
4. **Append-only semantics.** Entries are never mutated except for the `[OBSOLETE]` tombstone. Any tool that writes to `DEBUG_LOG.md` must preserve this — including the MCP server.
5. **Zero-dependency distribution where possible.** The skill ships as a zip. The validator is stdlib-only. The CLI should be stdlib-only. MCP / embeddings can require deps — but they must be opt-in, not blocking.

---

## Phase 1 — Trustworthy contract (shipped in v2.0)

Reconcile the gap between what the docs promised and what the validator enforced, and centralise the schema so that gap can't reopen.

Delivered:
- `scripts/debug_log_schema.py` — single source of truth for vocabulary (11 fields, 12 severities, 14 Root Cause Categories, 7 track tags, 124 semantic tags).
- Validator refactor: imports schema; strips HTML comments; enforces `[OBSOLETE]`/`Supersedes DL-NNN` in both directions; caps track tags at 2; `--strict` flag for closed semantic vocabulary.
- 17 fixture tests in `tests/fixtures/` + `tests/run_tests.py`.
- Docs reconciled (severity, track-tag count, skill paths, workflow header, CHANGELOG migration guide, init.sh scaffolds full integration set).
- `scripts/package-skill.sh` exclude lists unified across rsync and fallback branches.

---

## Phase 2 — Python CLI (`dls`)

A stdlib-only Python entry point that wraps the validator and adds read-only analytics. Cross-platform (no bash required), `--json` output so agents can call it as a tool.

### Proposed subcommands

| Subcommand | Shape | Notes |
|---|---|---|
| `dls lint [--strict] [PATH]` | Exit 0/1 | Alias for the validator, default arg `DEBUG_LOG.md`. |
| `dls stats [PATH]` | Prints counts | Total / active / obsolete; breakdown by Root Cause Category, track, severity; top semantic tags; median iterations; "rules repeating 3+ times → promote". |
| `dls query --file PATH --tag #Compose --category "Race Condition" [--json]` | Lists DL-NNN matches | What you would otherwise compose from two greps. `--json` prints a machine-readable hit list for agents. |
| `dls doctor [PATH]` | Health check | Wraps lint + flags soft problems (single-use tags, repeat-3 promotion candidates, stale [OBSOLETE] chains). Exit 0 even on warnings. |
| `dls supersede DL-NNN --reason "..."` | Writes a new entry | Prepends `[OBSOLETE]` to the named entry and appends a superseder stub with correct `Supersedes DL-NNN` line + placeholder fields. Author still fills the stub in. |

**Explicitly NOT in Phase 2:** `dls append`, `dls init` (we have `init.sh`), `dls promote`. Rationale under "Concerns" below.

### Evaluation

**Why Phase 2 helps the skill:**
- **Cross-platform parity.** Today the packaging and init scripts are Bash. Windows users either use WSL or cannot run them. A Python CLI means one `python3 -m dls lint` invocation works everywhere Python 3.11 does — which is more places than Bash.
- **Agent-tool-call surface.** `dls query --json` gives LLM agents a structured retrieval tool. Right now agents shell out to `grep`, which returns line-numbered text that the model has to re-parse. A CLI is strictly easier for the model to consume reliably.
- **Stats are a real missing signal.** "42% of entries are Race Conditions" is the kind of insight the log is supposed to surface — but today a human has to compute it by hand. `dls stats` makes it one command.
- **Supersede hygiene.** `dls supersede DL-042` with a template-enforced `Supersedes DL-042` line prevents the exact mistake we fixed in the example log (DL-008 mis-marked as `[OBSOLETE]`). The tool writes the handshake correctly by construction.

**How Phase 2 could alter the skill for the worse:**
- **Tool-first drift.** If the README starts with `pip install dls`, the pitch becomes "install our CLI" rather than "adopt this practice." Some teams will skip. **Mitigation:** the skill stays copy-pastable; CLI is positioned as optional power user tooling; SKILL.md keeps teaching `grep DEBUG_LOG.md` as the primary interface.
- **Replacement-of-discipline risk.** If we add `dls append` that prompts for 11 fields interactively, users will type "bug fix" × 11 and move on. The whole point of the format is to force the *author to think*. **Mitigation:** Phase 2 has no `append`. Ever. Authors write entries in their editor — that's the design, not a deficiency.
- **Two-code-paths drift.** CLI + validator both parse the log. **Mitigation:** both import `debug_log_schema.py` and `validate_debug_log.py`'s parsing helpers; adding a `dls` layer on top, not a reimplementation.
- **Python version spread.** 3.11 features (PEP 604 union syntax) are in the validator already; if we set 3.9 as the floor we lose some quality of life. **Mitigation:** pin 3.11+. That matches the CI workflow.

**Verdict:** **Yes, build Phase 2.** It's additive, respects the principles, and closes real gaps (cross-platform, agent retrieval, stats, supersede hygiene). Do NOT add write-mutating subcommands beyond `supersede`.

### Concrete layout

```
scripts/
  dls/
    __init__.py       # exposes __main__ for `python -m dls`
    __main__.py       # dispatch
    schema.py         # re-export from ../debug_log_schema.py (no duplicate)
    parse.py          # split_entries / parse_fields (shared w/ validator)
    cmd_lint.py       # wraps validate_debug_log.main
    cmd_stats.py
    cmd_query.py
    cmd_doctor.py
    cmd_supersede.py
README.md             # `python -m dls lint` instead of `dls` until we add
                      # a setuptools entry point (a later polish).
```

Shipping without a packaging step means users run `python -m dls <cmd>`. A `setup.py` / `pyproject.toml` and a `dls` shim are a small polish step that lands once the command set is stable.

---

## Phase 3 — Environment-aware tooling

Make the skill *aware* of the project it's installed in, so the active pre-flight and the entry template both pull context automatically.

Proposed capabilities:
- **Track detection from the CLI** (`dls doctor` prints the detected tracks; `init.sh` already does this server-side).
- **Environment auto-fill.** `dls supersede` and a future entry-writing flow populate the `Environment` field from `package.json` / `build.gradle.kts` / `Package.swift` / `pyproject.toml` / `go.mod`.
- **File-path validation.** The `File(s)` field is checked against the working tree — DL-NNN entries that reference a non-existent file surface as a warning (might be a renamed file; requires author disposition).
- **Commit SHA auto-link.** When a `Fix:` field says `commit abc1234`, `dls doctor` checks that SHA exists in the repo history.

### Evaluation

**Pros:** Removes the tax of hand-copying SDK versions into every entry. Catches `File(s)` fields that have rotted after a rename. Makes the log a live artifact.

**Cons / risk:** Environment auto-fill can get it *wrong* — different PR branches ship with different `package.json` versions, and the entry's environment should reflect what was shipped *when the bug fired*, not today's state. So auto-fill is a *suggestion* at authoring time, not a rewriter of historical entries.

**Verdict:** Good, but scope down. Ship it as suggestions from `dls doctor` first; only add auto-fill to `dls supersede` once the suggestions are accurate ≥95% of the time. Never rewrite historical entries based on current environment.

---

## Phase 4 — Retrieval intelligence

Make pre-flight smarter than plain grep. This is where the log stops being "searchable by regex" and starts being "retrievable by meaning."

Proposed capabilities:
- **Symbolic ranking for `dls query`.** Not embeddings yet: given a file path, extract the directory, extension, and stack-trace-looking substrings; rank entries by shared tags × shared file × shared category.
- **Diff-aware retrieval.** `dls query --diff $(git diff HEAD^)` surfaces DL entries whose `File(s)` list overlaps the diff or whose Root Cause Category is a known failure mode for the touched API. Built on top of symbolic ranking; agents can call this directly.
- **Stack-trace parser.** Given a stack-trace string, surface entries whose `Symptom` or `File(s)` contains the firing frame. Works for the three common stack formats (Python tracebacks, JS `Error` strings, JVM stacks).
- **Version-aware ranking.** If DL-042's `Environment` says "Compose 1.6" and the project is on Compose 1.7, down-weight it. If DL-042 was later `[OBSOLETE]`'d by DL-088, hide it from active retrieval and surface DL-088 instead.

### Evaluation

**Pros:** This is where the skill gets distinctive. "The LLM grep'd the log and found three entries" is good; "The LLM got a ranked list that already filtered out obsolete and version-mismatched entries" is much better.

**Cons / risk:** Ranking is where LLM-memory systems usually go wrong — opaque scores cause the agent to overtrust irrelevant entries. Every result must carry a *reason string* explaining why it ranked ("shared file `PostCard.tsx`; shared category `Hydration Mismatch`") so the agent can judge fit.

**Embeddings opt-in, not default.** Local lexical ranking is good enough for the first 95%. Embeddings (sentence-transformers, OpenAI) earn their keep only at scale (≥500 entries) and gate a network call / model download. Add them as `dls query --embeddings` with a one-line install instruction — don't require them.

**Verdict:** Good, in this order: symbolic ranking → diff-aware → stack-trace parser → version-aware. Embeddings last, optional.

---

## Phase 5 — Rule promotion

Teach the log to *write its own enforcement*.

Proposed capabilities:
- **Promotion detection.** `dls stats --promote` lists prevention rules whose substring appears in ≥3 active entries — candidates for `PREVENTION_RULES.md`.
- **Rule → linter stub.** For a promoted rule whose `Why:` line names a symbol, generate a lint-rule stub (eslint, detekt, swiftlint, ruff) that encodes it. Human still reviews.
- **Rule → CI check stub.** Same, for CI policies (GitHub Actions step that greps for a banned pattern).
- **Rule → codemod stub.** For mechanical replacements (e.g., deprecated API), generate a `jscodeshift` / `AST-grep` stub.

### Evaluation

**Pros:** The ultimate form of "ambient tooling beats ambient discipline" — a rule that appeared three times becomes a check that runs on every PR.

**Cons / risk:** Generated stubs are only useful if reviewed. An unreviewed generated lint rule that misfires is *worse* than no rule. Ship them as suggestions in a PR description, not auto-commits.

**Distribution concern:** Linter stub generators are ecosystem-specific (detekt vs ruff vs eslint). We'd be maintaining 5+ generators. **Mitigation:** ship one generator (ruff, because it covers Python backend which is under-represented today) and make the stub format documented so the community adds the others.

**Verdict:** Good *eventually*, but low priority until Phases 2–4 are real. Rule promotion is the "lesson → linter" loop; it only pays off if there are already many promoted lessons to loop.

---

## Phase 6 — Evidence capture (proposed by you)

Capture investigation *structure*, not just the final lesson. Two options on the table:

- **Option A:** Richer DL entries — add optional `Evidence`, `Hypotheses tried`, `Rejected fixes`, `Verification`, `Artifact links` fields.
- **Option B:** Sidecar files — `.debug-log/incidents/DL-042.md` per incident; `DEBUG_LOG.md` keeps the distilled 11-field entry.

### Evaluation

**Why this is a genuinely good idea:**
- The log today captures the *lesson* beautifully but erases the *reasoning trail*. For 5+ iteration incidents, the trail is the most valuable part — it names which assumptions the team (or the agent) kept re-making, in what order. Three months later, a post-mortem reviewer who only has the final entry cannot reconstruct whether anyone considered the race condition or went straight to "add a retry".
- Modern agent workflows *already* produce this trail — hypotheses, rejected fixes, verification runs are in the transcript. Throwing it away at entry-write time is a loss of signal.
- It makes the skill useful for an under-served audience: **SRE / incident response teams**. Those teams already write post-mortems; today they do not map to DL entries cleanly.

**Why Option A (richer entries) is the wrong shape:**
- The entry template is already 11 fields. Pushing it to 16 makes a Write-a-DL-entry feel like filing an expense report. Authors start skipping entries, which kills rule #2 ("never skip").
- The value of the 11-field table is that it *fits on a screen* and an LLM can grep it cheaply. Longer entries defeat both.
- Optional fields become *de facto* required in CI ("we'd like all entries to have Hypotheses"), and then we're back to expense reports.

**Why Option B (sidecar per-incident) is the right shape:**
- `DEBUG_LOG.md` stays scannable. The 11-field entry links out to the sidecar with an `Artifact: .debug-log/incidents/DL-042.md` line.
- Sidecars are free-form — prose, transcripts, before/after screenshots, flamegraphs. The format doesn't pressure brevity.
- Sidecars are *opt-in at authoring time*. For a 1-iteration typo fix, no sidecar. For a 5-iteration incident, a sidecar is natural.
- Per-track templates in `templates/incident.<track>.template.md` keep the authoring cost low.

**Concerns with Option B:**
- **Fragmentation.** Two places to read. **Mitigation:** the DL entry in `DEBUG_LOG.md` is still the canonical summary; the sidecar is only consulted when the reader wants reasoning depth. `dls query` does not index sidecars by default — they're opt-in for deep dives.
- **Staleness.** Sidecars can rot. **Mitigation:** `dls doctor` checks that every `Artifact:` link resolves.
- **Skill positioning.** Some users will think "this is too heavy" and not write any sidecars. **Mitigation:** make it crystal-clear that sidecars are for iterations ≥ 3 or severity = Incident; everything else stays in the 11-field entry.

**Verdict:** **Yes to Option B, no to Option A.** Ship as:
- New optional field `Artifact` (URL or relative path) — additive, validator tolerates absent.
- `templates/incident.template.md` + per-track variants as starting points.
- `dls doctor` checks Artifact links resolve.
- SKILL.md documents: "For iterations ≥ 3 or severity = Incident, write a sidecar."

This *adds* rigor for the cases that need it without taxing the cases that don't. That's the shape of help.

---

## Phase 7 — Expand the track surface (proposed by you)

Agreed. The current skill leans mobile + web heavily; the frontier is elsewhere.

### Evaluation

**Which tracks first, in priority order:**

1. **Python backend** — FastAPI, Django, SQLAlchemy, async / asyncio, Celery / Dramatiq. This is the biggest gap. Python backend has a distinctive set of traps (ORM N+1, event-loop blocking in `def` vs `async def`, Pydantic v1→v2 migration) and a huge audience.
2. **Databases / SQL** — Postgres first. Index usage, transaction isolation, migration locks, `pg_stat_statements` gotchas, `EXPLAIN ANALYZE` patterns. Cross-cuts every backend track.
3. **Infra / DevOps** — Docker + Kubernetes + GitHub Actions + Terraform. Canonical failure modes: image size, ConfigMap vs Secret leak, OOM kills, kubelet evictions, Actions matrix explosion.
4. **Node backend** — Express / Nest / Fastify / Prisma / streaming / auth (JWT / session). Overlaps with web but has its own trap surface.
5. **Go** — goroutine leaks, context cancellation, slice aliasing, map iteration order, null interface vs nil struct.
6. **React Native / Flutter** — mobile cross-platform; high leverage for teams that don't want separate iOS/Android references.

**Skipping deliberately (for now):** Java/Spring (large track but declining share; add if demand appears), Rust (small current audience; growing fast, revisit in a year), Electron (niche).

**Concerns:**
- **Quality over quantity.** Thin `references/python-backend.md` is worse than none. Each new reference must have ~15 entries on par with the existing web/ios/android depth.
- **Maintenance surface.** Every new track doubles the surface to keep current. **Mitigation:** dated reference docs, track owners.
- **Validator taxonomy burden.** Each track = new track tag. We add `#python`, `#node`, `#go`, `#sql`, `#infra`, `#k8s`, `#docker`, `#gha`, `#terraform` to `TRACK_TAGS` in the schema. The existing taxonomy's "cross-cutting" covers databases poorly; `#sql` deserves its own track.

**Repo-level rigor:** Every new track is added to `SKILL.md` detection table, `references/tag-taxonomy.md`, `templates/PREVENTION_RULES.<track>.template.md`, and `scripts/init.sh` detection heuristic in the same commit. The schema module is the validator-side change. CHANGELOG documents new tags.

**Verdict:** **Yes, but sequenced.** Ship Python backend + Postgres + Docker/K8s as Phase 7a — those three are the biggest leverage. Node backend + Go + GHA as Phase 7b. React Native + Flutter as Phase 7c. Ship each track as a separate PR; no big-bang.

---

## Phase 8 — Machine interface for agents (proposed by you)

This is the most ambitious phase and the one most likely to reshape the skill if we get it wrong.

Proposed design: `DEBUG_LOG.md` stays human-readable source of truth; `dls` generates a sidecar index (`.debug-log/index.json` or `.debug-log/index.sqlite`) and exposes it via CLI `--json` and an MCP server.

### Evaluation

**Why this is genuinely valuable:**

- **Retrieval is where agents underperform.** A single grep against a 200-entry log returns noisy text the model has to re-parse. A tool call that returns a JSON array of {DL-NNN, title, tags, category, why}{n} is strictly better for an LLM. Multi-turn retrieval becomes cheap.
- **Authoring assistance is the *right* kind of help.** `suggest_tags(symptom, file, fix)` is useful because it enforces discipline (you see the canonical tags, not your first-pass guess). Contrast with `auto_write_entry(diff)` which is the banned anti-pattern.
- **`relevant_rules_for_diff(patch)` is a killer feature.** Pre-flight becomes "before you start this diff, here are the three DL entries that apply." Agents can call this automatically.
- **`stale_rule_candidates()` closes a lifecycle gap.** No human remembers to retire rules; an index can find rules whose `File(s)` no longer exist, whose `Environment` version is two majors out of date, or whose last-match-with-new-entries was months ago.

**Concerns:**

- **Distribution cost.** An MCP server is harder to ship than a zip. Users have to install and run a process. **Mitigation:** treat the MCP server as a *separate package* (`debug-log-mcp`) with its own release cadence; the skill itself stays copy-pastable.
- **Index staleness.** `DEBUG_LOG.md` is append-only but is frequently edited in PR reviews (typo fixes, tag additions pre-merge). Every edit invalidates the index. **Mitigation:** (a) rebuild the index on every `dls lint` invocation — fast because it's one pass over a Markdown file; (b) a `.debug-log/index.json` written next to `DEBUG_LOG.md` with `generated_at` and `source_sha` fields; (c) MCP server verifies `source_sha` before serving a tool call.
- **Grounding risk.** If agents only call `query_debug_log()` and never *read* the DL entry's prose, they lose the *why*. The prose Root Cause Context and Prevention Rule are where the real value is. **Mitigation:** every tool response includes the entry's full Prevention Rule string with the `**Why:**` line intact, and `relevant_rules_for_diff` returns the prose excerpt (not just DL numbers) so the agent has the reasoning inline.
- **Scope creep risk.** "A skill + CLI + MCP server + index + AI suggestions" is no longer a skill. **Mitigation:** tight layering:
  - Skill: markdown, protocol, references. Works with no tooling.
  - Validator: stdlib Python. Optional.
  - CLI (`dls`): stdlib Python, `--json`. Optional.
  - MCP server: separate package, depends on CLI. Optional.
  - Embeddings / suggestions: optional deps to the MCP server.

  Each layer works without the next. Users can adopt exactly as much as they want.
- **`append_debug_log_entry` is where I disagree with your design.** As I flagged under Phase 2, automated entry-writing is the anti-pattern this skill exists to prevent. The value is in the *author's* act of writing the `**Why:**` line. I would:
  - **Include** `supersede_debug_log_entry` — it's mechanical; the tool should get the handshake right.
  - **Include** `suggest_tags` + `suggest_root_cause_category` — these enforce the taxonomy and keep the author authoring.
  - **Exclude** `append_debug_log_entry` in its wizard form. Provide instead a `stub_debug_log_entry(diff)` tool that *writes the skeleton* with placeholder fields and forces the author to fill the prose. The agent can then *propose* text for the prose fields as a suggestion in chat — but the author pastes it in.

**Verdict:** **Yes, but sequenced and layered.** Phase 8 is the one that turns the system from "a skill" into "an agent-native debugging memory substrate" — and that phrase is worth earning. The way to earn it is to keep `DEBUG_LOG.md` readable without any of this, and to ship each layer as an opt-in add-on.

Concrete MCP tools I would ship, in priority order:
1. `query_debug_log(tag?, category?, track?, file?, include_obsolete?)` — read-only, returns hits with excerpts.
2. `relevant_rules_for_diff(patch)` — wraps Phase 4 diff-aware retrieval.
3. `suggest_tags(symptom, file, fix)` — returns top-k from the taxonomy.
4. `suggest_root_cause_category(symptom, root_cause_context)` — classifier over the 14 closed categories.
5. `supersede_debug_log_entry(number, reason)` — writes the handshake correctly; caller fills the rest.
6. `stub_debug_log_entry(diff)` — writes skeleton, does not fill `Why:`.
7. `stale_rule_candidates()` — read-only; used by `dls doctor`.

I would **not** ship a full `append_debug_log_entry` that fills every field from a diff. That's where the discipline evaporates.

---

## Sequencing recommendation

If you want a "most-leverage-first" path:

- **v2.1:** Phase 2 (CLI with `lint`, `stats`, `query`, `doctor`, `supersede`) + Phase 7a (Python backend + Postgres + Docker/K8s references). Gives existing users cross-platform tooling and opens the skill to backend/infra teams.
- **v2.2:** Phase 4 (symbolic ranking + diff-aware retrieval) + Phase 6 (sidecar incident files). Makes retrieval meaningfully better and captures investigation depth for the cases that need it.
- **v2.3:** Phase 3 (environment auto-fill as suggestions) + Phase 7b (Node backend, Go, GHA).
- **v2.4:** Phase 8 (MCP server in separate package, priority tools 1–4). First agent-native version.
- **v3.0:** Phase 5 (rule promotion: linter/CI stubs) + Phase 8 tools 5–7 + Phase 7c (mobile cross-platform).

This keeps every release shippable on its own and avoids bundling a multi-phase change into one breaking version bump.

---

## Non-goals

Things I have *intentionally* left off the roadmap, flagged here so future contributors don't reopen them:

- **UI / web dashboard for the log.** The log is a Markdown file. A dashboard re-introduces drift.
- **Automatic DL entry generation from commit messages.** Commit messages are usually terse and don't capture the *misconception*. Forcing them into DL entries produces bumper-sticker rules.
- **Cross-repo "shared" DEBUG_LOG.** Each repo's log captures *its own* scar tissue; merging them loses the precondition that the reader can trust every rule applies here.
- **LLM-generated Prevention Rules.** An LLM writing its own prevention rule for its own mistake is a conflict of interest. Rules are authored by the team, proposed by the agent.
