# Geek-Trainer — Implementation Plan

## Context

`/home/prince-soni/Desktop/Geek-Trainer` contains one file: `SPECIFICATIONS.MD`
(revision 2), a 50KB product spec for **Geek-Trainer** — a training app that
holds the user's equipment and goals, finds compatible exercises, plans a week
with AI help, logs every set in the gym, and turns the log into progress,
personal records and AI analysis.

The spec is now strong on *what* and deliberately silent on most of *how*. This
plan settles the *how* before any code exists, and lays out a build order where
every phase ships something usable.

**Intended outcome:** a phased, executable plan that takes the repo from empty
to the §29 feature scope and the §30 acceptance criteria — with every remaining
implementation choice pinned to a specific, defensible answer.

Decisions are labelled **D1–D16** and are meant to be cited from code comments
the way `SPECIFICATIONS.MD` sections are.

---

## The decisions I made

These were open after the spec. Each is now settled, with reasoning.

### D1. Two services, not one, and not three.

```text
web/     Next.js (App Router) + TypeScript + Tailwind — the PWA
api/     FastAPI + Python + Postgres — accounts, sync, derived data, AI
```

No monorepo tooling (no Turborepo, no Nx) until there is a third package. Two
directories, two lockfiles, one `docker-compose.yml` for local Postgres.

Rejected: a Next.js-only app with route handlers as the backend. The spec needs
a scheduled ingest job (§5.1), server-side recomputation (§13.4) and real SQL
aggregation for charts — that is a backend, and pretending otherwise means
writing it twice when it moves.

### D2. The client is local-first. The server is authoritative.

The single most important structural decision, and it follows from
`SPECIFICATIONS.MD` §1.1 and §12.

```text
Writes:   IndexedDB first → render immediately → enqueue mutation → sync later
Reads:    IndexedDB for the active session and recent history
          API for charts, aggregates and anything older than the local window
Truth:    the server, after sync; the client's derived values are provisional
```

Practically, this means the logging UI **never awaits fetch**. A set write that
can fail on a bad connection is a set the user loses, and losing sets is the
one failure this product cannot recover from.

Local window: the current session, the last 90 days of sessions, the user's
plans, and the exercise catalogue. Everything else is fetched.

### D3. Sync is a mutation log with client-generated ids.

```json
POST /api/v1/sync
{
  "mutations": [
    {
      "id": "01J8...",             // client mutation id (UUIDv7), idempotency key
      "type": "set.upsert",
      "at": "2026-08-31T18:22:04Z",
      "payload": { "set_id": "01J8...", "session_id": "...", "weight_kg": 60, "reps": 10 }
    }
  ],
  "since": "2026-08-31T17:00:00Z"
}
→ { "applied": [...ids], "rejected": [{id, code}], "changes": [...server records], "cursor": "..." }
```

```text
Every entity the client can create carries a client-generated UUIDv7 primary key.
Every mutation carries a mutation id; applying it twice is a no-op (unique index).
Mutation types are a closed set: session.start, session.finish, session.cancel,
  session_exercise.upsert, session_exercise.delete, set.upsert, set.delete.
Rejected mutations are surfaced to the user, never dropped silently.
```

**Rationale:** UUIDv7 rather than UUIDv4 because it is time-ordered, so the
primary-key index stays sequential and the "sets for this session in order"
query is a range scan. Idempotency lives in the mutation id rather than an HTTP
header because the same mutation may be replayed inside a batch after a partial
failure.

Conflict rule: last-write-wins on `updated_at` per record (spec §12.4). This is
honest for a single user on one device at a time, and it is written down rather
than emergent.

### D4. Postgres from day one. IndexedDB via Dexie.

Postgres because every interesting read is an aggregate over sets grouped by
week, muscle or exercise, and SQLite-then-migrate would mean rewriting exactly
those queries.

Dexie over raw IndexedDB because the raw API is callback-shaped and the schema
migration story is the part everyone gets wrong.

Local stores: `exercises`, `plans`, `sessions`, `session_exercises`, `sets`,
`mutations`, `meta`.

### D5. A seed exercise dataset is checked into the repo.

