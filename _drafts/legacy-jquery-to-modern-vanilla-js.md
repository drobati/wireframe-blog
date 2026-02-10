---
layout: default
title: "Legacy jQuery to Modern Vanilla JS"
categories: javascript refactoring frontend
---

I have a confession. Before I was a React developer, before I was even a JavaScript developer, I was a Python test automation engineer. And when I started writing front-end code, jQuery was the first library I reached for. It made the DOM feel approachable. It smoothed over browser inconsistencies. It was everywhere. But here's the thing -- modern JavaScript has caught up. The browser APIs that jQuery was built to paper over have gotten really good, and in many cases, the vanilla equivalent is just as clean. If you're maintaining a codebase that still leans on jQuery, this guide will show you what the modern replacements look like, side by side.

## Why Migrate?

Let's start with the honest question: do you actually need to migrate? jQuery still works. It's stable, well-tested, and it's not going to break. But there are real reasons to move away from it.

**Bundle size.** jQuery minified and gzipped is around 30KB. That might not sound like much, but if you're already loading React or another framework, you're shipping redundant DOM manipulation code. And if you're not using a framework, 30KB for things the browser does natively is hard to justify.

**Performance.** Native DOM methods are faster than jQuery's abstractions. `document.getElementById('app')` is significantly faster than `$('#app')` because jQuery has to parse the selector, create a jQuery object, and wrap the result. For most apps you won't feel the difference, but in tight loops or performance-critical code, it adds up.

**Modern browser support.** jQuery was essential in 2010 because IE6, IE7, and IE8 all had wildly different DOM APIs. That world is gone. Every modern browser -- Chrome, Firefox, Safari, Edge -- implements the same standard APIs. The inconsistencies jQuery was built to handle simply don't exist anymore.

**Developer skills.** When your team learns vanilla JavaScript instead of jQuery's API, those skills transfer everywhere. They work in React, Vue, Svelte, Node.js, Deno, and plain scripts. jQuery knowledge is jQuery-specific.

That said, migration doesn't have to be all-or-nothing. You can replace jQuery patterns incrementally, one file at a time. That's usually the smartest approach.

## DOM Selection & Manipulation

This is where jQuery made its name. The `$()` function was a revelation when `document.getElementById` was the only clean option. But now we have `querySelector` and `querySelectorAll`, which accept any CSS selector and are built into every element and the document itself.

```javascript
// jQuery
const $header = $('.header');
const $items = $('ul.nav > li');
const $first = $('p:first-child');

// Vanilla JS
const header = document.querySelector('.header');
const items = document.querySelectorAll('ul.nav > li');
const first = document.querySelector('p:first-child');
```

One important difference: `querySelectorAll` returns a `NodeList`, not an array. In modern JavaScript, `NodeList` supports `forEach`, but if you need `map`, `filter`, or `reduce`, spread it into an array first.

```javascript
// jQuery - .each() works on jQuery collections
$('.card').each(function(index) {
  $(this).text(`Card ${index + 1}`);
});

// Vanilla JS - forEach on NodeList
document.querySelectorAll('.card').forEach((card, index) => {
  card.textContent = `Card ${index + 1}`;
});

// Need array methods? Spread it
const cardTexts = [...document.querySelectorAll('.card')]
  .map(card => card.textContent)
  .filter(text => text.includes('important'));
```

For DOM manipulation, jQuery's chainable methods like `.addClass()`, `.removeClass()`, `.toggleClass()`, `.attr()`, and `.css()` all have native equivalents through `classList` and direct property access.

```javascript
// jQuery
$('#box')
  .addClass('active')
  .removeClass('hidden')
  .css('color', 'red')
  .attr('data-state', 'open')
  .text('Hello');

// Vanilla JS
const box = document.querySelector('#box');
box.classList.add('active');
box.classList.remove('hidden');
box.style.color = 'red';
box.dataset.state = 'open';
box.textContent = 'Hello';
```

Yes, it's more lines. But each line does exactly one thing, and you can see what's happening without knowing jQuery's API. For creating elements, `createElement` plus property assignment replaces jQuery's HTML string parsing.

```javascript
// jQuery
const $card = $('<div class="card"><h3>Title</h3><p>Content</p></div>');
$('#container').append($card);

// Vanilla JS
const card = document.createElement('div');
card.className = 'card';
card.innerHTML = '<h3>Title</h3><p>Content</p>';
document.querySelector('#container').append(card);

// Or use template literals with insertAdjacentHTML for bulk insertion
document.querySelector('#container').insertAdjacentHTML('beforeend', `
  <div class="card">
    <h3>Title</h3>
    <p>Content</p>
  </div>
`);
```

