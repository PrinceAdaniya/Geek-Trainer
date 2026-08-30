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
