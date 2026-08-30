"""The seed exercise catalogue. PLAN.md D5.

Checked into the repo so development needs no API key, tests are deterministic,
and a first deploy has a usable catalogue before the first ingest runs. The
full third-party catalogue arrives via app/ingest/; this is the floor, not the
ceiling.

Every row is written by hand against SPECIFICATIONS.MD 5.3, so metric_type and
bodyweight_load_factor are correct rather than defaulted - which matters,
because those two fields decide whether a set of pull-ups scores any volume at
all (Sec 13.1).

Row shape:
    (name, primary_muscle, secondary, equipment, difficulty, type,
     metric, bodyweight_factor, cue)

Short codes: difficulty b/i/a - type c(ompound)/i(solation)/cardio/mobility
metric wr=weight_reps br=bodyweight_reps wb=weighted_bodyweight
       t=time d=distance td=time_distance
"""

# fmt: off
CHEST = [
    ("Barbell Bench Press", "pectorals", ["triceps", "front-delts"], ["barbell", "bench"], "i", "c", "wr", None, "Lower the bar to mid-chest with elbows about 45 degrees from your body, then press back to lockout."),
    ("Incline Barbell Bench Press", "pectorals", ["front-delts", "triceps"], ["barbell", "bench"], "i", "c", "wr", None, "Set the bench to 30 degrees and press from the upper chest."),
    ("Decline Barbell Bench Press", "pectorals", ["triceps"], ["barbell", "bench"], "i", "c", "wr", None, "On a declined bench, lower to the lower chest and press up."),
    ("Dumbbell Bench Press", "pectorals", ["triceps", "front-delts"], ["dumbbell", "bench"], "b", "c", "wr", None, "Press two dumbbells from chest level, letting them travel slightly inward at the top."),
    ("Incline Dumbbell Bench Press", "pectorals", ["front-delts", "triceps"], ["dumbbell", "bench"], "b", "c", "wr", None, "Press from the upper chest on a 30 degree incline."),
    ("Dumbbell Fly", "pectorals", [], ["dumbbell", "bench"], "i", "i", "wr", None, "With a soft elbow bend, open your arms wide and bring them together above the chest."),
    ("Incline Dumbbell Fly", "pectorals", ["front-delts"], ["dumbbell", "bench"], "i", "i", "wr", None, "Same arc as a flat fly, performed on an incline."),
    ("Cable Crossover", "pectorals", ["front-delts"], ["cable"], "i", "i", "wr", None, "Step forward between two high pulleys and bring the handles together in front of you."),
    ("Cable Fly (Low to High)", "pectorals", ["front-delts"], ["cable"], "i", "i", "wr", None, "Sweep the handles upward and inward from hip height to chest height."),
    ("Machine Chest Press", "pectorals", ["triceps", "front-delts"], ["machine"], "b", "c", "wr", None, "Press the handles forward with the seat set so the handles sit at chest height."),
    ("Pec Deck", "pectorals", [], ["machine"], "b", "i", "wr", None, "Bring the pads together in front of your chest with a fixed elbow angle."),
    ("Push-Up", "pectorals", ["triceps", "front-delts", "abs"], ["bodyweight"], "b", "c", "br", 0.64, "Keep a straight line from head to heels and lower until your chest is just off the floor."),
    ("Incline Push-Up", "pectorals", ["triceps", "front-delts"], ["bodyweight"], "b", "c", "br", 0.45, "Hands elevated on a bench or bar; easier than a floor push-up."),
    ("Decline Push-Up", "pectorals", ["front-delts", "triceps"], ["bodyweight"], "i", "c", "br", 0.74, "Feet elevated, which shifts the load toward the upper chest and shoulders."),
    ("Diamond Push-Up", "triceps", ["pectorals", "front-delts"], ["bodyweight"], "i", "c", "br", 0.64, "Hands close together under the chest, elbows tracking back."),
    ("Chest Dip", "pectorals", ["triceps", "front-delts"], ["dip-bars"], "i", "c", "wb", 1.0, "Lean the torso forward and let the elbows flare slightly to bias the chest."),
    ("Smith Machine Bench Press", "pectorals", ["triceps"], ["smith-machine", "bench"], "b", "c", "wr", None, "A fixed bar path; useful when pressing heavy without a spotter."),
    ("Svend Press", "pectorals", [], ["medicine-ball"], "b", "i", "wr", None, "Squeeze a ball between your palms and press it straight out from the chest."),
]

