---
layout: default
title: "Building a CLI Tool That Actually Ships"
categories: node cli tooling
---

I've written about building a basic Node CLI before, but there's a massive gap between a script that works on your machine and a tool that other developers actually install and rely on. I've shipped a few CLI tools to npm at this point, and every time I learn something new about what separates a toy from a tool. This post covers the full journey -- from picking the right framework to publishing a polished package that people can trust.

## Choosing Your Stack

The Node ecosystem has three serious contenders for CLI frameworks, and picking the right one early saves you from painful rewrites later.

**Commander** is the minimalist choice. It's been around forever, has zero opinions about your architecture, and gets out of your way. If you're building something with a handful of commands and flags, Commander is probably all you need. It's what I reach for on smaller tools.

```javascript
import { program } from 'commander';

program
  .name('deploy')
  .description('Deploy your app to production')
  .version('1.0.0');

program
  .command('push')
  .description('Push the current build')
  .option('-e, --env <environment>', 'target environment', 'staging')
  .option('--dry-run', 'simulate the deploy without executing')
  .action((options) => {
    console.log(`Deploying to ${options.env}...`);
  });

program.parse();
```

**Yargs** is the Swiss Army knife. It gives you automatic help generation, argument coercion, and a really expressive API for defining complex argument relationships. If your CLI has lots of options with interdependencies (like "flag X requires flag Y"), yargs handles that beautifully. The downside is the API can feel verbose for simple cases.

**oclif** (by Salesforce/Heroku) is the heavy hitter. It's a full framework with a plugin system, auto-generated documentation, and a class-based architecture. If you're building something like the Heroku CLI or a tool with dozens of commands that multiple teams contribute to, oclif is the right call. For most of us, though, it's overkill.

My recommendation: start with Commander. If you outgrow it, you'll know because you'll find yourself fighting it. Migrating to yargs or oclif at that point is straightforward because you'll have a clear picture of what you actually need.

## Argument Parsing Done Right

Bad argument parsing is the fastest way to make your CLI feel broken. Users expect flags, subcommands, and validation to work exactly like every other Unix tool they use.

Here's a pattern I use for subcommands with proper validation:

```javascript
import { program, InvalidArgumentError } from 'commander';

function parsePort(value) {
  const port = parseInt(value, 10);
  if (isNaN(port) || port < 1 || port > 65535) {
    throw new InvalidArgumentError('Must be a number between 1 and 65535.');
  }
  return port;
}

program
  .command('serve')
  .description('Start the development server')
  .argument('<directory>', 'directory to serve')
  .option('-p, --port <number>', 'port to listen on', parsePort, 3000)
  .option('-H, --host <address>', 'host to bind to', 'localhost')
  .option('--cors', 'enable CORS headers')
  .action((directory, options) => {
    startServer(directory, options);
  });

program
  .command('build')
  .description('Create a production build')
  .argument('<entry>', 'entry point file')
  .option('-o, --output <dir>', 'output directory', './dist')
  .option('--minify', 'minify the output', true)
  .option('--no-minify', 'skip minification')
  .option('--sourcemap', 'generate source maps')
  .action((entry, options) => {
    runBuild(entry, options);
  });

program.parse();
```

A few things to notice: custom argument parsers with `InvalidArgumentError` give users clear error messages instead of cryptic failures. Default values mean users don't need to specify everything. The `--no-minify` pattern lets you flip boolean defaults. These details matter more than you think.

Always support `--help` implicitly (Commander does this for free) and add examples to your command descriptions. A user who can't figure out your tool in 10 seconds will uninstall it.

## User Experience in the Terminal

A CLI that dumps raw text to stdout works, but it feels like talking to a wall. A few small additions make a dramatic difference in how professional your tool feels.

