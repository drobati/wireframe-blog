---
layout: default
title: "The JavaScript Feature Nobody Uses (But Should)"
categories: javascript webdev
---

If I told you there's a built-in JavaScript function that deep clones objects -- handles Dates, RegExps, Maps, Sets, ArrayBuffers, and even circular references -- and it's been sitting in your browser since 2022, you'd probably think I was making it up. But it's real, it's called `structuredClone()`, and almost nobody uses it.

## The Feature

`structuredClone()` is a global function that creates a deep copy of a value using the structured clone algorithm. That's the same algorithm the browser uses internally when passing data between Web Workers or storing things in IndexedDB. It's not new tech -- it's just newly exposed to us as a simple function call.

Here's the basic usage:

```javascript
const original = {
  name: "Derek",
  settings: {
    theme: "dark",
    notifications: { email: true, sms: false }
  },
  createdAt: new Date("2024-01-15"),
  tags: new Set(["javascript", "react", "node"])
};

const clone = structuredClone(original);

clone.settings.notifications.email = false;
clone.tags.add("python");

console.log(original.settings.notifications.email); // true (unchanged!)
console.log(original.tags.has("python")); // false (unchanged!)
```

That's it. One function call. No libraries, no hacks, no edge cases to worry about. The clone is completely independent of the original, all the way down through every nested level.

It works in all modern browsers (Chrome 98+, Firefox 94+, Safari 15.4+), Node.js 17+, and Deno. If you're building anything in 2025, your target environments almost certainly support it.

## Why It's Overlooked

I think there are two reasons `structuredClone()` flies under the radar. First, the JavaScript ecosystem already had "solutions" to this problem, and once you learn a workaround, you stop looking for better answers. Every JS developer learns the JSON trick early on:

```javascript
const clone = JSON.parse(JSON.stringify(original));
```

It works for simple objects, so people internalize it as "the way to deep clone" and move on. The second reason is that it wasn't announced with fanfare. There was no big TC39 proposal, no conference talks, no hype cycle. It quietly shipped across browsers and runtimes, and most devs just never heard about it.

Meanwhile, libraries like Lodash have had `_.cloneDeep()` for years, and plenty of codebases still pull in Lodash for that one function. I've seen `package.json` files where Lodash was a dependency solely because someone needed deep cloning in three places. That's a lot of bundle weight for something the platform gives you for free.

## Real-World Use Case

Let me show you where this actually matters. Say you're building a form in React where users can edit their profile, and you want to let them cancel and revert to the original state. You grab the user object from your API and stash a copy as the "original" to diff against or revert to.

```javascript
function ProfileEditor({ user }) {
  const [original] = useState(() => structuredClone(user));
  const [draft, setDraft] = useState(() => structuredClone(user));

  const hasChanges = JSON.stringify(original) !== JSON.stringify(draft);

  const handleCancel = () => {
    setDraft(structuredClone(original));
  };

  // ... render form fields bound to draft
}
```

Without `structuredClone()`, you'd risk the `original` and `draft` sharing nested references. One mutation to a nested address object or a preferences map would corrupt your "clean" copy, and suddenly your cancel button doesn't work anymore.

Here's another one I hit all the time: Redux-style state updates where you need to deeply modify a slice of state without mutating the source. Or when you're writing tests and need to set up isolated fixtures from a shared template object. Any time you need a true, independent copy of a complex data structure, `structuredClone()` is your tool.

```javascript
// Test fixtures without cross-contamination
const baseUser = {
  id: 1,
  profile: { name: "Test User", preferences: new Map([["lang", "en"]]) },
  loginHistory: [new Date("2024-06-01"), new Date("2024-07-15")]
};

test("updating preferences doesn't affect other tests", () => {
  const user = structuredClone(baseUser);
  user.profile.preferences.set("lang", "fr");
  expect(baseUser.profile.preferences.get("lang")).toBe("en"); // safe
});
```

## Before & After