BACK = [
    ("Pull-Up", "lats", ["biceps", "rhomboids", "teres-major"], ["pull-up-bar"], "i", "c", "wb", 1.0, "Hang with an overhand grip and pull until your chin clears the bar."),
    ("Chin-Up", "lats", ["biceps", "rhomboids"], ["pull-up-bar"], "i", "c", "wb", 1.0, "Underhand grip, which lets the biceps contribute more than a pull-up."),
    ("Neutral-Grip Pull-Up", "lats", ["biceps", "teres-major"], ["pull-up-bar"], "i", "c", "wb", 1.0, "Palms facing each other - usually the most shoulder-friendly variation."),
    ("Lat Pulldown", "lats", ["biceps", "rhomboids"], ["cable"], "b", "c", "wr", None, "Pull the bar to your upper chest, leading with the elbows rather than the hands."),
    ("Close-Grip Lat Pulldown", "lats", ["biceps"], ["cable"], "b", "c", "wr", None, "A narrow or neutral grip that increases the range at the bottom."),
    ("Barbell Row", "lats", ["rhomboids", "traps", "biceps", "lower-back"], ["barbell"], "i", "c", "wr", None, "Hinge to about 45 degrees and row the bar to your lower ribs."),
    ("Pendlay Row", "lats", ["rhomboids", "traps"], ["barbell"], "a", "c", "wr", None, "Row explosively from a dead stop on the floor with a flat back."),
    ("One Arm Dumbbell Row", "lats", ["rhomboids", "biceps"], ["dumbbell", "bench"], "b", "c", "wr", None, "Brace a hand and knee on the bench and row the dumbbell to your hip."),
    ("Chest-Supported Row", "rhomboids", ["lats", "rear-delts"], ["dumbbell", "bench"], "b", "c", "wr", None, "Lie face down on an incline bench so the lower back does no work."),
    ("Seated Cable Row", "rhomboids", ["lats", "biceps"], ["cable"], "b", "c", "wr", None, "Pull the handle to your navel and keep the torso still."),
    ("T-Bar Row", "lats", ["rhomboids", "traps"], ["barbell"], "i", "c", "wr", None, "Straddle a landmine bar and row it to your chest."),
    ("Inverted Row", "rhomboids", ["lats", "biceps"], ["barbell"], "b", "c", "br", 0.55, "Hang under a fixed bar with straight legs and pull your chest to the bar."),
    ("Straight-Arm Pulldown", "lats", ["teres-major"], ["cable"], "b", "i", "wr", None, "With locked elbows, sweep the bar from overhead down to your thighs."),
    ("Dumbbell Pullover", "lats", ["pectorals", "triceps"], ["dumbbell", "bench"], "i", "i", "wr", None, "Lower one dumbbell behind your head in an arc and pull it back over your chest."),
    ("Machine Row", "rhomboids", ["lats", "biceps"], ["machine"], "b", "c", "wr", None, "A supported row with a fixed path."),
    ("Deadlift", "lower-back", ["glutes", "hamstrings", "traps", "quads"], ["barbell"], "a", "c", "wr", None, "Drive the floor away with a neutral spine and lock out at the hips."),
    ("Rack Pull", "lower-back", ["traps", "glutes"], ["barbell"], "i", "c", "wr", None, "A partial deadlift from pins at or just below the knee."),
    ("Barbell Shrug", "traps", ["forearms"], ["barbell"], "b", "i", "wr", None, "Lift the shoulders straight up; no rolling."),
    ("Dumbbell Shrug", "traps", ["forearms"], ["dumbbell"], "b", "i", "wr", None, "Same movement with dumbbells at your sides."),
    ("Face Pull", "rear-delts", ["traps", "rotator-cuff"], ["cable"], "b", "i", "wr", None, "Pull a rope to your forehead with the elbows high and rotate outward."),
    ("Back Extension", "lower-back", ["glutes", "hamstrings"], ["machine"], "b", "i", "wr", None, "Hinge at the hips over a pad and extend to a straight line, not beyond."),
    ("Good Morning", "hamstrings", ["lower-back", "glutes"], ["barbell"], "a", "c", "wr", None, "With the bar on your back, hinge forward with soft knees and a flat spine."),
]

