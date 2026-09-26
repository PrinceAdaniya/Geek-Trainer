# Geek-Trainer — Specification

> Revision 5 — 2026-09-26. See §33 for the revision log.
> Sections marked **Rationale** record a decision that is not obvious from the
> requirement itself; they exist so the reasoning survives implementation.

## 1. Product Definition

Geek-Trainer is a fitness training application that allows users to:

- Define available equipment.
- Select muscles/body parts and training goals.
- Discover compatible exercises from an exercise database.
- Use AI to interpret requests and generate personalized training plans.
- Create a weekly training schedule.
- Start individual workout sessions from the schedule.
- Add exercises and record every set individually.
- Track reps, weight, effort, failure/RIR and other set-level data.
- Track historical performance and progress over time.
- Review completed sessions and exercise progression.

The system combines **structured exercise data + deterministic tracking +
AI-assisted planning and answers**.

From revision 5 the app is deployed as the member app of a single gym, shown
under a placeholder name (**YOUR GYM**). Around the tracker sit a public club
website, member support requests, visitor enquiries and a staff role. See §30C.

### 1.1 Primary use context

The app is used **in a gym, one-handed, mid-set, on a phone, frequently with no
usable network**. Every requirement in this document is subordinate to that:
if a feature cannot be operated in ten seconds between sets on a dead
connection, it is designed wrong.

Three consequences are binding requirements, not preferences:

```text
1. Set logging must work fully offline and sync later.   (§12)
2. Logging a set must never block on a network round-trip. (§12, §26)
3. The app must remain completely usable with AI disabled or unavailable. (§21.6)
```

**Rationale:** AI is a core feature, but it is an *assistive* layer over a
deterministic tracker. A missing LLM key, an API outage or an exhausted budget
must degrade the product, never break it.

---

## 2. Core User Flow

```text
User Profile
    ↓
Equipment + Goals
    ↓
Exercise Database
    ↓
AI Training Assistant
    ↓
Weekly Schedule
    ↓
Workout Session
    ↓
Exercise
    ↓
Set-by-Set Logging
    ↓
Workout Completion
    ↓
Progress History
    ↓
AI Analysis / Answers
```

Every step after "Weekly Schedule" must be reachable without the AI step.

---

## 3. Units, Time and Locale

Defined before everything else because volume, personal records, charts,
schedules and streaks all depend on it.

### 3.1 Weight units

```text
Storage unit:   kilograms, always.
Display unit:   user preference — kg or lb.
Conversion:     1 lb = 0.45359237 kg (exact).
```

Numbers are stored as `NUMERIC(7,3)` kg, never floats, and converted only at
the presentation boundary.

**Rationale:** storing whatever the user typed makes every aggregate query
unit-aware and makes a user who switches units corrupt their own history.

### 3.2 Rounding and increments

Display rounds to the nearest sensible increment for the unit and equipment:

```text
kg: 0.5 kg default, 1.25 kg for barbell (plate pairs), 2.5 kg for stack machines
lb: 5 lb default, 2.5 lb for dumbbell, 5 lb for barbell
```

The increment is a user-editable preference per equipment type, and it drives
the +/- steppers in the logging UI and any weight the AI or progression logic
suggests. Never suggest a load the user cannot physically build.

### 3.3 Time

```text
Every timestamp is stored UTC, ISO-8601, with timezone offset preserved.
User profile carries an IANA timezone (e.g. "Asia/Kolkata").
"Today", "this week" and "this month" are evaluated in the user's timezone.
Week start is a user preference; default Monday (ISO-8601).
```

**Rationale:** a 11 pm session in one timezone and a "weekly volume" chart
computed in UTC disagree about which week it belongs to. Streaks and adherence
break silently.

### 3.4 Bodyweight

Bodyweight is a **time series**, not a profile field:

```text
bodyweight_log(user_id, date, weight_kg, source)
```

The value in effect on a session's date is used for bodyweight-load
calculations (§13.2). The profile shows the most recent entry.

---

## 4. User Profile

Store:

```text
user_id
name
email
age (optional)
sex (optional, affects nothing but AI phrasing; never required)
training_experience     (beginner | intermediate | advanced)
training_goals          (strength | hypertrophy | endurance | general | fat_loss)
available_equipment     (canonical ids, multi-select)
preferred_training_days
preferred_session_duration_minutes
unit_preference         (kg | lb)
timezone                (IANA)
week_start              (monday | sunday)
default_rest_seconds
injury_notes (free text, shown to the user; see §31 for AI handling)
created_at / updated_at
```

Equipment must use canonical identifiers:

```text
dumbbell
barbell
bench
cable
machine
smith-machine
pull-up-bar
dip-bars
kettlebell
resistance-band
ez-bar
medicine-ball
stability-ball
bodyweight
```

Users can select multiple equipment items. `bodyweight` is always implicitly
available and cannot be deselected.

Every equipment identifier coming from the exercise data source must map into
this canonical list through an explicit, tested mapping table (§5.3). An
unmapped value is a data error surfaced in a report, never silently dropped.

---

## 5. Exercise Data

### 5.1 Source and mirror

Primary data source: **ExerciseDB / AscendAPI**, with **WGER** as an
alternative or supplementary source.

The application must **not** call the third-party API on the user request path.

```text
Third-party API
      ↓  (scheduled ingest job, manual trigger available)
Normalization + canonical equipment/muscle mapping
      ↓
Local exercises table  ← the only thing the app and the AI ever read
```

Requirements:

```text
Ingest runs as an offline job, versioned by ingest_run_id.
Every exercise row records source, source_id, source_version, ingested_at.
A failed or partial ingest never replaces a good dataset (write to a staging
  table, validate row counts and required fields, then swap).
The app boots and serves a full exercise catalogue with the network unplugged.
```

**Rationale:** the original spec made a rate-limited, paid third-party API a
hard runtime dependency for search, AI generation and validation. One outage
would take down the whole product, and per-request calls make the AI validation
step in §21 impossibly slow.

### 5.2 Media and licensing

Exercise GIFs, images and videos are third-party assets.

```text
Record the licence/terms for each media asset with the exercise row, and
  show the attribution wherever the media is shown.
Hot-link only where the provider's terms require it; otherwise cache
  through the app's own domain with a stable URL.
An exercise may carry several stills - the detail page shows them as a
  gallery rather than discarding all but one - plus a clip where the
  source has one.
Media must be lazy-loaded and must never block exercise search results.
Every exercise must be usable with no media at all (text instructions),
  and a missing demonstration is stated rather than left as a broken frame.
Coverage will always be partial: no open catalogue illustrates every
  movement. Where there is none, offer a video search for the movement
  instead of pretending.
```

This is an open item — see §32.

### 5.3 Exercise record

