# editor-integrations

Sample configuration files that tell different LLM editors / harnesses to load the `debug-log-skill`.

Pick the one matching your tool, copy it into your project at the indicated path, and you're done.

| Your tool | File | Where it goes in your project |
|---|---|---|
| Claude Code, Claude Desktop, Cowork | [`CLAUDE.md`](CLAUDE.md) | Project root: `CLAUDE.md` |
| Cursor | [`cursor/rules/debug-log.mdc`](cursor/rules/debug-log.mdc) | `.cursor/rules/debug-log.mdc` |
| Aider, Codex, OpenAI Agents, any agent that reads `AGENTS.md` | [`AGENTS.md`](AGENTS.md) | Project root: `AGENTS.md` |

## What each file does

All three do the same four things:

1. Point the LLM at the `debug-log-skill` folder (SKILL.md + references).
2. Enforce the four non-negotiable rules (sequence / never skip / read before coding / append-only).
3. Make the pre-mortem workflow the default approach for new work.
4. Require a DL entry on every bug fix in the same commit.

They differ only in format — each tool has its own frontmatter / file-naming convention.

## Using multiple tools on the same project

Most teams use Claude Code AND Cursor side-by-side, or Claude + Aider. Dropping in multiple files is fine — each tool reads its own, they don't conflict. Just keep them in sync when you update the skill version.

## Customising

Two tweaks most projects want:

- **Path to the skill.** Replace `~/.claude/skills/debug-log` with wherever you've installed it (often a submodule at `tools/debug-log-skill/`).
- **Track list.** Delete references to tracks you don't use. A pure Rails shop doesn't need iOS or Android in its CLAUDE.md.

## If your editor isn't listed

The skill is plain Markdown. Any harness that (a) lets you include a project-level system prompt and (b) lets the agent read additional files on demand can use it. The frontmatter fields to include:

- A description rich in trigger keywords (bug / crash / error / flaky test / new feature / build failure / stack trace + exception names).
- A pointer to `SKILL.md`.
- Instructions to read `references/<track>.md` when the project's stack matches.

Model yours on `CLAUDE.md` here.