The ingest job (§5.1) pulls from ExerciseDB/WGER. But a normalized snapshot of
~1,300 exercises lives in `api/seeds/exercises.json`, and `make seed` loads it.

```text
Development needs no API key.
Tests are deterministic — fixtures reference stable exercise ids.
A first deploy has a full catalogue before the first ingest runs.
Contributors are not blocked on a third-party account.
```

This also de-risks open question §32 Q1: if licensing turns out to forbid
redistribution, the seed shrinks to a small public-domain set and only
development convenience is lost — not the architecture.

### D6. Derived data: materialize the hot and stable, compute the rest.

```text
Materialized (written at session finish, recomputed on edit):
  session_summary   — totals, duration, muscles trained
  personal_records  — one row per (user, exercise, record_type)

Computed on read (SQL, indexed):
  every chart series, weekly/monthly volume, muscle frequency, adherence
```

**Rationale:** PRs must be materialized because §11.2 needs "is this set a PR"
answerable *during* the set, on device, in milliseconds. Charts must not be
materialized because editing a set from three weeks ago has to change them
(§13.4), and a cache that must be invalidated by any historical edit is a cache
that will be wrong.

Recomputation is a single pure function, `recompute(user_id, exercise_id, from_date)`,
called by the mutation handler. It is deterministic and idempotent — the same
set history always yields the same output — which makes it testable without
mocking time.

### D7. The formulas, pinned.

```python
LB_PER_KG          = 0.45359237          # exact
E1RM               = w * (1 + reps / 30) # Epley, only for 1 <= reps <= 12
VOLUME             = load * reps         # per metric type, §13.1
EFFECTIVE_LOAD     = bodyweight_kg * factor + added_kg
```

Stored in one module, `api/core/formulas.py`, with no I/O and no ORM imports,
and imported by everything that needs them — including the TypeScript side via
a generated constants file, so the client's optimistic PR check and the
server's authoritative one cannot disagree.

Weights are `Decimal` in Python and `NUMERIC(7,3)` in Postgres. Never `float`:
`0.1 + 0.2` kg is not a number a user should ever see.

### D8. Local dates are denormalized onto the session.

```sql
sessions.date          DATE NOT NULL   -- the user's local calendar date
sessions.start_time    TIMESTAMPTZ
```

Computed once, at session start, from the user's IANA timezone. Every "this
week", "this month", streak and adherence query groups on `date`.

**Rationale:** the alternative — `start_time AT TIME ZONE user.timezone` inside
every aggregate — is unindexable, and it silently rewrites history if the user
travels and changes their timezone setting. The date a workout belongs to is
decided when it happens.

### D9. Auth is a cookie session, not a JWT.

```text
Opaque 256-bit random token, stored SHA-256-hashed server-side.
httpOnly + Secure + SameSite=Lax cookie. Sliding 30-day expiry.
Argon2id for passwords.
CSRF: SameSite=Lax covers navigation; unsafe cross-site requests are additionally
  rejected by an Origin check.
```

**Rationale:** JWTs cannot be revoked, and "log out of all devices" (§24) is a
listed requirement. A token in `localStorage` is readable by any XSS; an
httpOnly cookie is not. Statelessness buys nothing here — every request already
touches Postgres.

### D10. AI: Claude, behind an interface, with Pydantic as the contract.

```python
# api/ai/client.py
class LLMClient(Protocol):
    async def structured(self, *, system: str, user: str, schema: type[BaseModel]) -> BaseModel: ...
    async def prose(self, *, system: str, user: str) -> AsyncIterator[str]: ...
```

```text
Default model:  claude-opus-5   ($5 / $25 per MTok, 1M context)
Structured out: output_config.format against the Pydantic schema
                (client.messages.parse validates the response)
Thinking:       {"type": "adaptive"} — plan generation is genuinely reasoning work
Streaming:      chat and analysis stream; generation does not need to
Prompt caching: the system prompt and the exercise candidate block are stable
                within a session — cache_control on the prefix, volatile user
                context last
```

Two implementations from day one: `AnthropicClient` and `FakeLLMClient`. Every
test uses the fake; no test spends money or needs a network.