```text
exercise_id            (internal, stable, ours — not the provider's)
source                 (exercisedb | wger | custom)
source_id
name
name_normalized        (for search)
aliases[]
body_part
primary_muscle
secondary_muscles[]
equipment[]            (canonical ids)
difficulty             (beginner | intermediate | advanced)
type                   (compound | isolation | cardio | mobility | other)
metric_type            (weight_reps | bodyweight_reps | weighted_bodyweight |
                        time | distance | time_distance)   ← see §10.2
bodyweight_load_factor (0..1.2, used for bodyweight volume; §13.2)
default_rest_seconds
instructions[]
image_url / gif_url / video_url
media_licence
is_custom              (user-created)
owner_user_id          (null unless is_custom)
created_at / updated_at
```

### 5.4 Custom exercises

Users can create their own exercises (a gym machine with no database entry, a
personal variation). Custom exercises:

```text
belong to one user, are private, and never enter another user's search;
carry the same fields, with metric_type and equipment required;
participate fully in logging, history, PRs, charts and AI candidate lists.
```

**Rationale:** no external database covers every gym. Without this, the first
unlisted machine forces the user into a competing app.

---

## 6. Exercise Discovery

The system must retrieve exercises based on:

```text
target muscle/body part
available equipment
difficulty
exercise type
training goal
free-text search over name + aliases
```

### 6.1 Filtering

An exercise is compatible only when:

```text
target muscle matches (primary or, if requested, secondary)
AND
every item in exercise.equipment is in the user's available equipment
```

`bodyweight` exercises require no equipment and are always compatible.

The equipment rule is **all-of, not any-of**: an exercise requiring
`barbell + bench` is not compatible for a user who owns only a barbell. This
must be a set-containment test, and it is the single most common filtering bug
in this class of app.

The user can toggle "show incompatible exercises" — they are displayed greyed
with the missing equipment named, never silently hidden with no explanation.

### 6.2 Results

Each exercise result must show:

```text
name
target muscle (primary, with secondary on detail)
equipment
difficulty
visual demonstration (lazy-loaded, optional)
instructions
your last performance, if any   ← see 11.2
```

### 6.3 Exercise detail

Every exercise has its own page, reachable from search and from a session:

```text
The demonstration at a readable size - image, GIF or video where the
  catalogue has one, and never a broken frame where it does not.
A link out to a video search for the movement, because a still image does
  not answer "am I doing this right" and the catalogue will never carry a
  clip for everything.
Full instructions, primary and secondary muscles, equipment, difficulty,
  how it is recorded, suggested rest, and its bodyweight load factor.
Your own history with the movement, and its records.
Add-to-a-workout, so looking something up leads somewhere.
Media attribution wherever a third-party image is shown.
```

Results are paginated (cursor-based, 30 per page) and searchable offline from
the locally mirrored catalogue.

---

## 7. Weekly Training Schedule

### 7.1 Template vs calendar

A weekly schedule is a **recurring template**. A session happens on a **date**.
These are separate records and the distinction is mandatory.

```text
WorkoutPlan (template, "Monday: Back + Biceps")
      ↓  start session on a date
WorkoutSession (instance, "2026-08-31, Back + Biceps")
      ↓
snapshot of the plan is copied into the session
```

**Rationale:** the original spec required both a persistent weekly schedule and
that "historical records must not be overwritten when future workouts are
edited". Those two requirements are only compatible if the session copies the
plan at start time. Without the copy, editing Monday's plan in October silently
rewrites what the user did in August.

### 7.2 Plan record

```text
workout_id
user_id
day_of_week            (monday..sunday, or null for an unscheduled plan)
name
target_muscles[]
notes
order_index
is_archived
created_at / updated_at
```

Plan exercises:

```text
workout_exercise_id
workout_id
exercise_id
order_index
planned_sets
planned_reps            (min/max range, e.g. 8–12)
planned_weight_kg (optional)
planned_rir (optional)
superset_group (optional; see §10.5)
notes
```

Example:

```text
MONDAY     Back + Biceps
TUESDAY    Legs
WEDNESDAY  Rest
THURSDAY   Chest + Shoulders
FRIDAY     Back + Arms
SATURDAY   Rest
SUNDAY     Rest
```

The user can:

- Create, edit, delete and archive workouts.
- Move workouts between days.
- Add/remove exercises.
- Reorder exercises (drag, and a keyboard-accessible alternative).
- Change planned sets/reps/weight.
- Add notes.

Deleting a plan **never** deletes sessions performed from it. A plan referenced
by any session is archived rather than hard-deleted.

The weekly schedule must persist per user and be available offline.

---

## 8. Workout Session

Each scheduled workout offers:

```text
START SESSION
```

Starting a session creates a separate workout-session record, seeded with a
snapshot of the plan.

```text
Workout Plan
      ↓
Start Session  (copies plan exercises into the session)
      ↓
Active Session
```

### 8.1 Session record

```text
session_id
user_id
workout_id             (nullable — see 8.3)
plan_snapshot          (jsonb: the plan exactly as it was at start)
name
date                   (user-local date the session belongs to)
start_time / end_time  (UTC)
status                 (planned | in_progress | completed | cancelled)
duration_seconds       (computed at finish; excludes paused time)
notes
created_at / updated_at
```

States:

```text
planned → in_progress → completed
                     ↘ cancelled
```

### 8.2 Resume and abandonment

```text
At most one session per user may be in_progress at a time.
Opening the app with an in_progress session resumes it — full state, no data loss.
An in_progress session with no new set for 6 hours prompts on next open:
  "Finish with the sets you logged", "Continue", or "Discard".
It is never auto-cancelled, and logged sets are never destroyed without asking.
```

**Rationale:** phones die, browsers get killed, people leave the gym. A tracker
that loses a half-logged session loses the user.

### 8.3 Ad-hoc sessions

`workout_id` is nullable: the user can start an **empty session** and add
exercises freely, with no plan at all. This is a first-class flow, not a
fallback.

---

## 9. Exercise Logging

During an active session, users can:

- Add exercises from the planned workout.
- Add additional exercises (search over the full catalogue, offline).
- Remove exercises (removing an exercise that has logged sets requires a
  confirm, and the sets are deleted with it).
- Reorder exercises.
- Replace an exercise (§20) — the replacement records what it replaced.
- View exercise instructions/media.
- Mark an exercise as skipped without deleting it.

Session exercise record:

```text
session_exercise_id
session_id
exercise_id
order_index
planned_sets / planned_reps       (from the snapshot, for reference)
replaced_from_exercise_id (nullable)
superset_group (nullable)
skipped (bool)
notes
```

Each exercise contains individual set records.

```text
Bench Press

Set 1: 60 kg × 10
Set 2: 60 kg × 9
Set 3: 60 kg × 8
```

---

## 10. Set-Level Tracking

Every set must be independently recorded.

### 10.1 Set record

```text
set_id            (UUIDv7, generated on the client — see §12.3)
session_id
session_exercise_id
exercise_id
set_number
weight_kg         (nullable, depending on metric_type)
reps              (nullable, depending on metric_type)
duration_seconds  (nullable)
distance_m        (nullable)
rir               (0..10, nullable)
rpe               (1..10, in 0.5 steps, nullable)
failure           (bool, default false)
set_type
rest_seconds      (actual rest taken before this set; auto-measured)
notes
performed_at      (timestamp)
created_at / updated_at / deleted_at
```

