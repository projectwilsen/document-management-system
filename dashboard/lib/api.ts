const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface QuotaResponse {
  remaining: number | null;
  limit: number | null;
  used: number;
}

export interface MeResponse {
  id: string;
  email: string;
  role: "owner" | "member";
  organization_id: string;
  plan: "free" | "starter" | "pro";
  quota: QuotaResponse;
}

export interface UserOut {
  id: string;
  email: string;
  role: "owner" | "member";
  created_at: string;
}

export const api = {
  register: (email: string, password: string, name?: string, invite?: string) => {
    const url = invite ? `/auth/register?invite=${invite}` : "/auth/register";
    return request<TokenResponse>(url, {
      method: "POST",
      body: JSON.stringify({ email, password, name }),
    });
  },
  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: () => request<MeResponse>("/me"),
  quota: () => request<QuotaResponse>("/usage/quota"),
  listUsers: () => request<UserOut[]>("/admin/users"),
  invite: () => request<{ invite_url: string }>("/admin/users/invite", { method: "POST" }),
  removeUser: (id: string) => request<void>(`/admin/users/${id}`, { method: "DELETE" }),
};
