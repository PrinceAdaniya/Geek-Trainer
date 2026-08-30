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
