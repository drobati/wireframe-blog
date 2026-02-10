---
layout: default
title: "I Replaced React With Web Components for 30 Days"
categories: webcomponents react javascript
---

Look, I write React professionally. It pays my bills. But after building this blog with Wired Elements -- a web component library that gives everything that hand-drawn, sketchy look you see here -- I started wondering: how far can web components actually take you? So I gave myself a challenge. Thirty days. One side project. No React. Just the web platform and custom elements. Here's what happened.

## The Experiment

The rules were simple. I'd build a recipe manager app -- something with CRUD operations, search, filtering, and a responsive layout. Complex enough to hit real problems, but not so complex that I'd need a team. No React, no Vue, no Svelte. Just web components, vanilla JavaScript, and whatever lightweight libraries I needed along the way.

I gave myself one escape hatch: I could use a templating helper like `lit-html` if raw `innerHTML` got too painful. But no full frameworks. The goal was to understand what the platform gives you for free and where the gaps are.

My setup was dead simple. An `index.html`, a `components/` folder, and a dev server. That's it. No webpack, no Babel, no `node_modules` black hole. I won't lie -- that alone felt liberating.

```html
<!-- index.html - the entire build system -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Recipe Manager</title>
  <script type="module" src="./components/app-shell.js"></script>
</head>
<body>
  <app-shell></app-shell>
</body>
</html>
```

No build step. No transpilation. Just files and a browser. I was already smiling.

## Week 1: The Honeymoon

The first few days were genuinely exciting. Creating a custom element felt clean and straightforward. You extend `HTMLElement`, define your shadow DOM, and register it. That's the whole API.

```javascript
class RecipeCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    const title = this.getAttribute('title') || 'Untitled';
    const time = this.getAttribute('cook-time') || 'N/A';

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          border: 1px solid #ddd;
          border-radius: 8px;
          padding: 16px;
          cursor: pointer;
        }
        :host(:hover) {
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        h3 { margin: 0 0 8px 0; }
        .meta { color: #666; font-size: 0.9em; }
      </style>
      <h3>${title}</h3>
      <p class="meta">Cook time: ${time}</p>
      <slot></slot>
    `;
  }
}

customElements.define('recipe-card', RecipeCard);
```

Shadow DOM encapsulation was a revelation. Coming from React where CSS-in-JS or CSS Modules are entire conversations, having style isolation built into the platform felt like cheating. My component's styles couldn't leak out, and nothing from the outside could accidentally break them.

Slots were another highlight. Instead of React's `children` prop, you get `<slot>` elements that pull in light DOM content. It took a mental shift, but once it clicked, the composition model felt natural. I could nest components, project content, and build layouts without prop-drilling.

By the end of week one, I had a working card grid, a search bar component, and a basic app shell. All without a single `npm install`. The browser's dev tools showed me my component tree, and I could inspect shadow roots directly. No React DevTools extension needed.

## Week 2: The Friction

This is where reality showed up. My recipe manager needed state -- a list of recipes that could be filtered, sorted, and edited. In React, I'd reach for `useState` and `useContext` and be done in ten minutes. With web components, there's no built-in state management. At all.

I tried the simplest thing first: custom events bubbling up and a top-level component dispatching back down through attributes. It worked for a while, but it got messy fast.

```javascript
// Child dispatches an event
this.dispatchEvent(new CustomEvent('recipe-deleted', {
  bubbles: true,
  composed: true, // crosses shadow DOM boundaries
  detail: { id: this.recipeId }
}));

// Parent listens
this.addEventListener('recipe-deleted', (e) => {
  this.recipes = this.recipes.filter(r => r.id !== e.detail.id);
  this.render(); // manually re-render everything
});
```

That `this.render()` call is the problem. There's no reactive system. When state changes, you're responsible for figuring out what needs to update. I found myself writing a lot of imperative DOM manipulation code -- the exact stuff React was invented to eliminate.

The attribute vs. property distinction also bit me. HTML attributes are always strings, so passing complex data through attributes means serializing and deserializing JSON. Properties work fine for JavaScript access, but they don't show up in HTML and they aren't reflected in `attributeChangedCallback`. I spent an entire afternoon debugging why my recipe objects were showing up as `[object Object]`.

```javascript
// Attributes are strings - this doesn't work how you'd think
<recipe-card data='{"title": "Pasta"}'>  // works but feels wrong

// Properties are better for complex data
const card = document.querySelector('recipe-card');
card.recipe = { title: 'Pasta', ingredients: [...] };  // clean, but imperative
```

Component composition was also harder than expected. React's JSX makes it trivial to map over an array and render child components. With vanilla web components, you're back to `document.createElement` in a loop, or building HTML strings manually. Neither feels great.

## Week 3: Finding My Groove

By week three, I'd accepted that I needed some help. Not a framework -- just a smarter rendering approach. Enter `lit-html`, a tiny templating library from the Google team behind Polymer. It gives you tagged template literals with efficient DOM updates, without the overhead of a full framework.

```javascript
import { html, render } from 'lit-html';
import { repeat } from 'lit-html/directives/repeat.js';

