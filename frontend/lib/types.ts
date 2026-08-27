export interface UserPublic {
  id: string;
  email: string;
  created_at: string;
  is_student: boolean;
  exam_track: string | null;
  display_name: string | null;
}

export type TaskStatus = "todo" | "in_progress" | "done";

export interface Note {
  id: string;
  owner_id: string;
  title: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  owner_id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  due_date: string | null;
  reminder_minutes_before: number | null;
  created_at: string;
  updated_at: string;
}

export interface PushSubscriptionKeys {
  p256dh: string;
  auth: string;
}

export interface PushSubscriptionRequest {
  endpoint: string;
  keys: PushSubscriptionKeys;
}

// --- Exam prep (Panhellenic) ---

export interface ExamSubject {
  id: string;
  code: string;
  name_el: string;
  name_en: string;
  weight_coefficient: number;
  display_order: number;
}

export interface ExamConfig {
  track: string;
  academic_year: string;
  exam_date: string;
  days_remaining: number;
}

export type StudySessionSource = "focus_timer" | "manual";

export interface StudySession {
  id: string;
  owner_id: string;
  subject_code: string | null;
  duration_seconds: number;
  source: StudySessionSource;
  occurred_at: string;
}

export interface SubjectAllocation {
  subject_code: string;
  name_el: string;
  name_en: string;
  weight_coefficient: number;
  planned_share: number;
  actual_seconds: number;
  actual_share: number;
  delta: number;
}

// --- Accountability pods ---

export interface Pod {
  id: string;
  name: string;
  invite_code: string;
  owner_id: string;
  member_count: number;
  created_at: string;
}

export interface PodMemberFeedItem {
  user_id: string;
  display_name: string;
  current_streak: number;
  active_today: boolean;
  last_active_at: string | null;
}

export interface PodFeed {
  pod: Pod;
  members: PodMemberFeedItem[];
}

export interface Streak {
  current_streak: number;
  active_today: boolean;
  last_active_at: string | null;
}