**Rationale on the model:** plan generation and progress analysis are the two
places this product is either good or embarrassing, and both are reasoning
tasks over a constrained candidate set. Start on the most capable model, measure,
and let *the user* decide whether to trade quality for cost later — that is a
product decision, not one to make silently in the client constructor. Effort
level is a config value so it can be tuned per endpoint without a code change.

### D11. The AI's output space is the candidate list.

The mechanism behind spec §21.1, spelled out:

```text
1. SQL selects ≤ 60 exercises matching equipment + target muscles + difficulty.
2. The prompt carries them as a compact table: id, name, equipment, primary muscle.
3. The response schema types the exercise field as a string id.
4. Validation rejects any id not in the candidate set — a hard failure, not a warning.
```

The model chooses and orders; it never names. This is what makes "the AI must
not invent exercises" a property of the system rather than a hope about the
prompt.

### D12. Every AI feature has a deterministic twin, written first.

```text
generate_plan   → rules: filter by equipment/muscle, compound → isolation,
                  cap by duration, avoid muscles trained in the last 48h
substitute      → SQL: same primary muscle, available equipment, rank by
                  shared secondary muscles and matching difficulty
analyze         → the chart series and a plain-language template
```

The deterministic version ships in an earlier phase than the AI version that
wraps it. The AI path is then a ranking-and-explaining layer over a working
feature, and §21.6 degradation is free rather than retrofitted.

### D13. Types are generated from the OpenAPI schema.

FastAPI emits OpenAPI; `openapi-typescript` generates `web/src/api/types.ts` in
a `make types` step checked by CI. No hand-written duplicate interfaces, and a
backend field rename fails the frontend typecheck instead of failing in
production.

### D14. Testing, and what each layer is for.

```text
pytest        formulas, recomputation, PR revocation, validation pipeline,
              ownership (a test that fails if any query omits user_id)
Vitest        Dexie store, mutation queue, optimistic PR check, unit conversion
Playwright    the acceptance criteria in §30, including an offline run driven
              by CDP Network.emulateNetworkConditions
Locust/k6     the 20k-set fixture against §26 latency budgets
```

The §30 acceptance criteria are written as Playwright test names before the
features they describe. A1–A14 are the definition of done, not a summary of it.

### D15. Migrations are Alembic, and every one has a down.

No schema change without a migration; no migration without a tested
downgrade. The seed loader is idempotent and separate from migrations.

### D21. The interface is a HUD, and the colour rules are computed, not judged.

The app is a training instrument, so it reads like one: a faint grid ground,
corner-bracketed panels, monospace tabular readouts, full-bleed layout rather
than a narrow column.

The colour decisions were run through a validator rather than eyeballed, and
two of them changed as a result:

```text
The ten-hue rank ladder FAILED - #e879f9 against #a78bfa is a Delta E of 0.4
  for a protan viewer, which is invisible. Replaced with four validated
  accents, escalating, with the level number and name always beside them.
The training heatmap is a MAGNITUDE encoding, so it is one hue on a
  sequential ramp: monotone lightness, adjacent gaps >= 0.06, light end
  clearing the surface. Validated: all checks pass.
```

The lesson worth keeping: a palette that looks fine is not evidence. Both of
these read well on my screen and one of them was unreadable.

*Superseded by D23 for the look.* The validation rule survives: the new
heatmap ramp was checked the same way (monotone OKLab lightness, adjacent
gaps >= 0.08).

### D22. The product surface is a requirement, not decoration.

Everything through D21 made the app *correct*. It still read as something built
for one person: the signed-out page was three sentences and two buttons, the
dashboard never mentioned the 960-exercise catalogue it was sitting on, and
there was no title template, favicon, footer or attribution anywhere.

```text
A landing page that says what the product is before asking for an account.
The exercise library surfaced on the dashboard - browsing is how people find
  movements they did not know to search for.
Title template, favicon, Open Graph metadata, footer with attribution and
  the Sec 31 disclaimer.
Copy written for a stranger.
```

The HUD aesthetic stays - it is deliberate and it suits a training instrument.
What changed is that it now explains itself.

### D23. The gym deployment: one config file, one photo folder.