SHOULDERS = [
    ("Overhead Press", "front-delts", ["triceps", "side-delts"], ["barbell"], "i", "c", "wr", None, "Press from the front rack to lockout with the ribs down and glutes tight."),
    ("Seated Dumbbell Shoulder Press", "front-delts", ["triceps", "side-delts"], ["dumbbell", "bench"], "b", "c", "wr", None, "Press two dumbbells overhead from ear height."),
    ("Arnold Press", "front-delts", ["side-delts", "triceps"], ["dumbbell", "bench"], "i", "c", "wr", None, "Start palms-in and rotate outward as you press."),
    ("Machine Shoulder Press", "front-delts", ["triceps"], ["machine"], "b", "c", "wr", None, "A supported overhead press with a fixed path."),
    ("Dumbbell Lateral Raise", "side-delts", [], ["dumbbell"], "b", "i", "wr", None, "Raise the dumbbells out to shoulder height leading with the elbows."),
    ("Cable Lateral Raise", "side-delts", [], ["cable"], "b", "i", "wr", None, "A lateral raise with constant tension through the whole range."),
    ("Machine Lateral Raise", "side-delts", [], ["machine"], "b", "i", "wr", None, "Supported lateral raise against pads."),
    ("Front Raise", "front-delts", [], ["dumbbell"], "b", "i", "wr", None, "Raise the weight straight in front of you to shoulder height."),
    ("Reverse Fly", "rear-delts", ["rhomboids"], ["dumbbell"], "b", "i", "wr", None, "Hinge forward and open the arms wide with soft elbows."),
    ("Reverse Pec Deck", "rear-delts", ["rhomboids"], ["machine"], "b", "i", "wr", None, "Face the pad and sweep the handles backward."),
    ("Upright Row", "side-delts", ["traps", "biceps"], ["barbell"], "i", "c", "wr", None, "Pull the bar to chest height with the elbows leading, keeping the grip wide."),
    ("Band Pull-Apart", "rear-delts", ["rhomboids"], ["resistance-band"], "b", "i", "wr", None, "Hold a band at shoulder height and pull it apart until your arms are wide."),
    ("Cuban Rotation", "rotator-cuff", ["rear-delts"], ["dumbbell"], "i", "i", "wr", None, "Row to a high-elbow position, rotate up, then press. Light weight only."),
    ("Pike Push-Up", "front-delts", ["triceps"], ["bodyweight"], "i", "c", "br", 0.6, "Hips high, lower the crown of your head toward the floor between your hands."),
]

ARMS = [
    ("Barbell Curl", "biceps", ["forearms"], ["barbell"], "b", "i", "wr", None, "Curl the bar with the elbows pinned to your sides."),
    ("EZ-Bar Curl", "biceps", ["forearms"], ["ez-bar"], "b", "i", "wr", None, "The angled grip is easier on the wrists than a straight bar."),
    ("Dumbbell Curl", "biceps", ["forearms"], ["dumbbell"], "b", "i", "wr", None, "Curl one or both dumbbells, supinating as you rise."),
    ("Hammer Curl", "biceps", ["forearms"], ["dumbbell"], "b", "i", "wr", None, "Neutral grip throughout, which loads the brachialis and forearm."),
    ("Incline Dumbbell Curl", "biceps", [], ["dumbbell", "bench"], "i", "i", "wr", None, "Curl with the arms hanging behind you on an incline bench for a longer stretch."),
    ("Preacher Curl", "biceps", [], ["ez-bar", "bench"], "b", "i", "wr", None, "Curl over a preacher pad so the upper arms cannot swing."),
    ("Cable Curl", "biceps", ["forearms"], ["cable"], "b", "i", "wr", None, "Constant tension from a low pulley."),
    ("Concentration Curl", "biceps", [], ["dumbbell", "bench"], "b", "i", "wr", None, "Seated, elbow braced against the inner thigh."),
    ("Close-Grip Bench Press", "triceps", ["pectorals", "front-delts"], ["barbell", "bench"], "i", "c", "wr", None, "Shoulder-width grip, elbows tucked, press from the lower chest."),
    ("Triceps Pushdown", "triceps", [], ["cable"], "b", "i", "wr", None, "Push the bar or rope down to lockout with the elbows fixed at your sides."),
    ("Overhead Triceps Extension", "triceps", [], ["dumbbell"], "b", "i", "wr", None, "Lower the weight behind your head and extend, keeping the elbows narrow."),
    ("Skull Crusher", "triceps", [], ["ez-bar", "bench"], "i", "i", "wr", None, "Lower the bar toward your forehead with the upper arms vertical."),
    ("Triceps Dip", "triceps", ["pectorals", "front-delts"], ["dip-bars"], "i", "c", "wb", 1.0, "Stay upright and lower until the elbows reach about 90 degrees."),
    ("Bench Dip", "triceps", ["front-delts"], ["bench"], "b", "c", "br", 0.55, "Hands on a bench behind you, lower the hips toward the floor."),
    ("Kickback", "triceps", [], ["dumbbell"], "b", "i", "wr", None, "Hinge forward and extend the elbow straight back."),
    ("Wrist Curl", "forearms", [], ["dumbbell"], "b", "i", "wr", None, "Forearms on your thighs, curl the weight up with the wrists only."),
    ("Reverse Wrist Curl", "forearms", [], ["dumbbell"], "b", "i", "wr", None, "Palms down; extend the wrists against the load."),
    ("Farmer's Carry", "forearms", ["traps", "abs"], ["dumbbell"], "b", "c", "d", None, "Carry a heavy weight in each hand and walk with tall posture."),
]
# fmt: on

