---
layout: default
title: "3 Production Bugs I Shipped and What They Taught Me"
categories: webdev career lessons
---

Nobody likes talking about the bugs they shipped to production. We'd all rather share the clever solutions, the clean architectures, the elegant code. But I've learned more from my production bugs than from anything I got right on the first try. These are three real bugs I shipped, the damage they caused, and the lessons that permanently changed how I write code.

If you've never shipped a bug to production, you either haven't been doing this long enough or you're not being honest with yourself. Here are my greatest hits.

## Bug #1: The Timezone That Stole a Day

### What Happened

I was working on an e-commerce app that showed estimated delivery dates at checkout. The logic seemed simple enough: take the current date, add the shipping window, and display "Delivery by [date]" to the user. I wrote the code, tested it, it worked great. Shipped it.

About a week later, customer support started getting complaints from West Coast users. People who ordered at 9 PM Pacific time were seeing delivery estimates that were a day off. Someone ordering on a Tuesday night would see "Delivery by Thursday" when it should have said "Delivery by Friday."

The problem was painfully simple once I found it. The server was running in UTC. When a user in PST placed an order at 9 PM their time, it was already 5 AM the next day in UTC. My code was calculating the delivery date based on the server's date, not the user's date. So the server thought it was Wednesday and calculated delivery from Wednesday, while the user was still sitting in their Tuesday evening.

```javascript
// What I wrote (broken)
const estimatedDelivery = new Date();
estimatedDelivery.setDate(estimatedDelivery.getDate() + shippingDays);

// The server's "today" was already "tomorrow" for PST users
```

The bug had been in production for a week before anyone caught it because most of our test users were on the East Coast, where the UTC offset is only a few hours. The West Coast users, eight hours behind UTC, hit the problem every evening.

### The Fix

The fix had two parts. First, I changed the delivery calculation to always work in UTC and only convert to the user's local timezone for display purposes. Second, I started passing the user's timezone from the client so the server had the context it needed.

```javascript
// What I should have written
const now = new Date();
const userTimezone = req.headers['x-user-timezone'] || 'UTC';

// Calculate in UTC
const estimatedDeliveryUTC = new Date(now.getTime());
estimatedDeliveryUTC.setUTCDate(estimatedDeliveryUTC.getUTCDate() + shippingDays);

// Convert for display using the user's timezone
const displayDate = estimatedDeliveryUTC.toLocaleDateString('en-US', {
  timeZone: userTimezone,
  weekday: 'long',
  month: 'long',
  day: 'numeric',
});
```

We also went back and corrected the delivery estimates for any orders that had been affected and sent apology emails to the customers who got wrong information. It was a small bug in terms of code, but a big one in terms of customer trust.

### The Lesson

Never trust `new Date()` in production without explicitly thinking about timezones. JavaScript's Date object is one of the most deceptively dangerous things in the language. It looks simple, it works fine on your machine, and then it breaks in production because your server, your users, and your database might all be in different timezones.

My rule now: store everything in UTC, compare everything in UTC, and only convert to a local timezone at the last possible moment when you're rendering something for a human to read. And always, always test with timezones that aren't your own.

## Bug #2: The useEffect That Took Down an API

### What Happened

This one still makes me wince. I was building a dashboard component in React that fetched analytics data from our API. Standard stuff: component mounts, calls the API, displays the data. I wrote a `useEffect` to handle the data fetching and moved on to the next task.

What I forgot was the dependency array.

```javascript
// What I wrote
useEffect(() => {
  fetchAnalytics().then(setData);
});

// What I should have written
useEffect(() => {
  fetchAnalytics().then(setData);
}, []);
```

See that missing `[]` at the end? That's the difference between "run this once when the component mounts" and "run this on every single render." Without the dependency array, the effect runs after every render. And since `setData` triggers a re-render, which triggers the effect, which calls the API, which calls `setData`... you can see where this is going.

In development with React's strict mode, this manifested as two API calls instead of one. I noticed it, thought "that's just strict mode doing its double-render thing," and ignored it. In production, without strict mode's double-render but with real data and real users, the component entered an infinite loop. It was firing API requests as fast as the browser could send them. Thousands of requests per second, per user.

Our API monitoring lit up like a Christmas tree. The API started returning 429 (Too Many Requests) errors, which caused the dashboard to show an error state, which triggered a re-render, which triggered another API call. We were basically DDoS-ing ourselves. The API slowed to a crawl for all users, not just the ones on the dashboard.

### The Fix

The immediate fix was adding the dependency array. One pair of brackets.

But we also added protections to make sure this kind of thing couldn't take down the API again. We added rate limiting on the API endpoint so a single client couldn't make more than a few requests per second. We also added a check in the React component to prevent re-fetching if a request was already in flight.

```javascript
useEffect(() => {
  let cancelled = false;

  const loadData = async () => {
    try {
      const result = await fetchAnalytics();
      if (!cancelled) {
        setData(result);
      }
    } catch (err) {
      if (!cancelled) {
        setError(err.message);
      }
    }
  };

  loadData();

  return () => {
    cancelled = true;
  };
}, []);
```

We also turned on the `react-hooks/exhaustive-deps` ESLint rule, which would have caught this immediately, and made it a blocking error in our CI pipeline so no code with a missing dependency array could get merged.

