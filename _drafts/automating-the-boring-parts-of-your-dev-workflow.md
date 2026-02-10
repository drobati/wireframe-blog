---
layout: default
title: "Automating the Boring Parts of Your Dev Workflow"
categories: tooling productivity automation
---

Every developer has that one task they do twenty times a day without thinking about it. Switching branches and rebuilding. Creating a new component with the same boilerplate. Running lint before every commit because you forgot that one time and broke the build. These tiny friction points add up, and they're exactly the kind of thing computers should be doing for you. Let me walk you through the automations that have saved me the most time -- and be honest about when automation isn't worth the effort.

## Identifying What to Automate

I live by the rule of three: if I do something three times, I automate it. Not twice -- that's just a coincidence. Not once -- that's a one-off. Three times means it's a pattern, and patterns are what automation is built for.

But not everything that repeats is worth automating. You want to look for tasks that are all three of these: **frequent**, **mechanical**, and **stable**. Frequent means you do it often enough that the automation pays for itself. Mechanical means there's no judgment call involved -- it's the same steps every time. Stable means the process doesn't change often, so your automation won't need constant maintenance.

Here's my quick litmus test. Before I automate something, I ask: "If I gave these exact instructions to someone who's never seen this project, could they do it without asking me any questions?" If the answer is yes, it's a great candidate. If the answer is "well, it depends," there's probably a human judgment step that's hard to encode.

Start a running list. Seriously, keep a note somewhere -- I use a `TODO-automate.md` in my home directory -- and jot down every time you think "I wish this was automatic." After a week, look at the list. The things that show up multiple times are where you should invest your time.

## Git Hooks That Save You

Git hooks are the single highest-value automation I've set up. They run automatically at key points in your git workflow, and they catch mistakes before they become problems. I use **husky** to manage hooks and **lint-staged** to run linters only on changed files.

First, get the tools installed:

```bash
npm install --save-dev husky lint-staged
npx husky init
```

That creates a `.husky/` directory in your project. Now set up a pre-commit hook that runs lint-staged:

```bash
echo "npx lint-staged" > .husky/pre-commit
```

And configure lint-staged in your `package.json`:

```json
{
  "lint-staged": {
    "*.{js,jsx,ts,tsx}": [
      "eslint --fix",
      "prettier --write"
    ],
    "*.{json,md,css}": [
      "prettier --write"
    ]
  }
}
```

Now every commit automatically lints and formats only the files you changed. No more "fix lint" commits. No more code review comments about formatting. It just happens.

For enforcing conventional commit messages, add a `commit-msg` hook:

```bash
npm install --save-dev @commitlint/cli @commitlint/config-conventional
echo "npx --no -- commitlint --edit \$1" > .husky/commit-msg
```

Then create a `commitlint.config.js`:

```javascript
export default {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'subject-case': [2, 'never', ['start-case', 'pascal-case', 'upper-case']],
    'type-enum': [2, 'always', [
      'feat', 'fix', 'docs', 'style', 'refactor',
      'test', 'chore', 'perf', 'ci', 'build'
    ]]
  }
};
```

Now `git commit -m "fixed stuff"` gets rejected, but `git commit -m "fix: resolve race condition in auth flow"` goes through. Your git log becomes actually useful.

I also add a pre-push hook that runs the test suite. Pushing broken code to a shared branch wastes everyone's time:

```bash
echo "npm test" > .husky/pre-push
```

## Shell Aliases & Functions

I spend most of my day in the terminal, so shaving even a few keystrokes off common commands adds up fast. Here are the aliases and functions I actually use every day. These go in your `.zshrc` or `.bashrc`:

```bash
# Git shortcuts
alias gs='git status'
alias gco='git checkout'
alias gcb='git checkout -b'
alias gp='git push'
alias gpu='git push -u origin HEAD'
alias gl='git log --oneline -20'
alias gd='git diff'
alias gds='git diff --staged'
alias gca='git commit --amend --no-edit'

# Project shortcuts
alias dev='npm run dev'
alias build='npm run build'
alias test='npm test'
alias lint='npm run lint'

# Navigation
alias ..='cd ..'
alias ...='cd ../..'
alias proj='cd ~/projects'
```

Aliases are great for simple substitutions, but for anything with logic, you want shell functions. Here's one I use all the time -- it creates a new branch from the latest main:

```bash
function fresh() {
  git checkout main && git pull && git checkout -b "$1"
  echo "Ready to work on $1"
}

# Usage: fresh feature/add-search
```

And here's one that kills whatever's running on a given port, because I'm constantly forgetting to stop dev servers:

```bash
function killport() {
  local pid=$(lsof -ti :$1)
  if [ -n "$pid" ]; then
    kill -9 $pid
    echo "Killed process $pid on port $1"
  else
    echo "Nothing running on port $1"
  fi
}

# Usage: killport 3000
```

The key with aliases and functions is to only create them for things you actually type frequently. I see people with 200 aliases and they can't remember any of them. Keep it to the commands you use daily, and your muscle memory will take over within a week.

## Project Scaffolding

If you create React components regularly, you know the drill: create the file, write the boilerplate, create the test file, create the styles file, add the export to the index. It's five minutes of work that feels like busywork because it is.

Here's a shell function that does it all in one command:

```bash
function newcomp() {
  local name=$1
  local dir="src/components/${name}"

  mkdir -p "$dir"

  # Component file
  cat > "${dir}/${name}.tsx" << EOF
interface ${name}Props {
  className?: string;
}

export function ${name}({ className }: ${name}Props) {
  return (
    <div className={className}>
      <h2>${name}</h2>
    </div>
  );
}
EOF

  # Test file
  cat > "${dir}/${name}.test.tsx" << EOF
import { render, screen } from '@testing-library/react';
import { ${name} } from './${name}';

describe('${name}', () => {
  it('renders without crashing', () => {
    render(<${name} />);
    expect(screen.getByText('${name}')).toBeInTheDocument();
  });
});
EOF

  # Index file
  echo "export { ${name} } from './${name}';" > "${dir}/index.ts"

  echo "Created component ${name} at ${dir}"
}

# Usage: newcomp SearchBar
```

For more complex scaffolding across a whole team, look at **degit**. It clones a git repo without the history, which makes it perfect for templates:

```bash
npx degit your-org/react-component-template src/components/NewFeature
```

You can maintain template repos for different patterns -- a component template, a page template, an API route template -- and `degit` pulls them down instantly. It's simpler than yeoman or plop and doesn't require any configuration in the target project.

## Automating Repetitive Refactors

Sometimes you need to make the same change across dozens of files. Renaming a prop, updating an import path, changing an API call signature. For simple text replacements, a one-liner does the job:

```bash
# Rename a component across all files
find src -name "*.tsx" -exec sed -i '' 's/OldButton/Button/g' {} +

# Update an import path
find src -name "*.ts" -o -name "*.tsx" | xargs sed -i '' 's|@/lib/old-utils|@/lib/utils|g'
```

But for structural changes -- where you need to understand the code's AST, not just its text -- **jscodeshift** is the right tool. It lets you write transforms that understand JavaScript syntax:

```javascript
// transforms/rename-prop.js
export default function transformer(file, api) {
  const j = api.jscodeshift;
  const root = j(file.source);

  // Find all JSX elements named "Button" and rename the "color" prop to "variant"
  root
    .find(j.JSXOpeningElement, { name: { name: 'Button' } })
    .find(j.JSXAttribute, { name: { name: 'color' } })
    .forEach(path => {
      path.node.name.name = 'variant';
    });

  return root.toSource();
}
```

Run it across your codebase:

```bash
npx jscodeshift -t transforms/rename-prop.js src/**/*.tsx
```

This is way safer than regex because it won't accidentally rename a `color` prop on a completely different component, or mangle a string that happens to contain the word "color." I learned this the hard way with a sed command that renamed things inside comments and string literals. The jscodeshift approach understands the difference.

## When Automation Isn't Worth It

I want to be honest here because the automation-everything mindset can waste more time than it saves. There's a classic XKCD about spending six hours automating a task that takes five minutes, and I've lived that comic more than once.

**Don't automate one-off tasks.** If you're migrating a database schema once, just do it manually. Writing a script for something you'll never do again is procrastination disguised as productivity.

**Don't automate things that change frequently.** If your deploy process changes every sprint because the team is still figuring it out, any automation you write will be outdated by next week. Wait until the process stabilizes, then automate it.

**Don't automate things that need human judgment.** Code review, architecture decisions, choosing between two valid approaches -- these require context that's really hard to encode in a script. Automating the mechanical parts around these tasks (like setting up the PR template or running checks) is great. Automating the decision itself is usually a mistake.

**Watch out for maintenance costs.** Every automation you write is code you have to maintain. Shell scripts break when you upgrade your OS. Git hooks break when you change your toolchain. The best automations are the simple ones that have minimal dependencies and rarely need updating.

The sweet spot is automating the tasks that are boring, frequent, and stable. Nail those, and you free up your mental energy for the work that actually requires your brain. That's the whole point -- not to automate everything, but to automate the right things so you can focus on the interesting problems.