# fmt: off
LEGS = [
    ("Back Squat", "quads", ["glutes", "hamstrings", "lower-back"], ["barbell"], "i", "c", "wr", None, "Bar on the upper back; sit down and back to at least parallel, then drive up."),
    ("Front Squat", "quads", ["glutes", "abs"], ["barbell"], "a", "c", "wr", None, "Bar in the front rack with the elbows high, which keeps the torso upright."),
    ("Goblet Squat", "quads", ["glutes", "abs"], ["dumbbell"], "b", "c", "wr", None, "Hold one dumbbell at your chest and squat between your knees."),
    ("Bodyweight Squat", "quads", ["glutes"], ["bodyweight"], "b", "c", "br", 0.65, "Squat to depth with your heels down and chest up."),
    ("Bulgarian Split Squat", "quads", ["glutes", "hamstrings"], ["dumbbell", "bench"], "i", "c", "wr", None, "Rear foot elevated; lower straight down over the front leg."),
    ("Walking Lunge", "quads", ["glutes", "hamstrings"], ["dumbbell"], "b", "c", "wr", None, "Step forward and lower the back knee toward the floor, then step through."),
    ("Reverse Lunge", "glutes", ["quads", "hamstrings"], ["dumbbell"], "b", "c", "wr", None, "Step backward instead of forward - usually easier on the knees."),
    ("Step-Up", "quads", ["glutes"], ["dumbbell", "bench"], "b", "c", "wr", None, "Drive through the top foot without pushing off the trailing leg."),
    ("Leg Press", "quads", ["glutes", "hamstrings"], ["machine"], "b", "c", "wr", None, "Press the platform away without letting the lower back round at the bottom."),
    ("Hack Squat", "quads", ["glutes"], ["machine"], "i", "c", "wr", None, "A machine squat with the back supported."),
    ("Smith Machine Squat", "quads", ["glutes"], ["smith-machine"], "b", "c", "wr", None, "A fixed-path squat, useful for training close to failure alone."),
    ("Leg Extension", "quads", [], ["machine"], "b", "i", "wr", None, "Extend the knees against the pad and control the way down."),
    ("Romanian Deadlift", "hamstrings", ["glutes", "lower-back"], ["barbell"], "i", "c", "wr", None, "Push the hips back with soft knees until you feel the hamstrings, then stand."),
    ("Dumbbell Romanian Deadlift", "hamstrings", ["glutes"], ["dumbbell"], "b", "c", "wr", None, "The same hip hinge with dumbbells."),
    ("Stiff-Leg Deadlift", "hamstrings", ["glutes", "lower-back"], ["barbell"], "i", "c", "wr", None, "A hinge with near-straight legs and a long hamstring stretch."),
    ("Lying Leg Curl", "hamstrings", ["calves"], ["machine"], "b", "i", "wr", None, "Curl the pad toward your glutes without lifting the hips."),
    ("Seated Leg Curl", "hamstrings", [], ["machine"], "b", "i", "wr", None, "Seated version, which trains the hamstrings in a lengthened position."),
    ("Nordic Curl", "hamstrings", [], ["bodyweight"], "a", "i", "br", 0.7, "Anchor the ankles and lower your torso forward as slowly as you can."),
    ("Hip Thrust", "glutes", ["hamstrings"], ["barbell", "bench"], "b", "c", "wr", None, "Shoulders on a bench, drive the hips to full extension and squeeze."),
    ("Glute Bridge", "glutes", ["hamstrings"], ["bodyweight"], "b", "c", "br", 0.4, "From the floor, lift the hips until the body forms a straight line."),
    ("Cable Kickback", "glutes", ["hamstrings"], ["cable"], "b", "i", "wr", None, "Drive one leg backward against the cable with a still torso."),
    ("Hip Abduction Machine", "abductors", ["glutes"], ["machine"], "b", "i", "wr", None, "Press the knees outward against the pads."),
    ("Hip Adduction Machine", "adductors", [], ["machine"], "b", "i", "wr", None, "Squeeze the knees together against the pads."),
    ("Standing Calf Raise", "calves", [], ["machine"], "b", "i", "wr", None, "Rise onto the toes through a full range and pause at the top."),
    ("Seated Calf Raise", "calves", [], ["machine"], "b", "i", "wr", None, "Bent knees bias the soleus rather than the gastrocnemius."),
    ("Dumbbell Calf Raise", "calves", [], ["dumbbell"], "b", "i", "wr", None, "Hold dumbbells and rise onto the toes, ideally off a step."),
    ("Kettlebell Swing", "glutes", ["hamstrings", "lower-back", "cardiovascular"], ["kettlebell"], "i", "c", "wr", None, "Hinge and snap the hips to float the bell to chest height. It is not a squat."),
    ("Box Jump", "quads", ["glutes", "calves"], ["bodyweight"], "i", "c", "br", 0.9, "Jump onto a box and land softly with bent knees. Step down, do not jump down."),
]

