# Web — error catalog

Covers: React (16+), Next.js (Pages router and App router / React Server Components), Vite, TypeScript, Node.js runtime, browser runtime (CORS, cookies, storage, CSP), CSS / layout, testing.

Each entry follows the same shape: **Symptom → Root cause → Fix → Prevention rule.**

## Table of contents

1. [Hydration mismatch: `Text content does not match server-rendered HTML`](#w01)
2. [Infinite re-render loop from setState-in-render](#w02)
3. [Stale closure in `useEffect` / `setInterval`](#w03)
4. [`useEffect` fires twice in dev (React 18 Strict Mode)](#w04)
5. [Accessing `window` / `document` / `localStorage` during SSR](#w05)
6. ["Objects are not valid as a React child" on conditional render](#w06)
7. [Event handler captures old state](#w07)
8. [`useState` initialiser running every render](#w08)
9. [List rendering with unstable `key`](#w09)
10. [Zombie Context provider (re-render storm)](#w10)
11. [Race condition between `fetch` and unmount](#w11)
12. [Missing `suspense` boundary — whole page flashes loading](#w12)
13. [RSC: "You're importing a component that needs useState"](#w13)
14. [Cookies in Next.js App Router — `cookies()` is read-only in most contexts](#w14)
15. [`redirect()` in a try/catch — Next throws to signal redirect](#w15)
16. [CORS preflight fails only in production](#w16)
17. [CSP blocks inline styles / scripts](#w17)
18. [`fetch` caches aggressively in Next 14+ App Router](#w18)
19. [Environment variable is `undefined` at runtime](#w19)
20. [TypeScript: "Object is possibly null" after a null check](#w20)
21. [TypeScript: non-null assertion hiding a real bug](#w21)
22. [Node: `EADDRINUSE` on restart](#w22)
23. [Node: `unhandledRejection` in an async route handler](#w23)
24. [Node streams: backpressure ignored, memory blows up](#w24)
25. [Z-index war / stacking context confusion](#w25)
26. [Mobile Safari 100vh accounts for URL bar](#w26)
27. [Flexbox: `min-height: 0` trick for scrolling children](#w27)
28. [Playwright / Cypress test flaky on CI only](#w28)
29. [Bundle size explodes after a "small" dependency](#w29)
30. [Largest Contentful Paint regresses after image swap](#w30)

---

## <a name="w01"></a>1. Hydration mismatch: "Text content does not match server-rendered HTML"

**Symptom.** Console warning after page load: `Warning: Text content did not match. Server: "12:04 PM" Client: "12:04:01 PM"`. Sometimes the whole page renders blank below the mismatch.

**Root cause.** The server and client rendered different HTML for the same component. Usually caused by reading a non-deterministic value during render: `Date.now()`, `new Date()`, `Math.random()`, `window.innerWidth`, a user-timezone-dependent format.

**Fix.** Move the non-deterministic read out of render. Either (a) read it in `useEffect` and set it to state, which makes the initial SSR match a placeholder, or (b) mark the component with `'use client'` and wrap in `<Suspense>` with a skeleton fallback, or (c) use `suppressHydrationWarning` if and only if the mismatch is cosmetic (e.g., a formatted time) and the rendered DOM structure is identical.

**Prevention rule.** Never read `window`, `document`, `localStorage`, `navigator`, `Date.now()`, `new Date()`, `performance.now()`, or `Math.random()` during React render in any component that can render on the server. These belong in `useEffect`, event handlers, or client-only modules. Why: SSR/CSR mismatch corrupts the hydration tree — downstream state can be subtly wrong in ways that don't warn.

## <a name="w02"></a>2. Infinite re-render loop from setState-in-render

**Symptom.** "Too many re-renders. React limits the number of renders to prevent an infinite loop." Sometimes tab freezes before the error fires.

**Root cause.** A `setState` call executed during render (not inside a handler or effect). Common pattern: `<div onClick={setOpen(true)}>` (note: missing arrow — calls immediately), or `setState(value)` called at the top of the function body.

**Fix.** Wrap the setter in a function: `onClick={() => setOpen(true)}`. If you actually need to initialise state from props once, use the `useState(() => initialiser)` pattern or `useEffect` with the correct deps.

**Prevention rule.** `setState` only inside event handlers, `useEffect`, `useLayoutEffect`, or `useReducer`/`useSyncExternalStore` callbacks. Never in the component body. Why: React treats a body-level `setState` as a dependency of the render itself and loops.

## <a name="w03"></a>3. Stale closure in `useEffect` / `setInterval`

**Symptom.** A `setInterval` logs always the same value, even after state has updated. The `onClick` handler inside a memoised component uses old props.

**Root cause.** The callback was created in a closure that captured the state value at mount time; that closure does not re-read the latest state.

**Fix.** Either add the stale value to the effect's dependency array (effect re-runs, handler re-created), or use a ref to hold the mutable value, or use the functional `setState(prev => …)` form which reads latest state from React itself.

**Prevention rule.** Any value read inside a `useEffect` / `useCallback` / `useMemo` that can change between renders **must** be in the dependency array. Disable the exhaustive-deps ESLint rule only with a comment explaining why, and never without the `useRef` or functional-setter escape hatch. Why: stale closures are the #1 cause of "ghost" state bugs in React.

## <a name="w04"></a>4. `useEffect` fires twice in dev (React 18 Strict Mode)

**Symptom.** An effect that posts to an analytics endpoint fires two events in development, one in production.

**Root cause.** React 18 Strict Mode deliberately double-invokes effects on mount in dev to surface cleanup bugs. The effect is also missing a cleanup.

**Fix.** Add the cleanup that cancels the effect's side-effect: `AbortController`, `clearTimeout`, `unsubscribe`. For fire-once effects that genuinely shouldn't dedupe (rare), use a `useRef` "hasFired" guard, but prefer fixing the cleanup.

**Prevention rule.** Every `useEffect` that subscribes, fetches, sets a timer, or posts a side effect must return a cleanup function. Treat the double-fire in dev as a test that your cleanup works. Why: production sometimes double-mounts too (Suspense, React Cache); effects without cleanup leak.

## <a name="w05"></a>5. Accessing `window` / `document` / `localStorage` during SSR

**Symptom.** `ReferenceError: window is not defined` at build time or on the server in Next.js / Remix / SvelteKit.

**Root cause.** The code path runs during server render, where browser globals don't exist.

**Fix.** Gate the access: `if (typeof window !== 'undefined') { … }` inside a non-render path, or move the code into a `useEffect`, or mark the component `'use client'` and lazy-import it with `ssr: false` in Next.js.

**Prevention rule.** Browser globals are never safe to reference at module top-level or during render. The only safe locations are: event handlers, `useEffect` body, `useLayoutEffect` body, or an explicitly client-only module loaded with `dynamic(..., { ssr: false })`. Why: SSR breaks build-time for Pages router and renders blank pages for App router.

## <a name="w06"></a>6. "Objects are not valid as a React child" on conditional render

**Symptom.** `Error: Objects are not valid as a React child (found: object with keys {message, stack}).`

**Root cause.** You rendered an Error object, a Promise, or a raw object — usually from `{error && <div>{error}</div>}` where `error` is an Error instance, not a string.

**Fix.** Render a specific property: `{error && <div>{error.message}</div>}`, or coerce with `String(error)`.

**Prevention rule.** Every JSX expression inside curly braces must evaluate to a string, number, boolean, null, undefined, React element, or array thereof. Never `{objectValue}`. TypeScript helps here — type error-rendering paths as `string | null`. Why: React's error is verbose enough to hide above the interesting stack frame.

## <a name="w07"></a>7. Event handler captures old state

**Symptom.** Clicking a button calls a handler that uses a stale value of a `useState` variable. User sees "Count is 0" even though UI shows "Count: 3".

**Root cause.** The handler closure was created in a previous render, and the logger inside it still references the state from that render.

**Fix.** Use `setCount(prev => prev + 1)` for writes. For reads inside async handlers, capture the current value with a ref (`countRef.current`) or mark the handler `useCallback` with `count` in deps (accepting re-creation cost).

**Prevention rule.** In any event handler that performs an async step (await, setTimeout, Promise chain), assume the closure is stale by the time it resumes. Re-read state via functional setter or ref. Why: the await boundary is an invisible render boundary for closures.

## <a name="w08"></a>8. `useState` initialiser running every render

**Symptom.** An expensive computation (`generateSeed()`, `new Date()`) runs on every render, not just the first.

**Root cause.** `useState(expensiveCall())` invokes `expensiveCall` on every render, then discards the result. React only keeps the first-render initial value.

**Fix.** Wrap in a function: `useState(() => expensiveCall())`. React now calls the function only on the mount render.

**Prevention rule.** Use the lazy initialiser form `useState(() => …)` whenever the initial value requires work (JSON parse, random, computation, local-storage read). Why: the expensive call is otherwise running on every render, invisibly.

## <a name="w09"></a>9. List rendering with unstable `key`

**Symptom.** Animations restart when an item is added to the middle of a list. Form inputs inside rendered rows lose focus on unrelated state changes.

**Root cause.** `key={index}` or `key={Math.random()}` was used. React's reconciler uses `key` to match elements across renders; unstable keys destroy and recreate DOM nodes.

**Fix.** Use a stable, unique id — usually a database `id` field. If you must synthesise, use `crypto.randomUUID()` *once* at item creation and carry it with the item, not at render time.

**Prevention rule.** `key` must be stable across renders and unique among siblings. Never `key={index}` for lists that can reorder or have items inserted/removed in the middle. Why: unstable keys cause DOM churn that breaks animations, focus, and user input — none of these warn.

## <a name="w10"></a>10. Zombie Context provider (re-render storm)

**Symptom.** Every component in the tree re-renders when a single unrelated value changes.

**Root cause.** A Context `value` is being re-created on every render (inline object), so every consumer sees a "new" value and re-renders.

**Fix.** Memoise the context value: `const value = useMemo(() => ({ a, b }), [a, b])`. Split the context into narrower ones if different consumers care about different fields.

**Prevention rule.** Any object or array passed as `value` to a Context provider must be memoised. Primitives are safe. Why: Context propagates referential identity; new refs trigger every consumer.

## <a name="w11"></a>11. Race condition between `fetch` and unmount

**Symptom.** "Can't perform a React state update on an unmounted component" warning. Or, subtly worse: the user navigates away, comes back quickly, and sees data from the previous request overwritten by the slow first response.

**Root cause.** The effect started a fetch, the component unmounted (or the effect re-ran with new deps), the first fetch resolved after the second.

**Fix.** Use `AbortController` and abort on cleanup:

```js
useEffect(() => {
  const ac = new AbortController();
  fetch(url, { signal: ac.signal })
    .then(r => r.json())
    .then(setData)
    .catch(e => { if (e.name !== 'AbortError') setError(e); });
  return () => ac.abort();
}, [url]);
```

**Prevention rule.** Every `fetch` triggered by an effect must be cancelled in the cleanup. Every async handler that writes state after `await` must check whether it is still the latest request (AbortController, ignore-flag, or a library like SWR / React Query that handles this for you). Why: the second bug (stale overwrite) is silent and production-visible; the warning is the benign half.

## <a name="w12"></a>12. Missing `suspense` boundary — whole page flashes loading

**Symptom.** A single slow data fetch causes the entire page (header, sidebar, footer) to blank to a loading state.

**Root cause.** The Suspense boundary is at the root, so every suspending child takes down the whole tree.

**Fix.** Wrap the slow section in its own `<Suspense fallback={…}>` as close as possible to the suspending component. In App router, use a nested `loading.tsx` file.

**Prevention rule.** Place `<Suspense>` boundaries at the narrowest point that makes sense — typically around each independently-loading data region. Never rely on a single root-level boundary. Why: Suspense is how React coordinates loading states; broad boundaries make the UI feel slow even when only one widget is.

## <a name="w13"></a>13. RSC: "You're importing a component that needs useState"

**Symptom.** Build error in Next.js App Router: "You're importing a component that needs useState. It only works in a Client Component but none of its parents are marked with 'use client'."

**Root cause.** Imported a client-side hook (`useState`, `useEffect`, `useRouter` from `next/navigation` used as event listener) into a Server Component.

**Fix.** Either mark the file `'use client'` at the top, or refactor so hooks live in a leaf component that you then import from a Server Component.

**Prevention rule.** Keep the client/server boundary as leaf-ward as possible — only the smallest interactive widget should be a Client Component. Stateless, data-fetching, and layout components stay Server Components. Why: the boundary marks where React stops sending serialised UI and starts shipping JS; moving it root-ward bloats the bundle.

## <a name="w14"></a>14. Cookies in Next.js App Router — `cookies()` is read-only in most contexts

**Symptom.** "Cookies can only be modified in a Server Action or Route Handler" error, or the `Set-Cookie` silently ignored.

**Root cause.** Tried to call `cookies().set(...)` inside a Server Component render. The App Router only allows mutation in Server Actions and Route Handlers.

**Fix.** Move the cookie write into a Server Action (`'use server'` function) or a Route Handler (`app/api/**/route.ts`). For reads, `cookies()` is fine everywhere, but remember it makes the route dynamic.

**Prevention rule.** Separate cookie *reads* (allowed everywhere, marks route dynamic) from *writes* (only in Server Actions / Route Handlers). Plan auth flows so the write site is one of those two. Why: App Router's rendering model caches Server Components; allowing cookie writes during render would break cache invariants.

## <a name="w15"></a>15. `redirect()` in a try/catch — Next throws to signal redirect

**Symptom.** Your Next.js `redirect()` / `notFound()` call doesn't redirect; instead you hit the generic error boundary with "NEXT_REDIRECT" swallowed.

**Root cause.** `redirect()` works by throwing a special error that the Next framework catches. A surrounding `try/catch (e) { … }` caught it first.

**Fix.** Either call `redirect()` outside the `try/catch`, or re-throw the error unless it's handleable. The idiomatic form:

```ts
try { … } catch (e) {
  if (isRedirectError(e) || isNotFoundError(e)) throw e;
  // handle the real error
}
```

**Prevention rule.** Never wrap `redirect()`, `notFound()`, or `permanentRedirect()` calls in a catch-all. When you must, re-throw Next's framework errors. Why: these functions use throw-for-control-flow; catching them silences the redirect.

## <a name="w16"></a>16. CORS preflight fails only in production

**Symptom.** Everything works locally, production shows "Access to fetch … has been blocked by CORS policy: Response to preflight request doesn't pass access control check."

**Root cause.** In dev, a proxy (Vite, `next.config.js` rewrites) forwards requests to the API so they're same-origin. In prod, the browser fires an actual cross-origin request, and the API doesn't return the right preflight response.

**Fix.** On the API side, respond to `OPTIONS` with `Access-Control-Allow-Origin`, `-Methods`, `-Headers`, and (if cookies are used) `-Credentials: true` + a specific origin (not `*`). On the client side, remove any accidental custom headers that trigger preflight (e.g., `Content-Type: application/json` is fine; `Authorization: Bearer …` triggers preflight).

**Prevention rule.** Reproduce cross-origin locally before shipping — either by disabling the dev proxy or by deploying a preview environment. Never discover CORS in prod. Why: the dev proxy hides the preflight contract entirely.

## <a name="w17"></a>17. CSP blocks inline styles / scripts

**Symptom.** Console error "Refused to apply inline style because it violates the following Content Security Policy directive …". Styled-components, emotion, or inline `style={{ … }}` may all trigger it depending on config.

**Root cause.** A strict CSP was added (often by a new WAF or a framework default) that disallows `unsafe-inline`. Libraries that inject style tags fail.

**Fix.** Either (a) add a nonce to your CSP and pipe it through to the CSS-in-JS library (most support it), (b) switch to zero-runtime CSS (Tailwind, vanilla-extract, linaria, CSS modules), or (c) allowlist `'unsafe-inline'` for styles only, understanding the XSS implications.

**Prevention rule.** Write your CSP in a format that includes `style-src` and `script-src` directives, not just a blanket header, and test it in a CSP-in-report-only mode first. Why: CSP violations are console-only in browsers and easy to miss; the page still "works" but styling silently breaks.

## <a name="w18"></a>18. `fetch` caches aggressively in Next 14+ App Router

**Symptom.** A Next.js `fetch(url)` call returns the same data for hours even though the upstream is changing.

**Root cause.** App Router wraps `fetch` and applies full-route caching by default. The data is cached at build time (for static routes) or indefinitely (for dynamic ones) unless you opt out.

**Fix.** Use `fetch(url, { cache: 'no-store' })` for always-fresh, or `fetch(url, { next: { revalidate: 60 } })` for time-based revalidation, or call `revalidatePath('/…')` / `revalidateTag('…')` from a Server Action when data changes.

**Prevention rule.** For any `fetch` inside a Next App Router Server Component, explicitly declare your caching strategy (`cache: 'no-store'`, `revalidate: N`, or a tag). Never rely on default behaviour — it changes across Next versions. Why: silent over-caching is the single most reported App-Router bug in production.

## <a name="w19"></a>19. Environment variable is `undefined` at runtime

**Symptom.** `process.env.API_URL` is `undefined` in the browser; `NEXT_PUBLIC_*` works fine.

**Root cause.** In Next.js (and most bundler-based setups), env vars not prefixed `NEXT_PUBLIC_` / `VITE_` / `PUBLIC_` are stripped from the client bundle. They exist only on the server.

**Fix.** Either prefix the var (`NEXT_PUBLIC_API_URL`) and accept that it's shipped to the client, or do the network call server-side and never ship the value.

**Prevention rule.** Public env vars must be explicitly prefixed. Treat the prefix as a signal of "this will be shipped to every user" — never put secrets behind a public prefix. Why: a single `NEXT_PUBLIC_STRIPE_SECRET_KEY` in prod is a security incident; the prefix discipline is the only guardrail.

## <a name="w20"></a>20. TypeScript: "Object is possibly null" after a null check

**Symptom.** You wrote `if (user) { … user.name … }` and TS complains `Object is possibly 'null'`.

**Root cause.** Usually: (a) `user` is a property of an object that TS can't narrow (optional chaining doesn't always narrow), (b) there's an async boundary between the check and the use, or (c) `user` is typed as a getter / computed property whose value TS treats as non-narrowable.

**Fix.** Hoist into a local: `const u = user; if (u) { … u.name … }`. TS narrows locals much more aggressively than properties.

**Prevention rule.** When a type guard doesn't narrow, hoist the value into a local `const` first, then guard, then use the local. Why: TS's control-flow analysis is sound on locals, not on repeated property reads — the property could change between reads in principle.

## <a name="w21"></a>21. TypeScript: non-null assertion hiding a real bug

**Symptom.** Code ships with `foo!.bar.baz` assertions everywhere; occasional "Cannot read properties of undefined" in prod.

**Root cause.** `!` tells TS "trust me, this isn't null" — it generates zero runtime check. The assertion is only valid until the data changes.

**Fix.** Replace `foo!` with a real null check, optional chaining (`foo?.bar.baz`), or a schema validator (Zod, Yup, Valibot) at the boundary.

**Prevention rule.** `!` (non-null assertion) is allowed only in two places: tests (where you assert test setup), and just-after-narrowing patterns the compiler can't see (rare, document why). Everywhere else, use a runtime check. Why: `!` tells the compiler to be quiet, not the program to be safe; production will find the gap.

## <a name="w22"></a>22. Node: `EADDRINUSE` on restart

**Symptom.** After crashing or Ctrl-C, `next dev` / `vite` / `node server.js` won't restart: "Error: listen EADDRINUSE: address already in use :::3000".

**Root cause.** The previous process didn't clean up its port (often a hung watcher or nodemon child).

**Fix.** Find and kill: `lsof -i :3000` → `kill -9 <pid>`. In CI, use `kill-port 3000` from the `kill-port` package. Root-cause: add `process.on('SIGTERM')` / `SIGINT` handlers that call `server.close()`.

**Prevention rule.** Every long-lived Node process must register `SIGTERM` and `SIGINT` handlers that gracefully close its servers, database connections, and file watchers. Why: without it, dev loops leak processes and prod deployments leave sockets in TIME_WAIT.

## <a name="w23"></a>23. Node: `unhandledRejection` in an async route handler

**Symptom.** Server crashes with no obvious stack; log shows `UnhandledPromiseRejectionWarning` and an upstream async function.

**Root cause.** An `async` function was called without `await` — its rejection is unhandled. Common in Express handlers: `app.get('/x', (req, res) => asyncWork())` forgets to `await`.

**Fix.** `await` the call, wrap in try/catch, or use an error-forwarding middleware. Modern frameworks (Fastify, Next route handlers, Hono) handle async rejections by default; Express does not.

**Prevention rule.** Every route/request handler in a framework that doesn't auto-forward async errors (Express, raw Node) must be wrapped in an async-error adapter. Why: unhandled rejections crash Node 15+ by default and corrupt observability.

## <a name="w24"></a>24. Node streams: backpressure ignored, memory blows up

**Symptom.** Reading a large file / HTTP response and transforming it OOMs the process. `node --max-old-space-size` raised, repeats at higher limit.

**Root cause.** Data is being pulled from a fast source (disk) faster than a slow sink (network) can consume it. Buffers accumulate in memory.

**Fix.** Use `pipeline()` from `node:stream/promises`: it propagates backpressure automatically. Avoid `data.on('data', chunk => writable.write(chunk))` without checking the return value of `write()`.

**Prevention rule.** Always compose streams with `pipeline()`. Never hand-roll `on('data')` → `.write()` unless you are handling backpressure explicitly via `.write()`'s return value and `drain`. Why: the naive pattern works up to the point where data rates diverge, which is usually production.

## <a name="w25"></a>25. Z-index war / stacking context confusion

**Symptom.** A modal with `z-index: 9999` still renders behind a header with `z-index: 10`.

**Root cause.** Stacking context is created by properties other than z-index — `transform`, `filter`, `opacity < 1`, `will-change`, `isolation: isolate`. An ancestor with one of these creates a new stacking context and clamps the z-index of its descendants.

**Fix.** Portal the modal out of the problem ancestor (React: `createPortal(children, document.body)`) or remove the offending transform/filter/opacity from the ancestor.

**Prevention rule.** Render modals, popovers, tooltips, and toasts in a portal to `document.body` — never inline in the tree. Why: you cannot predict which ancestor will grow a `transform` tomorrow.

## <a name="w26"></a>26. Mobile Safari 100vh accounts for URL bar

**Symptom.** A full-height hero looks right on desktop, gets cropped at the bottom on mobile Safari because the URL bar eats 60px.

**Root cause.** `100vh` on mobile Safari is the viewport **when the URL bar is hidden**, not the visible area when it's shown.

**Fix.** Use `100dvh` (dynamic viewport height) in modern browsers. For older fallbacks, set `--vh` from JS on resize: `document.documentElement.style.setProperty('--vh', `${window.innerHeight * 0.01}px`)` and use `height: calc(var(--vh, 1vh) * 100)`.

**Prevention rule.** Use `100dvh` for full-viewport height; only fall back to `100vh` with a JS shim. Test on real iOS Safari, not just Chrome DevTools mobile emulation. Why: iOS Safari's URL-bar behaviour is not emulated correctly in DevTools.

## <a name="w27"></a>27. Flexbox: `min-height: 0` trick for scrolling children

**Symptom.** A scrolling child inside a flex column grows unbounded instead of scrolling; the whole page scrolls instead.

**Root cause.** Flex items have an implicit `min-height: auto` (or `min-width: auto`), which prevents them from being smaller than their content. An inner `overflow: auto` then has nothing to scroll against.

**Fix.** Set `min-height: 0` (or `min-width: 0`) on the flex child that contains the scrolling content.

**Prevention rule.** Any flex child that itself contains a scroll area needs explicit `min-height: 0`. Why: the auto-min-size default is one of flex's most-surprising behaviours; it silently breaks nested scroll.

## <a name="w28"></a>28. Playwright / Cypress test flaky on CI only

**Symptom.** E2E test passes locally, fails in CI 1-in-5 runs. Usually at a click or assertion that races with an animation.

**Root cause.** CI runs slower; clicks land before hydration completes, or on an animating element, or before a layout shift repositions it.

**Fix.** (a) Wait on semantic state, not timing — `await expect(locator).toBeEnabled()` / `toBeVisible()` before acting. (b) Disable animations in test mode (CSS `*, *::before, *::after { animation: none !important; transition: none !important; }` injected for E2E). (c) Increase retries for network-dependent specs.

**Prevention rule.** E2E tests never sleep and never click without an "is ready" precondition. Animations are disabled in the test build. Why: `await page.waitForTimeout(500)` is an admission that you don't know what you're waiting for — it will fail eventually.

## <a name="w29"></a>29. Bundle size explodes after a "small" dependency

**Symptom.** `npm i date-fns` bumps the main bundle by 400KB gzipped. Lighthouse score drops.

**Root cause.** The library was imported as a default (`import d from 'date-fns'`), pulling the whole thing. Or the library is not tree-shakeable (CommonJS-only, uses side effects).

**Fix.** Import only what you use: `import { format } from 'date-fns/format'`. Run `npx next build && npx next bundle-analyzer` (or `vite-bundle-visualizer`) to see what's in the bundle. Replace non-tree-shakeable libraries with alternatives (`date-fns/fp` → `dayjs`, `lodash` → `lodash-es` + named imports).

**Prevention rule.** Add a bundle-size budget to CI (`@next/bundle-analyzer`, `size-limit`, or `bundlesize`). Any PR that grows the main bundle by more than 10KB gzipped requires explicit approval. Why: the death of web performance is a thousand "small" imports.

## <a name="w30"></a>30. Largest Contentful Paint regresses after image swap

**Symptom.** LCP was 1.8s, is now 3.4s. The only change was swapping a hero image.

**Root cause.** The new image is larger, not preloaded, or served without proper dimensions, causing layout shift and delayed paint.

**Fix.** Use `next/image` / `<img>` with explicit `width` / `height` and `fetchpriority="high"` / `priority` for above-the-fold images. Preload: `<link rel="preload" as="image" href="/hero.avif">`. Use modern formats (AVIF → WebP → JPEG) with `<picture>` fallbacks.

**Prevention rule.** Every above-the-fold image must have explicit dimensions, a modern format, and `priority` / `fetchpriority="high"`. Run Lighthouse on the deployed preview before merging image-touching PRs. Why: LCP is directly scored by Google and correlates with revenue; regressions don't warn.

---

## Where to look next

- `references/cross-cutting.md` — universal bugs that happen on web too (timezones, encoding, flaky-test causes beyond what's listed here).
- `references/preempt-checklist.md` — the "web" section contains pre-mortem questions for new features.
