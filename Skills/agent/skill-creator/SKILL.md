---
name: skill-creator
description: Guidance for creating or updating AgentConsole skills. Use when the user wants to add a new file-based skill, improve an existing SKILL.md, design skill frontmatter, organize scripts/references/assets, validate skill discovery, or prepare a skill for deployment.
category: agent
tags: [agent, skills, skill-creation, authoring]
---

# Skill Creator

Use this skill when the user wants to create, update, review, or troubleshoot an AgentConsole skill. AgentConsole skills are file-based operational instructions loaded from a configured skills root and injected into future payloads when active. They are not compiled code and they are not tool results.

## AgentConsole Skill Layout

Create each skill as a directory with a required `SKILL.md` file:

```text
Skills/
  <category>/
    <skill-name>/
      SKILL.md
      scripts/       optional
      references/    optional
      assets/        optional
```

For deployment, `deploy/publish-deploy.ps1` copies only directories that contain `SKILL.md` into:

```text
deploy/JioAgent/Skills/<category>/<skill-name>/
```

Do not add unrelated files such as `README.md`, `CHANGELOG.md`, or setup notes unless they are truly used by the skill. Put user-facing project documentation in `USER_GUIDE.md`, not inside the skill folder.

## Naming

Use lowercase letters, digits, and hyphens for the skill folder and `name` value. Prefer short action-oriented names such as:

```text
external-mcp-server-setup
payload-composition
skill-creator
```

Keep the folder name and frontmatter `name` the same unless there is a deliberate compatibility reason.

## Frontmatter

Start `SKILL.md` with frontmatter:

```markdown
---
name: my-skill
description: Clear trigger-oriented description of what this skill helps with and when to use it.
category: agent
tags: [agent, setup]
---
```

Required:

- `name`: stable skill id. Defaults to the folder name if omitted, but include it for clarity.
- `description`: the main trigger text. Include the task type and concrete contexts where the skill should be used.

Recommended for AgentConsole:

- `category`: normally the parent folder name, such as `agent`, `api`, or `testing`.
- `tags`: short labels for filtering and future discovery.

Put all "when to use this skill" trigger information in `description`, because the body is loaded only after the skill is selected or activated.

## Body Writing Rules

Write the body as concise operational guidance for another agent. Assume the agent is capable; include only details that are non-obvious, project-specific, fragile, or easy to forget.

Prefer:

- Concrete paths, commands, examples, and validation steps.
- Short checklists for multi-step work.
- Small examples that users can adapt.
- Clear warnings around secrets, deployment, destructive actions, or brittle behavior.

Avoid:

- Long generic explanations.
- Marketing copy.
- Duplicating large reference material inside `SKILL.md`.
- Instructions that depend on unavailable helper scripts.
- Putting secrets, API keys, tokens, or credentials in skill files.

## Progressive Disclosure

Keep `SKILL.md` focused. If detailed material is large or only sometimes needed, move it into a directly linked file:

```text
references/
  provider-a.md
  provider-b.md
```

In `SKILL.md`, explain when to read each reference:

```markdown
For Provider A setup details, read `references/provider-a.md`.
For Provider B setup details, read `references/provider-b.md`.
```

Keep references one level deep from `SKILL.md` so the agent can find them without a long search chain.

## Optional Resources

Use `scripts/` when repeated work needs deterministic code, such as generating a manifest, validating a schema, or transforming files. Test scripts by running them at least once.

Use `references/` for API docs, schemas, detailed procedures, examples, or policy text that should be loaded only when needed.

Use `assets/` for templates, images, sample project files, or other resources used to produce outputs.

Only create resource folders that the skill actually needs.

## Creation Workflow

1. Understand the user's intended skill with concrete examples.
2. Choose a concise skill name and category.
3. Decide whether optional `scripts`, `references`, or `assets` are justified.
4. Create `Skills/<category>/<skill-name>/SKILL.md`.
5. Write trigger-oriented frontmatter.
6. Write concise body instructions and examples.
7. Validate discovery and deployment.
8. Update `CODE_NOTES.md` and `USER_GUIDE.md` when the skill changes architecture, setup, operation, deployment, or user-facing behavior.

Ask for clarification only when the skill's target workflow or safe operating boundaries are unclear. Otherwise make conservative choices aligned with existing AgentConsole skill patterns.

## Update Workflow

When updating an existing skill:

- Read the current `SKILL.md` first.
- Keep edits scoped to the requested behavior.
- Preserve useful existing examples and local conventions.
- Remove stale instructions that would cause the agent to do the wrong thing.
- Re-check that `description` still describes the new trigger conditions.
- Re-run build/deploy verification when deployment behavior or docs changed.

## Validation

After adding or changing a skill, run or check:

```powershell
dotnet build jio_agent.sln
powershell -NoProfile -ExecutionPolicy Bypass -File .\deploy\publish-deploy.ps1 -Configuration Release
Test-Path .\deploy\JioAgent\Skills\<category>\<skill-name>\SKILL.md
```

For runtime verification in AgentConsole:

```text
/skills
/skill show <skill-name>
/skill activate <skill-name>
/skill active
```

Expected results:

- `/skills` lists the skill metadata.
- `/skill show <skill-name>` displays the intended instructions.
- `/skill activate <skill-name>` marks it active.
- The next payload includes the active skill body.

If the skill does not appear, check the configured `--skills-root`, the folder path, the filename `SKILL.md`, frontmatter syntax, duplicate skill names, and whether AgentConsole needs to be restarted.
