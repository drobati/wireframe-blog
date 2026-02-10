---
layout: default
title: "Refactoring Callback Hell to async/await"
categories: javascript refactoring es6
---

I spent my first two years writing JavaScript thinking deeply nested callbacks were just how things worked. Coming from Python, where everything ran top-to-bottom, the pyramid of doom felt like a rite of passage. It wasn't until I sat down and actually refactored a real piece of callback-heavy code that I understood how much cleaner JavaScript can be. Let me walk you through the exact process I use.

## The Original Code

Here's the kind of code I'm talking about. This function reads a config file, parses it to get a user ID, fetches that user's data from an API, and then updates a database record. Every step depends on the previous one, and every step can fail.

```javascript
const fs = require('fs');
const https = require('https');
const db = require('./db');

function processUserUpdate(configPath, callback) {
  fs.readFile(configPath, 'utf8', (err, data) => {
    if (err) {
      callback(new Error('Failed to read config: ' + err.message));
      return;
    }

    let config;
    try {
      config = JSON.parse(data);
    } catch (parseErr) {
      callback(new Error('Failed to parse config: ' + parseErr.message));
      return;
    }

    https.get(`https://api.example.com/users/${config.userId}`, (res) => {
      let body = '';
      res.on('data', (chunk) => { body += chunk; });
      res.on('end', () => {
        let user;
        try {
          user = JSON.parse(body);
        } catch (parseErr) {
          callback(new Error('Failed to parse API response'));
          return;
        }

        db.updateUser(user.id, { lastSync: Date.now(), profile: user.profile }, (dbErr, result) => {
          if (dbErr) {
            callback(new Error('Database update failed: ' + dbErr.message));
            return;
          }

          console.log('User updated successfully');
          callback(null, result);
        });
      });
    }).on('error', (httpErr) => {
      callback(new Error('API request failed: ' + httpErr.message));
    });
  });
}
```

Count the indentation levels. We're five or six deep by the time we hit the database call. Every error needs its own `return` statement to avoid falling through. The control flow is genuinely hard to follow, and if you need to add another step -- say, sending a notification after the DB update -- you're nesting even deeper.

This is what people mean by callback hell. It's not just ugly -- it's a maintenance nightmare. Let's fix it.

## Step 1: Promises

The first step is wrapping the callback-based APIs in Promises. This doesn't change the logic at all -- it just gives us a different interface to work with.

```javascript
const fs = require('fs');
const https = require('https');
const db = require('./db');

function readFileAsync(path) {
  return new Promise((resolve, reject) => {
    fs.readFile(path, 'utf8', (err, data) => {
      if (err) reject(new Error('Failed to read config: ' + err.message));
      else resolve(data);
    });
  });
}

function fetchUser(userId) {
  return new Promise((resolve, reject) => {
    https.get(`https://api.example.com/users/${userId}`, (res) => {
      let body = '';
      res.on('data', (chunk) => { body += chunk; });
      res.on('end', () => {
        try {
          resolve(JSON.parse(body));
        } catch (err) {
          reject(new Error('Failed to parse API response'));
        }
      });
    }).on('error', (err) => {
      reject(new Error('API request failed: ' + err.message));
    });
  });
}

function updateUserAsync(id, data) {
  return new Promise((resolve, reject) => {
    db.updateUser(id, data, (err, result) => {
      if (err) reject(new Error('Database update failed: ' + err.message));
      else resolve(result);
    });
  });
}
```

Now we can chain them with `.then()`:

```javascript
function processUserUpdate(configPath) {
  return readFileAsync(configPath)
    .then(data => JSON.parse(data))
    .then(config => fetchUser(config.userId))
    .then(user => updateUserAsync(user.id, {
      lastSync: Date.now(),
      profile: user.profile
    }))
    .then(result => {
      console.log('User updated successfully');
      return result;
    });
}
```

Already way better. The flow reads top-to-bottom. Each step is one line. But we can do even better.

## Step 2: async/await

With our Promise-based wrappers in place, switching to async/await is almost trivial. In real projects, you'd probably use `fs.promises` (built into Node) and a proper HTTP client like `fetch` or `axios` that already returns Promises, so you wouldn't even need the wrappers. But let's work with what we have.

```javascript
async function processUserUpdate(configPath) {
  const data = await readFileAsync(configPath);
  const config = JSON.parse(data);

  const user = await fetchUser(config.userId);

  const result = await updateUserAsync(user.id, {
    lastSync: Date.now(),
    profile: user.profile
  });

  console.log('User updated successfully');
  return result;
}
```

Look at that. It reads exactly like synchronous code. Each line does one thing. The data flows downward in a way your brain can follow without tracing callback arguments. If you need to add a step -- say, logging the update to an audit trail -- you just add a line. No re-indenting, no restructuring.

In practice, I'd go one step further and use Node's built-in promise APIs to eliminate the wrappers entirely:

```javascript
const { readFile } = require('fs/promises');