The app now runs as the member app and website of a single gym, shown as
**YOUR GYM** until a real name goes in. Everything gym-specific lives in
`web/src/lib/gym.ts` and `web/public/gym/`:

```text
Name, contact, hours, plans, prices, timetable, facilities, FAQ - gym.ts.
Derived values are computed, never typed twice: the annual price, the
  per-session PT price, "classes a week", "days open", the open/closed badge.
Photos are addressed by fixed file names, so replacing a stock image with a
  real one is a file copy, not a code change.
New members start with the gym's equipment list (GYM_EQUIPMENT), so the
  equipment-aware catalogue matches the gym floor with no setup step.
```

The HUD look from D21 is replaced: a deep indigo ground with a pink-orange-
yellow gradient accent, Anton for display type and Inter for text, and a gym
photo fixed behind every page under a dark wash.

Before designing the public site I fetched and parsed the homepages of 211
gym websites; 108 were real gym sites that returned readable HTML. The
features they share (a join call to action, pricing, class timetable,
personal training, FAQ) became the section list in spec 30C.1. What few of
them do (opening hours on the homepage, stated cancellation and freeze
terms, progress tracking) became the facts bar, the terms beside the
prices, and the member app section.

### D24. Support requests are user-owned; the staff inbox is the one exception.

```text
support_tickets carries user_id and is in the guard's USER_OWNED_TABLES, so
  the member side goes through TicketRepo like every other member table.
Staff need to read across members. That happens in exactly one place,
  StaffInbox, and every cross-member statement there is wrapped in
  unscoped("reason") - the exception is greppable, not ambient.
The staff flag is set from the command line (make staff email=...), not
  through an endpoint. An API that can grant staff is an API that can be
  talked into granting staff.
Staff endpoints return 403 to members. The member endpoints keep returning
  404 for another member's ticket (23.1, no enumeration).
```

### D25. Enquiries are public; referral codes need no new column.

```text
POST /leads takes no session - the visitor is not a member yet. Spam is
  handled with a honeypot field: a filled honeypot gets a 201 and nothing is
  stored, so a bot learns nothing.
A referral code is the first 8 hex characters of the member's UUID. It is
  short enough to read out, needs no column or migration, and resolves with
  one prefix query. An unknown code is ignored rather than rejected, so a
  typo never costs the visitor their enquiry.
Payment is out of scope. A membership enquiry records the plan the visitor
  chose; staff complete the membership.
```

### D26. Members never see how the AI is wired.

Revision 5 of the spec reverses 21.6's "visibly disabled with a reason". For
a gym's member app, "AI not configured - plans are built from rules" and an
environment-variable name are noise at best. So:

```text
The coach page is a "Workout builder". It never shows provider, budget or
  source. Fallbacks and provider errors go to the geektrainer.ai log.
The rules path still runs whenever the AI does not, so A9 holds - it is
  just silent.
Streak levels were renamed from anime references to plain tiers.
All member-facing copy was rewritten in plain language (spec 30C.7).
```

Related fix: the console email sender logged at INFO with no handler
attached, so password-reset links never appeared anywhere in development.
The app now attaches a handler for `geektrainer.mail` in development.

### D16. Deferred, explicitly.

```text
Nutrition, social, wearables, coach accounts, video form analysis  — spec §29.1
Periodization / deload logic          — open question §32 Q5; revisit after
                                        real usage data exists
Multi-device concurrent editing       — §32 Q4; LWW until a user complains
Native apps                           — the PWA is the answer for v1
Media re-hosting                      — blocked on §32 Q1, hot-link until then
```

### D19. The web app reaches the API through a same-origin proxy.

`next.config.mjs` rewrites `/api/*` to the FastAPI origin, so the browser only
ever talks to one origin.

```text
The session cookie needs no SameSite negotiation and no CORS preflight.
There is no window where a misconfigured CORS origin silently breaks auth.
Production swaps the rewrite target for the deployed API; nothing else moves.
```

The API still sets permissive CORS for direct use (curl, /docs), but the app
does not rely on it.

### D20. Next 15 with an explicit postcss bump, not Next 16.

Next 16 requires Node 20; this machine runs Node 18. Rather than pull in a
second runtime, the app pins Next 15.5.24 and bumps `postcss` to `^8.5.6`
directly, which clears the advisories that would otherwise have forced the
major upgrade. `npm audit` reports zero vulnerabilities.

