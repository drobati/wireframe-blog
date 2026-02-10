---
layout: default
title: "How We Structure Our React Codebase at Scale"
categories: react architecture frontend
---

When your React app is five components, folder structure doesn't matter. When it's two hundred components with a team of eight developers, it's the difference between shipping features and playing hide-and-seek with files. This is how we organize our codebase at work, what's worked, and what we'd change if we started over.

## Our Folder Structure

Here's the top-level layout we've settled on after a couple of painful reorganizations:

```
src/
  features/
    auth/
    dashboard/
    invoices/
    settings/
  shared/
    components/
    hooks/
    utils/
  lib/
    api-client.js
    analytics.js
    storage.js
  styles/
    global.css
    variables.css
  App.jsx
  main.jsx
```

The big idea is separation of concerns at the directory level. `features/` holds everything specific to a product area. `shared/` is for truly reusable pieces that cross feature boundaries. `lib/` is for low-level utilities that don't depend on React at all -- your API client, analytics wrapper, local storage abstraction.

We tried having a flat `components/` folder at the top level. It worked for a while, then it had 80 files in it and nobody could find anything. The move to feature-based organization was the best refactor we ever did.

One thing I want to call out: the `lib/` directory is deliberately separate from `shared/`. The distinction is that `shared/` contains React-specific code (components, hooks) while `lib/` contains plain JavaScript that could work in any environment. That boundary has saved us a few times when we needed to share logic with a Node.js backend service.

## Feature-Based Organization

Each feature directory is a self-contained unit with its own components, hooks, utilities, and API calls:

```
src/features/invoices/
  components/
    InvoiceTable.jsx
    InvoiceRow.jsx
    InvoiceFilters.jsx
    CreateInvoiceModal.jsx
  hooks/
    useInvoices.js
    useInvoiceFilters.js
  utils/
    format-currency.js
    calculate-totals.js
  api/
    invoices-api.js
  index.js
```

The `index.js` at the feature root is the public API. It exports only what other features are allowed to import. This is a soft boundary -- JavaScript won't enforce it -- but it's a convention the team respects:

```javascript
// src/features/invoices/index.js
export { InvoiceTable } from './components/InvoiceTable';
export { useInvoices } from './hooks/useInvoices';
```

If a developer on the dashboard team needs to show a list of recent invoices, they import from `features/invoices`, not from `features/invoices/components/InvoiceTable`. This gives the invoices team freedom to refactor internals without breaking other features.

The biggest win of feature-based organization is onboarding. When a new developer picks up a ticket for the invoices feature, they open one folder and everything they need is right there. No jumping between a top-level `components/` directory, a separate `hooks/` directory, and a `utils/` directory trying to piece together which files belong to which feature.

## Shared Components vs Feature Components

Drawing the line between shared and feature-specific components is an art, not a science. Our rule of thumb: a component starts in a feature directory. If a second feature needs it, we have a conversation about whether to move it to `shared/`.

Shared components are generic building blocks with no business logic:

```jsx
// src/shared/components/Button.jsx
function Button({ variant = 'primary', size = 'md', children, ...props }) {
  return (
    <button
      className={`btn btn--${variant} btn--${size}`}
      {...props}
    >
      {children}
    </button>
  );
}

// src/shared/components/Modal.jsx
function Modal({ isOpen, onClose, title, children }) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{title}</h2>
          <button onClick={onClose} aria-label="Close">&times;</button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}
```

Feature components know about the domain. An `InvoiceTable` knows what an invoice looks like, how to format currency, which columns to show. It doesn't belong in `shared/` because it's useless outside the invoicing context.

The mistake I see most often is premature abstraction -- someone builds a "generic" `DataTable` in `shared/` that takes column configs, custom renderers, sort handlers, filter callbacks, and ends up with 30 props. Just build the specific table you need. If you later need a second table with similar behavior, then extract the common pieces.

## State Management Approach

We don't have a single global store. State lives as close to where it's used as possible, and we escalate only when necessary.

The hierarchy looks like this:

1. **useState / useReducer** -- Component-local state. Form inputs, toggles, loading flags.
2. **Lift state up** -- When siblings need to share state, move it to the nearest common parent.
3. **React Context** -- For cross-cutting concerns that many components need: current user, theme, feature flags, toast notifications.
4. **Zustand** -- For genuinely complex global state that multiple features read and write. We have one Zustand store for real-time notification state because it involves websocket connections and background updates.

```javascript
// Context for cross-cutting concerns
const AuthContext = React.createContext(null);

function AuthProvider({ children }) {
  const [user, setUser] = React.useState(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    checkSession().then(setUser).finally(() => setLoading(false));
  }, []);

  const login = async (credentials) => {
    const user = await loginApi(credentials);
    setUser(user);
  };

  const logout = async () => {
    await logoutApi();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

function useAuth() {
  const context = React.useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
```

The biggest lesson: resist the urge to put everything in global state. I've worked on a codebase where even the "is this dropdown open" state lived in Redux. Every dropdown toggle dispatched an action, went through a reducer, and updated the store. It was absurd. Local state is not a code smell -- it's the correct default.

## Naming Conventions

Consistency beats cleverness. Here's what we enforce:

- **Components**: PascalCase, one component per file, filename matches the component name. `InvoiceTable.jsx` exports `InvoiceTable`.
- **Hooks**: camelCase with the `use` prefix. `useInvoices.js` exports `useInvoices`.
- **Utilities**: camelCase functions in kebab-case files. `format-currency.js` exports `formatCurrency`.
- **Constants**: UPPER_SNAKE_CASE in a `constants.js` file per feature.
- **Types (if using TypeScript)**: PascalCase, colocated with the code that uses them or in a `types.ts` file per feature.

```
// Good
InvoiceTable.jsx      -> export function InvoiceTable
useInvoices.js        -> export function useInvoices
format-currency.js    -> export function formatCurrency
constants.js          -> export const MAX_INVOICE_AMOUNT = 999999

// Bad
invoiceTable.jsx      // component file should be PascalCase
UseInvoices.js        // hook file shouldn't start with uppercase
formatCurrency.js     // utility files use kebab-case
```

We also have a convention that test files sit next to their source files with a `.test.js` suffix. `InvoiceTable.test.jsx` lives right next to `InvoiceTable.jsx`. This makes it obvious when a file is missing tests and keeps the mental link between code and tests tight.

One more: we prefix internal-only components with an underscore in the filename. `_InvoiceRowActions.jsx` signals "this component is an implementation detail of this feature, don't import it from outside." It's not bulletproof, but it communicates intent.

## What We'd Do Differently

No codebase is perfect, and ours has some decisions I'd reverse if we started fresh.

**Barrel files were a mistake.** We have `index.js` files in every directory that re-export everything. The idea was clean imports: `import { Button } from 'shared/components'` instead of `import { Button } from 'shared/components/Button'`. In practice, barrel files cause circular dependency headaches, make tree-shaking harder for the bundler, and slow down your IDE's auto-import. If I started over, I'd import directly from the file every time.

**We should have adopted TypeScript strict mode from day one.** We started with TypeScript in "loose" mode with `strict: false` because the team was new to it. Converting to strict mode later was a multi-week project. Those early `any` types propagated everywhere. Start strict and stay strict -- it's easier to relax a rule than to tighten one.

**More colocation, less separation.** We split CSS into a top-level `styles/` directory early on. We should have colocated styles with their components from the start, whether that's CSS modules, Tailwind, or styled-components. The same applies to test fixtures and mock data -- keep them next to the code they support.

**We should have documented our conventions earlier.** For the first year, conventions lived in people's heads and code review comments. New developers had to absorb the patterns by osmosis. A simple `CONVENTIONS.md` in the repo root would have saved hours of back-and-forth in pull requests.

The best folder structure is the one your whole team understands and follows. Ours isn't perfect, but it's consistent, and that consistency is what lets us move fast. If you're setting up a new project, steal whatever parts of this work for your team and throw away the rest. The important thing is to pick a structure early and commit to it.