CORE = [
    ("Plank", "transverse-abdominis", ["abs", "obliques"], ["bodyweight"], "b", "i", "t", None, "Hold a straight line from head to heels with the glutes and abs braced."),
    ("Side Plank", "obliques", ["transverse-abdominis"], ["bodyweight"], "b", "i", "t", None, "Stack the hips and hold, keeping the bottom shoulder packed."),
    ("Hollow Body Hold", "abs", ["hip-flexors"], ["bodyweight"], "i", "i", "t", None, "Press the lower back into the floor and hold arms and legs off it."),
    ("Dead Bug", "transverse-abdominis", ["abs"], ["bodyweight"], "b", "i", "br", 0.2, "Extend the opposite arm and leg without letting the lower back arch."),
    ("Crunch", "abs", [], ["bodyweight"], "b", "i", "br", 0.25, "Curl the ribs toward the hips; this is a short range, not a sit-up."),
    ("Cable Crunch", "abs", ["obliques"], ["cable"], "b", "i", "wr", None, "Kneel under a high pulley and crunch the ribs down toward the knees."),
    ("Hanging Leg Raise", "abs", ["hip-flexors", "forearms"], ["pull-up-bar"], "i", "i", "br", 0.45, "Hang and raise straight legs to hip height without swinging."),
    ("Hanging Knee Raise", "abs", ["hip-flexors"], ["pull-up-bar"], "b", "i", "br", 0.35, "The bent-knee version of the leg raise."),
    ("Ab Wheel Rollout", "abs", ["transverse-abdominis", "lats"], ["bodyweight"], "a", "i", "br", 0.5, "Roll out only as far as you can go without the lower back arching."),
    ("Russian Twist", "obliques", ["abs"], ["medicine-ball"], "b", "i", "wr", None, "Seated and leaning back, rotate the ball from hip to hip."),
    ("Pallof Press", "obliques", ["transverse-abdominis"], ["cable"], "b", "i", "wr", None, "Press a cable straight out while resisting the pull to rotate."),
    ("Bicycle Crunch", "obliques", ["abs"], ["bodyweight"], "b", "i", "br", 0.3, "Alternate elbow to opposite knee with the legs cycling."),
    ("Mountain Climber", "abs", ["hip-flexors", "cardiovascular"], ["bodyweight"], "b", "c", "t", None, "From a push-up position, drive the knees to the chest alternately."),
    ("Stability Ball Rollout", "abs", ["transverse-abdominis"], ["stability-ball"], "i", "i", "br", 0.4, "Forearms on the ball, roll it away and pull it back with the abs."),
]

