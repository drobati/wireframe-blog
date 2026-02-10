---
layout: default
title: "Node.js Gotchas That Bit Me in Production"
categories: node backend javascript
---

I came to Node.js from Python, where the runtime mostly stays out of your way. Node is different. It gives you incredible performance out of the box, but it also gives you a dozen ways to shoot yourself in the foot if you don't understand what's happening under the hood. Every gotcha on this list cost me real production downtime. Learn from my mistakes.

## Blocking the Event Loop

This is the cardinal sin of Node.js, and I committed it early. The event loop is single-threaded. If you block it, every request in your application waits. Every websocket message queues up. Health checks stop responding. Your load balancer thinks the server is dead.

My first encounter: we had an endpoint that accepted a JSON payload from a partner integration. Most payloads were a few kilobytes. One day, a partner sent a 50MB JSON blob. `JSON.parse()` is synchronous, and parsing 50MB of JSON on the main thread locked the event loop for several seconds. During those seconds, our API returned zero responses. Monitoring lit up like a Christmas tree.

The fix was straightforward -- validate payload size before parsing and stream large payloads:

```javascript
app.use(express.json({ limit: '1mb' }));

// For endpoints that genuinely need large payloads,
// parse in a worker thread
const { Worker } = require('worker_threads');

function parseJsonInWorker(jsonString) {
  return new Promise((resolve, reject) => {
    const worker = new Worker(`
      const { parentPort } = require('worker_threads');
      parentPort.on('message', (data) => {
        try {
          parentPort.postMessage(JSON.parse(data));
        } catch (err) {
          parentPort.postMessage({ error: err.message });
        }
      });
    `, { eval: true });

    worker.postMessage(jsonString);
    worker.on('message', (result) => {
      if (result.error) reject(new Error(result.error));
      else resolve(result);
      worker.terminate();
    });
  });
}
```

Another version of this: CPU-bound crypto operations. We had a password hashing endpoint using bcrypt with a cost factor of 14. Each hash took ~800ms of solid CPU time. Under load, this crushed our throughput. We switched to the async version (`bcrypt.hash` with a callback) which uses a thread pool under the hood, and the problem disappeared.

The takeaway: anything that takes more than a few milliseconds of synchronous computation needs to happen off the main thread. Profile with `--prof` or use `clinic.js` if you're not sure where the bottleneck is.

## Memory Leaks in Closures

Memory leaks in Node.js are sneaky because they don't crash your app immediately. They slowly eat memory over hours or days until the process hits its limit and gets OOM-killed. Then it restarts, runs fine for a while, and the cycle repeats.

The leak that cost me the most debugging time was a closure in an event handler. We had a service that listened for events from a message queue, and for each event, it created a handler that closed over the full event payload:

```javascript
// The leaky version
const EventEmitter = require('events');
const emitter = new EventEmitter();

function processEvents(eventStream) {
  eventStream.on('data', (event) => {
    // This closure captures `event` - a potentially large object
    const handler = () => {
      console.log(`Processing event ${event.id}`);
      // ... process the event
    };

    // BUG: registering a listener but never removing it
    emitter.on('flush', handler);
  });
}
```

Every incoming event registered a new listener on the `flush` event, and each listener held a reference to the full event object. Over thousands of events, memory ballooned. The fix was to either remove the listener after it fires or use `once` instead of `on`:

```javascript
// Fixed version
function processEvents(eventStream) {
  eventStream.on('data', (event) => {
    const eventId = event.id; // capture only what you need

    const handler = () => {
      console.log(`Processing event ${eventId}`);
    };

    emitter.once('flush', handler); // auto-removes after firing
  });
}
```

To debug this, I used `--inspect` to attach Chrome DevTools and took heap snapshots at 1-minute intervals. Comparing snapshots showed a growing number of closure objects tied to the emitter. If you suspect a memory leak, heap snapshots are your best tool. Take one early, take one later, diff them, and look for what's growing.

A quick diagnostic trick: monitor `process.memoryUsage().heapUsed` over time. If it trends upward and never comes back down after garbage collection, you have a leak.

## Unhandled Promise Rejections

Before Node 15, unhandled promise rejections just printed a warning and kept going. Your app would silently swallow errors and continue running in a potentially corrupted state. Since Node 15, unhandled rejections crash the process by default, which is actually better -- a loud crash is easier to fix than silent data corruption.

The problem is that it's easy to create unhandled rejections without realizing it:

```javascript
// This looks fine but has no error handling
app.get('/users/:id', async (req, res) => {
  const user = await getUserById(req.params.id);
  res.json(user);
});

// If getUserById throws, Express doesn't catch async errors
// in versions before Express 5. The promise rejects, nobody
// handles it, and in Node 15+ your process crashes.
```

The fix for Express 4 is to wrap every async route handler:

```javascript
// Wrapper that catches async errors and forwards to Express error handler
const asyncHandler = (fn) => (req, res, next) => {
  Promise.resolve(fn(req, res, next)).catch(next);
};

app.get('/users/:id', asyncHandler(async (req, res) => {
  const user = await getUserById(req.params.id);
  res.json(user);
}));
```

Express 5 handles this natively, but many production codebases are still on Express 4. Either way, you should also add a global safety net:

```javascript
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection:', reason);
  // Log to your error tracking service
  // Optionally: process.exit(1) to force a clean restart
});
```

My rule: every `await` should be inside a try/catch, or the calling function should propagate the error. Every `.then()` should have a `.catch()`. No exceptions.

