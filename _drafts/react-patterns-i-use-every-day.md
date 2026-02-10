---
layout: default
title: "React Patterns I Use Every Day at Work"
categories: react javascript frontend
---

Every codebase I've worked on has a handful of patterns that show up over and over. Not the flashy stuff from conference talks -- the boring, reliable patterns that keep your components maintainable when the feature requests start piling up. These are the ones I reach for daily.

## Compound Components

If you've ever built a component that needs flexible composition -- tabs, accordions, dropdown menus -- compound components are your best friend. The idea is simple: instead of cramming everything into one mega-component with a dozen props, you break it into related pieces that share implicit state.

Here's a Tabs component I've built variations of at least three times across different projects:

```jsx
const TabsContext = React.createContext(null);

function Tabs({ children, defaultIndex = 0 }) {
  const [activeIndex, setActiveIndex] = React.useState(defaultIndex);

  return (
    <TabsContext.Provider value={{ activeIndex, setActiveIndex }}>
      <div className="tabs">{children}</div>
    </TabsContext.Provider>
  );
}

function TabList({ children }) {
  return <div className="tab-list" role="tablist">{children}</div>;
}

function Tab({ index, children }) {
  const { activeIndex, setActiveIndex } = React.useContext(TabsContext);

  return (
    <button
      role="tab"
      aria-selected={activeIndex === index}
      className={`tab ${activeIndex === index ? 'tab--active' : ''}`}
      onClick={() => setActiveIndex(index)}
    >
      {children}
    </button>
  );
}

function TabPanel({ index, children }) {
  const { activeIndex } = React.useContext(TabsContext);

  if (activeIndex !== index) return null;
  return <div role="tabpanel" className="tab-panel">{children}</div>;
}
```

The consumer gets a clean, readable API:

```jsx
<Tabs defaultIndex={0}>
  <TabList>
    <Tab index={0}>Overview</Tab>
    <Tab index={1}>Settings</Tab>
    <Tab index={2}>Billing</Tab>
  </TabList>
  <TabPanel index={0}><Overview /></TabPanel>
  <TabPanel index={1}><Settings /></TabPanel>
  <TabPanel index={2}><Billing /></TabPanel>
</Tabs>
```

The beauty is that the parent doesn't need to know which tab is active, and you can rearrange the panels without touching any state logic. I've seen teams try to build this with a single `<Tabs items={[...]} />` prop-based API, and it always gets painful once you need custom rendering inside a panel.

## Custom Hooks for Business Logic

Coming from Python test automation, I was used to pulling reusable logic into utility functions. Custom hooks are the React equivalent, but better -- they can tap into the component lifecycle.

The two hooks I write most often are `useApi` for data fetching and `useForm` for form state. Here's a simplified `useApi`:

```javascript
function useApi(fetchFn) {
  const [data, setData] = React.useState(null);
  const [error, setError] = React.useState(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        const result = await fetchFn();
        if (!cancelled) setData(result);
      } catch (err) {
        if (!cancelled) setError(err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [fetchFn]);

  return { data, error, loading };
}
```

And a `useForm` that handles validation:

```javascript
function useForm(initialValues, validate) {
  const [values, setValues] = React.useState(initialValues);
  const [errors, setErrors] = React.useState({});
  const [touched, setTouched] = React.useState({});

  const handleChange = (field) => (e) => {
    setValues((prev) => ({ ...prev, [field]: e.target.value }));
  };

  const handleBlur = (field) => () => {
    setTouched((prev) => ({ ...prev, [field]: true }));
    if (validate) setErrors(validate(values));
  };

  const handleSubmit = (onSubmit) => (e) => {
    e.preventDefault();
    const validationErrors = validate ? validate(values) : {};
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length === 0) onSubmit(values);
  };

  return { values, errors, touched, handleChange, handleBlur, handleSubmit };
}
```

The key thing is that the hook owns the lifecycle. That `cancelled` flag in `useApi` prevents setting state on an unmounted component. You could write that logic inline in every component, but you'd forget the cancellation flag eventually. I know because I did, many times.

## Controlled vs Uncontrolled

This one sounds basic, but I still see teams get it wrong. The rule I follow: use controlled inputs when you need to react to every change, use uncontrolled when you just need the final value on submit.

A search input that filters a list in real-time? Controlled:

```jsx
function SearchableList({ items }) {
  const [query, setQuery] = React.useState('');

  const filtered = items.filter((item) =>
    item.name.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search..."
      />
      <ul>
        {filtered.map((item) => (
          <li key={item.id}>{item.name}</li>
        ))}
      </ul>
    </div>
  );
}
```

