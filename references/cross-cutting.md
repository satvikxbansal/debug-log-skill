# Cross-cutting — universal error catalog

Covers: bugs that appear across every platform, language, and stack — timezones, character encoding, floating-point, HTTP retries & timeouts, caching, race conditions, flaky tests, secrets, logging, dependency drift. If the bug reproduces identically on web, iOS, Android, and backend, it lives here.

Each entry follows the same shape: **Symptom → Root cause → Fix → Prevention rule.**

## Table of contents

1. [Timezone math using local time on the server](#x01)
2. [Daylight-saving transitions produce duplicate / missing hours](#x02)
3. [UTF-8 vs UTF-16 length — emoji counted as 2 characters](#x03)
4. [BOM in a text file breaks JSON parser](#x04)
5. [`\r\n` vs `\n` — string comparison fails on one platform](#x05)
6. [Floating-point arithmetic for money](#x06)
7. [Integer overflow in duration math (milliseconds → seconds)](#x07)
8. [HTTP 502 / 504 on retryable endpoint — duplicate side effect](#x08)
9. [Exponential backoff without jitter → thundering herd](#x09)
10. [Client-side cache never invalidated after backend shape change](#x10)
11. [CDN / ETag cache returns stale content for minutes after deploy](#x11)
12. [Race condition: two writers, last-write-wins silently](#x12)
13. [TOCTOU: check-then-act with a filesystem or DB state](#x13)
14. [Flaky test: order-dependent via shared state](#x14)
15. [Flaky test: network-bound without stub / timeout](#x15)
16. [Secret committed to source control](#x16)
17. [Environment variable set for dev but missing in prod container](#x17)
18. [Clock skew between client and server — token expiry is "now"](#x18)
19. [Log rotation lost the line that explains the crash](#x19)
20. [Dependency version drift between lockfile and CI cache](#x20)
21. [Feature flag default wrong — flag rollout looks neutral because default is wrong](#x21)
22. [A/B test contaminated by bot traffic](#x22)

---

## <a name="x01"></a>1. Timezone math using local time on the server

**Symptom.** "Daily report generated at midnight" is delivered at 6 PM for some customers, 2 AM for others. Weekly aggregate is off by one day for users near a date boundary.

**Root cause.** Code used a naïve `Date` / `LocalDateTime` without zone context. The server's local zone (often UTC in cloud, but PST on the developer's mac) leaked into computed boundaries.

**Fix.** All backend time math happens in UTC. Convert to user-local at the rendering boundary using the user's stored timezone. For "today" / "this week" in user terms, use the user's zone to compute the boundary, then convert back to UTC for querying.

**Prevention rule.** Time types carry zone context explicitly (`ZonedDateTime`, `Instant`). Naïve types (`LocalDateTime` without zone) are banned from persistence and APIs. Why: "what is midnight" has no universal answer; picking one silently is a bug waiting for a traveller or a weekly-report customer to notice.

## <a name="x02"></a>2. Daylight-saving transitions produce duplicate / missing hours

**Symptom.** A 2 AM-scheduled job runs twice on the "fall back" date, or not at all on the "spring forward" date. An event with local time `2:30 AM on March 10 2026` in US/Pacific doesn't exist.

**Root cause.** Local time is not monotonic. Between 2 AM and 3 AM on DST change, an hour is added (fall) or removed (spring). Naïve local-time math doesn't account for it.

**Fix.** Schedule in UTC; convert for display. For user-facing "every day at 9 AM", interpret the wall-clock time in the user's zone and compute the next UTC instant — using a zone-aware library (`java.time.ZonedDateTime`, Swift `Calendar.nextDate`, date-fns-tz).

**Prevention rule.** Scheduling is UTC-based; wall-clock semantics ("9 AM every day") are computed at dispatch time via zone-aware libs, never by adding 86400000 ms. Why: DST transitions break any code that assumes days are 24 hours long, and the bug only appears twice a year.

## <a name="x03"></a>3. UTF-8 vs UTF-16 length — emoji counted as 2 characters

**Symptom.** User types "🙂" (one emoji). Code counts it as 2 characters in Java / JavaScript, 1 in Swift `String.count`, 4 bytes in UTF-8. A character limit fires inconsistently across platforms.

**Root cause.** `String.length` in Java / JavaScript is UTF-16 code units, not grapheme clusters. Emoji (code points ≥ U+10000) use surrogate pairs — 2 code units. Modern emoji with ZWJ sequences (👨‍👩‍👧) are many code points but one visual character.

**Fix.** For user-facing "character count", use grapheme cluster counting: Swift `String.count` (already graphemes), JS `[...str].length` or `Intl.Segmenter`, Kotlin `BreakIterator`. For byte-level limits (database columns, network), use UTF-8 byte count.

**Prevention rule.** Length semantics are declared: "grapheme count for display", "byte count for storage". APIs that accept "max length" specify which. Why: mismatched length counts across client and server produce one-character-off truncation that ships.

## <a name="x04"></a>4. BOM in a text file breaks JSON parser

**Symptom.** A JSON config file saved on Windows parses fine in Notepad. Node / Python / Java parsers reject it with "Unexpected token  in JSON at position 0".

**Root cause.** Windows tools sometimes write a UTF-8 BOM (byte-order mark, U+FEFF) at the start of a file. JSON.parse and friends see an invisible character before the opening `{`.

**Fix.** Strip BOM on read: `fs.readFileSync(path, 'utf8').replace(/^\uFEFF/, '')`. For `JSON.parse`, some implementations accept BOM; most don't. Configure editors to save without BOM.

**Prevention rule.** Text files that will be machine-parsed are saved as UTF-8 without BOM. `.editorconfig` and `.gitattributes` enforce this. Why: BOM is invisible; the error message doesn't point at the first byte.

## <a name="x05"></a>5. `\r\n` vs `\n` — string comparison fails on one platform

**Symptom.** A test that compares file contents passes on Linux, fails on Windows CI. Or vice versa. A template match fails because one side has `\r\n`.

**Root cause.** Git's `core.autocrlf` setting converts line endings on checkout based on platform. A test fixture committed with LF appears as CRLF on Windows. String comparison is byte-exact.

**Fix.** Normalise before comparing: `.replace(/\r\n/g, '\n')`. Or commit `.gitattributes` with `* text=auto eol=lf` (or `eol=crlf`) to pin line endings.

**Prevention rule.** Tests that compare strings normalise line endings, or the repo has a pinned-eol `.gitattributes`. Why: CRLF bugs are "works on my machine" incarnate and burn CI hours.

## <a name="x06"></a>6. Floating-point arithmetic for money

**Symptom.** Order total is $9.99 + $0.01 = $10.00. Computed total: `10.000000000000002`. Rounding fixes the display but reconciliation with payments is off by a cent.

**Root cause.** `Double` / `Float` (IEEE 754 binary) can't represent most decimal fractions exactly. `0.1 + 0.2 === 0.30000000000000004`.

**Fix.** Use integer cents (or minor units for the currency): store amounts in smallest unit, do math in integers, format for display. Or `BigDecimal` / `Decimal` / `NSDecimalNumber` — language-provided decimal types. Never `Double` for money.

**Prevention rule.** A `Money` type (alias for `BigDecimal` / integer minor units) is used everywhere financial. `Double`-to-money conversion is forbidden. Why: this is a compliance issue; financial mismatches surface as reconciliation bugs that auditors notice.

## <a name="x07"></a>7. Integer overflow in duration math (milliseconds → seconds)

**Symptom.** `int millis = durationSec * 1000` where `durationSec = 3_600_000` (an hour in ms was already passed as seconds by mistake) — overflow, negative result.

**Root cause.** 32-bit signed int overflows at ~2.1 billion. Milliseconds overflow at 24 days. Nanoseconds overflow at 2 seconds. Mixing units + int32 is a crash waiting.

**Fix.** Use 64-bit ints (`long` in Java/Kotlin, `Int64` in Swift, `bigint` in JS when needed) for durations. Use typed duration types (`Duration` in Kotlin/Java/Swift; `ms` libs in JS) to avoid unit confusion.

**Prevention rule.** Durations are typed (`Duration`), not `int` / `long`. Unit conversion is explicit: `.toMillis()`, `.inWholeSeconds`. Comparing "raw numbers" of time requires a comment about the unit. Why: unit-mixing bugs are the classic "Mars Climate Orbiter" family — they pass code review and crash under edge-case inputs.

## <a name="x08"></a>8. HTTP 502 / 504 on retryable endpoint — duplicate side effect

**Symptom.** User taps "Submit payment". Network flakes; client gets 504, retries. The backend actually received the first request; user is charged twice.

**Root cause.** The request was not idempotent, or was idempotent but the retry didn't carry an idempotency key. 5xx responses leave the server state ambiguous — the operation may or may not have happened.

**Fix.** Every mutating request carries a client-generated idempotency key (UUID). The server deduplicates by key for N minutes. On 5xx, the client retries with the *same* key — if the server already processed it, returns cached result.

**Prevention rule.** Every non-`GET` request carries an idempotency key. The server has a dedup store keyed by it. Client retry preserves the key. Why: 5xx retries without idempotency are the canonical "double charge" bug; once in production, it's a finance problem, not an engineering problem.

## <a name="x09"></a>9. Exponential backoff without jitter → thundering herd

**Symptom.** A shared backend has a transient outage; 10,000 clients all retry in exact exponential steps. The second-wave reload hits at the same instant and takes the backend down again.

**Root cause.** Backoff without jitter produces perfectly synchronised retries. Instead of spreading load, the clients amplify.

**Fix.** Add jitter: `sleep = base * (2^attempt) * (0.5 + random())` or "decorrelated jitter" (`sleep = random(base, min(cap, prev * 3))`). Upper-cap the backoff.

**Prevention rule.** Every retry policy has jitter. A shared library (`retry-policy`) encodes the pattern so every service uses the same one. Why: coordinated retries are a DoS of your own making; the one-line jitter fix prevents outage amplification.

## <a name="x10"></a>10. Client-side cache never invalidated after backend shape change

**Symptom.** Backend ships a new field. New clients work. Users on the same app version from yesterday see a crash or missing field. App update doesn't help because the cached blob is still the old shape.

**Root cause.** Cached API response on device was stored as raw JSON (or a Codable blob). Schema versioning wasn't in the cache key. Old-shape blob deserialises with missing fields (or throws).

**Fix.** Include a schema version in the cache key or the cached payload: `cache["user_v3_12345"]`. On version bump, migrate or invalidate. For evolvable Codable, use optional fields + defaults — same discipline as for wire-format migrations.

**Prevention rule.** Caches version their contents. Migration paths are written at the time of schema change. Why: "new app, old cache" produces field-report bugs that can't be reproduced in dev because the dev's cache is always current.

## <a name="x11"></a>11. CDN / ETag cache returns stale content for minutes after deploy

**Symptom.** Deploy complete. New code is live for users who hard-refresh but not for others — who see the old code for 10–30 minutes.

**Root cause.** HTML / JS / asset files are served with `Cache-Control: max-age` or `s-maxage`. CDN caches them for that duration. Deploy pushed new files but the CDN still serves the old response.

**Fix.** Versioned asset URLs (hash in filename) + immutable `Cache-Control: public, max-age=31536000, immutable`. HTML bootstrap is `no-cache` (must revalidate) and references the hashed assets. Purge CDN on deploy for the bootstrap.

**Prevention rule.** Assets are content-addressed (hash in URL). HTML is no-cache. Cache policy is a deploy artifact, not a best-effort header. Why: stale-cache bugs ship features that users can't see until they refresh, and some never do.

## <a name="x12"></a>12. Race condition: two writers, last-write-wins silently

**Symptom.** User A edits a field, saves. User B edits at the same time, saves. A's changes are gone; B doesn't know they overwrote anything.

**Root cause.** The update is `PUT /resource/42 { … }` with no concurrency check. Last write wins by clock order.

**Fix.** Optimistic concurrency: every update includes a `version` or `If-Match: etag`. The server rejects with 409 if mismatched. Client shows a merge UI or explicit "someone else edited" message.

**Prevention rule.** Every mutable resource has a version field and a concurrency check on update. Last-write-wins is never silent — it either surfaces a conflict UI or is a deliberate design choice with a comment. Why: silent data loss is one of the worst bugs because the victims don't know it happened.

## <a name="x13"></a>13. TOCTOU: check-then-act with a filesystem or DB state

**Symptom.** `if (!file.exists()) file.create()` — under concurrent load, two processes both see "doesn't exist", both create, one overwrites the other.

**Root cause.** Time-of-check vs time-of-use race. State can change between the check and the action.

**Fix.** Use atomic operations: `createNewFile()` (returns false if exists), `INSERT ... ON CONFLICT`, compare-and-swap. For filesystem, `O_CREAT | O_EXCL`. For DBs, unique constraints + upsert.

**Prevention rule.** "Check then act" is a TOCTOU smell. Prefer atomic primitives. Every race-prone pattern (file create, row insert, counter increment) uses the atomic API. Why: TOCTOU bugs are rare in dev and common in prod because real concurrent load is hard to reproduce locally.

## <a name="x14"></a>14. Flaky test: order-dependent via shared state

**Symptom.** Test suite passes locally; fails in CI. Or passes with one ordering and fails with another. `--random-order` breaks it.

**Root cause.** A test leaves shared state behind (static field, file on disk, row in a test DB) that another test depends on (or is broken by). Test order is not declared; the framework may parallelise.

**Fix.** Each test starts from a known-clean state: tearDown cleans up; the DB is transactional with rollback per test; no static mutable state. Run the suite with random order locally before merging.

**Prevention rule.** Tests don't share mutable state. Setup creates fixtures; teardown disposes them. CI runs with random order. Why: order-dependent flakes waste enormous amounts of time and can only be fixed by removing the shared state — individual retries don't help.

## <a name="x15"></a>15. Flaky test: network-bound without stub / timeout

**Symptom.** CI occasionally times out at 30 minutes. Retry passes. Never reproduces locally.

**Root cause.** Tests talk to real external services — a third-party staging API, a shared DB, an LLM endpoint. Any one of them can be slow or down; the test hangs until CI kills the job.

**Fix.** All external dependencies are stubbed in tests: WireMock / MSW / fakes. Integration tests that need real endpoints are tagged, gated, run in a separate job with aggressive timeouts, and marked as allowed-to-fail (but tracked).

**Prevention rule.** Unit tests don't touch the network. Integration tests that do are tagged, isolated, and have per-test timeouts. A "test DB up" check runs first; if it fails, tests skip with a clear message rather than hang. Why: network flakes are the #1 cause of "re-run the job" churn; the fix is stubbing, not retries.

## <a name="x16"></a>16. Secret committed to source control

**Symptom.** A dev pushes a branch; GitHub alerts that a secret (AWS key, Stripe key, OpenAI key) was committed. Or: the alert never fires and the secret is exfiltrated months later.

**Root cause.** Secrets in `.env`, `config.json`, or hard-coded in the source. Git history retains them even after removal.

**Fix.** Rotate the leaked secret immediately. Remove from history with `git filter-repo` or BFG — but assume it's been scraped. For prevention: `.gitignore` all env files, pre-commit hook with `detect-secrets` / `gitleaks`, CI scan, and secrets live in a vault (AWS Secrets Manager, HashiCorp Vault, 1Password CLI).

**Prevention rule.** Secrets never appear in source. A pre-commit hook scans for patterns (`AKIA…`, `sk-…`, etc.) and blocks commits. CI re-scans. Rotation is a muscle, not an emergency. Why: leaked secrets are breaches, not bugs; the prevention cost is seconds, the damage cost is unbounded.

## <a name="x17"></a>17. Environment variable set for dev but missing in prod container

**Symptom.** Feature works locally and in staging. Prod returns 500 with "API_KEY is undefined".

**Root cause.** Dev machine has the var in `.env`; staging has it in the orchestrator's secret store; prod container was deployed without the binding. The code uses `process.env.API_KEY` without failing fast.

**Fix.** Fail fast on startup: validate required env vars on boot and crash if missing, with a clear message. Use a typed config layer (envsafe / zod / kotlinx-serialization on env). CI runs a "required env present" check against each environment's manifest.

**Prevention rule.** Required env vars are validated at boot with clear error messages. Deploy manifests are the source of truth for "what env does this environment have" and are checked against code's requirements. Why: "undefined API_KEY at request-time" is a two-hour debugging trip; "crash at boot with 'missing API_KEY'" is a five-second fix.

## <a name="x18"></a>18. Clock skew between client and server — token expiry is "now"

**Symptom.** Mobile user's clock is off by 20 minutes. Server issues a JWT with `exp` = now + 15m. Client checks exp-vs-now locally and thinks the token is already expired.

**Root cause.** Client-side expiry check uses the device clock, which can drift or be deliberately set. Comparing server-issued `exp` (UTC) to device `now` produces false positives.

**Fix.** Don't rely on client-side expiry checks for gating requests. Attempt the request; on 401, refresh. For proactive refresh, use "issued at + TTL", not "compare exp to now". Include a small tolerance (30 s).

**Prevention rule.** Token validity is determined by the server. Client uses "refresh on 401" + proactive refresh using server-provided TTLs, not client-clock comparisons to server-issued exp. Why: client clocks are unreliable; design assuming they drift.

## <a name="x19"></a>19. Log rotation lost the line that explains the crash

**Symptom.** Production crash at 3 AM. By morning, the relevant log is rotated out and compressed; the debug context is gone. Stack trace exists but the context (request id, user id, feature flags) doesn't.

**Root cause.** Logs were written to a file with aggressive rotation (say, 100 MB). The rotation size was tuned for a less chatty service. The crash context was in an old file that got aged out before the on-call could retrieve it.

**Fix.** Structured logs to a centralised system (CloudWatch, Datadog, Sentry) with long retention for ERROR and above. Crash dumps include recent log context. Local files are backup only.

**Prevention rule.** Errors are sent to a centralised, queryable log store. Rotation of local files is sized for the debug window, not for disk-frugality. The "what was happening just before the crash" context is attached to the crash report, not left in log files. Why: post-mortems without context are guesses; the log you need is the one that rotated last night.

## <a name="x20"></a>20. Dependency version drift between lockfile and CI cache

**Symptom.** Local build works, CI build fails with "cannot find method X in class Y". Deleting `node_modules` / `.gradle` locally reproduces the failure.

**Root cause.** The lockfile is out of date with the manifest (someone edited `package.json` / `build.gradle.kts` without running install). Local has stale cached modules; CI does a clean install and picks the updated manifest.

**Fix.** CI runs `npm ci` (exact lockfile install) not `npm install` (which can update the lockfile). Same for `yarn install --frozen-lockfile`, `pnpm install --frozen-lockfile`. A pre-commit hook verifies lockfile is in sync with manifest.

**Prevention rule.** CI uses strict lockfile installs. A check verifies `package.json` + `package-lock.json` are in sync on every PR. Why: "works locally, fails in CI" is usually drift, and the fix is to make local more strict — not to debug CI.

## <a name="x21"></a>21. Feature flag default wrong — flag rollout looks neutral because default is wrong

**Symptom.** A feature is behind a flag default-off. Team rolls it to 10%; metrics look fine; ramp to 100%. Post-rollout, bug reports spike — the feature was *broken* the whole time, but only 10% of users experienced it, and the control group looked the same.

**Root cause.** The flag's off-path was also broken — e.g., the code path executes regardless of flag because the guard was added in the wrong place. Control and treatment both behaved the same, showing no delta.

**Fix.** Ramp carefully. Include a "flag is on but doing nothing" explicit branch. Test the off-path and on-path independently. Monitor both absolute metrics (not just delta) during ramp.

**Prevention rule.** Every feature flag has independent tests for on and off paths. Ramp monitoring watches absolute values, not just deltas. If the control arm's metric moves in parallel with treatment, that's a signal the flag isn't actually gating anything. Why: flag rollouts that only watch deltas can miss bugs that affect both arms.

## <a name="x22"></a>22. A/B test contaminated by bot traffic

**Symptom.** A/B test shows variant B increases conversion by 40%. Shipped to 100%. Conversion returns to baseline.

**Root cause.** Bots (search crawlers, uptime monitors, scripts) hit both variants. Their behaviour didn't change but their presence swamped the signal — or they disproportionately landed in one bucket.

**Fix.** Filter bots from the experiment before analysis: user-agent, behavioural (one request, immediate exit), IP rate-limit signatures. Require authentication or session depth before bucketing. Post-experiment, review the population distribution.

**Prevention rule.** Experiments bucket only humans. Bot traffic is filtered upstream or excluded from the analysis pipeline. Experiment reviews include "is the population what we think it is" as a first check. Why: great A/B numbers that don't survive rollout are typically sampling issues, and bots are the most common source.
