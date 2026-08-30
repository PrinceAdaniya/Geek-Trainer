# Geek-Trainer — Errors and Fixes

A running log of problems that cost real time, and what actually fixed them.
One entry per problem, newest last, labelled `E1`, `E2`, … so `PLAN.md` and code
comments can cite them.

Write an entry when a problem was **surprising** — a wrong assumption, a library
behaving differently than documented, an environment quirk. Not for ordinary
bugs caught by a test.

Format:

```text
## E1. One-line summary

**Symptom:** what was observed.
**Cause:** what was actually wrong.
**Fix:** what resolved it.
**Lesson:** what to do differently next time, if anything.
```

---

## E1. Failed login attempts were rolled back with the 401, so rate limiting never fired

**Symptom:** `test_rate_limited_after_repeated_failures` got twelve `401`s and
never a `429`. The rate-limit code and its query were both correct.

**Cause:** `get_db` runs one transaction per request — commit on success,
**roll back on any exception**. A failed login records the attempt and *then*
raises `NotAuthenticated`, so the insert was rolled back along with the request.
The attempts table was empty on every read, and the counter never reached the
threshold.

**Fix:** `repo.users.record_login_attempt` opens its own session and commits
there, independently of the request transaction.

**Lesson:** anything that must survive a failed request needs its own
transaction. Worth re-checking wherever a security or audit record is written
on a path that then raises — rate limiting, lockouts, audit logs, and the AI
budget counter in Phase 7 all have this shape.

---

## E2. `pgserver` shut the database down as soon as the starting process exited

**Symptom:** `scripts/devdb.py start` printed a URL, but the next command failed
with `connection to server on socket ... failed: No such file or directory`.

**Cause:** `pgserver.get_server()` defaults to `cleanup_mode='stop'` — it stops
the server when the last handle is closed, which for a one-shot script is
immediately.

**Fix:** `cleanup_mode=None` in `scripts/devdb.py` for `start`, so the dev
database outlives the process that started it. The test harness keeps the same
setting and uses a separate `.pgdata-test` directory.

**Lesson:** none beyond the flag — but it is the first thing to check if the dev
database ever seems to vanish between commands.

---

## E3. The user_id guard passed every query, because `user_id` is always in a SELECT

**Symptom:** `test_an_unscoped_read_of_a_user_owned_table_raises` did not raise.
The guard was installed and running; it just never objected to anything.

**Cause:** the check was `if "user_id" in sql`. Every `SELECT` of a user-owned
table lists `user_id` in its *column list*, so the substring was always present
and the guard approved every statement — including the completely unscoped
`SELECT * FROM bodyweight_log` it exists to catch.

**Fix:** inspect the predicate, not the statement. Split on `WHERE` and look for
`user_id` there; for `INSERT`, look in the inserted column list; no `WHERE` at
all on a user-owned table is a violation.

**Lesson:** a safety net that never fires looks identical to a safety net that
works. The test that proves it *rejects* the bad case is the one that matters —
if it had only tested the allowed case, this would have shipped.

---

## E4. The guard then rejected every ORM write

**Symptom:** with E3 fixed, updating a bodyweight entry raised
`UnscopedQueryError` on `UPDATE bodyweight_log SET ... WHERE bodyweight_log.id = %(id)s`.

**Cause:** SQLAlchemy's unit of work flushes a loaded object with a primary-key
predicate. It never adds `user_id`, and it should not — the row was already
loaded through a scoped read.

**Fix:** the guard allows `UPDATE`/`DELETE`/`SELECT` addressing one row by that
table's own `id`. This is written down in `app/repo/guard.py` as a deliberate
limit: the guard defends against queries that **fan out across users**; a
statement addressing one row by a primary key the caller already holds is the
IDOR question instead, and that is covered by the A10 endpoint tests.

**Lesson:** don't fight the ORM's unit of work. Decide what a guard is *for*,
state the gap in the guard itself, and cover the gap with a different test.

---

## E5. A weight read back differently than it was written

**Symptom:** `POST /profile/bodyweight` with `72.5` returned `72.5`, but reading
it back afterwards returned `72.500`.

**Cause:** the response was built from the in-session Python object, which held
the value as typed. Only after a database round-trip did it become
`NUMERIC(7,3)`.

