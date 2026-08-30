# Geek-Trainer

A training tracker built around one constraint: it is used **in a gym,
one-handed, mid-set, on a phone, often with no usable network.** Everything
else in the design follows from that.

Tell it what equipment you own and it only ever offers exercises you can
actually load. Log every set on its own — weight, reps, RIR, whether you hit
failure. Keep the streak alive and the power level climbs.

## Running it

Needs Python 3.12 and Node 18.18+. **No Docker, no sudo, no system Postgres** —
`pgserver` ships PostgreSQL 16 in a Python wheel.

```bash
make devdb        # start a local Postgres in .pgdata/
make migrate      # build the schema
make seed         # 134 hand-written exercises
make ingest       # optional: +826 exercises and 273 images from wger.de
make api          # http://localhost:8000  (docs at /docs)
make web          # http://localhost:3000
```

Or `make dev` for all of it at once. Then open **http://localhost:3000**.

```bash
make test         # 241 tests
make perf         # the 20,000-set performance run (A14)
make typecheck    # the web app
```

The AI assistant is optional. With no `ANTHROPIC_API_KEY` set, plan generation,
substitution and analysis all still work — each has a deterministic
rules-based path, and the UI says why AI is off rather than breaking.

## Layout

| Path | What it is |
|---|---|
| `api/app/core/` | Pure helpers: formulas, units, clock, ids, security. No I/O. |
| `api/app/domain/` | SQLAlchemy models and the Pydantic schemas that are the API contract. |
| `api/app/repo/` | Every query. `guard.py` enforces that user-owned tables are never read unscoped. |
| `api/app/services/` | Auth, set validation, offline sync, recompute. |
| `api/app/ai/` | The LLM boundary, candidate retrieval, validation, deterministic fallbacks. |
| `api/app/ingest/` | Canonical mapping, the seed loader, the WGER fetcher. |
| `api/seeds/` | `catalogue.py` (source) → `exercises.json` (validated build). |
| `web/src/lib/` | API client, session, offline outbox, units mirrored from the backend. |
| `web/src/components/` | HUD primitives, charts, set entry. |

`SPECIFICATIONS.MD` is the product spec. `PLAN.md` is the build plan and the
reasoning behind every decision, labelled D1–D21 and cited from the code.
`ERRORS-AND-FIXES.md` is every bug that cost real time, with what it taught.

## What it does

- **Equipment-aware catalogue** — 960 exercises. The filter is set containment,
  so barbell + bench is never offered to someone who owns only a barbell.
  Incompatible movements can be shown greyed, with the missing kit named.
- **Weekly schedule** — plans are templates; starting a session snapshots the
  plan, so editing or deleting it later cannot rewrite what you did.
- **Set-level logging** — metric-aware, so a plank takes seconds, a push-up
  refuses a weight and an assisted pull-up carries a negative load. Rest timer
  and session clock run off wall-clock time, so they survive the screen
  sleeping. Screen wake lock while training.
- **Offline** — sets are written locally and queued; a forced replay of an
  entire offline session is a no-op, never a duplicate.
- **Progress** — volume, per-muscle sets, estimated-1RM trends and personal
  records, all recomputed from the log, so correcting a mistyped set revokes
  the record it wrongly set.
- **Streaks and power levels** — ten ranks, a charge meter to the next, and a
  power-up when you cross a threshold.
- **AI** — plan generation, substitution and analysis, constrained to exercise
  ids the backend supplied, proposing rather than writing.

## Status

All eight phases complete; the fourteen acceptance criteria in
`SPECIFICATIONS.MD` §30 pass. See `PLAN.md` for what is deliberately deferred.
