---
layout: default
title: "From 4s to 400ms: How I Optimized a Node API"
categories: node performance backend
---

A few months back I was staring at our dashboard endpoint in the network tab, watching the spinner go round for over four seconds. Four seconds to load a page that should feel instant. The data wasn't even that complicated -- a list of orders with some customer info and aggregated totals. But somewhere between the database and the browser, something had gone very wrong. Here's how I tracked down the bottlenecks and brought that response time down to 400ms.

## The Problem

The endpoint in question was `/api/dashboard`, and it powered the main screen our operations team lived in all day. It returned a list of recent orders, each with customer details, line items, and some calculated metrics like average order value and fulfillment rate.

The payload wasn't huge -- maybe 50 orders at a time. But the endpoint had grown organically over six months. Different developers had added fields, joined extra data, and layered on transformations. Nobody had measured the performance because it had always been "fast enough." Then the dataset grew past 10,000 orders and suddenly it wasn't.

The response time varied between 3.5 and 4.5 seconds. On a cold start or when the database was under load, it would occasionally hit 6 seconds and trigger our timeout alert. Our frontend team had already added a skeleton loader as a band-aid, but that was treating the symptom, not the disease.

Before I touched anything, I set up a baseline. I added a simple timer to the endpoint and logged it for a week:

```javascript
app.get('/api/dashboard', async (req, res) => {
  const start = performance.now();

  try {
    const data = await getDashboardData(req.query);
    const duration = performance.now() - start;
    console.log(`[dashboard] ${duration.toFixed(0)}ms`);
    res.json(data);
  } catch (error) {
    console.error('[dashboard] error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});
```

Average over the week: **4,100ms**. That was my number to beat.

## Profiling & Measuring

You can't optimize what you can't measure, and guessing at performance bottlenecks is almost always wrong. I've been burned too many times thinking "it's probably the database" only to find out it was something totally different. So I brought out the profiling tools.

**clinic.js** is the first thing I reach for. It's a suite of tools from the Node.js team that profiles your application and generates visual reports:

```bash
npm install -g clinic

# Generates a flame chart of where time is spent
clinic flame -- node server.js

# While that's running, hit the endpoint a few times
curl http://localhost:3000/api/dashboard

# Ctrl+C to stop, and clinic opens a browser with the report
```

The flame chart showed me immediately that the vast majority of time was spent in database calls -- not in my JavaScript logic, not in JSON serialization, but waiting on Postgres. Good. That narrowed the search.

For more granular timing within the endpoint itself, I used `console.time` to instrument the key sections:

```javascript
async function getDashboardData(query) {
  console.time('dashboard:total');

  console.time('dashboard:fetch-orders');
  const orders = await fetchOrders(query);
  console.timeEnd('dashboard:fetch-orders');

  console.time('dashboard:fetch-customers');
  const enriched = await enrichWithCustomerData(orders);
  console.timeEnd('dashboard:fetch-customers');

  console.time('dashboard:transform');
  const result = transformForResponse(enriched);
  console.timeEnd('dashboard:transform');

  console.timeEnd('dashboard:total');
  return result;
}
```

The output told the whole story:

```
dashboard:fetch-orders: 380ms
dashboard:fetch-customers: 2,800ms
dashboard:transform: 900ms
dashboard:total: 4,100ms
```

Three clear bottlenecks, each contributing significantly. Time to tackle them one by one, starting with the biggest.

## Bottleneck #1: N+1 Queries

The 2,800ms in `enrichWithCustomerData` was the worst offender, and when I looked at the code, I immediately saw why. It was a classic N+1 query -- fetching a list of orders, then looping through each one to fetch the customer individually:

```javascript
// The original code -- DON'T DO THIS
async function enrichWithCustomerData(orders) {
  const enriched = [];

  for (const order of orders) {
    const customer = await db.query(
      'SELECT * FROM customers WHERE id = $1',
      [order.customer_id]
    );
    enriched.push({
      ...order,
      customer: customer.rows[0]
    });
  }

  return enriched;
}
```

With 50 orders, that's 50 individual round trips to the database. Each one takes 40-60ms on its own (not bad for a single query), but fifty of them in sequence adds up to nearly three seconds.

