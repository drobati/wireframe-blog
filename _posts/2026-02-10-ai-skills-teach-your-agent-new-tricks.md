---
layout: default
title: "AI Skills: Teach Your Coding Agent New Tricks"
categories: tooling ai productivity
hero: /assets/images/posts/ai-skills-hero.png
---

What if your AI coding agent could learn your team's exact workflow and run it on command? Not some vague system prompt you paste every session, but a reusable, shareable skill you install once and invoke forever. That's what AI skills are, and they're changing how I work with Claude Code every day.

## What Are AI Skills?

At their core, skills are just markdown files. A `SKILL.md` file with some YAML frontmatter and instructions in the body. When you invoke a skill, its instructions get injected into the conversation so your AI agent knows exactly what to do.

Here's the simplest possible skill:

```markdown
---
name: greet
description: Greet the user with a fun fact
---

Say hello to the user and share a random programming fun fact.
```

That's it. Drop that in `.claude/skills/greet/SKILL.md` and you can type `/greet` in Claude Code. But the real power isn't in toy examples. It's in encoding your team's actual workflows into repeatable commands.

Skills follow the [Agent Skills](https://agentskills.io) open standard, which means they're not locked to one tool. The same `SKILL.md` format works across Claude Code, Cursor, GitHub Copilot, VS Code, and dozens of other AI-powered editors. Write once, use everywhere.

## How Skills Work Under the Hood

When you launch Claude Code, it scans for skills in three locations:

1. **Project level**: `.claude/skills/` in your repo (shared with your team via git)
2. **User level**: `~/.claude/skills/` (your personal skills across all projects)
3. **Enterprise level**: Managed by your org (highest priority)

Claude doesn't load every skill's full instructions into memory. That would be a waste of context. Instead, it reads just the `name` and `description` from each skill's frontmatter. Think of it like scanning a menu. Claude sees the one-line descriptions and decides which skill matches what you're asking for.

When a skill gets invoked, either by you typing `/skill-name` or by Claude automatically detecting it's relevant, the full `SKILL.md` content gets injected into the conversation. That's where the real instructions live.

### The Frontmatter

The YAML header controls how the skill behaves:

```yaml
---
name: repo-docs
description: Generate project documentation from codebase analysis
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
model: sonnet
context: fork
agent: general-purpose
---
```

The interesting fields:

- **`allowed-tools`** pre-approves tools so Claude doesn't ask for permission on every file read
- **`model`** can force a specific model (use `sonnet` for speed, `opus` for complex reasoning)
- **`context: fork`** runs the skill in an isolated subagent so it doesn't pollute your main conversation
- **`disable-model-invocation: true`** means Claude won't auto-trigger the skill. You have to explicitly type the slash command

### String Substitutions

Skills can accept arguments. When you type `/fix-issue 423`, the skill content can reference `$ARGUMENTS` (the full string) or `$0` (first argument):

```markdown
---
name: fix-issue
description: Look up a GitHub issue and fix it
---

Fetch issue #$0 from GitHub, analyze the problem, and implement a fix.
```

You can even inject live data with shell commands using the `` !`command` `` syntax:

```markdown
## Current branch context
- Branch: !`git branch --show-current`
- Recent commits: !`git log --oneline -5`
- Uncommitted changes: !`git status --short`
```

Those commands run *before* the skill instructions reach Claude, so it gets real-time context about your repo.

## The skills.sh Ecosystem

You don't have to write every skill from scratch. [skills.sh](https://skills.sh/) is an open registry with over 52,000 skills contributed by the community. Think of it as npm for AI agent skills.

The `npx skills` CLI makes it dead simple to install them:

```bash
# Install Vercel's curated skills collection
npx skills add vercel-labs/agent-skills

# Install from any GitHub repo
npx skills add anthropics/skills

# Install globally (available in all projects)
npx skills add owner/repo --global

# Install specific skills only
npx skills add vercel-labs/agent-skills --skill frontend-design --skill react-best-practices

# Browse what's available in a repo
npx skills add owner/repo --list
```

You can also manage your installed skills:

```bash
npx skills list          # See what's installed
npx skills find "react"  # Search for skills
npx skills update        # Update all to latest
npx skills remove        # Interactively remove skills
```

Some popular skills from the community:

- **react-best-practices** (Vercel) - 40+ rules across 8 categories for React/Next.js
- **web-design-guidelines** (Vercel) - 100+ rules for accessibility, performance, UX
- **skill-creator** (Anthropic) - An interactive skill that helps you create new skills
- **superpowers** (obra) - A full framework with brainstorming, planning, and TDD workflows

## Building a Real Skill: `/repo-docs`

Let's build something useful. I want a `/repo-docs` skill that:

1. Analyzes the codebase to generate a summary
2. Uses that summary to create a proper `AGENTS.md` (instructions for AI agents working on the project)
3. Generates a `README.md` from the same analysis
4. Uses templates so the output is consistent every time

### The Directory Structure

```
.claude/skills/repo-docs/
├── SKILL.md
└── templates/
    ├── AGENTS.md.template
    └── README.md.template
```

### The Skill File

```markdown
---
name: repo-docs
description: Generate AGENTS.md and README.md from codebase analysis.
  Use when asked to document a repo, create agent instructions, or
  generate a README.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task
---

# Repo Documentation Generator

Generate comprehensive project documentation by analyzing the codebase.

## Step 1: Analyze the Codebase

First, run `/code-summary` to generate a full codebase analysis.
Save the output to `docs/code-summary.md`.

If `docs/code-summary.md` already exists and is less than 24 hours
old, skip this step and use the existing summary.

## Step 2: Read Templates

Load the templates that define the output format:
- Read `templates/AGENTS.md.template` (relative to this skill)
- Read `templates/README.md.template` (relative to this skill)

## Step 3: Generate AGENTS.md

Using the code summary and the AGENTS.md template, generate an
`AGENTS.md` file in the project root. This file should:

- Describe the project architecture and structure
- List key conventions and patterns used in the codebase
- Specify testing commands and how to run the project
- Include file organization and naming conventions
- Note any gotchas or non-obvious patterns

Fill in every section of the template. Be specific and reference
actual files, functions, and patterns found in the code summary.

## Step 4: Generate README.md

Using the code summary and the README.md template, generate a
`README.md` file in the project root. This file should:

- Explain what the project does in plain language
- Include setup and installation instructions
- Show usage examples based on actual code
- Document the tech stack and dependencies
- Add contributing guidelines

## Step 5: Verify

After generating both files:
1. Read back both generated files
2. Verify all template sections were filled in
3. Check that file paths and commands referenced actually exist
4. Report what was generated and any sections that need manual review
```

### The AGENTS.md Template

```markdown
<!-- templates/AGENTS.md.template -->

# AGENTS.md

> Auto-generated by /repo-docs. Last updated: {date}

## Project Overview

{Brief description of what this project does, the main technologies
used, and its purpose.}

## Architecture

{Describe the high-level architecture. What pattern does the code
follow? MVC? Feature-based? Monorepo? Include a directory tree of
the key folders.}

## Key Conventions

### Naming
{How are files, functions, components, and variables named?
PascalCase? camelCase? kebab-case? Be specific.}

### Code Style
{Linting setup, formatting rules, import ordering, etc.}

### Patterns
{Common patterns used in the codebase. State management approach,
error handling conventions, API call patterns, etc.}

## Development Commands

```bash
# Install dependencies
{install command}

# Run development server
{dev command}

# Run tests
{test command}

# Build for production
{build command}

# Lint and format
{lint command}
```

## File Organization

{Describe where different types of code live. Where do new
components go? Where do tests go? Where do utilities go?}

## Testing

{Testing framework used, test file naming conventions, how to write
a new test, any test utilities or helpers available.}

## Common Gotchas

{Non-obvious things an AI agent (or new developer) should know.
Environment variables needed, build quirks, deployment requirements,
files that should never be modified, etc.}
```

### The README Template

```markdown
<!-- templates/README.md.template -->

# {Project Name}

{One-line description of what this project does.}

## Features

{Bulleted list of key features, derived from the codebase analysis.}

## Tech Stack

{List the main technologies, frameworks, and libraries used.}

## Getting Started

### Prerequisites

{What needs to be installed before setup. Node version, package
manager, system dependencies, etc.}

### Installation

```bash
{Step-by-step installation commands}
```

### Running Locally

```bash
{Command to start the development server}
```

## Usage

{Show 2-3 examples of how to use the project. Screenshots, code
snippets, or CLI commands.}

## Project Structure

```
{Directory tree showing the key folders and what they contain}
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

## License

{License type, or "See LICENSE file for details."}
```

### Using It

Once you've got those three files in place, just type:

```
/repo-docs
```

Claude will analyze your codebase, fill in both templates with real data from your project, and drop the files in your root. The whole process takes about 30 seconds for a medium-sized repo.

The beauty of the template approach is consistency. Every project gets the same structure. If you want to change the format, update the template and re-run. And because the skill calls `/code-summary` first, it's always working from a fresh analysis of your actual code, not hallucinating file paths or outdated function names.

## Writing Your Own Skills

Here's my process for deciding when something should be a skill:

1. **You've explained it to Claude more than twice.** If you keep pasting the same instructions, it's a skill.
2. **It involves multiple steps.** Simple tasks don't need skills. Multi-step workflows do.
3. **Other people on your team could use it.** Project-level skills in `.claude/skills/` get version-controlled with your repo.

Start with `npx skills init my-skill` to scaffold a new skill directory. Keep the `SKILL.md` under 500 lines. If you need more detail, put reference material in a `references/` subdirectory that Claude can load on demand.

The [skill-creator](https://github.com/anthropics/skills) skill from Anthropic is great for this too. Just type `/skill-creator` and it'll walk you through an interactive Q&A to generate a well-structured skill.

## Key Takeaways

- **Skills are just markdown files** with YAML frontmatter. No special tooling required to create them.
- **The skills.sh registry** has 52,000+ ready-to-use skills installable with `npx skills add`.
- **Templates + codebase analysis = consistent docs** that actually reflect your code.

If you're using an AI coding agent and you haven't started building skills yet, you're doing the same work twice every session. Pick your most-repeated workflow, turn it into a `SKILL.md`, and never explain it again.

Browse the registry at [skills.sh](https://skills.sh/) or get started with Vercel's curated collection:

```bash
npx skills add vercel-labs/agent-skills
```

Happy automating.
