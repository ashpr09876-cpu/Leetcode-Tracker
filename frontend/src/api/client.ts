import axios, { AxiosError } from "axios";

export const api = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
  headers: { "X-Requested-With": "codetrack" },
});

// The access token lives only in memory. The refresh token is an HttpOnly cookie the JS cannot read.
let accessToken: string | null = null;
let onAuthLost: (() => void) | null = null;
export const setAccessToken = (t: string | null) => { accessToken = t; };
export const setAuthLostHandler = (fn: (() => void) | null) => { onAuthLost = fn; };

api.interceptors.request.use((cfg) => {
  if (accessToken) cfg.headers.Authorization = `Bearer ${accessToken}`;
  return cfg;
});

let refreshing: Promise<string | null> | null = null;
export function refreshSession(): Promise<string | null> {
  if (!refreshing) {
    refreshing = api
      .post<{ access_token: string }>("/auth/refresh")
      .then((r) => { setAccessToken(r.data.access_token); return r.data.access_token; })
      .catch(() => { setAccessToken(null); return null; })
      .finally(() => { refreshing = null; });
  }
  return refreshing;
}

api.interceptors.response.use(
  (r) => r,
  async (err: AxiosError) => {
    const cfg = err.config as (typeof err.config & { _retry?: boolean }) | undefined;
    if (err.response?.status === 401 && cfg && !cfg._retry && !cfg.url?.startsWith("/auth/")) {
      cfg._retry = true;
      const t = await refreshSession();
      if (t) { cfg.headers.Authorization = `Bearer ${t}`; return api(cfg); }
      onAuthLost?.();
    }
    return Promise.reject(err);
  }
);

/** Turn any backend/network error into a user-readable message. */
export function errMsg(e: unknown): string {
  if (axios.isAxiosError(e)) {
    if (!e.response) return "Cannot reach the server. Check that the backend is running.";
    const d = e.response.data?.detail;
    if (typeof d === "string") {
      const errs = e.response.data?.errors as { loc: string[]; msg: string }[] | undefined;
      return errs?.length ? `${d}: ${errs.map((x) => `${x.loc.slice(1).join(".")} ${x.msg}`).join("; ")}` : d;
    }
    if (d && typeof d === "object" && typeof d.message === "string") return d.message;
    return `Request failed (${e.response.status})`;
  }
  return e instanceof Error ? e.message : "Something went wrong";
}

export function errCode(e: unknown): string | undefined {
  return axios.isAxiosError(e) ? e.response?.data?.detail?.code : undefined;
}