Revisit when Node here moves to 20+.

### D17. The development and test database is a Python wheel, not Docker.

`pgserver` ships real PostgreSQL 16 binaries in a wheel. `scripts/devdb.py`
starts one against `.pgdata/`, and the test suite starts its own against
`.pgdata-test/`.

```text
No Docker daemon, no apt, no sudo, no system service.
The version is pinned by a Python dependency like everything else.
The test suite builds its schema by running the real migrations, so a
  migration that does not apply fails the suite.
```

This replaces the `docker-compose.yml` named in D1. It was forced — this
machine has neither Docker nor passwordless sudo — but it is the better default
regardless: a contributor with Python and nothing else can run the whole stack.

Production still runs a managed Postgres; nothing in the app knows the
difference, because the only coupling is a URL.

### D18. Synchronous SQLAlchemy, not async.

FastAPI runs sync handlers in a threadpool. Every request here is a handful of
indexed queries against a database on the same network; there is no fan-out to
slow external services on the request path — the AI calls are the exception and
they are already their own endpoints.

Async would buy nothing measurable and would cost the greenlet debugging, the
two-coloured repo layer, and the async test fixtures. If a Phase 7 endpoint
turns out to need concurrency, it can be async on its own.

---

## Architecture

```text
Geek-Trainer/
├── SPECIFICATIONS.MD
├── PLAN.md
├── ERRORS-AND-FIXES.md          # kept as problems are hit
├── docker-compose.yml           # postgres
├── Makefile                     # dev, seed, types, test, migrate
├── api/
│   ├── core/
│   │   ├── formulas.py          # D7 — pure, no I/O
│   │   ├── recompute.py         # D6 — pure over a set list
│   │   └── units.py
│   ├── domain/                  # SQLAlchemy models + Pydantic schemas
│   ├── routes/                  # one module per §23 group
│   ├── repo/                    # every query; user_id enforced here (D9)
│   ├── sync/                    # D3 — mutation types and handlers
│   ├── ai/
│   │   ├── client.py            # D10 — LLMClient protocol + fake
│   │   ├── candidates.py        # D11
│   │   ├── schemas.py           # structured-output contracts
│   │   ├── validate.py          # §21.3 pipeline
│   │   └── fallback.py          # D12
│   ├── ingest/                  # §5.1 staging → validate → swap
│   ├── seeds/exercises.json     # D5
│   └── migrations/              # D15
├── web/
│   ├── src/db/                  # D2 — Dexie schema, mutation queue, sync
│   ├── src/core/                # formulas mirrored from D7 constants
│   ├── src/api/types.ts         # D13 — generated
│   ├── src/features/
│   │   ├── session/             # the logging screen — the product
│   │   ├── plan/  exercises/  progress/  ai/
│   └── src/ui/                  # primitives
└── tests/
    ├── e2e/                     # §30 A1–A14
    └── fixtures/                # 20k-set perf fixture
```

**The one screen that matters** is `web/src/features/session/`. It is built
first among the UI, tested hardest, and no other feature is allowed to make it
slower.

---

## Phases

Each phase is shippable and independently verifiable. The acceptance criteria
each phase closes are named.

### Phase 1 — Foundation

```text
docker-compose Postgres, Alembic, FastAPI skeleton, Next.js PWA shell.
Auth: register, login, logout, me, password reset (D9).
Profile + settings: units, timezone, week start, equipment, increments (§3, §4).
Bodyweight log.
The repo layer with user_id enforcement, and the test that proves it.
```

Closes: **A10**, **A11** (storage half).
Done when: two users exist and neither can see anything of the other's,
proven per endpoint.

### Phase 2 — Exercise catalogue

```text
exercises schema, canonical equipment/muscle mapping tables.
Seed loader from api/seeds/exercises.json (D5).
Ingest job: fetch → normalize → stage → validate → swap (§5.1).
GET /exercises with all filters, cursor pagination, trigram search.
Custom exercises (§5.4).
Web: exercise browser, detail view, lazy media, offline mirror in Dexie.
```