```javascript
import chalk from 'chalk';
import ora from 'ora';

async function deploy(environment) {
  console.log(chalk.bold(`\nDeploying to ${chalk.cyan(environment)}\n`));

  const spinner = ora('Building assets...').start();

  try {
    await buildAssets();
    spinner.succeed('Assets built');

    spinner.start('Uploading to CDN...');
    await uploadToCDN();
    spinner.succeed('Upload complete');

    spinner.start('Invalidating cache...');
    await invalidateCache();
    spinner.succeed('Cache invalidated');

    console.log(chalk.green('\nDeploy successful!'));
    console.log(chalk.dim(`View at: https://${environment}.example.com\n`));
  } catch (error) {
    spinner.fail('Deploy failed');
    console.error(chalk.red(`\nError: ${error.message}`));
    process.exit(1);
  }
}
```

**Chalk** adds color without going overboard. I use it for three things: highlighting important values (cyan), success messages (green), and errors (red). That's it. Don't rainbow your output.

**Ora** gives you spinners for long-running operations. Users need to know something is happening, especially for network calls or builds that take more than a second. The `.succeed()` and `.fail()` methods transition the spinner into a final status message, which looks clean.

For progress bars on operations where you know the total (like processing files), use `cli-progress`:

```javascript
import { SingleBar } from 'cli-progress';

const bar = new SingleBar({ format: '{bar} {percentage}% | {value}/{total} files' });
bar.start(files.length, 0);

for (const file of files) {
  await processFile(file);
  bar.increment();
}

bar.stop();
```

One more thing: respect the `NO_COLOR` environment variable and pipe detection. If your output is being piped to another program, strip the colors. Chalk handles this automatically, which is another reason to use it.

## Error Handling & Exit Codes

Exit codes aren't just a nice-to-have -- they're how your CLI communicates with the rest of the Unix ecosystem. Scripts, CI pipelines, and other tools all depend on exit codes to decide what to do next.

```javascript
// 0 = success (default, no action needed)
// 1 = general error
// 2 = misuse of command (bad arguments, missing required flags)

function handleError(error) {
  if (error.code === 'ENOENT') {
    console.error(chalk.red(`Error: File not found: ${error.path}`));
    console.error(chalk.dim('Run with --help for usage information.'));
    process.exit(2);
  }

  if (error.code === 'EACCES') {
    console.error(chalk.red(`Error: Permission denied: ${error.path}`));
    console.error(chalk.dim('Try running with sudo or check file permissions.'));
    process.exit(1);
  }

  // Unexpected errors -- show the stack trace in verbose mode
  if (process.env.DEBUG || globalOptions.verbose) {
    console.error(error);
  } else {
    console.error(chalk.red(`Error: ${error.message}`));
    console.error(chalk.dim('Run with DEBUG=1 for more details.'));
  }
  process.exit(1);
}

// Catch unhandled rejections globally
process.on('unhandledRejection', (error) => {
  handleError(error);
});
```

The key insight is that error messages should be actionable. Don't just say "file not found." Tell the user which file, why you were looking for it, and what they can do about it. Coming from Python test automation, I learned that the quality of your error output determines whether someone can debug a problem in 5 seconds or 5 minutes.

Also, always handle `SIGINT` (Ctrl+C) gracefully. Clean up temp files, kill child processes, and exit with code 130 (the Unix convention for SIGINT):

```javascript
process.on('SIGINT', () => {
  console.log(chalk.dim('\nCleaning up...'));
  cleanup();
  process.exit(130);
});
```

## Testing a CLI

Testing a CLI is awkward because your "function" is a whole process with stdin, stdout, stderr, and exit codes. Here's how I break it down into layers.

**Unit test your logic separately from the CLI layer.** Extract your business logic into plain functions and test those directly. The CLI should be a thin wrapper that parses arguments and calls your functions.

```javascript
// lib/deploy.js -- pure logic, easy to test
export async function buildManifest(directory, options) {
  const files = await glob(`${directory}/**/*`);
  return files.filter(f => !options.ignore.includes(f));
}

// deploy.test.js
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { buildManifest } from './lib/deploy.js';