## Stream Backpressure

Streams are one of Node's superpowers, but backpressure is the part nobody explains well. The problem: if you pipe a fast readable stream (like reading from disk) to a slow writable stream (like an HTTP response over a slow connection), the readable will keep pushing data into memory faster than it can be consumed. Eventually, you run out of memory.

I hit this when building a file download endpoint. Under normal conditions it worked fine. Under load with slow clients, the server's memory usage spiked and crashed.

The naive approach:

```javascript
// Dangerous: no backpressure handling
app.get('/download/:fileId', (req, res) => {
  const fileStream = fs.createReadStream(getFilePath(req.params.fileId));

  fileStream.on('data', (chunk) => {
    res.write(chunk); // What if res can't keep up?
  });

  fileStream.on('end', () => res.end());
});
```

The correct approach uses `pipe()`, which handles backpressure automatically by pausing the readable when the writable's buffer is full:

```javascript
// Correct: pipe handles backpressure
app.get('/download/:fileId', (req, res) => {
  const fileStream = fs.createReadStream(getFilePath(req.params.fileId));

  fileStream.pipe(res);

  fileStream.on('error', (err) => {
    console.error('File stream error:', err);
    if (!res.headersSent) {
      res.status(500).json({ error: 'Download failed' });
    }
  });
});
```

Or with the modern `pipeline` function, which also handles cleanup:

```javascript
const { pipeline } = require('stream/promises');

app.get('/download/:fileId', async (req, res) => {
  try {
    const fileStream = fs.createReadStream(getFilePath(req.params.fileId));
    await pipeline(fileStream, res);
  } catch (err) {
    if (!res.headersSent) {
      res.status(500).json({ error: 'Download failed' });
    }
  }
});
```

The lesson: never manually read from a stream and write to another using `data` events unless you're explicitly handling the `drain` event on the writable. Use `pipe()` or `pipeline()` and let Node handle the flow control.

## Timezone Assumptions

This one isn't Node-specific, but Node makes it easy to get wrong because `new Date()` uses the server's local timezone, and you probably don't know what timezone your server is in.

I once shipped a billing feature that calculated subscription renewal dates using `new Date()`. Worked perfectly on my machine (US Eastern time), worked in staging (UTC), broke in production because one of our production servers had been configured with Pacific time by a previous ops team. Renewal dates were three hours off for a subset of users.

The rules I follow now:

```javascript
// ALWAYS store dates in UTC
const createdAt = new Date().toISOString(); // "2024-03-15T14:30:00.000Z"

// NEVER do date math with local time
// Bad:
const tomorrow = new Date();
tomorrow.setDate(tomorrow.getDate() + 1);

// Good: use UTC methods explicitly
const now = new Date();
const tomorrowUTC = new Date(Date.UTC(
  now.getUTCFullYear(),
  now.getUTCMonth(),
  now.getUTCDate() + 1
));

// For display, let the client handle timezone conversion
// or use Intl.DateTimeFormat with an explicit timezone
function formatForUser(isoString, userTimezone) {
  return new Intl.DateTimeFormat('en-US', {
    timeZone: userTimezone,
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(isoString));
}

formatForUser('2024-03-15T14:30:00.000Z', 'America/New_York');
// "Mar 15, 2024, 10:30 AM"
```

Also, set your server's timezone explicitly in your Dockerfile or process manager: `ENV TZ=UTC`. Don't assume it's already UTC. Verify it. I run `console.log(Intl.DateTimeFormat().resolvedOptions().timeZone)` on startup now, just to be safe.

## What I Check Before Every Deploy

After getting burned enough times, I built a mental checklist (and later an actual checklist in our CI pipeline) that I run through before every production deploy.

**Health checks are working.** Not just "the server returns 200" -- the health check should verify that the app can reach its database and any critical external services. A process that's running but can't connect to its database is worse than a process that's down, because the load balancer keeps sending it traffic.

```javascript
app.get('/health', async (req, res) => {
  try {
    await db.query('SELECT 1');
    await redis.ping();
    res.json({ status: 'ok', uptime: process.uptime() });
  } catch (err) {
    res.status(503).json({ status: 'unhealthy', error: err.message });
  }
});
```

**Graceful shutdown is implemented.** When you deploy, the old process needs to finish its in-flight requests before exiting. Without graceful shutdown, users get connection resets mid-request.

```javascript
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down gracefully');
  server.close(() => {
    db.end();
    redis.quit();
    process.exit(0);
  });

  // Force exit after 30 seconds if connections won't close
  setTimeout(() => process.exit(1), 30000);
});
```

**Memory limits are set.** Use `--max-old-space-size` to set a memory ceiling. This way a leak causes an OOM crash and restart rather than consuming all available server memory and affecting other processes.

**Structured logging is in place.** `console.log` is fine for development, but production needs JSON-formatted logs with timestamps, request IDs, and log levels. Use `pino` or `winston`. Your future self debugging a 3 AM incident will thank you.

```javascript
const pino = require('pino');
const logger = pino({ level: 'info' });

logger.info({ userId: user.id, action: 'login' }, 'User logged in');
// {"level":30,"time":1710512345678,"userId":"abc123","action":"login","msg":"User logged in"}
```

Node.js is a fantastic runtime once you understand its constraints. Most of these gotchas boil down to one principle: respect the event loop. Keep it free, handle your errors, manage your memory, and your Node services will be rock solid. Good luck out there.