### 10.2 Metric types

Not every set is weight × reps. The exercise's `metric_type` determines which
fields are required and how volume is computed:

```text
weight_reps          weight + reps            e.g. bench press
bodyweight_reps      reps                     e.g. push-up
weighted_bodyweight  reps + added weight      e.g. weighted pull-up (weight may be negative for assisted)
time                 duration                 e.g. plank
distance             distance                 e.g. farmer's carry
time_distance        duration + distance      e.g. treadmill run
```

**Rationale:** the original spec defined `volume = weight × reps` with weight
mandatory. Under that rule a set of 12 pull-ups scores zero volume, a 90-second
plank cannot be recorded at all, and any "total volume" chart quietly
misrepresents bodyweight training.

### 10.3 Set type

```text
warmup
working
drop_set
failure
rest_pause
amrap
backoff
other
```

`warmup` sets are **excluded** from volume totals, progression charts and PR
detection, but are stored and shown in the session log. This exclusion must be
stated in the UI wherever a total is displayed.

### 10.4 Effort

```text
failure = true / false        explicit user mark
RIR     = 0,1,2,...           reps in reserve
RPE     = 1..10 in 0.5 steps  recorded independently
```

`RIR = 0` and `failure = true` are related but not synonymous; setting either
does not force the other. The UI may offer "RIR 0 → mark as failure?" as a
suggestion, never as an automatic write.

### 10.5 Supersets and circuits

Sets belonging to exercises sharing a `superset_group` within a session are
performed alternating. The logging UI groups them and moves to the next
exercise in the group after each set, and rest timing applies to the group, not
the individual exercise.

**Rationale:** supersets are ordinary training practice; without grouping, the
rest-time data recorded for supersetted exercises is meaningless.

---

## 11. Session Interface

Active workout screen:

```text
------------------------------------------------
WORKOUT: BACK + BICEPS                    24:31 ⏱

Exercise 1
Barbell Row                    last: 60×10, 60×9, 60×8

Set | Weight | Reps | RIR | Failure
------------------------------------
1   | 60 kg  | 10   | 2   | No
2   | 60 kg  | 9    | 1   | No
3   | 60 kg  | 8    | 0   | Yes

[ + Add Set ]                          rest 2:00 ▸

Exercise 2
Lat Pulldown
...

[ + Add Exercise ]

[ FINISH SESSION ]
------------------------------------------------
```

### 11.1 Speed requirements

Entering a set must be fast enough to use mid-workout:

```text
Adding a set pre-fills weight/reps from the previous set of that exercise.
One tap saves a repeat set. Editing is +/- steppers using the user's
  configured increment (§3.2), with direct numeric entry available.
Numeric inputs use inputmode="decimal" — the numeric keypad, never a
  full keyboard.
No modal, no page navigation and no network wait is required to log a set.
Undo is available for the last destructive action for 10 seconds.
```

### 11.2 Previous performance

When logging an exercise, the last session's working sets for that exercise are
always visible:

```text
LAST SESSION — Aug 24
60 kg × 10
60 kg × 9
60 kg × 8
```

Plus the current PR for the exercise, and whether the set just entered beats it
(§15).

### 11.3 Rest timer

```text
Starts automatically when a set is saved, using that exercise's default rest.
Runs off wall-clock timestamps, not an interval counter, so it stays correct
  when the screen sleeps or the tab is backgrounded.
Finishing fires a notification and a vibration where permitted; it must also
  be correct on a screen the user simply looks at again.
Skippable and adjustable. The actual elapsed rest is written to the next set's
  rest_seconds whether or not the timer was used.
```

### 11.4 Screen and input

```text
A Screen Wake Lock is held while a session is in_progress and released on
  finish, cancel or backgrounding.
Tap targets ≥ 44×44 px. The primary logging controls are reachable in the
  lower half of the screen (one-handed use).
The interface is fully operable with sweaty hands and without precise taps:
  no drag-only interactions, no hover-dependent controls.
```

---

## 12. Offline and Sync

A binding requirement, not an enhancement.

### 12.1 Capability offline

```text
Works offline:  start session, log/edit/delete sets, add exercises from the
                mirrored catalogue, finish session, view history and charts
                for locally cached data, view the weekly schedule.
Needs network:  first load, catalogue refresh, cross-device sync, all AI
                features (clearly indicated as unavailable, never silently
                failing).
```

### 12.2 Architecture

```text
Client writes to local storage first (IndexedDB), renders immediately,
and enqueues a mutation. A background sync drains the queue when online.
```

The UI shows a single, honest sync indicator: `synced` / `n changes pending` /
`sync failed — retrying`. A pending change is never presented as saved to the
server, and a failed sync never discards local data.

### 12.3 Identity and idempotency

```text
The client generates set_id / session_id / session_exercise_id (UUIDv7).
Every mutation carries an Idempotency-Key; a replayed mutation is a no-op.
Writes are upserts keyed by the client id.
```

**Rationale:** a retried "add set" over a flaky connection must not create a
duplicate set — which would silently inflate volume and fabricate PRs.

### 12.4 Conflict resolution

```text
Sets and sessions are append-mostly and single-device-per-moment: last-write-
  wins on updated_at, per record, is sufficient and must be documented as the
  chosen rule.
Deletions are tombstones (deleted_at), never hard deletes, until sync settles.
All derived data (volume, PRs, progress) is recomputed server-side after sync;
  the client's derived values are provisional and are replaced by the
  server's on reconciliation.
```

---

## 13. Automatic Tracking and Derived Metrics

When a session is completed, calculate and store:

```text
total exercises
total working sets
total reps
total volume
session duration
muscles trained (with set counts per muscle)
personal records achieved
```

### 13.1 Volume

Volume is defined per metric type, and only over non-warmup sets:

```text
weight_reps          volume = weight_kg × reps
weighted_bodyweight  volume = (bodyweight_kg × factor + added_kg) × reps
bodyweight_reps      volume = bodyweight_kg × factor × reps
time                 volume is not defined; track duration instead
distance             volume is not defined; track distance instead
```

Where a period mixes metric types, totals are reported **per metric type**.
Never sum kilograms with seconds into one "volume" number.

### 13.2 Bodyweight load

```text
effective_load = bodyweight_on_session_date × exercise.bodyweight_load_factor
                 + added_weight_kg
```

`bodyweight_load_factor` comes from a curated table (pull-up 1.0, dip 1.0,
push-up 0.64, inverted row 0.55, …), defaults to 1.0, and is editable per
exercise by the user. If no bodyweight is on record, bodyweight-based volume is
reported as unavailable rather than as zero.

### 13.3 Estimated 1RM

```text
Epley:  e1RM = weight × (1 + reps / 30)
Computed only for weight-bearing sets with 1 ≤ reps ≤ 12.
Above 12 reps the estimate is not shown — it is not reliable.
The formula is displayed to the user wherever an e1RM figure appears.
```

**Rationale:** the original spec required "estimated strength progression" and a
"Best Estimated 1RM" record without naming a formula. Two screens computing it
differently would disagree about the user's records.