describe('buildManifest', () => {
  it('excludes ignored files', async () => {
    const result = await buildManifest('./fixtures', {
      ignore: ['fixtures/secret.env']
    });
    assert.ok(!result.includes('fixtures/secret.env'));
  });
});
```

**Integration test the actual CLI with `child_process`:**

```javascript
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const exec = promisify(execFile);

describe('CLI integration', () => {
  it('prints help with --help flag', async () => {
    const { stdout } = await exec('node', ['./bin/cli.js', '--help']);
    assert.match(stdout, /Usage:/);
    assert.match(stdout, /deploy/);
  });

  it('exits with code 2 on unknown command', async () => {
    try {
      await exec('node', ['./bin/cli.js', 'nonexistent']);
      assert.fail('Should have thrown');
    } catch (error) {
      assert.strictEqual(error.code, 2);
    }
  });

  it('serves directory on specified port', async () => {
    const { stdout } = await exec('node', [
      './bin/cli.js', 'serve', './fixtures', '--port', '9999'
    ]);
    assert.match(stdout, /Listening on.*9999/);
  });
});
```

Run these as part of your CI pipeline. I usually have unit tests running on every commit and integration tests on PRs. The integration tests are slower but they catch the argument parsing bugs that unit tests can't see.

## Publishing to npm

Getting your package onto npm is straightforward, but there are a few things that trip people up the first time.

Your `package.json` needs a `bin` field that maps command names to entry files:

```json
{
  "name": "my-deploy-tool",
  "version": "1.0.0",
  "bin": {
    "deploy": "./bin/cli.js"
  },
  "files": [
    "bin",
    "lib"
  ],
  "engines": {
    "node": ">=18"
  }
}
```

Make sure your entry file has a shebang line at the top:

```javascript
#!/usr/bin/env node

import { program } from 'commander';
// ... rest of your CLI
```

The `files` array is important -- it controls what actually gets published. Without it, npm publishes everything that isn't in `.gitignore`, which might include test fixtures, docs, or other stuff your users don't need.

For the actual publishing workflow, I use **np** instead of raw `npm publish`. It handles version bumping, git tagging, and running your tests before publishing:

```bash
npm install -g np

# When you're ready to publish
np minor  # or np patch, np major
```

`np` walks you through a checklist: it runs tests, bumps the version, creates a git tag, pushes to GitHub, and publishes to npm. It's the difference between "I hope I didn't forget a step" and "I know I didn't."

Before your first publish, test your package locally with `npm link`:

```bash
cd my-deploy-tool
npm link

# Now "deploy" command is available globally
deploy --help

# When done testing
npm unlink -g my-deploy-tool
```

## Lessons From Shipping

After shipping a few CLI tools, here's what I wish someone had told me upfront.

**Start with the smallest useful thing.** Your first version should do one thing well. Ship that, get feedback, then add features. I spent weeks building a comprehensive tool once, and the first user request was for something I hadn't even considered. Ship early.

**Add `--help` before anything else.** It forces you to think about your API design before you write implementation code. If you can't explain a command clearly in a help string, the design is probably wrong.

**Respect Unix conventions.** Stdout is for output, stderr is for messages. Exit code 0 means success. Flags use `--long-name` and `-s` for short forms. Your users already know these conventions even if they can't articulate them, and breaking them creates friction.

**Version everything.** Use semver properly. If you change a flag name, that's a breaking change. If you add a new command, that's a minor bump. Your users might be pinning your tool in CI configs, and breaking them silently is a fast way to lose trust.

**Write a good README.** Include installation instructions, a quick-start example, and a full command reference. Most people will decide whether to use your tool based entirely on the README. A gif or screenshot of your tool in action is worth a thousand words.

Building CLI tools is one of the most satisfying things you can do as a developer. You're making something that lives right where other developers work -- in the terminal. Take the time to make it feel solid, and people will thank you for it.