class RecipeList extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._recipes = [];
  }

  set recipes(value) {
    this._recipes = value;
    this.update();
  }

  update() {
    const template = html`
      <style>
        :host { display: block; }
        .grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: 16px;
        }
      </style>
      <div class="grid">
        ${repeat(this._recipes, r => r.id, r => html`
          <recipe-card
            title="${r.title}"
            cook-time="${r.cookTime}"
            @recipe-deleted="${() => this.handleDelete(r.id)}">
            <p>${r.description}</p>
          </recipe-card>
        `)}
      </div>
    `;
    render(template, this.shadowRoot);
  }

  handleDelete(id) {
    this.dispatchEvent(new CustomEvent('delete', {
      bubbles: true, composed: true, detail: { id }
    }));
  }
}

customElements.define('recipe-list', RecipeList);
```

This changed everything. I had efficient re-rendering, declarative templates, and event binding -- all in about 7KB of library code. I started building a small component library: `recipe-card`, `recipe-list`, `recipe-form`, `search-bar`, `tag-filter`. Each one was a self-contained file with its own styles and behavior.

I also built a simple event bus for cross-component communication. It wasn't Redux, but it was enough. A plain `EventTarget` subclass that any component could import and subscribe to.

```javascript
// event-bus.js
class EventBus extends EventTarget {
  emit(event, detail) {
    this.dispatchEvent(new CustomEvent(event, { detail }));
  }

  on(event, callback) {
    this.addEventListener(event, callback);
    return () => this.removeEventListener(event, callback);
  }
}

export const bus = new EventBus();
```

By the end of week three, I had a functional recipe manager with add, edit, delete, search, and tag filtering. The total JavaScript payload was under 30KB. No build artifacts, no source maps, no chunking strategy. Just files the browser could run.

## Week 4: The Verdict

The last week was about polish and reflection. I added some transitions, cleaned up the component APIs, and wrote a few tests using Web Test Runner. Then I sat down and thought honestly about the experience.

What surprised me most was how much the platform gives you. Custom elements, shadow DOM, slots, CSS containment, native lazy loading, `<template>` elements, ES modules -- these aren't experimental features anymore. They're stable, performant, and supported everywhere that matters.

But I also missed React. Specifically, I missed the developer experience. JSX is more ergonomic than template literals. React's component model -- where you just return UI based on props and state -- is genuinely elegant. The ecosystem of hooks, dev tools, and community solutions saves you from reinventing wheels.

The performance was interesting. My web component app loaded faster because there was less JavaScript to parse. But complex interactions -- like filtering a list while debouncing search input -- required more manual optimization than React's virtual DOM diffing would. It's a tradeoff.

Here's my honest scorecard after 30 days:

- **Developer experience**: React wins. JSX, hooks, and the ecosystem are hard to beat.
- **Performance (initial load)**: Web components win. Less JavaScript, no framework overhead.
- **Encapsulation**: Web components win. Shadow DOM is real isolation, not convention.
- **State management**: React wins. Built-in hooks plus the Context API cover most cases.
- **Portability**: Web components win. They work in any framework or no framework.
- **Learning curve**: Web components are simpler to start, but the lack of conventions means you hit walls faster.

## When to Use Which

After this experiment, I have a clear mental model for when to reach for each.

**Use web components when** you're building a design system or component library that needs to work across frameworks. This is their superpower. A `<date-picker>` web component works in React, Angular, Vue, and plain HTML. You write it once and it works everywhere. That's not something any framework can claim.

Web components also shine for embeddable widgets -- anything you'd drop into a CMS, a third-party site, or a micro-frontend architecture. The encapsulation of shadow DOM means your widget won't break the host page's styles, and the host page won't break yours.

**Use React when** you're building a complex, stateful application with a team. React's opinions about data flow, its dev tools, its testing ecosystem, and its hiring pool all matter in that context. Server-side rendering, concurrent features, and the Next.js/Remix ecosystem give you capabilities that web components simply don't address.

```javascript
// The sweet spot: web components consumed by React
import './components/wired-card.js';  // register the custom element

function RecipePage({ recipe }) {
  return (
    <wired-card elevation={2}>
      <h2>{recipe.title}</h2>
      <p>{recipe.description}</p>
    </wired-card>
  );
}
```

This is actually what I do on this blog. Wired Elements are web components, and if I ever swapped the blog engine or added a React-based feature, those components would still work. That's the promise of the web platform, and it delivers.

My takeaway? Web components aren't a React replacement. They're a React complement. Learn both, and you'll know which tool fits the job. And if nothing else, spending a month with just the platform will make you a better developer regardless of which framework you use day to day.

Give it a try. Even a week will teach you something.