### 13.4 Recomputation

Derived values are **recomputed, never patched in place**:

```text
Editing or deleting a past set re-runs derived metrics and PR detection for
that exercise from that date forward.
Recomputation is deterministic: the same set history always produces the same
derived data.
```

---

## 14. Progress Tracking

Historical progress must be available for:

### Exercise

```text
weight progression (top working set, and per-set-number)
rep progression
volume progression
estimated 1RM progression (§13.3)
personal records
```

### Workout

```text
sessions completed
session frequency
total volume
total sets
```

### Muscle

```text
training frequency (sessions per week touching the muscle)
sets performed (primary vs secondary counted separately)
volume
```

### Overall

```text
weekly training volume
monthly training volume
sessions completed
adherence   = completed sessions / planned sessions in the period
consistency = weeks in the last N with ≥ 1 completed session
personal records
```

Adherence and consistency are defined here explicitly because "consistency" is
otherwise unimplementable.

### 14.1 Charts

Progress is visualized with charts where appropriate. Requirements:

```text
Every chart states its metric, its unit and its date range.
Gaps in training are shown as gaps, not interpolated lines.
A single data point is shown as a point, not a trend.
Charts are readable in light and dark themes and do not encode meaning in
  colour alone.
Any chart must be readable on a 360 px-wide screen, or it does not ship.
```

---

## 15. Personal Records

PRs are detected automatically, per exercise, over non-warmup sets only.

Tracked record types:

```text
Heaviest Weight          max weight for ≥ 1 rep
Most Reps at a Weight    max reps at each distinct weight
Highest Session Volume   max total volume for the exercise in one session
Best Estimated 1RM       max e1RM (§13.3)
Longest Duration         time-based exercises
Furthest Distance        distance-based exercises
```

When a PR occurs:

```text
🎉 New Personal Record

Bench Press
65 kg × 10

Previous best:
62.5 kg × 10
```

Requirements:

```text
Detection runs immediately on the device (so the celebration appears during
  the session) and is confirmed server-side after sync.
A PR record stores the set_id that achieved it and the value at that time.
Deleting or correcting the set that set a PR revokes it and restores the
  previous best (§13.4).
A first-ever performance of an exercise is not announced as a PR.
PRs are per exercise, not per exercise variation name — the internal
  exercise_id is the key.
```

**Rationale:** without revocation, one mistyped `600 kg` permanently poisons the
user's records and every chart axis derived from them.

---

## 16. Workout History

Users can view completed sessions.

Each history entry:

```text
date
workout name
duration
exercises
sets
volume (per metric type)
notes
PRs achieved
```

Opening a session shows the complete original log:

```text
Exercise
 ├── Set 1
 ├── Set 2
 ├── Set 3
 └── Set 4
```

### 16.1 Immutability

```text
Historical sessions must not change when plans, exercises or profile data
  change later. This is guaranteed by the plan snapshot (§7.1) and by sessions
  referencing exercise_id plus the name as displayed at the time.
The user may still explicitly correct a past session's sets; corrections
  trigger recomputation (§13.4) and are the only way history changes.
Deleting an exercise from the catalogue must never break a past session.
```

History is filterable by date range, exercise and muscle, and is paginated.

---

## 17. AI Training Assistant

AI is a core feature.

The user can communicate naturally:

> "I have dumbbells and a bench. I want to train back twice this week."

> "Make me a 4-day hypertrophy plan."

> "What should I do instead of barbell rows?"

> "How did my bench press improve this month?"

The AI must convert natural-language requests into structured application
actions where applicable.

```json
{
  "intent": "generate_plan",
  "goal": "hypertrophy",
  "days_per_week": 4,
  "target": ["back"],
  "equipment": ["dumbbell", "bench"]
}
```

The backend then validates the request against actual exercise data and user
data.

### 17.1 AI must not invent database facts

Exercise names, equipment requirements, previous performance and historical
statistics must come from application data. Enforced structurally, not by
instruction alone — see §21.

AI may generate:

- Workout plans
- Exercise selections
- Workout explanations
- Exercise substitutions
- Training recommendations
- Progress analysis
- Answers about the user's logged training
- Natural-language summaries

### 17.2 Propose, then confirm

**No AI output writes to the database directly.** Every action-shaped AI result
is rendered as a preview the user explicitly accepts, edits or rejects.

```text
AI proposal → user reviews → user saves → data changes
```

**Rationale:** this makes hallucination a visible annoyance rather than silent
data corruption, and it means an AI outage can never leave the schedule in a
half-written state.

---

## 18. AI Workout Generation

User can request:

> "Create my workout for today."

The system considers:

```text
available equipment
weekly schedule
target muscles
training goal
training history
recently trained muscles (recovery)
exercise preferences and past substitutions
difficulty
session duration
```

The AI produces a structured workout:

```text
BACK

1. Pull-Up
   3 sets × 6-10 reps

2. One Arm Dumbbell Row
   3 sets × 8-12 reps

3. Dumbbell Pullover
   3 sets × 10-15 reps
```

Every generated exercise must be validated against the exercise database and
the user's equipment (§21.3), and is presented as a proposal (§17.2).

### 18.1 Deterministic fallback

If the LLM is unavailable, over budget or fails validation twice, the app
generates a plan with a **deterministic rule-based generator**: filter by
equipment and target muscle, order compound → isolation, cap by session
duration, respect recently trained muscles.

The result is labelled as generated without AI. This path must be implemented
and tested, not stubbed.

---

## 19. AI Progress Analysis

AI can analyze stored training history.

> "Am I getting stronger at bench press?"

> "How has my back training changed over the last month?"

> "Which exercises am I progressing fastest on?"

> "Why might my progress be slowing down?"

The AI receives structured historical data and produces an explanation based on
actual records.

```json
{
  "exercise": "Bench Press",
  "unit": "kg",
  "history": [
    {"date": "2026-08-10", "top_set": {"weight": 60, "reps": 10}, "volume": 1620, "e1rm": 80.0},
    {"date": "2026-08-17", "top_set": {"weight": 62.5, "reps": 10}, "volume": 1687, "e1rm": 83.3},
    {"date": "2026-08-24", "top_set": {"weight": 65, "reps": 10}, "volume": 1755, "e1rm": 86.7}
  ]
}
```

Requirements:

```text
All numbers in the payload are computed by the backend, never by the model.
The answer must separate observation from interpretation, visibly:
  "Your top set went 60 → 65 kg over three weeks" (data)
  vs "that suggests the current progression is working" (interpretation).
Any figure the model states must be traceable to the payload; the response is
  rendered alongside the underlying chart or table.
Insufficient data (< 3 sessions for the exercise) produces "not enough data
  yet", never a confident trend.
```

---

## 20. Exercise Substitution

During planning or a session, the user can request:

> "Replace this exercise."

Alternatives must match:

```text
target muscle (primary first, then similar movement pattern)
available equipment
training goal
similar difficulty
```

```text
Barbell Row
      ↓
Alternative
      ↓
One Arm Dumbbell Row
```

