# Claude Code Skills: Comprehensive Research

> Research compiled on 2026-02-10. Covers the Claude Code skills system, the Agent Skills open standard, the skills.sh ecosystem, and the `npx skills` CLI tool.

---

## Table of Contents

1. [What Are Claude Code Skills?](#1-what-are-claude-code-skills)
2. [How Skills Work Technically](#2-how-skills-work-technically)
3. [The SKILL.md File Format](#3-the-skillmd-file-format)
4. [Where Skills Are Stored](#4-where-skills-are-stored)
5. [How Skills Get Invoked](#5-how-skills-get-invoked)
6. [The skills.sh Registry](#6-the-skillssh-registry)
7. [The npx skills CLI Tool](#7-the-npx-skills-cli-tool)
8. [The Agent Skills Open Standard](#8-the-agent-skills-open-standard)
9. [User-Level vs Project-Level Skills](#9-user-level-vs-project-level-skills)
10. [Community Skills and Popular Examples](#10-community-skills-and-popular-examples)
11. [Sources](#11-sources)

---

## 1. What Are Claude Code Skills?

Claude Code skills are reusable instruction sets that extend Claude's capabilities within Claude Code. A skill is fundamentally a directory containing a `SKILL.md` file with YAML frontmatter and markdown instructions. When activated, the skill's instructions are injected into Claude's conversation context, modifying how it approaches tasks.

Skills serve two primary purposes:

- **Reference content**: Adds knowledge Claude applies to current work (conventions, patterns, style guides, domain knowledge).
- **Task content**: Provides step-by-step instructions for specific actions (deployments, commits, code generation).

Custom slash commands have been merged into skills as of Claude Code version 2.1.3. A file at `.claude/commands/review.md` and a skill at `.claude/skills/review/SKILL.md` both create `/review` and work identically. Existing `.claude/commands/` files continue to work, but skills are the recommended approach going forward because they support additional features like supporting files, frontmatter-based invocation control, and automatic discovery.

Claude Code skills follow the [Agent Skills](https://agentskills.io) open standard, which works across multiple AI tools including Cursor, GitHub Copilot, OpenAI Codex, and others.

---

## 2. How Skills Work Technically

### The Skill Tool Meta-Architecture

Skills are not injected into the system prompt. Instead, they are managed through a **Skill meta-tool** that appears in Claude's tools array. This tool has a dynamic `prompt` field that generates descriptions at runtime by aggregating all available skills' names and descriptions.

The Skill tool's description includes an `<available_skills>` section formatted as:

```
"skill-name": description text
```

This list is subject to a token budget (typically ~16,000 characters, scaling dynamically at 2% of the context window) to prevent context bloat.

### Skill Selection Mechanism

Claude's selection is **purely language-model based reasoning**. There is no algorithmic routing, regex matching, or semantic classifier. When Claude sees the skills list, it uses native language understanding to match user intent against skill descriptions. A clearly written description directly influences whether Claude invokes that skill.

### Invocation and Context Injection

When a skill executes, the system injects **two separate user messages** into conversation history:

1. **Metadata message** (`isMeta: false`): Visible to users, contains XML tags like `<command-message>The "pdf" skill is loading</command-message>` for transparency.

2. **Skill prompt message** (`isMeta: true`): Hidden from UI but sent to the Anthropic API, containing the full `SKILL.md` content with detailed instructions.

The `isMeta` flag enables dual-channel communication where humans see clean status indicators while Claude receives comprehensive instructions.

### Execution Context Modification

Skills modify the execution context through a `contextModifier` function that:

- **Pre-approves tools**: If `allowed-tools` is specified in frontmatter, those tools are added to always-allow rules, eliminating the need for user permission prompts during execution.
- **Overrides model**: The `model` field can specify a different Claude version for skill execution, reverting to the session model when complete.

These modifications are **scoped to the skill execution** and do not permanently alter the session context.

### Progressive Disclosure Design

Skills implement a three-tier information model:

| Tier | Content | When Loaded |
|------|---------|-------------|
| Tier 1 (Discovery) | Frontmatter metadata (name, brief description) | At startup for all skills |
| Tier 2 (Selection) | Full SKILL.md content | After Claude chooses the skill |
| Tier 3 (Execution) | Referenced assets, scripts, reference files | As needed during task completion |

This prevents the skills list from overwhelming context while making detailed documentation available on demand.

---

## 3. The SKILL.md File Format

### Basic Structure

Every skill requires a `SKILL.md` file with two parts: YAML frontmatter (between `---` markers) and markdown content with instructions.

```yaml
---
name: my-skill
description: What this skill does and when to use it
---

Your skill instructions in markdown here...
```

### Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | No (uses directory name if omitted) | Display name for the skill. Lowercase letters, numbers, and hyphens only (max 64 chars). |
| `description` | Recommended | What the skill does and when to use it. Claude uses this to decide when to apply the skill. Max 1024 chars. |
| `argument-hint` | No | Hint shown during autocomplete, e.g. `[issue-number]` or `[filename] [format]`. |
| `disable-model-invocation` | No | Set to `true` to prevent Claude from automatically loading this skill. Default: `false`. |
| `user-invocable` | No | Set to `false` to hide from the `/` menu. Default: `true`. |
| `allowed-tools` | No | Tools Claude can use without asking permission when this skill is active. |
| `model` | No | Model to use when this skill is active. |
| `context` | No | Set to `fork` to run in a forked subagent context. |
| `agent` | No | Which subagent type to use when `context: fork` is set. |
| `hooks` | No | Hooks scoped to this skill's lifecycle. |

### Name Field Rules

- 1-64 characters
- Lowercase alphanumeric characters and hyphens only
- Must not start or end with a hyphen
- Must not contain consecutive hyphens (`--`)
- Must match the parent directory name

### String Substitutions

Skills support dynamic value substitution in the skill content:

| Variable | Description |
|----------|-------------|
| `$ARGUMENTS` | All arguments passed when invoking the skill |
| `$ARGUMENTS[N]` | Access a specific argument by 0-based index |
| `$N` | Shorthand for `$ARGUMENTS[N]` (e.g., `$0`, `$1`) |
| `${CLAUDE_SESSION_ID}` | The current session ID |

### Dynamic Context with Shell Commands

The `` !`command` `` syntax runs shell commands before the skill content is sent to Claude. The command output replaces the placeholder:

```yaml
---
name: pr-summary
description: Summarize changes in a pull request
context: fork
agent: Explore
---

## Pull request context
- PR diff: !`gh pr diff`
- PR comments: !`gh pr view --comments`
- Changed files: !`gh pr diff --name-only`

## Your task
Summarize this pull request...
```

### Directory Structure

A skill is a directory with `SKILL.md` as the entrypoint. Additional supporting files are optional:

```
my-skill/
├── SKILL.md           # Main instructions (required)
├── template.md        # Template for Claude to fill in
├── examples/
│   └── sample.md      # Example output showing expected format
├── references/
│   └── REFERENCE.md   # Detailed technical reference
├── scripts/
│   └── validate.sh    # Script Claude can execute
└── assets/
    └── schema.json    # Static resources
```

Best practice: Keep `SKILL.md` under 500 lines. Move detailed reference material to separate files. The full SKILL.md body should be under 5000 tokens.

---

## 4. Where Skills Are Stored

Skills are stored at different levels, and the storage location determines who can use them:

| Level | Path | Applies To |
|-------|------|------------|
| **Enterprise** | Managed via organizational settings | All users in the organization |
| **Personal (User-Level)** | `~/.claude/skills/<skill-name>/SKILL.md` | All projects for this user |
| **Project** | `.claude/skills/<skill-name>/SKILL.md` | This project only |
| **Plugin** | `<plugin>/skills/<skill-name>/SKILL.md` | Where the plugin is enabled |

### Priority / Conflict Resolution

When skills share the same name across levels, higher-priority locations win:

**Enterprise > Personal > Project**

Plugin skills use a `plugin-name:skill-name` namespace, so they cannot conflict with other levels.

### Legacy Commands Compatibility

Files in `.claude/commands/` still work. If a skill and a command share the same name, the skill takes precedence.

### Monorepo Support

When working with files in subdirectories, Claude Code automatically discovers skills from nested `.claude/skills/` directories. For example, editing a file in `packages/frontend/` causes Claude Code to also look for skills in `packages/frontend/.claude/skills/`.

### Additional Directories

Skills defined in `.claude/skills/` within directories added via `--add-dir` are loaded automatically and picked up by live change detection, so you can edit them during a session without restarting.

---

## 5. How Skills Get Invoked

### Two Invocation Modes

1. **User invocation (slash commands)**: Type `/skill-name` directly in the Claude Code prompt. Arguments can be passed after the skill name.
2. **Model invocation (automatic)**: Claude reads the skill descriptions and decides when to use a skill based on the current conversation context.

### Controlling Invocation

| Frontmatter Setting | You Can Invoke | Claude Can Invoke | When Loaded Into Context |
|---------------------|----------------|-------------------|--------------------------|
| (default) | Yes | Yes | Description always in context; full skill loads when invoked |
| `disable-model-invocation: true` | Yes | No | Description not in context; full skill loads when you invoke |
| `user-invocable: false` | No | Yes | Description always in context; full skill loads when invoked |

### Invocation Lifecycle

1. Claude receives the Skill tool with all available skill descriptions listed.
2. Claude reasons about whether a skill matches the user's intent.
3. Claude invokes the Skill tool with `command: "skill-name"`.
4. The system validates the command exists and checks permissions.
5. The `SKILL.md` file is loaded and parsed.
6. Two messages are injected into conversation history (one visible, one hidden).
7. The execution context is modified (pre-approved tools, model override).
8. The request is sent to the Anthropic API with enriched conversation history.
9. Claude processes the injected skill instructions and uses tools to complete the task.

### Passing Arguments

Arguments are available via the `$ARGUMENTS` placeholder:

```
/fix-issue 123
```

If the skill content includes `$ARGUMENTS`, it gets replaced with `123`. If `$ARGUMENTS` is not present in the content, arguments are appended as `ARGUMENTS: 123`.

Individual arguments can be accessed with `$ARGUMENTS[0]`, `$ARGUMENTS[1]`, etc., or shorthand `$0`, `$1`, etc.

### Running Skills in a Subagent

Add `context: fork` to run a skill in an isolated subagent. The skill content becomes the prompt that drives the subagent, which will not have access to conversation history.

```yaml
---
name: deep-research
description: Research a topic thoroughly
context: fork
agent: Explore
---

Research $ARGUMENTS thoroughly...
```

Agent options include built-in agents (`Explore`, `Plan`, `general-purpose`) or custom subagents from `.claude/agents/`.

### Restricting Claude's Skill Access

You can control which skills Claude can invoke through permission rules:

```
# Allow only specific skills
Skill(commit)
Skill(review-pr *)

# Deny specific skills
Skill(deploy *)
```

---

## 6. The skills.sh Registry

### What Is skills.sh?

[skills.sh](https://skills.sh/) is an open directory and leaderboard for agent skill packages, launched by Vercel on January 20, 2026. It functions as an npm-style registry for AI agent skills, allowing developers to discover, browse, and install reusable agent capabilities.

### Key Features

- **Leaderboard views**: All Time (cumulative installs), Trending (24h), and Hot (currently active).
- **Search**: A search function with "/" keyboard shortcut for quick skill lookup.
- **Metrics**: Real-time install counts and categorization.
- **Scale**: Over 52,000 skills listed as of early 2026.

### Top Skills by Installs

| Skill | Installs |
|-------|----------|
| find-skills | 177,500+ |
| vercel-react-best-practices | 116,100+ |
| Various React, design, and testing skills | Thousands each |

### Supported Agents

The platform supports 35+ agent environments including:
- Claude Code, Cline
- OpenAI Codex, GitHub Copilot
- Google Gemini
- Cursor, Windsurf
- VS Code, Roo, Trae
- And many others

---

## 7. The npx skills CLI Tool

### Overview

The `npx skills` CLI is the primary tool for discovering, installing, and managing agent skills. It is maintained by Vercel Labs and available as the `skills` npm package.

### Installation Commands

```bash
# Install from GitHub shorthand
npx skills add owner/repo

# Install from full GitHub URL
npx skills add https://github.com/owner/repo

# Install from GitLab URL
npx skills add https://gitlab.com/owner/repo

# Install from any git URL
npx skills add https://git.example.com/owner/repo.git

# Install from local directory
npx skills add ./path/to/local/skills

# Install specific skills from a repo
npx skills add vercel-labs/agent-skills --skill frontend-design --skill skill-creator

# Install globally (user-level)
npx skills add owner/repo --global

# Install for specific agents
npx skills add vercel-labs/agent-skills -a claude-code -a opencode

# Non-interactive (CI/CD friendly)
npx skills add owner/repo --yes

# Install all skills to all agents
npx skills add owner/repo --all
```

### CLI Options

| Flag | Purpose |
|------|---------|
| `-g, --global` | Install to user directory instead of project |
| `-a, --agent <agents>` | Target specific coding agents |
| `-s, --skill <skills>` | Install specific skills by name |
| `-l, --list` | Display available skills without installing |
| `-y, --yes` | Skip confirmation prompts |
| `--all` | Install everything without interaction |

### Management Commands

```bash
# List installed skills
npx skills list

# Search for skills interactively or by keyword
npx skills find [query]

# Remove installed skills
npx skills remove

# Check for available updates
npx skills check

# Update all skills to latest versions
npx skills update

# Create a new skill template
npx skills init [name]
```

### Installation Scope

- **Project scope** (default): Installs to `./<agent>/skills/` (e.g., `.claude/skills/`)
- **Global scope** (`-g` flag): Installs to `~/<agent>/skills/` (e.g., `~/.claude/skills/`)

Installation can use symlinks (recommended) or file copies.

### Getting Started

The recommended starting point:

```bash
npx skills add vercel-labs/agent-skills
```

This installs Vercel's official skills collection, which includes `react-best-practices`, `web-design-guidelines`, `react-native-guidelines`, `composition-patterns`, and `vercel-deploy-claimable`.

---

## 8. The Agent Skills Open Standard

### Overview

The [Agent Skills specification](https://agentskills.io/specification) is an open standard maintained at [agentskills.io](https://agentskills.io). It defines a simple, portable format for giving agents new capabilities. The specification is intentionally minimal.

### Specification Requirements

**Required:**
- A directory containing at minimum a `SKILL.md` file
- YAML frontmatter with `name` and `description` fields
- Markdown body with instructions

**Optional Directories:**
- `scripts/` - Executable code agents can run (Python, Bash, JavaScript)
- `references/` - Additional documentation loaded on demand
- `assets/` - Static resources (templates, images, data files)

### Frontmatter Fields (Agent Skills Standard)

| Field | Required | Constraints |
|-------|----------|-------------|
| `name` | Yes | Max 64 chars, lowercase alphanumeric and hyphens |
| `description` | Yes | Max 1024 chars, describes what and when |
| `license` | No | License name or reference to bundled license file |
| `compatibility` | No | Max 500 chars, environment requirements |
| `metadata` | No | Arbitrary key-value mapping |
| `allowed-tools` | No | Space-delimited list of pre-approved tools (experimental) |

Note: Claude Code extends this standard with additional fields like `disable-model-invocation`, `user-invocable`, `context`, `agent`, `model`, and `hooks`.

### Validation

You can validate skills with the reference library:

```bash
skills-ref validate ./my-skill
```

### Adopting Platforms

The Agent Skills standard has been adopted by:
- Anthropic Claude Code
- OpenAI Codex
- GitHub Copilot
- Cursor
- VS Code
- And many others

---

## 9. User-Level vs Project-Level Skills

### Detailed Comparison

| Aspect | User-Level (Personal) | Project-Level | Enterprise (Managed) |
|--------|----------------------|---------------|---------------------|
| **Path** | `~/.claude/skills/<name>/SKILL.md` | `.claude/skills/<name>/SKILL.md` | Managed via org settings |
| **Scope** | All projects for this user | Single project only | All users in organization |
| **Version Control** | Not in project repo | Committed to repo with project | Centrally managed |
| **Sharing** | Not shared with team | Shared via version control | Distributed to all team members |
| **Priority** | Overrides project-level | Lowest priority | Highest priority |
| **Use Case** | Personal workflow preferences | Team standards for a project | Organization-wide policies |

### When to Use Each Level

**User-level skills** are best for:
- Personal productivity shortcuts
- Workflows you use across multiple projects
- Experimental skills you are developing
- Individual coding style preferences

**Project-level skills** are best for:
- Team coding standards and conventions
- Project-specific deployment workflows
- Shared code review checklists
- Domain-specific knowledge for the project

**Enterprise/Managed skills** are best for:
- Enforcing compliance and security practices
- Standardizing deployment procedures across teams
- Distributing approved workflows organization-wide
- Ensuring consistent best practices

### Priority Chain

If a skill with the same name exists at multiple levels:

```
Enterprise (highest) > Personal > Project (lowest)
```

Plugin skills use namespaced identifiers (`plugin-name:skill-name`) and cannot conflict with other levels.

---

## 10. Community Skills and Popular Examples

### Anthropic Official Skills

The [anthropics/skills](https://github.com/anthropics/skills) repository (67.3k stars) contains official skill examples:

| Category | Skills |
|----------|--------|
| **Document Processing** | docx, pdf, pptx, xlsx |
| **Design & Creative** | algorithmic-art, canvas-design, slack-gif-creator |
| **Development** | frontend-design, web-artifacts-builder, mcp-builder, webapp-testing |
| **Communication** | brand-guidelines, internal-comms |
| **Skill Creation** | skill-creator (interactive Q&A tool) |

Installation via plugin:
```bash
/plugin marketplace add anthropics/skills
```

### Vercel Official Skills

The [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) repository (19.7k stars) contains:

| Skill | Description |
|-------|-------------|
| react-best-practices | 40+ rules across 8 categories for React/Next.js |
| web-design-guidelines | 100+ rules for accessibility, performance, UX |
| react-native-guidelines | 16 rules across 7 sections for React Native/Expo |
| composition-patterns | Architectural guidance for scaling React components |
| vercel-deploy-claimable | Auto-detects 40+ frameworks for deployment |

Installation:
```bash
npx skills add vercel-labs/agent-skills
```

### obra/superpowers

The [obra/superpowers](https://github.com/obra/superpowers) project is a comprehensive agentic skills framework with 20+ battle-tested skills:

- `/brainstorm` - Collaborative ideation
- `/write-plan` - Breaks work into bite-sized tasks (2-5 min each)
- `/execute-plan` - Systematic plan execution
- Test-driven development (TDD) enforcement: RED-GREEN-REFACTOR workflow
- Debugging patterns
- Skills search tool

Installation:
```bash
/plugin marketplace add obra/superpowers-marketplace
```

### Notable Community Skills

| Skill | Author | Purpose |
|-------|--------|---------|
| ios-simulator-skill | Community | iOS app development, navigation, and testing |
| playwright-skill | Community | Browser automation |
| claude-d3js-skill | Community | Data visualization with d3.js |
| claude-scientific-skills | Community | Scientific library integrations |
| web-asset-generator | Community | Favicon, icon, social media image generation |
| ffuf-web-fuzzing | Community | Penetration testing with web fuzzing |
| Trail of Bits Security | trailofbits | Static analysis, code auditing, vulnerability detection |
| planning-with-files | OthmanAdi | Manus-style persistent markdown planning |
| loki-mode | Community | Multi-agent startup system (37 agents, 6 swarms) |

### Curated Lists

- [awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills) - A curated list of Claude skills, resources, and tools
- [awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills) - 300+ agent skills from official teams and community

### Tools for Creating Skills

- **skill-creator** (from Anthropic) - Interactive Q&A tool for creating new skills
- **Skill_Seekers** - Converts documentation websites into Claude skills
- **slash-command-creator** - Helps create slash commands/skills

---

## 11. Sources

### Official Documentation
- [Extend Claude with Skills - Claude Code Docs](https://code.claude.com/docs/en/skills)
- [Agent Skills Specification](https://agentskills.io/specification)
- [Agent Skills Standard - agentskills.io](https://agentskills.io)
- [How to Create Custom Skills - Claude Help Center](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills)

### GitHub Repositories
- [anthropics/skills - Official Anthropic Skills](https://github.com/anthropics/skills)
- [vercel-labs/skills - The npx skills CLI](https://github.com/vercel-labs/skills)
- [vercel-labs/agent-skills - Vercel's Official Skills Collection](https://github.com/vercel-labs/agent-skills)
- [travisvn/awesome-claude-skills - Curated Skills List](https://github.com/travisvn/awesome-claude-skills)
- [VoltAgent/awesome-agent-skills - 300+ Agent Skills](https://github.com/VoltAgent/awesome-agent-skills)
- [obra/superpowers - Agentic Skills Framework](https://github.com/obra/superpowers)
- [agentskills/agentskills - Specification Repository](https://github.com/agentskills/agentskills)

### Registry and Ecosystem
- [skills.sh - The Agent Skills Directory](https://skills.sh/)
- [skills npm package](https://www.npmjs.com/package/skills)
- [Introducing skills - Vercel Changelog](https://vercel.com/changelog/introducing-skills-the-open-agent-skills-ecosystem)

### Articles and Deep Dives
- [Claude Agent Skills: A First Principles Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/)
- [Claude Code Merges Slash Commands Into Skills](https://medium.com/@joe.njenga/claude-code-merges-slash-commands-into-skills-dont-miss-your-update-8296f3989697)
- [Claude Code Customization Guide](https://alexop.dev/posts/claude-code-customization-guide-claudemd-skills-subagents/)
- [Claude Code Skills and Slash Commands: Complete Guide](https://oneaway.io/blog/claude-code-skills-slash-commands)
- [Skills vs Slash Commands](https://medium.com/@lakshminp/skills-vs-slash-commands-one-works-ones-a-prayer-fa6b065e78e6)
- [Skills for Claude!](https://blog.fsck.com/2025/10/16/skills-for-claude/)
- [Claude Code Skills Deep Dive Part 1](https://medium.com/spillwave-solutions/claude-code-skills-deep-dive-part-1-82b572ad9450)
- [How to Use skills.sh in Your Project](https://medium.com/frontendweb/how-to-use-skills-sh-in-your-project-without-stress-or-panic-867e152c3392)