Closes: **A1**.
Done when: the equipment filter is set-containment, proven by a test that a
barbell-only user is not offered a barbell+bench exercise.

### Phase 3 — Plans and the weekly schedule

```text
workout_plans + workout_exercises, full CRUD, reorder, move between days.
Archive-not-delete when a session references a plan (§7.2).
Web: week view, plan editor, drag reorder with a keyboard alternative.
```

Done when: a full week can be built, edited and reloaded, offline-readable.

### Phase 4 — Sessions and set logging (the load-bearing phase)

```text
Session start with plan snapshot (§7.1), finish, cancel, resume (§8.2).
Ad-hoc sessions with no plan (§8.3).
Set CRUD with all metric types (§10.2), set types, RIR/RPE/failure.
Supersets (§10.5).
Rest timer on wall-clock (§11.3). Wake lock (§11.4).
Web: the logging screen — prefilled sets, steppers, numeric keypad, undo,
     last-session panel, one-handed layout.
```

Closes: **A4**, **A5**, **A7**, **A13**.
Done when: a real workout can be logged on a phone without frustration. This is
tested by logging one, not by reading the code.

### Phase 5 — Offline and sync

```text
Dexie stores, mutation queue, optimistic writes, background drain (D2, D3).
POST /sync with idempotent replay.
Sync status UI. Tombstones. LWW reconciliation.
Playwright offline run.
```

Closes: **A2**, **A3**.
Done when: a session logged with the network disabled, then reconnected —
and every mutation force-replayed — produces exactly one session server-side.

### Phase 6 — Derived data, history, PRs, charts

```text
recompute() (D6), session summaries, PR detection and revocation.
Progress endpoints: exercise, muscle, workout, overall; adherence and
  consistency as defined in §14.
Web: history list and detail, exercise progression, charts (Recharts,
  360px-first, light and dark).
20k-set fixture and the perf run.
```

Closes: **A6**, **A12**, **A14**.
Done when: deleting a PR-setting set restores the previous best everywhere,
and the perf fixture stays inside the §26 budgets.

### Phase 7 — AI

Built in this order, each shipping on top of a working deterministic version
(D12):

```text
7a  Substitution — SQL candidates, then AI ranking and explanation.
7b  Generation   — rules-based generator, then AI selection over candidates
                   (D11), the §21.3 validation pipeline, the proposal-and-
                   confirm UI (§17.2).
7c  Analysis     — backend-computed series, then AI narration with the
                   observation/interpretation split (§19).
7d  Chat         — streaming, intent routing into 7a–7c.
Cross-cutting: rate limits, token budget, caching, budget display (§21.5),
               safety-boundary system prompt and adversarial tests (§31).
```

Closes: **A8**, **A9**.
Done when: with `ANTHROPIC_API_KEY` unset, every flow still works and the UI
says why AI is unavailable.

### Phase 8 — Polish before calling it v1

```text
Data export and account deletion (§25).
Accessibility pass against §26 (keyboard, screen reader, contrast).
Empty states and error copy (§27).
iOS PWA storage-limit testing — the one that will surprise us.
```

---

### Phase 9 — Gym deployment

```text
Migration: users.is_staff, support_tickets, leads.
API: member tickets, public leads, referral code, staff inbox.
Web: gym website (home page), /join, /classes, /support, /staff,
  /forgot and /reset, bottom tab bar on phones, gym-wide restyle,
  plain-language copy throughout.
Tests: tests/test_tickets.py (15) - privacy of tickets between members,
  staff-only access, reply and status flow, urgent-first ordering, status
  filter, honeypot, referral credit, membership plan capture, export.
Checked in a real browser: sign-up, raising a request, log-in, wrong
  password, forgot -> email link -> new password -> log-in, staff inbox,
  and no sideways scrolling at 390px.
```

## Cross-cutting requirements

Applied in every phase, not deferred to Phase 8:

```text
Every user-owned query goes through repo/ and carries user_id (D9).
Every weight is Decimal/NUMERIC and stored in kg (D7).
Every new endpoint gets an ownership test.
Every mutation type is idempotent (D3).
No feature may make the logging screen slower — measured, not assumed.
Anything surprising enough to cost an hour goes into ERRORS-AND-FIXES.md.
```

