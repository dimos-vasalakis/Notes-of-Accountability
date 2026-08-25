export interface UserPublic {
  id: string;
  email: string;
  created_at: string;
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