### The Lesson

Linters exist for a reason. I knew the exhaustive-deps rule existed. I'd seen it in blog posts. I just hadn't enabled it because I thought I was careful enough to not need it. I was wrong. Enable every linting rule that catches common mistakes and make them errors, not warnings. Warnings get ignored. Errors get fixed.

The broader lesson is to never dismiss weird behavior in development as "just a dev mode thing." If something is acting differently than you expect, investigate it. My instinct to dismiss the double API call as a strict mode artifact was the moment I could have caught this bug, and I chose to look away.

## Bug #3: The Payment That Said "Success" When It Didn't

### What Happened

This is the one that still keeps me up at night sometimes. I was working on a checkout flow that processed credit card payments through a third-party payment API. The integration was straightforward: send the payment details, get back a success or failure response, update the UI accordingly.

I wrapped the payment call in a try/catch because that's what you do. If something went wrong, I'd catch the error and... well, here's where it went sideways.

```javascript
const processPayment = async (orderDetails) => {
  try {
    const result = await paymentAPI.charge(orderDetails);
    return result;
  } catch (error) {
    console.log('Payment error:', error);
    // TODO: handle this properly
    return { status: 'completed' };
  }
};
```

You see it, right? The catch block logs the error and then returns a success status. I wrote that as a placeholder during development when I was stubbing out the payment flow. The `TODO` comment was supposed to remind me to come back and handle the error properly. I never came back.

When the payment API was up and running, everything worked fine. The try block succeeded, the real result came back, and the order went through normally. But when the payment API had an intermittent connectivity issue one evening, the catch block kicked in. It logged the error to the browser console where nobody was looking, returned a fake success, and the rest of the checkout flow happily processed the order as if it had been paid for.

We shipped orders to customers who hadn't been charged. It took almost two hours before anyone noticed because the orders looked normal in our system. There was no alert, no error state in the UI, nothing. The only trace was a `console.log` that vanished the moment the user closed their browser tab.

### The Fix

The fix was multi-layered because this was a multi-layered failure. First, proper error handling in the payment flow:

```javascript
const processPayment = async (orderDetails) => {
  try {
    const result = await paymentAPI.charge(orderDetails);

    if (result.status !== 'succeeded') {
      throw new PaymentError(
        `Payment not successful: ${result.status}`,
        result
      );
    }

    return result;
  } catch (error) {
    // Log to our monitoring service, not just console
    logger.error('Payment processing failed', {
      orderId: orderDetails.orderId,
      error: error.message,
      stack: error.stack,
    });

    // Propagate the error so the UI can handle it
    throw error;
  }
};
```

Second, the UI got real error states. If payment failed, the user saw a clear message explaining what happened and asking them to try again. No more silent successes.

Third, we added server-side verification. Before marking an order as confirmed, the backend independently verified the payment status with the payment provider. The frontend couldn't just say "trust me, it worked." We also added monitoring alerts that fired whenever a payment error was logged, so the team would know immediately if something was wrong.

### The Lesson

Empty catch blocks and silent failures are the most dangerous bugs you can write, because nobody notices them until it's too late. A crash is loud. An error message is visible. But a function that quietly swallows an error and pretends everything is fine? That can run for days, weeks, or months before anyone realizes something is wrong.

I also learned that `TODO` comments in code are a liability. If something isn't done, it shouldn't be merged. That `TODO` sat in production code for weeks. Nobody reads TODO comments in code review. Nobody goes back to check on them. If the code isn't ready, it shouldn't ship. Period.

And never, ever return fake success from an error handler. If you need a placeholder during development, make it throw an error or return an obvious failure state. Make the unfinished code scream, not whisper.

## What I Do Differently Now

These three bugs fundamentally changed my development habits. Here's what I do now that I didn't do before.

**I write tests for error paths, not just happy paths.** It's easy to test that payment processing works when everything goes right. It's more important to test what happens when the payment API returns an error, times out, or returns an unexpected response. The happy path usually works. The error paths are where bugs hide.

**I use linting rules aggressively.** Every rule that catches a common mistake gets turned on and set to "error." If the team finds a rule annoying, we discuss it. But the default is on. I'd rather fix a linting error than debug a production incident at 2 AM.

**I test in production-like environments.** That means different timezones, slower network connections, flaky third-party APIs. If your staging environment is a perfect, fast, always-available version of the real world, you're not testing anything useful. I specifically test with my machine set to different timezones now. It takes thirty seconds and catches an entire category of bugs.

**I add monitoring and alerting from day one.** Not after the first incident. Not when we "have time." From the start. If a payment fails, someone should know within minutes, not hours. If an API is getting hammered with requests, an alert should fire before users notice. Monitoring isn't a nice-to-have. It's part of the feature.

**I treat TODO comments as tech debt with a deadline.** If I write a TODO, I create a ticket for it immediately. If it's not important enough for a ticket, it's not important enough for a TODO. And if a TODO is blocking production readiness, the code doesn't ship until it's resolved.

Every senior developer I respect has a collection of production bug stories. They're not proud of them, but they'll share them if you ask. These stories are where the real lessons live. Not in tutorials or documentation, but in the moment when you realize your code is broken and real people are affected. That feeling is terrible, and it's the best teacher you'll ever have.