---

## Verification

```text
make test        pytest + vitest
make e2e         Playwright, including the offline run
make perf        20k-set fixture against §26 budgets
make types       regenerate web/src/api/types.ts; CI fails if it drifts
```

The §30 acceptance criteria are the release gate. A phase is not done because
its code exists; it is done when the criteria it closes pass.

---

## Status

**Complete.** All eight phases done; the fourteen acceptance criteria in
`SPECIFICATIONS.MD` Sec 30 pass.

```text
Phase 1  Foundation ................ done
Phase 2  Exercise catalogue ........ done, including the WGER ingest
Phase 3  Plans and schedule ........ done
Phase 3A Streaks and dashboard ..... done (Sec 30A, added on request)
Phase 4  Sessions and set logging .. done
Phase 5  Offline and sync .......... done
Phase 6  Derived data and charts ... done
Phase 7  AI ....................... done
Phase 8  Polish ................... done
Phase 9  Gym deployment ........... done (spec 30C, revision 5)
```

```text
256 tests in the default run, plus a 6-test 20,000-set performance run.
960 exercises, 273 with demonstration images.
Run it: make dev, then http://localhost:3000
```

Acceptance criteria:

```text
A1  equipment set containment ............ tests/test_exercises.py
A2  session survives the app dying ....... tests/test_sessions.py
A3  offline replay is not a duplicate .... tests/test_sync.py
A4  plan edits never rewrite history ..... tests/test_sessions.py
A5  bodyweight and time-based work ....... tests/test_formulas.py, test_sessions.py
A6  deleting a PR set restores the best .. tests/test_progress.py
A7  warm-ups excluded but logged ......... tests/test_progress.py
A8  invented exercises are rejected ...... tests/test_ai.py
A9  everything works with AI off ......... tests/test_ai.py
A10 no cross-user access ................. tests/test_ownership.py
A11 unit switch changes no stored value .. tests/test_formulas.py, test_profile.py
A12 late sessions land in the local day .. tests/test_progress.py
A13 keyboard and screen-reader operable .. built in: labelled inputs, visible
                                           focus, aria-expanded/pressed/live,
                                           no drag-only or hover-only controls.
                                           NOT yet verified with a real screen
                                           reader - see below.
A14 correct and fast at 20,000 sets ...... tests/test_performance.py
```

## Media coverage

```text
960 exercises. 338 carry a demonstration (35%), of which 84 have more than
one angle and 54 have a video clip. The hand-written seed catalogue - the
movements people actually log - sits at 70 of 134 (52%).

That is the ceiling for wger.de, which holds 374 images and 78 clips in
total. Going further needs a second source; ExerciseDB has far more, and
needs an API key. Where there is no demonstration the page says so and
offers a video search rather than showing a broken frame.
```

## Not verified, and worth saying plainly

```text
A13 is built for but not proven. The markup is right - every input is
    labelled, focus is visible, state is announced - but nobody has driven
    this with VoiceOver or NVDA, and that is the only way to know.
iOS PWA storage limits are untested. IndexedDB on iOS Safari is evictable
    under pressure, which is exactly the case the offline queue exists for.
The AI path has never run against a real model. Every AI test uses the fake
    client by design; the request shape is written to the current API but the
    first real call will find something.
Adherence is null rather than computed - it needs planned-vs-completed
    sessions, which only becomes meaningful once someone uses the schedule
    for a few weeks.
```

Open questions from `SPECIFICATIONS.MD` Sec 32:

```text
Q1 (exercise data licensing)  settled for this build - personal and
                              non-commercial. Media comes from wger.de under
                              CC-BY-SA. Revisit before any release.
Q2 (LLM budget per user)      a conservative default of 40 requests/day is in
                              place; tune when there is real usage.
Q3 (email provider)           not blocking - EmailSender protocol with a
                              console implementation.
Q4 (multi-device)             deferred by D16; last-write-wins stands.
Q5 (periodization)            deferred by D16.
Q6 (hosting)                  still open; the ingest job needs a scheduler.
Q7 (loaded carries)           still open; carries record distance and lose
                              their load.
```