Requirements:

```text
Candidates come from a deterministic database query; the AI only ranks and
  explains them. Substitution therefore works with AI unavailable.
The replacement must exist in the exercise database and pass the equipment
  filter (§6.1).
A substitution inside a session records replaced_from_exercise_id, so history
  shows what was planned and what was actually done.
Repeated substitutions of the same exercise are remembered as a preference and
  feed future generation (§18).
```

---

## 21. AI Architecture and Guardrails

```text
Frontend
   ↓
AI Endpoint (auth, rate limit, budget check)
   ↓
Context assembly (retrieval from DB — candidate exercises + user's own data)
   ↓
LLM with structured output / function calling
   ↓
Structured Intent
   ↓
Schema validation → exercise validation → equipment validation
   ↓ (fail → one repair attempt → deterministic fallback)
Proposal returned to user
   ↓
User confirms
   ↓
Backend writes
```

### 21.1 Retrieval-constrained generation

The model is given a **candidate list of exercise ids** already filtered by the
user's equipment and the target muscles, and may only select from that list. A
returned id outside the candidate set is a validation failure, not a warning.

**Rationale:** "the AI must not invent exercise names" is unenforceable by
prompt. Constraining the output space to ids we supplied makes it structurally
impossible.

### 21.2 Structured output

All action-shaped AI calls use structured outputs / function calling against a
published JSON schema. Free-text answers are only used where the result is
prose (explanations, analysis narration).

### 21.3 Validation pipeline

```text
1. JSON schema validation.
2. Every exercise_id ∈ the supplied candidate set.
3. Every exercise's equipment ⊆ user's available equipment.
4. sets/reps within sane bounds (1..10 sets, 1..100 reps, 1..20 exercises).
5. Total estimated duration ≤ requested session duration × 1.25.
On failure: one repair round-trip with the errors; then deterministic fallback.
```

### 21.4 Data boundaries

```text
Only the requesting user's own data may enter a prompt.
The prompt carries the minimum needed: never the full history when a
  90-day window answers the question.
Free-text notes and injury_notes are included only for the user's own
  requests, and never used for training or sent anywhere else.
Prompts and completions are logged with the user id for debugging, retained
  30 days, and excluded from any analytics export.
```

### 21.5 Cost and abuse control

```text
Per-user rate limit and daily token budget, both configurable.
Request timeout (default 20 s) with a clear timeout state in the UI.
Chat responses stream; generation and analysis show real progress.
Analysis results are cached on (user, exercise, date-range, data-hash) —
  the same question over unchanged data must not re-bill.
The user can see their remaining AI budget.
```

### 21.6 Degradation

If AI is disabled, unconfigured, over budget or failing:

```text
Every AI feature falls back to the non-AI path named in this spec:
  generation → §18.1, substitution → §20, analysis → the charts in §14.
Members are not shown provider, configuration or budget state (revision 5).
  The feature keeps working and the reason for the fallback is written to the
  server log for the operator.
A daily request limit, when reached, is reported in plain language
  ("today's limit for generated workouts") without naming the provider.
```

---

## 22. Data Model

Core entities:

```text
User
UserSettings
BodyweightLog
Equipment (reference)
Muscle (reference)
Exercise
CustomExercise (Exercise with is_custom)
WorkoutPlan
WorkoutExercise
WorkoutSession
SessionExercise
Set
PersonalRecord
AIInteraction
SyncMutation
SupportTicket   (revision 5, §30C.5)
Lead            (revision 5, §30C.3)
```

Relationships:

```text
User
 ├── UserSettings
 ├── BodyweightLog
 ├── Equipment (selection)
 ├── WorkoutPlans
 │     └── WorkoutExercises
 │             └── Exercise
 ├── WorkoutSessions
 │     └── SessionExercises
 │           └── Sets
 │                 └── Exercise
 └── PersonalRecords
       └── Exercise, Set
```

Conventions, binding on every table:

```text
Every user-owned table carries user_id and is indexed on it.
Every table carries created_at, updated_at; user data carries deleted_at.
Money-like and load-like numbers are NUMERIC, never float.
Foreign keys are enforced; ON DELETE is explicit per relation, and never
  cascades from a plan or exercise into logged history.
```

Required indexes (the queries that will otherwise be slow):

```text
sets            (user_id, exercise_id, performed_at DESC)
sets            (session_id)
sessions        (user_id, date DESC)
sessions        (user_id, status) WHERE status = 'in_progress'
exercises       (name_normalized) + full-text/trigram index
personal_records(user_id, exercise_id, record_type)
```

**ProgressRecord** from revision 1 is deliberately removed: progress is derived
from sets and must not be a separately writable entity that can drift out of
agreement with the log.

---

## 23. Backend API

Base path `/api/v1`. JSON only. All endpoints except auth require a session.

```http
POST   /auth/register
POST   /auth/login
POST   /auth/logout
GET    /auth/me
POST   /auth/password/reset-request
POST   /auth/password/reset

GET    /profile
PUT    /profile
GET    /profile/bodyweight
POST   /profile/bodyweight

GET    /exercises?muscle=&equipment=&difficulty=&type=&q=&cursor=&limit=
GET    /exercises/{id}
POST   /exercises            (custom)
PUT    /exercises/{id}       (custom, own only)
DELETE /exercises/{id}       (custom, own only)

POST   /workouts
GET    /workouts
GET    /workouts/{id}
PUT    /workouts/{id}
DELETE /workouts/{id}
POST   /workouts/{id}/exercises
PUT    /workouts/{id}/exercises/{we_id}
DELETE /workouts/{id}/exercises/{we_id}

POST   /sessions                        (body may carry client-generated id)
GET    /sessions?from=&to=&exercise_id=&cursor=
GET    /sessions/{id}
PATCH  /sessions/{id}
POST   /sessions/{id}/finish
POST   /sessions/{id}/cancel
POST   /sessions/{id}/exercises
PATCH  /sessions/{id}/exercises/{se_id}
DELETE /sessions/{id}/exercises/{se_id}
POST   /sessions/{id}/sets
PUT    /sessions/{id}/sets/{set_id}
DELETE /sessions/{id}/sets/{set_id}

POST   /sync                            (batched offline mutations)

GET    /progress?from=&to=
GET    /progress/exercises/{id}
GET    /progress/muscles/{id}
GET    /records
GET    /records/exercises/{id}

POST   /ai/chat
POST   /ai/workout
POST   /ai/analyze
POST   /ai/substitute
GET    /ai/budget

GET    /tickets                          (revision 5, §30C.5)
POST   /tickets
GET    /tickets/{id}
POST   /tickets/{id}/close
GET    /referral
POST   /leads                            (public, no session)
GET    /staff/tickets?status=            (staff only)
PATCH  /staff/tickets/{id}               (staff only)
GET    /staff/leads?status=              (staff only)
PATCH  /staff/leads/{id}                 (staff only)
```

### 23.1 Conventions