FULL_BODY = [
    ("Burpee", "cardiovascular", ["quads", "pectorals", "abs"], ["bodyweight"], "i", "c", "br", 0.8, "Drop to a push-up, jump the feet in, and stand or jump."),
    ("Thruster", "quads", ["front-delts", "glutes", "triceps"], ["dumbbell"], "i", "c", "wr", None, "A front squat straight into an overhead press."),
    ("Clean and Press", "front-delts", ["quads", "traps", "glutes"], ["barbell"], "a", "c", "wr", None, "Pull the bar to the front rack, then press it overhead."),
    ("Turkish Get-Up", "abs", ["front-delts", "glutes", "obliques"], ["kettlebell"], "a", "c", "wr", None, "Stand up and lie back down with a weight locked overhead. Go slowly."),
    ("Bear Crawl", "transverse-abdominis", ["front-delts", "quads"], ["bodyweight"], "b", "c", "d", None, "Crawl with the knees an inch off the floor and the hips low."),
    ("Battle Rope Waves", "cardiovascular", ["front-delts", "forearms"], ["bodyweight"], "b", "cardio", "t", None, "Alternate arms to send waves down the rope without losing your brace."),
]

CARDIO = [
    ("Treadmill Run", "cardiovascular", ["quads", "calves"], ["machine"], "b", "cardio", "td", None, "Run at a steady pace or in intervals."),
    ("Outdoor Run", "cardiovascular", ["quads", "calves", "hamstrings"], ["bodyweight"], "b", "cardio", "td", None, "Road or trail running."),
    ("Stationary Bike", "cardiovascular", ["quads"], ["machine"], "b", "cardio", "td", None, "Steady-state or interval cycling."),
    ("Rowing Machine", "cardiovascular", ["lats", "quads", "rhomboids"], ["machine"], "b", "cardio", "td", None, "Drive with the legs, then the back, then the arms."),
    ("Elliptical", "cardiovascular", ["quads", "glutes"], ["machine"], "b", "cardio", "td", None, "Low-impact steady-state work."),
    ("Stair Climber", "cardiovascular", ["glutes", "quads", "calves"], ["machine"], "b", "cardio", "td", None, "Climb without leaning on the handles."),
    ("Jump Rope", "cardiovascular", ["calves"], ["bodyweight"], "b", "cardio", "t", None, "Small hops off the balls of the feet."),
    ("Sled Push", "quads", ["glutes", "calves", "cardiovascular"], ["machine"], "i", "c", "d", None, "Push a loaded sled with a low body angle and short steps."),
]

MOBILITY = [
    ("Cat-Cow", "lower-back", ["abs"], ["bodyweight"], "b", "mobility", "t", None, "Alternate arching and rounding the spine on all fours."),
    ("Hip Flexor Stretch", "hip-flexors", ["quads"], ["bodyweight"], "b", "mobility", "t", None, "Half-kneeling, tuck the pelvis and press the hips forward."),
    ("Thoracic Rotation", "lower-back", ["obliques"], ["bodyweight"], "b", "mobility", "t", None, "On all fours, hand behind the head, rotate the ribs open."),
    ("Shoulder Dislocate", "rotator-cuff", ["front-delts"], ["resistance-band"], "b", "mobility", "t", None, "Pass a band overhead and behind you with straight arms."),
    ("Couch Stretch", "quads", ["hip-flexors"], ["bodyweight"], "i", "mobility", "t", None, "Rear foot up a wall in a half-kneel; tuck the pelvis."),
    ("Deep Squat Hold", "adductors", ["glutes", "quads"], ["bodyweight"], "b", "mobility", "t", None, "Sit in the bottom of a squat and breathe."),
]

ALL_GROUPS = {
    "chest": CHEST, "back": BACK, "shoulders": SHOULDERS, "arms": ARMS,
    "legs": LEGS, "core": CORE, "full_body": FULL_BODY, "cardio": CARDIO,
    "mobility": MOBILITY,
}
# fmt: on