The fix is to batch the query. Fetch all the customers you need in one shot:

```javascript
// The fix -- one query instead of fifty
async function enrichWithCustomerData(orders) {
  const customerIds = [...new Set(orders.map(o => o.customer_id))];

  const customers = await db.query(
    'SELECT * FROM customers WHERE id = ANY($1)',
    [customerIds]
  );

  const customerMap = new Map(
    customers.rows.map(c => [c.id, c])
  );

  return orders.map(order => ({
    ...order,
    customer: customerMap.get(order.customer_id)
  }));
}
```

One query instead of fifty. The `ANY($1)` syntax in Postgres takes an array of IDs, and the `Map` gives us O(1) lookups when joining the data back together. This single change dropped `fetch-customers` from 2,800ms to **45ms**.

Even better, I could have eliminated the second query entirely by using a JOIN in the original orders query:

```javascript
const orders = await db.query(`
  SELECT o.*,
    json_build_object(
      'id', c.id,
      'name', c.name,
      'email', c.email
    ) as customer
  FROM orders o
  JOIN customers c ON c.id = o.customer_id
  WHERE o.created_at > $1
  ORDER BY o.created_at DESC
  LIMIT 50
`, [startDate]);
```

I went with the batch approach because the data shapes were already established in the frontend, and I didn't want to change the response structure. But if you're starting fresh, the JOIN is the right call.

**After this fix: 4,100ms down to ~1,300ms.**

## Bottleneck #2: Missing Indexes

With the N+1 problem solved, `fetch-orders` at 380ms was now the biggest remaining cost. I looked at the query:

```javascript
const orders = await db.query(`
  SELECT * FROM orders
  WHERE created_at > $1
    AND status IN ('pending', 'processing', 'shipped')
  ORDER BY created_at DESC
  LIMIT 50
`, [startDate]);
```

This looks reasonable, but 380ms for 50 rows out of a table with 10,000+ rows? That's a sign of a full table scan. I ran `EXPLAIN ANALYZE` to confirm:

```sql
EXPLAIN ANALYZE
SELECT * FROM orders
WHERE created_at > '2024-01-01'
  AND status IN ('pending', 'processing', 'shipped')
ORDER BY created_at DESC
LIMIT 50;
```

The output showed a `Seq Scan on orders` -- meaning Postgres was reading every single row in the table, filtering in memory, then sorting and limiting. With 10,000 rows that was manageable but slow. With 100,000 rows it would be catastrophic.

The fix was a composite index on the columns used in the WHERE and ORDER BY clauses:

```sql
CREATE INDEX idx_orders_status_created
ON orders (status, created_at DESC);
```

After adding the index and running `EXPLAIN ANALYZE` again:

```sql
-- Before: Seq Scan, 380ms
-- After:  Index Scan using idx_orders_status_created, 12ms
```

From 380ms to **12ms**. The index lets Postgres jump directly to the matching rows instead of scanning the entire table. If there's one performance lesson that applies everywhere, it's this: check your query plans. A missing index is the single most common cause of slow database queries.

A few rules of thumb for indexes: add them on columns in your WHERE clauses, your JOIN conditions, and your ORDER BY columns. But don't add them blindly on everything -- each index slows down writes and takes up storage. Index the queries that matter, which are the ones that run frequently and touch large tables.

**After this fix: 1,300ms down to ~930ms.**

## Bottleneck #3: Unnecessary Serialization

The remaining 900ms in `transformForResponse` surprised me. It was pure JavaScript -- no database, no I/O -- just transforming data into the shape the frontend expected. How could that take almost a second?

Here's what the code looked like:

```javascript
// The original transform -- death by a thousand copies
function transformForResponse(orders) {
  return orders.map(order => {
    // Deep clone to avoid mutating the original
    let result = JSON.parse(JSON.stringify(order));

    // Merge in computed fields
    result = Object.assign({}, result, {
      total: calculateTotal(result.line_items),
      formattedDate: formatDate(result.created_at),
    });

    // Remove internal fields
    const { internal_notes, cost_basis, ...publicFields } = result;

    // Another transformation layer added later by another dev
    return Object.assign({}, publicFields, {
      customer: Object.assign({}, publicFields.customer, {
        displayName: `${publicFields.customer.name} (${publicFields.customer.email})`,
      }),
    });
  });
}
```