```text
Writes accept an Idempotency-Key header; replays return the original result.
Collections are cursor-paginated: {data: [...], next_cursor: "..."}.
Errors use one envelope:
  {"error": {"code": "validation_failed", "message": "...", "details": {...}}}
Codes are stable strings, not prose. HTTP status is meaningful:
  400 malformed, 401 unauthenticated, 403 forbidden, 404 not found,
  409 conflict/version, 422 validation, 429 rate limited, 5xx server.
Accessing another user's resource returns 404, not 403 (no enumeration).
All mutating endpoints validate ownership at the repository layer, not the
  handler — ownership is not something a route can forget.
```

---

## 24. Authentication and Authorization

Users must have individual accounts so workout history and schedules are
persistent.

```text
registration (email + password)
login / logout
session management
password reset by emailed single-use token (15 min expiry)
user-specific data isolation
```

Concrete requirements:

```text
Passwords hashed with Argon2id (or bcrypt cost ≥ 12 if unavailable).
Minimum 10 characters; checked against a common-password list; no composition
  rules and no forced rotation.
Session token: opaque, random ≥ 256 bits, stored hashed server-side,
  delivered as an httpOnly, Secure, SameSite=Lax cookie.
Sliding 30-day expiry; logout revokes server-side; "log out of all devices".
Login rate-limited (10/min/IP, exponential backoff per account).
Registration and reset responses do not reveal whether an email exists.
```

A user must only be able to access their own:

```text
schedule, sessions, sets, progress, personal records, profile,
custom exercises, AI interactions
```

Enforced by a `user_id` predicate applied in the data-access layer for every
user-owned query, with a test that fails if any query omits it.

Staff (revision 5):

```text
users.is_staff, false by default. Granted from the server command line
  (make staff email=...), never through the API.
Staff endpoints return 403 to members.
Staff reads across members' support tickets go through one explicitly
  unscoped repository (StaffInbox) and nowhere else.
```

The web app provides the reset flow end to end: a "Forgot password?" link,
a request page, and a page that accepts the emailed token. The link base is
the `PUBLIC_URL` setting. In development the email is printed to the API log.

---

## 25. Privacy, Export and Deletion

```text
The user can export all their data (JSON + CSV of sets) on request. The JSON
  export includes the member's support tickets (revision 5).
The user can delete their account; deletion removes all personal data and
  training history within 30 days, and is confirmed by re-entering the password.
Training data is never used to train models or shared with third parties.
Third-party exercise data flows in only; no user data is sent to the exercise
  provider.
Only the AI provider receives user-derived content, limited by §21.4.
```

---

## 26. Non-Functional Requirements

```text
Logging a set renders in < 100 ms locally (optimistic, no network wait).
Server acknowledges a set write at p95 < 300 ms.
Exercise search returns at p95 < 300 ms over the local mirror.
First contentful paint < 2 s on a mid-range phone over 3G.
The app is a PWA: installable, offline-capable, with a service worker.
Correct with 5 years of history (≈ 20k sets) — pagination and indexes assumed,
  and load-tested at that size.
Accessibility: WCAG 2.1 AA. Full keyboard operation, visible focus, labelled
  inputs, sufficient contrast, and no meaning conveyed by colour alone.
Light and dark themes; dark is the default for gym use.
Supported browsers: last 2 versions of Chrome, Safari, Firefox; iOS Safari
  included, and iOS PWA storage limits explicitly tested.
```

**Rationale on PWA:** the target user is on a phone in a basement gym. A plain
web app that requires connectivity fails the primary use case; a native app is
disproportionate for v1.

---

## 27. Error Handling and Empty States

```text
Every failure states what happened, whether data was lost, and what to do next.
Network failures during a session are not errors — they are the expected case
  and are handled by §12.
Every list has a designed empty state that leads to the next action
  ("no sessions yet — start your first workout").
Validation errors appear next to the field, not as a toast.
Client errors are reported with enough context to reproduce, without logging
  the user's notes or personal data.
```

---

## 28. Recommended Stack

```text
Frontend:
Next.js (App Router), React, TypeScript, Tailwind CSS
PWA: service worker + IndexedDB (Dexie or equivalent) for offline (§12)

Backend:
Python, FastAPI, Pydantic (schemas double as the AI structured-output contract)

Database:
PostgreSQL

Migrations:
Alembic — no schema change without a migration

AI:
LLM API with structured outputs / function calling
Default to the most capable current Claude model; the provider is behind an
interface so it can be swapped, and every AI call is mockable in tests.

Exercise Data:
ExerciseDB / AscendAPI ingest job → local Postgres mirror (§5.1)

Charts:
Recharts or equivalent

Testing:
pytest + Vitest + Playwright, including an offline-mode end-to-end run
```

---

## 29. Scope and Build Order

The first complete version must include:

```text
✓ User accounts                    ✓ Workout history
✓ Equipment selection              ✓ Exercise history
✓ Muscle/body-part selection       ✓ Volume tracking
✓ Exercise database (mirrored)     ✓ Strength/progression tracking
✓ Exercise search/filtering        ✓ Personal records
✓ Exercise media where available   ✓ Progress charts
✓ Custom exercises                 ✓ AI assistant
✓ Weekly workout schedule          ✓ AI workout generation
✓ Workout editing                  ✓ AI progress analysis
✓ Start workout session            ✓ Exercise substitution
✓ Ad-hoc sessions                  ✓ Offline logging + sync
✓ Add/remove exercises in session  ✓ Rest timer
✓ Per-exercise and per-set tracking
✓ Weight, reps, RIR, RPE, failure, set type, notes
✓ Rest/session timing
```

Build order — each stage is shippable and testable on its own:

```text
1. Auth, profile, data model, migrations.
2. Exercise ingest + mirror + search.                        (§5, §6)
3. Plans and weekly schedule.                                (§7)
4. Sessions and set logging — the core loop.                 (§8–§11)
5. Offline + sync.                                           (§12)
6. Derived metrics, history, PRs, charts.                    (§13–§16)
7. AI: substitution → generation → analysis → chat.          (§17–§21)
```

Stages 1–6 constitute a complete, useful product with no AI. Stage 7 must not
require changes to 1–6 beyond additive endpoints.

The complete workflow must support:

```text
"I have dumbbells and a bench"
        ↓
Find suitable exercises
        ↓
Ask AI to build a weekly plan
        ↓
Review and save the plan
        ↓
Start Monday's workout
        ↓
Log every set (offline, in a basement)
        ↓
Finish workout
        ↓
See it in history
        ↓
Track progression over weeks
        ↓
Ask AI to analyze the progress
```

### 29.1 Explicitly out of scope for v1

```text
Nutrition and calorie tracking
Social features, sharing, leaderboards
Wearable and health-platform integration
Video form analysis
Coach/client multi-user accounts
Rehabilitation programming (see §31)
```

---

## 30. Acceptance Criteria

The build is not complete until each of these passes as a test:

```text
A1  A user with only "dumbbell" selected never sees a barbell-only exercise
    in compatible results, and an exercise needing barbell+bench does not
    appear for a user with barbell alone.
A2  Logging 3 sets, killing the app, and reopening it restores the session
    in_progress with all 3 sets intact.
A3  Logging a full session with the network disabled, then reconnecting,
    results in exactly that session server-side — no duplicates, after a
    forced retry of every mutation.
A4  Editing Monday's plan does not change any completed session performed
    from that plan.
A5  A 12-rep set of pull-ups produces non-zero volume, and a 90-second plank
    is recordable.
A6  Deleting the set that set a PR restores the previous best everywhere it
    is displayed.
A7  Warmup sets are excluded from volume, charts and PRs, and included in the
    session log.
A8  An AI-generated plan containing an exercise not in the candidate set is
    rejected and never shown to the user.
A9  With the AI provider unreachable, plan generation, substitution and every
    other flow still work. No provider or configuration detail is shown to
    the member; the fallback is logged server-side (revised in revision 5).
A10 A user cannot read or modify another user's session, set or plan through
    any endpoint (tested per endpoint).
A11 Switching the display unit from kg to lb changes no stored value and no
    historical figure's meaning.
A12 A session logged at 23:30 local time appears in that local day and week
    in every chart.
A13 The whole logging flow is operable by keyboard and by screen reader.
A14 With 20k sets seeded, history and progress views stay within the §26
    latency budgets.
```

---

## 30A. Streaks and Streak Levels

Added in revision 3. A tracker that only records is a spreadsheet; the reason
people open one daily is to see the streak survive.

### 30A.1 The streak

```text
Counted in distinct days with a completed session, in the user's timezone.
A gap of up to 2 days does not break it - rest is training, and an app that
  punishes a sensible rest day teaches people to train when they should not.
A longer gap resets the current streak; the longest streak is kept forever.
```

### 30A.2 Streak levels

A ten-level ladder keyed to the current streak. Each level has a number, a
name, a threshold and a one-line description. The level is displayed with a
glow whose intensity follows the level, and crossing a threshold plays a
one-off level-up animation.

```text
0  No streak    0 days
1  Starter      1
2  Regular      3
3  Committed    5
4  Consistent   8
5  Bronze      12
6  Silver      18
7  Gold        25
8  Platinum    35
9  Diamond     50
```

Revision 5 replaced the original names, which borrowed from anime, with plain
tiers that suit a gym's member app.

Requirements:

```text
The ladder is served by the API, never hardcoded in the client, so the two
  cannot drift.
The level-up animation fires on a real transition, once - the last rank seen
  is remembered per browser. It respects prefers-reduced-motion.
The rank colour never carries meaning alone: the level number and rank name
  are always rendered beside it. Ten distinguishable hues do not exist for a
  colourblind viewer, so the ladder uses four validated accents and escalates
  through them.
The next rank and the distance to it are always visible. A streak with no
  visible next step is just a number.
```

### 30A.3 Dashboard

```text
Current streak, longest streak, sessions, volume this week, total volume.
A twelve-week training heatmap: one cell per day, a sequential single-hue
  ramp - it encodes whether you trained, which is magnitude, not identity.
Warm-up sets are excluded from every headline number, and the tile says so.
```

---

## 30B. Product Surface

Added in revision 4. The app was correct before this section and still read as
a personal tool; these are the requirements that make it something a stranger
could land on and understand.

### 30B.1 Signed-out landing

Superseded in revision 5 by the gym website in §30C.1. Kept for the record:

```text
States what the product is and who it is for in the first screen, without
  requiring an account to find out.
Names the three things that actually differentiate it - equipment awareness,
  offline logging, honest numbers - rather than listing features.
Shows the loop: set up kit, build the week, train, watch it move.
Says plainly what it is not: a training log, not medical advice, and not a
  replacement for a coach.
```

### 30B.2 Dashboard

```text
The exercise library is visible from the dashboard, not only from search -
  browsing is how people find movements they did not know to look for.
Illustrated movements are preferred in that section; a wall of names is not
  a reason to browse.
Every panel leads somewhere. No dead ends.
```

### 30B.3 Throughout

```text
Page titles follow a template, so a browser tab and a shared link both say
  what the page is.
A favicon, an application name and Open Graph metadata.
A footer carrying navigation, third-party attribution, and the safety
  disclaimer from 31.
Copy is written for a stranger. No internal jargon in user-facing text.
```

---

## 30C. Gym Deployment

Added in revision 5. The app runs as the website and member app of one gym.
All gym-specific content is configuration, so another gym is a matter of
editing one file and one folder of photos.

### 30C.1 Public website

The signed-out home page is the gym's website. Sections, in order:

```text
Hero       headline offer, a live open/closed badge, "Get your free pass"
           and "View memberships".
Facts      days open per week, classes per week, joining fee, notice to
           cancel - each computed from configuration, never typed twice.
Memberships  plan cards with a monthly/annual switch; the annual price is
           derived from the monthly price and one discount constant.
           Membership terms are listed beside the prices.
Classes    seven-day timetable with day tabs, class length, room, coach and
           an intensity scale. Finished classes are dimmed and a running
           class is marked live.
Facilities photo gallery of training zones, plus amenities.
Personal training  packages with the per-session price derived.
Member app what membership includes in the app, with log-in and sign-up.
Visit      address, directions, click-to-call, tour booking.
FAQ        expandable questions and answers.
Footer     full weekly hours, contact details, social links.
```

A site-wide photo sits behind every page under a dark overlay.

### 30C.2 Configuration

```text
web/src/lib/gym.ts   name, tagline, address, phone, email, social links,
                     currency, headline offer, opening hours, plans,
                     annual discount, membership terms, timetable,
                     facilities, amenities, PT packages, FAQ, and the
                     equipment the gym owns.
web/public/gym/      every photo, by fixed file name; README lists where
                     each appears and credits the current stock images.
```

Prices are whole rupees with Indian digit grouping (₹1,499). New members
start with the gym's equipment list, so the exercise library matches the
gym floor without a setup step.

### 30C.3 Visitor enquiries

```text
Three forms on /join: free week pass, tour booking, membership enquiry.
No account required. Name and email required; phone, preferred date, plan
  and message optional.
The membership form arrives with the plan pre-selected from the pricing
  card the visitor chose.
A hidden honeypot field: a filled honeypot is acknowledged and not stored.
Stored as a Lead: kind, contact details, preferred date, plan, message,
  referring member, status (new / contacted / joined / closed).
Online payment is out of scope; a membership enquiry is completed by staff.
```

### 30C.4 Referrals

```text
Each member has a referral code: the first block of their user id. No extra
  column and no way to guess another member's code from it.
The dashboard offers a share link (/join?ref=CODE), using the native share
  sheet where available.
A lead carrying a valid code records the referring member; an invalid code
  is ignored.
```

### 30C.5 Support requests

Members report problems with the gym and follow them to resolution.

```text
Fields: category (equipment, cleanliness, facilities, classes, staff,
  membership, safety, other), optional location, subject, details, and an
  urgent flag. Safety requests are urgent automatically.
Statuses: open → in_progress → resolved, or closed. The member sees a
  three-step tracker and the staff reply on the request itself.
A member can close their own request.
User-owned: scoped by user_id like every other member table, included in
  the data export, deleted with the account.
```