Let's look at the JSON trick and where it falls apart. Here's a common scenario with mixed types:

**Before (JSON.parse/JSON.stringify):**

```javascript
const original = {
  name: "Project Alpha",
  createdAt: new Date("2024-03-15"),
  pattern: /^user-\d+$/,
  metadata: new Map([["version", 2], ["status", "active"]]),
  tags: new Set(["important", "reviewed"])
};

const clone = JSON.parse(JSON.stringify(original));

console.log(clone.createdAt);          // "2024-03-15T00:00:00.000Z" (string, not Date!)
console.log(clone.pattern);            // {} (empty object, RegExp is gone!)
console.log(clone.metadata);           // {} (Map is gone!)
console.log(clone.tags);               // {} (Set is gone!)
```

The JSON approach silently destroys your data. Dates become strings, RegExps become empty objects, and Maps and Sets vanish entirely. No error, no warning -- just broken data that might not surface until production.

**After (structuredClone):**

```javascript
const original = {
  name: "Project Alpha",
  createdAt: new Date("2024-03-15"),
  pattern: /^user-\d+$/,
  metadata: new Map([["version", 2], ["status", "active"]]),
  tags: new Set(["important", "reviewed"])
};

const clone = structuredClone(original);

console.log(clone.createdAt);                  // Date object (correct!)
console.log(clone.createdAt instanceof Date);  // true
console.log(clone.pattern);                    // /^user-\d+$/ (preserved!)
console.log(clone.metadata.get("version"));    // 2 (Map works!)
console.log(clone.tags.has("important"));      // true (Set works!)
```

Everything comes through intact. And here's the kicker -- it even handles circular references:

```javascript
const obj = { name: "circular" };
obj.self = obj; // circular reference

// JSON approach: THROWS
// JSON.parse(JSON.stringify(obj)); // TypeError: Converting circular structure to JSON

// structuredClone: works fine
const clone = structuredClone(obj);
console.log(clone.self === clone); // true (circular ref preserved, pointing to clone)
```

The spread operator is the other common approach, but it only does a shallow copy:

```javascript
const original = { user: { name: "Derek", scores: [95, 87, 92] } };

// Spread: shallow copy
const shallow = { ...original };
shallow.user.scores.push(100);
console.log(original.user.scores); // [95, 87, 92, 100] -- mutated!

// structuredClone: deep copy
const deep = structuredClone(original);
deep.user.scores.push(100);
console.log(original.user.scores); // [95, 87, 92] -- safe
```

## When Not to Use It

`structuredClone()` is great, but it's not universal. There are a few things it explicitly cannot clone:

- **Functions**: If your object has methods or callbacks attached, `structuredClone()` will throw a `DataCloneError`. The structured clone algorithm doesn't support functions.
- **DOM nodes**: You can't clone elements from the page.
- **Prototype chains**: The clone won't preserve custom prototypes. Class instances come back as plain objects.
- **Property descriptors**: Getters, setters, and non-enumerable properties are not preserved.

```javascript
// This will throw
const withFunction = {
  name: "Derek",
  greet() { return `Hi, I'm ${this.name}`; }
};
// structuredClone(withFunction); // DataCloneError!

// Class instances lose their prototype
class User {
  constructor(name) { this.name = name; }
  greet() { return `Hi, I'm ${this.name}`; }
}
const user = new User("Derek");
const clone = structuredClone(user);
console.log(clone instanceof User); // false
console.log(clone.greet);           // undefined
```

If you need to clone objects with methods, you're still in custom territory -- write a factory function or use a library that understands your specific types. And if all you need is a shallow copy of a flat object, the spread operator is perfectly fine and faster.

But for the vast majority of "I need a deep copy of this data structure" situations -- API responses, state snapshots, test fixtures, configuration objects -- `structuredClone()` is the right tool. It's built-in, it's fast, it's correct, and it handles the edge cases that have been silently breaking code for years.

Stop reaching for `JSON.parse(JSON.stringify())`. You've got something better now. Use it.
