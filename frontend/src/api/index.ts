import { api } from "./client";
import type { AIStatus, ActivityDay, Company, Goal, LeetCodeStatus, Page, Problem, Revision, Summary, Topic, TopicStat, User } from "../types";

const d = <T,>(p: Promise<{ data: T }>) => p.then((r) => r.data);

export const authApi = {
  register: (b: { email: string; password: string; name: string }) => d<{ access_token: string }>(api.post("/auth/register", b)),
  login: (b: { email: string; password: string }) => d<{ access_token: string }>(api.post("/auth/login", b)),
  logout: () => d(api.post("/auth/logout")),
  forgot: (email: string) => d<{ message: string }>(api.post("/auth/forgot-password", { email })),
  reset: (token: string, password: string) => d(api.post("/auth/reset-password", { token, password })),
  me: () => d<User>(api.get("/auth/me")),
  providers: () => d<{ google: boolean }>(api.get("/auth/providers")),
};
export const userApi = {
  update: (b: Record<string, unknown>) => d<User>(api.patch("/users/me", b)),
  remove: () => d(api.delete("/users/me")),
};
export const dashApi = {
  summary: () => d<Summary>(api.get("/dashboard/summary")),
  activity: (days = 365) => d<{ start: string; days: number; items: ActivityDay[] }>(api.get("/dashboard/activity", { params: { days } })),
  topics: () => d<TopicStat[]>(api.get("/dashboard/topic-progress")),
  recent: () => d<Problem[]>(api.get("/dashboard/recent-problems")),
};
export interface ProblemQuery { q?: string; difficulty?: string; status?: string; topic_id?: number; company_id?: number; bookmarked?: boolean; sort?: string; page?: number; page_size?: number }
export const problemApi = {
  list: (params: ProblemQuery) => d<Page<Problem>>(api.get("/problems", { params })),
  get: (id: number) => d<Problem>(api.get(`/problems/${id}`)),
  create: (b: Record<string, unknown>) => d<Problem>(api.post("/problems", b)),
  update: (id: number, b: Record<string, unknown>) => d<Problem>(api.patch(`/problems/${id}`, b)),
  remove: (id: number) => d(api.delete(`/problems/${id}`)),
  bookmark: (id: number) => d<Problem>(api.post(`/problems/${id}/bookmark`)),
  addNote: (id: number, body: string) => d(api.post(`/problems/${id}/notes`, { body })),
  removeNote: (id: number, noteId: number) => d(api.delete(`/problems/${id}/notes/${noteId}`)),
  scheduleRevision: (id: number) => d<Revision>(api.post(`/problems/${id}/revision`, {})),
};
export const topicApi = {
  list: () => d<Topic[]>(api.get("/topics")),
  create: (name: string) => d<Topic>(api.post("/topics", { name })),
  rename: (id: number, name: string) => d<Topic>(api.patch(`/topics/${id}`, { name })),
  remove: (id: number) => d(api.delete(`/topics/${id}`)),
  companies: () => d<Company[]>(api.get("/companies")),
};
export const goalApi = {
  list: () => d<Goal[]>(api.get("/goals")),
  create: (b: Record<string, unknown>) => d<Goal>(api.post("/goals", b)),
  remove: (id: number) => d(api.delete(`/goals/${id}`)),
};
export const revisionApi = {
  list: (params: { status?: string } = {}) => d<Revision[]>(api.get("/revisions", { params })),
  create: (b: Record<string, unknown>) => d<Revision>(api.post("/revisions", b)),
  update: (id: number, b: Record<string, unknown>) => d<Revision>(api.patch(`/revisions/${id}`, b)),
  remove: (id: number) => d(api.delete(`/revisions/${id}`)),
};
export const analyticsApi = {
  overview: () => d<Record<string, any>>(api.get("/analytics/overview")),
  difficulty: () => d<{ difficulty: string; total: number; solved: number }[]>(api.get("/analytics/difficulty")),
  topics: () => d<TopicStat[]>(api.get("/analytics/topics")),
  activity: (granularity: "week" | "month", periods: number) =>
    d<{ period: string; solved: number; attempts: number; active_days: number }[]>(api.get("/analytics/activity", { params: { granularity, periods } })),
};
export const lcApi = {
  status: () => d<LeetCodeStatus>(api.get("/integrations/leetcode/status")),
  connect: (username: string) => d<LeetCodeStatus>(api.post("/integrations/leetcode/connect", { username })),
  sync: () => d<LeetCodeStatus & { imported: number; skipped_existing: number }>(api.post("/integrations/leetcode/sync")),
  disconnect: () => d(api.delete("/integrations/leetcode/disconnect")),
};
export const aiApi = {
  status: () => d<AIStatus>(api.get("/ai/status")),
  chat: (message: string, conversation_id?: number) => d<{ conversation_id: number; reply: string; provider: string }>(api.post("/ai/chat", { message, conversation_id })),
  analyze: () => d<{ conversation_id: number; reply: string; provider: string }>(api.post("/ai/analyze-performance", {})),
  recommend: () => d<{ conversation_id: number; reply: string; provider: string }>(api.post("/ai/recommendations", {})),
  roadmap: () => d<{ conversation_id: number; reply: string; provider: string }>(api.post("/ai/roadmap", {})),
};
export const adminApi = {
  users: () => d<{ total: number; items: { id: number; email: string; name: string; is_admin: boolean; is_active: boolean; problem_count: number }[] }>(api.get("/admin/users")),
  setActive: (id: number, is_active: boolean) => d(api.patch(`/admin/users/${id}`, { is_active })),
  system: () => d<Record<string, any>>(api.get("/admin/system")),
};
