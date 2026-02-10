---
layout: default
title: "What Happens When You Type npm install"
categories: node javascript tooling
---

You've probably typed `npm install` thousands of times. I know I have. But have you ever actually thought about what happens between pressing Enter and seeing that "added 847 packages" message? There's a surprisingly complex pipeline running under the hood, and understanding it will save you real debugging time when things go sideways. Let's walk through the whole thing.

## The Command

When you run `npm install` with no arguments, npm does two things depending on context. If there's a `package-lock.json` present, it tries to reproduce the exact dependency tree described in that lockfile. If there's no lockfile, it resolves everything from scratch using the version ranges in `package.json`.

If you run `npm install some-package`, it does something different: it resolves that specific package, adds it to your `package.json` dependencies, updates the lockfile, and installs everything.

Either way, the first thing npm actually does is read your `package.json` and build a representation of what you've asked for. It parses every entry in `dependencies`, `devDependencies`, `peerDependencies`, and `optionalDependencies`. Each one is a package name paired with a semver range -- something like `"express": "^4.18.2"` or `"lodash": "~4.17.0"`.

```json
{
  "dependencies": {
    "express": "^4.18.2",
    "lodash": "~4.17.21",
    "uuid": "9.0.0"
  }
}
```

That caret (`^`) means "compatible with 4.18.2" -- so any version `>=4.18.2` and `<5.0.0`. The tilde (`~`) means "approximately 4.17.21" -- so `>=4.17.21` and `<4.18.0`. And a bare version like `9.0.0` means exactly that version, nothing else. These distinctions matter a lot for what happens next.

## Resolving Dependencies

This is where things get interesting. npm needs to figure out the complete dependency tree -- not just your direct dependencies, but everything they depend on, and everything *those* depend on, all the way down.

Take `express` as an example. When you install Express, you're not just getting one package. Express depends on `body-parser`, which depends on `raw-body`, which depends on `unpipe` and `bytes`. Express also depends on `accepts`, which depends on `mime-types`, which depends on `mime-db`. The tree fans out quickly -- a typical Express install pulls in around 60 packages.

npm builds this tree by reading each package's own `package.json` to discover its dependencies, then recursively doing the same for each of those. It's essentially a graph traversal. For each dependency, npm needs to find a version that satisfies the semver range while also being compatible with every other package that depends on the same thing.

```
your-app
├── express@4.18.2
│   ├── body-parser@1.20.1
│   │   ├── bytes@3.1.2
│   │   ├── raw-body@2.5.1
│   │   └── ...
│   ├── accepts@1.3.8
│   │   └── mime-types@2.1.35
│   │       └── mime-db@1.52.0
│   └── ... (50+ more)
└── lodash@4.17.21
```

When two packages depend on different versions of the same thing, npm has to make decisions. Can it find a single version that satisfies both ranges? If so, it uses that one version. If not, it has to install multiple versions of the same package and nest them appropriately. This resolution step is one of the most computationally expensive parts of the whole process.

## The Registry Request

For each package it needs to resolve, npm makes an HTTP request to the npm registry (by default, `https://registry.npmjs.org/`). Specifically, it fetches the package's metadata document, which contains every published version along with its own dependency declarations, tarball URLs, integrity hashes, and more.

The request looks something like this:

```
GET https://registry.npmjs.org/express
```

The response is a JSON document that can be surprisingly large -- the one for Express is over 500KB because it includes metadata for every version ever published. npm uses this to find the highest version that satisfies your semver range, then grabs the tarball URL for that specific version.

```json
{
  "name": "express",
  "versions": {
    "4.18.2": {
      "dependencies": {
        "body-parser": "1.20.1",
        "accepts": "~1.3.8"
      },
      "dist": {
        "tarball": "https://registry.npmjs.org/express/-/express-4.18.2.tgz",
        "integrity": "sha512-..."
      }
    }
  }
}
```

npm caches these metadata responses locally (in `~/.npm/_cacache` by default), so subsequent installs don't have to hit the network for packages it's already seen. It also caches the actual tarballs. If you've ever noticed that a second `npm install` on the same project runs way faster, that's the cache doing its job.

When you're behind a corporate proxy or using a private registry (like Artifactory or Verdaccio), npm routes these requests through your configured registry URL instead. This is set in your `.npmrc` file or via `npm config set registry`.

## Deduplication & Hoisting

Once npm has resolved the full dependency tree, it needs to figure out how to lay it out on disk. This is where deduplication and hoisting come in, and it's one of the cleverest (and most confusing) parts of the system.

The naive approach would be to nest every dependency inside the package that depends on it:

```
node_modules/
├── express/
│   └── node_modules/
│       ├── accepts/
│       │   └── node_modules/
│       │       └── mime-types/
│       └── body-parser/
│           └── node_modules/
│               └── bytes/
```

This works, but it's massively wasteful. If three packages all depend on `mime-types@2.1.35`, you'd have three copies on disk. Worse, on Windows you'd quickly hit path length limits with all that nesting.

So npm hoists packages up to the top level of `node_modules` whenever possible. If only one version of a package is needed across the entire tree, it goes at the root:

```
node_modules/
├── express/
├── accepts/
├── mime-types/     (hoisted -- used by multiple packages)
├── body-parser/
├── bytes/
└── ...
```