A simple contact form where you collect the values on submit? Uncontrolled with a ref or just `FormData`:

```jsx
function ContactForm({ onSubmit }) {
  const handleSubmit = (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    onSubmit({
      name: formData.get('name'),
      email: formData.get('email'),
      message: formData.get('message'),
    });
  };

  return (
    <form onSubmit={handleSubmit}>
      <input name="name" defaultValue="" />
      <input name="email" type="email" defaultValue="" />
      <textarea name="message" defaultValue="" />
      <button type="submit">Send</button>
    </form>
  );
}
```

The uncontrolled version has zero re-renders while the user types. For a simple form, that's a win. For the search input, you need every keystroke. Match the pattern to the use case.

## Render Props vs Hooks

I'll be honest -- render props are mostly dead. Hooks replaced them for 90% of use cases, and the code reads better. But there are a couple of spots where render props still make sense: when you need to share behavior that involves rendering decisions, not just data.

A resize observer is a good example. You want a component that tracks its own size and lets the consumer decide what to render based on those dimensions:

```jsx
function ResizeObserverBox({ children }) {
  const ref = React.useRef(null);
  const [size, setSize] = React.useState({ width: 0, height: 0 });

  React.useEffect(() => {
    const observer = new ResizeObserver(([entry]) => {
      setSize({
        width: entry.contentRect.width,
        height: entry.contentRect.height,
      });
    });

    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return <div ref={ref}>{children(size)}</div>;
}

// Usage
<ResizeObserverBox>
  {({ width }) => (
    width > 600 ? <WideLayout /> : <NarrowLayout />
  )}
</ResizeObserverBox>
```

The reason this works better than a hook here is that the `div` wrapper and the `ref` are part of the abstraction. A `useResizeObserver` hook would need the consumer to create and attach the ref themselves. Both approaches are valid -- I just find the render prop version more self-contained for this specific case.

That said, for data fetching, auth checks, and most business logic, hooks are the clear winner. Don't use render props just because you saw them in an older codebase.

## Error Boundaries in Practice

Error boundaries are one of those things every team says they'll add and then never does until something breaks in production. I've learned to add them early. Here's the class component you need (yes, it still has to be a class -- React hasn't added a hook equivalent):

```jsx
class ErrorBoundary extends React.Component {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Send to your error tracking service
    reportError(error, errorInfo.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback ? (
        this.props.fallback(this.state.error)
      ) : (
        <div className="error-fallback">
          <h2>Something went wrong</h2>
          <button onClick={() => this.setState({ hasError: false, error: null })}>
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
```

I wrap error boundaries at two levels: one around the entire app (catch everything), and one around each major feature area (so a crash in the settings panel doesn't take down the dashboard):

```jsx
<ErrorBoundary fallback={(err) => <AppCrashScreen error={err} />}>
  <Layout>
    <ErrorBoundary fallback={() => <p>Failed to load dashboard.</p>}>
      <Dashboard />
    </ErrorBoundary>
    <ErrorBoundary fallback={() => <p>Failed to load sidebar.</p>}>
      <Sidebar />
    </ErrorBoundary>
  </Layout>
</ErrorBoundary>
```

The `componentDidCatch` hook is where you plug in Sentry, Datadog, or whatever you're using. The important thing is that the user sees a recovery option instead of a blank screen.

## The Patterns I Stopped Using

Knowing what to stop doing is just as valuable as knowing what to start. Here's what I've moved away from:

**Higher-Order Components (HOCs).** I used to write `withAuth`, `withTheme`, `withLogging` wrappers everywhere. The problem is they create wrapper hell in React DevTools, make props opaque, and are hard to type correctly in TypeScript. Custom hooks do the same job with less indirection. `useAuth()` is clearer than `withAuth(MyComponent)`.

**Prop drilling through five levels.** Early in my React career, I'd pass callbacks and state down through three, four, five layers of components. Now I reach for Context when data needs to skip more than one or two levels. Not for everything -- just for cross-cutting concerns like the current user, theme, or feature flags.

**Redux for everything.** I've been on teams where every piece of state lived in Redux, including form inputs and modal open/close toggles. That's way too much ceremony. My approach now: start with `useState`. If state needs to be shared between siblings, lift it up. If it needs to cross several component boundaries, use Context. Only reach for Zustand or Redux when you have genuinely complex global state with lots of derived data.

These patterns weren't wrong when they were popular -- they solved real problems. But React has evolved, and simpler tools are available now. Don't cargo-cult patterns from 2018 tutorials.

Every codebase is different, and you'll develop your own set of go-to patterns over time. The important thing is to keep them simple, keep them consistent across your team, and be willing to drop a pattern when something better comes along. Happy coding.