**Fix:** `core.units.to_storage` quantizes to the column's precision, so the
value is identical before and after the round-trip.

**Lesson:** normalize at the storage boundary, not in the reader. Otherwise
every client has to re-normalize what the server should have settled — and the
offline client in Phase 5 would have compared its local value against a
differently-formatted server value and seen a conflict that was not one.

---

## E6. `TRUNCATE ... CASCADE` wiped the table the exclusion list was protecting

**Symptom:** every exercise test returned an empty catalogue. The seed loader
reported `134 created` and `ingest_runs` had rows, but `select count(*) from
exercises` was `0`.

**Cause:** test teardown truncated every table *except* `exercises` — with
`CASCADE`. Cascade follows foreign keys, and `exercises.owner_user_id`
references `users`. Truncating `users` therefore truncated `exercises` too,
exclusion list or not.

**Fix:** teardown uses `DELETE FROM` on the listed tables, with
`session_replication_role = replica` to skip foreign-key ordering.

**Lesson:** `TRUNCATE ... CASCADE` does not respect a list of tables you meant
to keep — it respects the foreign-key graph. Any table reachable from a
truncated one goes with it, silently.

---

## E7. A NUMERIC value read back differently than it was written — again

**Symptom:** creating a bodyweight custom exercise returned
`bodyweight_load_factor: 1`, but reading it back gave `1.000`.

**Cause:** the same shape as E5, in a second column. The response was built
from the in-session object before the `NUMERIC(4,3)` round-trip.

**Fix:** `core.formulas.quantize_factor`, applied on create and update, beside
the existing `quantize_kg`.

**Lesson:** E5's lesson was right but under-applied. Every `NUMERIC` column
needs a quantizer at the write boundary, not just the one that happened to have
a test. Worth a sweep when Phase 4 adds `weight_kg` on sets.

---

## E8. The guard read the table `sets` inside the column `planned_sets`

**Symptom:** every workout-plan query started failing with
`UnscopedQueryError: statement touches ['sets'] without a user_id predicate` —
on statements that never touched the sets table at all.

**Cause:** `_tables_in` did a plain substring test, and Phase 4 added a table
literally named `sets`. `workout_exercises.planned_sets` contains it. So did
`planned_reps_min`? No — but `planned_sets` was enough to break every plan
read the moment the table existed.

**Fix:** match table names on word boundaries. `_` is a word character, so
`\bsets\b` does not fire inside `planned_sets`.

**Lesson:** the third bug in this file caused by substring-matching SQL (E3 was
the first). Short table names are landmines for text-based analysis; the guard
now compiles a real pattern per table. If a future table is named `set`,
`user`, or `plan`, check this first.

---

## E9. The ORM's eager loads look exactly like unscoped queries

**Symptom:** with the guard fixed, loading a session raised
`UnscopedQueryError` on `SELECT ... FROM sets WHERE session_exercise_id IN (...)`.

**Cause:** `selectinload(session.exercises).selectinload(SessionExercise.sets)`
emits a second query keyed only on the parent ids. There is no `user_id` in it,
and there should not be — the parents were already loaded through a scoped
query.

**Fix:** `PARENT_SCOPED_KEYS` in the guard names, per table, the foreign keys
that pin a statement to a parent the caller already holds. Deliberately short
and justified in place, with the same reasoning as the primary-key exemption
(E4): the guard catches statements that *fan out* across users; pinned
statements are the IDOR question, covered by the A10 isolation tests.

**Lesson:** a guard over generated SQL has to account for what the ORM
generates, not just what you write. Each exemption needs to be listed and
argued rather than discovered by loosening the check until tests pass.

---

## E10. A stale relationship made an added exercise vanish

**Symptom:** `POST /sessions/{id}/exercises` returned 201 with the exercise
saved, but the session in the response had an empty `exercises` list. Reloading
the page showed it correctly.

**Cause:** the route re-queried the session after the insert, but SQLAlchemy's
identity map returned the same object with its already-loaded `exercises`
collection. A re-query is not a refresh.

**Fix:** `db.expire(session, ["exercises"])` after add, remove and reorder.

**Lesson:** after mutating a collection through anything other than the
relationship itself, expire it. Re-issuing the query is not enough — and the
symptom (right in the database, wrong in the response) points at the API layer
rather than at the ORM, which is where the time went.