When there's a version conflict -- say, package A needs `debug@4.3.4` and package B needs `debug@3.2.7` -- npm puts the more commonly used version at the top level and nests the other one:

```
node_modules/
├── debug/          (4.3.4, used by most packages)
├── package-a/
└── package-b/
    └── node_modules/
        └── debug/  (3.2.7, only used by package-b)
```

Node's module resolution algorithm walks up the directory tree looking for `node_modules` folders, so package B will find its own nested `debug@3.2.7` first, while everything else finds `debug@4.3.4` at the root. It's elegant once you understand it, but it also means the structure of `node_modules` is non-deterministic -- the same `package.json` can produce different folder layouts depending on install order. That's a big part of why the lockfile exists.

## Writing to Disk

With the tree resolved and the layout planned, npm downloads and extracts the actual package tarballs. Each package is distributed as a `.tgz` file containing the package's source code, `package.json`, and whatever else the author included.

npm extracts these into `node_modules` according to the layout it computed during the deduplication step. It also builds the `.package-lock.json` file inside `node_modules` (this is different from the top-level lockfile) which serves as a hidden cache of the tree structure.

If any packages have install scripts -- `preinstall`, `install`, or `postinstall` hooks in their `package.json` -- npm runs those now. This is how native addons like `node-sass` or `bcrypt` compile their C++ code. It's also a significant security surface: install scripts run arbitrary code on your machine with your user permissions. This is why `npm audit` and tools like `socket.dev` exist.

```json
{
  "scripts": {
    "postinstall": "node ./build.js"
  }
}
```

The write step is also where you might see npm rebuild things. If you switch between operating systems or Node versions, the cached packages might not be compatible, and npm needs to recompile native modules. That's what `npm rebuild` is for, and it happens implicitly during install when needed.

## The Lockfile

The `package-lock.json` file is npm's answer to "works on my machine" problems. It records the exact version of every package that was installed, along with the integrity hash and resolved URL for each one.

```json
{
  "packages": {
    "node_modules/express": {
      "version": "4.18.2",
      "resolved": "https://registry.npmjs.org/express/-/express-4.18.2.tgz",
      "integrity": "sha512-J7cjnX2KLSO+...",
      "dependencies": {
        "accepts": "~1.3.8",
        "body-parser": "1.20.1"
      }
    }
  }
}
```

When the lockfile exists and you run `npm install`, npm skips the resolution step entirely. It already knows the exact version of every package, so it just fetches the tarballs (from cache if possible) and writes them to disk. This is why `npm ci` exists -- it's a stricter version of `npm install` that refuses to run if the lockfile is out of date and always starts from a clean `node_modules`. It's what you should use in CI/CD pipelines.

**You should always commit your lockfile to git.** Without it, two developers on the same team could run `npm install` on the same `package.json` and end up with different dependency versions, because a transitive dependency published a new patch release between their installs. The lockfile prevents that drift.

The one exception: if you're publishing a library (not an application), your lockfile shouldn't be committed. Libraries should let the consuming application determine the exact versions, and the lockfile would have no effect anyway since npm ignores lockfiles in dependencies.

## What Can Go Wrong

Now for the fun part -- the failure modes. Once you understand the install pipeline, debugging these makes a lot more sense.

**Phantom dependencies** happen when your code imports a package that you never explicitly listed in your `package.json`. It works because some other dependency pulled it in and it got hoisted to the top of `node_modules`. Everything's fine until that other dependency drops or changes its version of the hoisted package, and your code suddenly breaks with "module not found." This is especially common when refactoring -- you remove a direct dependency without realizing your code was leaning on something it brought along.

```javascript
// This works... until it doesn't
const debug = require('debug'); // Not in your package.json!
// It's there because express depends on it and it got hoisted
```

**Version conflicts** get ugly when peer dependencies are involved. If you install two packages that declare incompatible peer dependency ranges, npm will warn you (or error in strict mode). The typical symptom is "Could not resolve peer dependency" messages that leave you choosing between downgrading one package or using `--legacy-peer-deps` to force the install.

**Corrupted cache** is the classic "turn it off and turn it on again" problem for npm. If your installs are failing with integrity errors or weird extraction failures, `npm cache clean --force` often fixes it. The cache lives at `~/.npm/_cacache`, and occasionally it gets into a bad state -- especially after interrupted installs or disk space issues.

**Platform-specific failures** hit you when a package has native code that needs compiling. If you don't have the right build tools installed (Python, C++ compiler, node-gyp), the install will fail during the postinstall step. This is less common than it used to be, but it still bites people regularly with packages like `sharp`, `sqlite3`, or `node-canvas`.

**The big node_modules** problem is more of an annoyance than a bug, but it's worth mentioning. A typical React project can have 200MB or more in `node_modules`. That's a lot of disk space and a lot of files, which makes operations like copying, searching, and backing up slow. Tools like `pnpm` address this with a content-addressable store that hard-links packages instead of copying them, and `yarn` uses its own caching strategy. But with standard npm, every project gets its own full copy of every dependency.

Understanding this pipeline won't prevent every npm headache, but it gives you a mental model for where things break. Next time you see a confusing error, you can ask yourself: is this a resolution problem, a registry problem, a hoisting problem, or a cache problem? That narrows the debugging space dramatically. Happy installing.
