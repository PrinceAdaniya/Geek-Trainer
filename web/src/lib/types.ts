/**
 * Hand-written for now. PLAN.md D13 replaces this file with types generated
 * from the API's OpenAPI schema once the surface stops moving - `make types`.
 */

export type Unit = "kg" | "lb";
export type WeekStart = "monday" | "sunday";

export interface Settings {
  unit_preference: Unit;
  timezone: string;
  week_start: WeekStart;
  default_rest_seconds: number;
  available_equipment: string[];
  weight_increments: Record<string, string>;
}

export interface Profile {
  id: string;
  email: string;
  name: string;
  age: number | null;
  sex: string | null;
  training_experience: string | null;
  training_goals: string[];
  preferred_training_days: string[];
  preferred_session_duration_minutes: number | null;
  injury_notes: string | null;
  created_at: string;
  settings: Settings;
  latest_bodyweight_kg: string | null;
}

export interface Exercise {
  id: string;
  name: string;
  body_part: string;
  primary_muscle: string;
  secondary_muscles: string[];
  equipment: string[];
  difficulty: "beginner" | "intermediate" | "advanced";
  type: string;
  metric_type: string;
  bodyweight_load_factor: string | null;
  default_rest_seconds: number;
  instructions: string[];
  image_url: string | null;
  gif_url: string | null;
  video_url: string | null;
  is_custom: boolean;
  compatible: boolean;
  missing_equipment: string[];
}

export interface ExercisePage {
  data: Exercise[];
  next_cursor: string | null;
  total: number;
}

export interface Vocabulary {
  equipment: string[];
  body_parts: string[];
  muscles: string[];
  body_part_muscles: Record<string, string[]>;
  difficulties: string[];
  types: string[];
  metric_types: string[];
  set_types: string[];
}

export interface BodyweightEntry {
  id: string;
  date: string;
  weight_kg: string;
  source: string;
}

export type DayOfWeek =
  | "monday" | "tuesday" | "wednesday" | "thursday"
  | "friday" | "saturday" | "sunday";

export const DAYS: DayOfWeek[] = [
  "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
];

export interface PlanExercise {
  id: string;
  exercise_id: string;
  order_index: number;
  planned_sets: number;
  planned_reps_min: number | null;
  planned_reps_max: number | null;
  planned_weight_kg: string | null;
  planned_rir: number | null;
  superset_group: string | null;
  notes: string | null;
  exercise: Exercise;
}

export interface Plan {
  id: string;
  name: string;
  day_of_week: DayOfWeek | null;
  target_muscles: string[];
  notes: string | null;
  order_index: number;
  created_at: string;
  exercises: PlanExercise[];
}

export interface Week {
  days: Record<DayOfWeek, Plan[]>;
  unscheduled: Plan[];
}

export type SetType =
  | "warmup" | "working" | "drop_set" | "failure"
  | "rest_pause" | "amrap" | "backoff" | "other";

export type MetricType =
  | "weight_reps" | "bodyweight_reps" | "weighted_bodyweight"
  | "time" | "distance" | "time_distance";

export type SessionStatus = "planned" | "in_progress" | "completed" | "cancelled";

export interface SetRecord {
  id: string;
  set_number: number;
  weight_kg: string | null;
  reps: number | null;
  duration_seconds: number | null;
  distance_m: string | null;
  rir: number | null;
  rpe: string | null;
  failure: boolean;
  set_type: SetType;
  rest_seconds: number | null;
  notes: string | null;
  performed_at: string;
}

export interface LastPerformance {
  date: string;
  sets: SetRecord[];
}

export interface SessionExercise {
  id: string;
  exercise_id: string;
  order_index: number;
  planned_sets: number | null;
  planned_reps_min: number | null;
  planned_reps_max: number | null;
  replaced_from_exercise_id: string | null;
  superset_group: string | null;
  skipped: boolean;
  notes: string | null;
  exercise: Exercise;
  sets: SetRecord[];
  last_performance: LastPerformance | null;
}

export interface WorkoutSession {
  id: string;
  workout_id: string | null;
  name: string;
  date: string;
  start_time: string;
  end_time: string | null;
  status: SessionStatus;
  duration_seconds: number | null;
  notes: string | null;
  exercises: SessionExercise[];
}

export interface SessionSummary {
  id: string;
  name: string;
  date: string;
  status: SessionStatus;
  duration_seconds: number | null;
  notes: string | null;
  exercise_count: number;
  set_count: number;
}

export interface Rank {
  level: number;
  name: string;
  threshold: number;
  band: number;
  color: string;
  blurb: string;
}

export interface Stats {
  current_streak: number;
  longest_streak: number;
  total_sessions: number;
  sessions_this_week: number;
  sets_this_week: number;
  volume_this_week_kg: string;
  total_volume_kg: string;
  last_session_date: string | null;
  trained_today: boolean;
  active_days: string[];
  rank: Rank;
  next_rank: Rank | null;
  progress_to_next: number;
  ladder: Rank[];
  heatmap_ramp: string[];
}

export interface PersonalRecord {
  record_type: string;
  qualifier: string;
  value: string;
  reps: number | null;
  weight_kg: string | null;
  achieved_on: string;
  session_id: string | null;
  exercise_id: string;
  exercise_name: string;
}

export interface SessionPoint {
  date: string;
  session_id: string;
  top_weight_kg: string | null;
  top_reps: number | null;
  best_e1rm_kg: string | null;
  volume_kg: string;
  sets: number;
}

export interface ExerciseProgress {
  exercise_id: string;
  exercise_name: string;
  metric_type: string;
  points: SessionPoint[];
  records: PersonalRecord[];
}

export interface Progress {
  weekly: { week_start: string; volume_kg: string; sets: number; sessions: number }[];
  muscles: { muscle: string; sets: number }[];
  sessions_completed: number;
  adherence: number | null;
  consistency_weeks: number;
}

export interface ProposedExercise {
  exercise: Exercise;
  sets: number;
  reps_min: number;
  reps_max: number;
  rationale: string;
}

export interface WorkoutProposal {
  name: string;
  target_muscles: string[];
  exercises: ProposedExercise[];
  notes: string;
  source: "ai" | "rules";
  warnings: string[];
}

export interface AiBudget {
  ai_configured: boolean;
  used_today: number;
  daily_limit: number;
  remaining: number;
}

export interface Analysis {
  exercise_name: string;
  sessions: number;
  observed: string[];
  interpretation: string[];
  suggestion: string;
  enough_data: boolean;
  source: "ai" | "rules";
}