The `insertAdjacentHTML` method is underrated. It lets you insert HTML at specific positions (`beforebegin`, `afterbegin`, `beforeend`, `afterend`) without destroying existing DOM content. It's one of those native APIs that's actually more flexible than jQuery's `append` and `prepend`.

## Event Handling

jQuery's `.on()` method was great because it gave you event delegation in a clean syntax. The vanilla equivalent, `addEventListener`, is just as capable but requires a slightly different pattern for delegation.

```javascript
// jQuery - direct binding
$('.btn').on('click', function() {
  console.log('clicked', $(this).text());
});

// Vanilla JS - direct binding
document.querySelectorAll('.btn').forEach(btn => {
  btn.addEventListener('click', () => {
    console.log('clicked', btn.textContent);
  });
});
```

For event delegation -- where you listen on a parent and filter by child selector -- jQuery's `.on()` with a selector argument was elegant. Vanilla JS needs a helper or a manual check.

```javascript
// jQuery - delegated event
$('#list').on('click', '.item', function() {
  $(this).toggleClass('selected');
});

// Vanilla JS - delegated event
document.querySelector('#list').addEventListener('click', (e) => {
  const item = e.target.closest('.item');
  if (item) {
    item.classList.toggle('selected');
  }
});
```

The `closest()` method is the key here. It walks up the DOM tree from `e.target` and returns the nearest ancestor (or the element itself) that matches the selector. This handles the case where the user clicks on a child element inside `.item` -- something that a naive `e.target.matches('.item')` check would miss.

For the `$(document).ready()` pattern, you have two clean alternatives:

```javascript
// jQuery
$(document).ready(function() {
  init();
});
// or the shorthand
$(function() {
  init();
});

// Vanilla JS - DOMContentLoaded event
document.addEventListener('DOMContentLoaded', () => {
  init();
});

// Or just put your script at the end of <body>
// Or use the defer attribute on your script tag:
// <script src="app.js" defer></script>
```

In practice, using `<script type="module">` or `<script defer>` is the modern approach. Both automatically defer execution until the DOM is ready, so you don't need a ready handler at all.

## AJAX to Fetch

This is probably the biggest ergonomic improvement. jQuery's `$.ajax()` was powerful but had a callback-heavy API (even with the deferred/promise wrapper). The Fetch API is native, promise-based, and supports `async/await` out of the box.

```javascript
// jQuery
$.ajax({
  url: '/api/users',
  method: 'GET',
  dataType: 'json',
  success: function(data) {
    console.log(data);
  },
  error: function(xhr, status, error) {
    console.error(error);
  }
});

// jQuery shorthand
$.getJSON('/api/users', function(data) {
  console.log(data);
});

// Vanilla JS with fetch
fetch('/api/users')
  .then(response => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  })
  .then(data => console.log(data))
  .catch(error => console.error(error));

// Vanilla JS with async/await (much cleaner)
async function loadUsers() {
  try {
    const response = await fetch('/api/users');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}
```

One gotcha with `fetch` that trips people up: it doesn't reject on HTTP error status codes. A 404 or 500 response still resolves the promise successfully. You have to check `response.ok` yourself. This is different from jQuery's `$.ajax`, which would trigger the error callback on non-2xx responses.

For POST requests with JSON:

```javascript
// jQuery
$.ajax({
  url: '/api/users',
  method: 'POST',
  contentType: 'application/json',
  data: JSON.stringify({ name: 'Derek', role: 'developer' }),
  success: function(data) { console.log(data); }
});

// Vanilla JS
const response = await fetch('/api/users', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ name: 'Derek', role: 'developer' })
});
const data = await response.json();
```

If you find yourself writing a lot of fetch calls with the same headers and error handling, make a small wrapper function. Don't reach for axios or another library -- a 10-line helper is all you need.

```javascript
async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

// Usage
const users = await api('/api/users');
const newUser = await api('/api/users', {
  method: 'POST',
  body: { name: 'Derek' }
});
```

## Animations With CSS

jQuery's `.animate()`, `.fadeIn()`, `.fadeOut()`, and `.slideDown()` were killer features in 2010. Today, CSS handles these cases better -- smoother performance (GPU-accelerated), declarative syntax, and no JavaScript required.

```javascript
// jQuery
$('.modal').fadeIn(300);
$('.modal').fadeOut(300);
$('.panel').slideDown(400);

// Vanilla JS + CSS - use classes and transitions
// CSS
// .modal {
//   opacity: 0;
//   visibility: hidden;
//   transition: opacity 300ms ease, visibility 300ms ease;
// }
// .modal.visible {
//   opacity: 1;
//   visibility: visible;
// }

// JavaScript - just toggle the class
document.querySelector('.modal').classList.add('visible');    // fade in
document.querySelector('.modal').classList.remove('visible'); // fade out
```

For slide animations, CSS `max-height` with overflow hidden does the trick, though it's not as clean as jQuery's `slideDown`:

```css
.panel {
  max-height: 0;
  overflow: hidden;
  transition: max-height 400ms ease;
}
.panel.open {
  max-height: 500px; /* set to a value larger than your content */
}
```

For more complex animations, the Web Animations API gives you programmatic control that's equivalent to jQuery's `.animate()` but with much better performance.

```javascript
// jQuery
$('#box').animate({
  left: '200px',
  opacity: 0.5
}, 1000, 'swing');

// Web Animations API
document.querySelector('#box').animate([
  { transform: 'translateX(0)', opacity: 1 },
  { transform: 'translateX(200px)', opacity: 0.5 }
], {
  duration: 1000,
  easing: 'ease-in-out',
  fill: 'forwards'
});
```

The Web Animations API returns an `Animation` object that you can `pause()`, `reverse()`, `cancel()`, and `finish()`. It also supports promises through the `finished` property, so you can `await` an animation completing before running the next step. jQuery couldn't do that without callbacks.

My general rule: if the animation is a simple state change (show/hide, expand/collapse, hover effect), use CSS transitions. If it's a complex, multi-step, or programmatically controlled animation, use the Web Animations API.

## Utility Methods You Don't Need Anymore

jQuery came with a bunch of utility methods that filled real gaps in JavaScript circa 2010. Those gaps are closed now.

```javascript
// $.each - iterating arrays and objects
$.each(items, function(index, item) {
  console.log(index, item);
});
// Now:
items.forEach((item, index) => console.log(index, item));
// For objects:
Object.entries(obj).forEach(([key, value]) => console.log(key, value));

// $.extend - merging objects
const merged = $.extend({}, defaults, userOptions);
// Now:
const merged = { ...defaults, ...userOptions };
// or for deep merge:
const merged = structuredClone({ ...defaults, ...userOptions });

// $.map - transforming arrays
const names = $.map(users, function(user) {
  return user.name;
});
// Now:
const names = users.map(user => user.name);

// $.grep - filtering arrays
const active = $.grep(users, function(user) {
  return user.isActive;
});
// Now:
const active = users.filter(user => user.isActive);

// $.inArray - finding index
const index = $.inArray('hello', myArray);
// Now:
const index = myArray.indexOf('hello');
// Or just check existence:
const exists = myArray.includes('hello');

// $.trim
const clean = $.trim('  hello  ');
// Now:
const clean = '  hello  '.trim();

// $.isArray
$.isArray(thing);
// Now:
Array.isArray(thing);

// $.parseJSON
const obj = $.parseJSON(jsonString);
// Now:
const obj = JSON.parse(jsonString);
```

The pattern is clear. Modern JavaScript has native methods for everything jQuery's utilities provided. `Array.from()`, `Object.assign()`, `Object.keys()`, `Object.values()`, `Object.entries()`, `Array.prototype.find()`, `Array.prototype.includes()`, the spread operator, destructuring, template literals -- the language itself has become expressive enough that you don't need a utility library for basic operations.

For anything more specialized, consider small focused libraries rather than jQuery's kitchen-sink approach. Need deep cloning? Use `structuredClone()`. Need debouncing? It's a five-line function. Need unique IDs? `crypto.randomUUID()`.

## When jQuery Still Makes Sense

I promised honesty, so here it is. There are situations where jQuery is still a reasonable choice.

**Legacy codebases where a full rewrite isn't feasible.** If you have 50,000 lines of jQuery code that works, rewriting it all to vanilla JS is a bad use of time. Migrate incrementally. When you touch a file for a bug fix or feature, modernize that file. Over time, the jQuery footprint shrinks organically.

**Quick prototypes and throwaway scripts.** If you're building a one-off internal tool and the team knows jQuery, there's no shame in using it. Speed of delivery matters, and familiarity reduces bugs.

**Environments where you can't control the JavaScript version.** Some CMS platforms, WordPress themes, and enterprise environments already load jQuery on every page. If it's there anyway, the bundle size argument disappears, and you might as well use it.

**Complex event delegation across deeply nested, dynamically generated DOM.** jQuery's `.on()` with delegation is still more ergonomic than vanilla event delegation for complex cases. The `closest()` pattern works, but if you're delegating many different events across many selectors, jQuery's syntax is hard to beat.

What I'd push back on is using jQuery for new greenfield projects. If you're starting fresh, learn the native APIs. They're well-documented, well-supported, and they'll serve you in any context -- not just jQuery-compatible environments.

The best migration strategy is gradual. Pick a file, replace the jQuery patterns with vanilla equivalents, test it, ship it. Over a few sprints, you'll find that most of your jQuery usage falls into a handful of patterns that are easy to replace. And every line of jQuery you remove is one less abstraction between you and the platform.

You've got this. The browser is a lot more capable than it was when jQuery was essential.