Every order was being `JSON.parse(JSON.stringify())`'d -- which is one of the most expensive operations you can do in JavaScript. Then it was being spread and `Object.assign`'d multiple times, creating intermediate objects that immediately become garbage. For 50 orders with nested line items and customer data, that added up fast.

The fix was to build the response object once, directly:

```javascript
function transformForResponse(orders) {
  return orders.map(order => ({
    id: order.id,
    status: order.status,
    total: calculateTotal(order.line_items),
    formattedDate: formatDate(order.created_at),
    lineItems: order.line_items,
    customer: {
      id: order.customer.id,
      name: order.customer.name,
      email: order.customer.email,
      displayName: `${order.customer.name} (${order.customer.email})`,
    },
    createdAt: order.created_at,
    updatedAt: order.updated_at,
  }));
}
```

No cloning, no intermediate objects, no `JSON.parse(JSON.stringify())`. Just directly mapping the fields you need into the shape you want. This is also more readable -- you can see exactly what the API returns by looking at this function.

This dropped the transform step from 900ms to **15ms**.

As a bonus, being explicit about which fields you include means you'll never accidentally leak an internal field like `cost_basis` to the frontend. The allowlist approach is inherently safer than the blocklist approach of the original code.

**After this fix: 930ms down to ~400ms.**

## The Results

Here's the full timeline of improvements:

| Change | Before | After | Savings |
|--------|--------|-------|---------|
| Baseline | 4,100ms | -- | -- |
| Fix N+1 queries | 4,100ms | 1,300ms | 2,800ms |
| Add database index | 1,300ms | 930ms | 370ms |
| Simplify serialization | 930ms | 400ms | 530ms |
| **Total** | **4,100ms** | **400ms** | **3,700ms (90%)** |

A 10x improvement from three targeted fixes, none of which required rewriting the application or adding caching layers or changing the architecture. The endpoint now responds in under half a second, the operations team stopped complaining, and I got to close that "dashboard is slow" ticket that had been open for months.

The most satisfying part is that none of these fixes were clever. They were all well-known patterns -- batch your queries, index your tables, don't copy data unnecessarily. The hard part was finding which patterns to apply, and that came from measuring.

## Performance Checklist

Here's the checklist I now run through whenever I need to optimize a Node API endpoint. I'm sharing it because past-me would have saved a lot of time having this upfront:

1. **Measure first.** Add timing to the endpoint and get a baseline number. Don't guess.
2. **Profile with clinic.js.** Generate a flame chart to see where time is actually being spent. The answer is almost never where you think it is.
3. **Check for N+1 queries.** If you're querying inside a loop, you have an N+1 problem. Batch or JOIN instead.
4. **Run EXPLAIN ANALYZE on slow queries.** Look for `Seq Scan` on large tables. Add indexes for columns in WHERE, JOIN, and ORDER BY clauses.
5. **Eliminate unnecessary data copying.** Avoid `JSON.parse(JSON.stringify())` for cloning. Build response objects directly.
6. **Use connection pooling.** If you're creating a new database connection per request, use a pool like `pg-pool`. This alone can save 50-100ms per request.
7. **Add caching for expensive, rarely-changing data.** If your aggregated metrics only need to be fresh within 5 minutes, cache them. Redis is the standard choice, but even an in-memory cache with a TTL works for single-server setups.
8. **Paginate everything.** If an endpoint could ever return more than ~100 items, add pagination. Unbounded queries are ticking time bombs.
9. **Compress responses.** Enable gzip/brotli compression in your server. For JSON-heavy APIs, this can cut transfer size by 70-80%.
10. **Monitor in production.** Set up alerting for response times. A p95 of 500ms today becomes 2 seconds in six months when the data grows. Catch it early.

Performance optimization doesn't have to be mysterious. Measure, find the biggest bottleneck, fix it, and repeat. Most of the time, the fix is straightforward once you know where to look. Go make your APIs fast -- your users will notice the difference even if they can't articulate why.