async function processUserUpdate(configPath) {
  const data = await readFile(configPath, 'utf8');
  const config = JSON.parse(data);

  const user = await fetchUser(config.userId);

  const result = await updateUserAsync(user.id, {
    lastSync: Date.now(),
    profile: user.profile
  });

  console.log('User updated successfully');
  return result;
}
```

## Step 3: Error Handling

With callbacks, you had to check for errors at every single level. Miss one and your app silently does the wrong thing. With async/await, you get to use try/catch, which is the same pattern you'd use in Python, Java, or any other language with structured error handling.

```javascript
async function processUserUpdate(configPath) {
  try {
    const data = await readFile(configPath, 'utf8');
    const config = JSON.parse(data);
    const user = await fetchUser(config.userId);

    const result = await updateUserAsync(user.id, {
      lastSync: Date.now(),
      profile: user.profile
    });

    console.log('User updated successfully');
    return result;
  } catch (error) {
    console.error('processUserUpdate failed:', error.message);
    throw error; // re-throw so the caller can handle it too
  }
}
```

One try/catch wraps the entire flow. Any error from any step lands in the same catch block. If you need more granular handling -- say, you want to retry the API call but not the file read -- you can nest try/catch blocks around specific steps:

```javascript
async function processUserUpdate(configPath) {
  const data = await readFile(configPath, 'utf8');
  const config = JSON.parse(data);

  let user;
  try {
    user = await fetchUser(config.userId);
  } catch (error) {
    console.warn('First attempt failed, retrying...');
    user = await fetchUser(config.userId); // retry once
  }

  const result = await updateUserAsync(user.id, {
    lastSync: Date.now(),
    profile: user.profile
  });

  return result;
}
```

Compare that to implementing retry logic in nested callbacks. It's not even close.

You can also use `.catch()` on individual awaited Promises if you prefer a more functional style, but I find try/catch reads better in most cases. The key insight is that async/await gives you the same error propagation behavior as synchronous code -- errors bubble up until something catches them.

## Step 4: Parallelism With Promise.all

Here's where things get really powerful. Say your requirements change and now you need to fetch the user data AND their recent orders before updating the database. These two API calls don't depend on each other, so there's no reason to run them sequentially.

```javascript
async function processUserUpdate(configPath) {
  const data = await readFile(configPath, 'utf8');
  const config = JSON.parse(data);

  // These two requests run in parallel
  const [user, orders] = await Promise.all([
    fetchUser(config.userId),
    fetchOrders(config.userId)
  ]);

  const result = await updateUserAsync(user.id, {
    lastSync: Date.now(),
    profile: user.profile,
    recentOrders: orders.slice(0, 5)
  });

  return result;
}
```

`Promise.all` takes an array of Promises and waits for all of them to resolve, returning their results in the same order. If either one fails, the whole thing rejects -- which is usually what you want. If you'd rather get partial results even when some fail, use `Promise.allSettled`:

```javascript
const results = await Promise.allSettled([
  fetchUser(config.userId),
  fetchOrders(config.userId),
  fetchNotifications(config.userId)
]);

// Each result has { status: 'fulfilled', value: ... }
// or { status: 'rejected', reason: ... }
const user = results[0].status === 'fulfilled' ? results[0].value : null;
const orders = results[1].status === 'fulfilled' ? results[1].value : [];
const notifications = results[2].status === 'fulfilled' ? results[2].value : [];
```

Try doing that cleanly with callbacks. You'd need a counter, a results array, and careful tracking of which callbacks have fired. It's one of those things that's technically possible but miserable to maintain.

## The Final Result

Here's the complete refactored code, start to finish. Compare this to the original callback version at the top:

```javascript
const { readFile } = require('fs/promises');

async function fetchUser(userId) {
  const response = await fetch(`https://api.example.com/users/${userId}`);
  if (!response.ok) throw new Error(`API error: ${response.status}`);
  return response.json();
}

async function fetchOrders(userId) {
  const response = await fetch(`https://api.example.com/users/${userId}/orders`);
  if (!response.ok) throw new Error(`API error: ${response.status}`);
  return response.json();
}

async function processUserUpdate(configPath) {
  try {
    const data = await readFile(configPath, 'utf8');
    const config = JSON.parse(data);

    const [user, orders] = await Promise.all([
      fetchUser(config.userId),
      fetchOrders(config.userId)
    ]);

    const result = await db.updateUser(user.id, {
      lastSync: Date.now(),
      profile: user.profile,
      recentOrders: orders.slice(0, 5)
    });

    console.log('User updated successfully');
    return result;
  } catch (error) {
    console.error('processUserUpdate failed:', error.message);
    throw error;
  }
}
```

It's flat, readable, and handles more functionality than the original (parallel fetches, clean error handling) in fewer lines. Every step is obvious. New developers on your team can read this and understand what it does without tracing callback chains.

## When Callbacks Still Make Sense

I don't want to give the impression that callbacks are always wrong. They're the right tool in a few specific situations.

**Event listeners** are inherently callback-based, and that's fine. You're not dealing with a one-time async operation -- you're subscribing to something that fires multiple times:

```javascript
button.addEventListener('click', handleClick);
socket.on('message', handleMessage);
emitter.on('data', processChunk);
```

**Streams** work the same way. When you're processing data chunk by chunk, you want the callback pattern because each chunk arrives independently:

```javascript
const stream = fs.createReadStream('large-file.txt');
stream.on('data', (chunk) => {
  // Process each chunk as it arrives
});
stream.on('end', () => {
  console.log('Done reading');
});
```

**Simple one-off operations** where you'd be wrapping a single callback in a Promise just to immediately await it sometimes aren't worth the overhead. If the API is already callback-based and you're in a context where that's fine, don't over-engineer it.

The rule of thumb I follow: if you have sequential async steps, use async/await. If you have repeated events, use callbacks or observables. And if you find yourself nesting more than two callbacks deep, it's time to refactor. Your future self will thank you.
