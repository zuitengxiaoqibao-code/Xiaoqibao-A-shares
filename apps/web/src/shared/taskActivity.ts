export type TaskActivityState = "queued" | "running" | "succeeded" | "failed";

export type TaskActivity = {
  id: string;
  label: string;
  stage: string;
  state: TaskActivityState;
  percent?: number | null;
  detail?: string | null;
  error?: string | null;
  updatedAt: string;
};

const tasks = new Map<string, TaskActivity>();
const listeners = new Set<() => void>();
let snapshot: TaskActivity[] = [];

function notify(): void {
  snapshot = [...tasks.values()].sort((left, right) => right.updatedAt.localeCompare(left.updatedAt));
  listeners.forEach((listener) => listener());
}

export function updateTaskActivity(input: Omit<TaskActivity, "updatedAt"> & { updatedAt?: string }): TaskActivity {
  const next = { ...input, updatedAt: input.updatedAt ?? new Date().toISOString() };
  tasks.set(input.id, next);
  notify();
  return next;
}

export function clearTaskActivity(id: string): void { if (tasks.delete(id)) notify(); }
export function readTaskActivities(): TaskActivity[] { return snapshot; }
export function subscribeTaskActivity(listener: () => void): () => void { listeners.add(listener); return () => listeners.delete(listener); }
export function resetTaskActivityForTests(): void { tasks.clear(); notify(); }