### 30C.6 Staff inbox

```text
/staff, visible to staff accounts only.
Member requests: urgent first, then oldest first. Requests waiting more
  than 24 hours are highlighted. Staff reply and set the status in place;
  replying to an open request moves it to in_progress.
Enquiries: every lead with its contact details and referrer, filterable by
  status, with the status editable in place.
```

### 30C.7 Member-facing copy

```text
Written the way a finished business site is written: plain, specific,
  descriptive headings. No slogans, no internal jargon, no explanations of
  how the product was built.
No provider, configuration, budget or fallback state is shown to members
  (see 21.6).
Phones get a bottom tab bar (Home, Train, Classes, Support, More); no page
  scrolls sideways at 390px.
```

---

## 31. Safety Boundary

Geek-Trainer is a fitness training and tracking application.

It must not:

```text
Diagnose injuries.
Provide medical diagnoses.
Present medical advice as fact.
Claim to replace a qualified trainer or healthcare professional.
Automatically prescribe rehabilitation exercises.
```

Exercise recommendations are presented as informational training guidance.

Implementation requirements:

```text
The AI system prompt carries these constraints, and they are covered by tests
  using adversarial prompts ("my shoulder clicks, what's torn?").
When a user's message describes pain or injury, the assistant acknowledges it,
  declines to diagnose, and suggests seeing a professional — once, plainly,
  without lecturing on every subsequent message.
injury_notes are used only to avoid suggesting exercises the user has flagged,
  never to reason about the injury itself.
Load and progression suggestions stay within conservative bounds
  (no single-jump increase beyond ~10%).
```

---

## 32. Open Questions

```text
Q1  ExerciseDB / AscendAPI licensing: which tier, and do the terms permit
    caching exercise data and re-hosting GIFs?
    SETTLED FOR NOW: this build is personal and non-commercial, so cached
    exercise data and media are used freely and 5.2 is not a blocker.
    Revisit before any public or commercial release.
Q2  Which LLM provider and model tier, and what is the monthly budget per
    user? This sets the limits in §21.5.
Q3  Email delivery for password reset — which provider?
Q4  Is a multi-device single user in scope for v1, or is last-write-wins
    across devices (§12.4) acceptable indefinitely?
Q5  Deload / periodization: out of scope for v1, or a lightweight
    "reduce volume this week" suggestion?
Q7  Loaded carries (farmer's walk, sled push) have both a load and a
    distance, and Sec 10.2 has no `weight_distance` metric type - so the
    seed catalogue records them as distance only and the load is lost.
    Either add the metric type or accept the gap; noticed while building
    the catalogue.

Q6  Hosting target — this determines the ingest job's scheduler and whether
    the service worker's caching strategy needs a CDN story.
```

---

## 33. Revision Log

### Revision 5 — 2026-09-26

```text
Added 30C - gym deployment: public club website, configuration in one file,
visitor enquiries, referrals, member support requests, staff role and inbox.
Revised 21.6 and A9 - members no longer see AI provider or configuration
state; fallbacks are logged for the operator.
Revised 30A.2 - streak level names replaced with plain tiers.
Added the staff role and the web password-reset flow to 24, tickets to the
export in 25, and the new tables and endpoints to 22 and 23.
```

### Revision 4 — 2026-08-31

```text
Added 30B - product surface. The app was correct and still looked like a
personal tool: no landing page worth reading, no exercise browsing from the
dashboard, no metadata, no footer, no attribution outside a detail page.
Added 6.3 - the exercise detail page requirement.
```

### Revision 3 — 2026-08-31

```text
Added 30A - streaks, power levels and the dashboard. The tracker was correct
but gave nobody a reason to open it on a rest day; the streak is that reason.
Recorded because it changes what the product is, not just how it looks.
Q1 settled for this build (personal, non-commercial).
Q7 added - loaded carries lose their load, since 10.2 has no weight_distance.
```

### Revision 2 — 2026-08-31

Changes from revision 1, with the problem each one fixes:

```text
1.  Added §1.1 primary use context — the gym/phone/offline constraint that
    the rest of the spec now derives from.
2.  Added §3 Units, Time and Locale. Revision 1 never named a storage unit,
    a timezone or a week start, while requiring weekly volume, monthly
    volume and consistency.
3.  §5 — exercise data is now mirrored locally by an ingest job instead of
    being fetched from a rate-limited third-party API on the request path.
4.  §5.4 — custom exercises added; no external catalogue covers every gym.
5.  §6.1 — the equipment rule is stated as set containment (all-of), the
    single most common filtering bug for this feature.
6.  §7.1 — plan/session split with a snapshot at start, which is what makes
    revision 1's "history must not be overwritten" actually true.
7.  §8.2 / §8.3 — session resume after a crash, and ad-hoc sessions with no
    plan (workout_id is nullable).
8.  §10.2 — metric types. Revision 1's volume = weight × reps scored
    bodyweight work as zero and could not record a plank at all.
9.  §10.3 — warmup sets excluded from volume, charts and PRs.
10. §10.5 — supersets, without which recorded rest times are meaningless.
11. §11.1–§11.4 — concrete speed, rest-timer, wake-lock and one-handed-use
    requirements behind revision 1's "fast enough for use during a workout".
12. §12 — offline and sync, with client-generated ids and idempotency keys
    so a retried write cannot duplicate a set and fabricate a PR.
13. §13.3 — e1RM formula named (Epley, ≤ 12 reps); revision 1 required
    "Best Estimated 1RM" without defining it.
14. §13.4 / §15 — derived data and PRs are recomputed, and a PR is revoked
    when the set behind it is corrected or deleted.
15. §14 — "consistency" and "adherence" given computable definitions.
16. §17.2 — AI proposes, the user confirms; no AI write path to the database.
17. §21.1 — retrieval-constrained generation: the model may only pick from a
    candidate id list, making "AI must not invent exercises" structural
    rather than a prompt instruction.
18. §18.1 / §21.6 — deterministic non-AI fallbacks for every AI feature.
19. §21.4 / §21.5 — AI data boundaries, rate limits, budget, caching.
20. §22 — table conventions and the indexes the app needs; removed the
    ProgressRecord entity so progress cannot drift from the set log.
21. §23 — /api/v1, auth and sync endpoints, pagination, idempotency, a single
    error envelope, ownership enforced in the data layer.
22. §24 — concrete auth: Argon2id, opaque httpOnly cookie sessions, reset
    flow, rate limits, no account enumeration.
23. §25 / §26 / §27 — privacy and export, non-functional targets, error and
    empty states.
24. §29 — build order in which stages 1–6 ship a complete product with no AI.
25. §30 — 14 testable acceptance criteria; revision 1 had none.
26. §31 — the safety boundary made enforceable (system prompt, adversarial
    tests, bounded load suggestions) rather than declarative.
27. §32 — open questions, chiefly exercise-data licensing and AI budget.
```

Revision 1 is preserved verbatim as the pre-2026-08-31 version of this file.
