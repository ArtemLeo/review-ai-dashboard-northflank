import api from "./api";
import type { AdminSession, LoginInput } from "@/types";

/** Authentication service — wraps the login, session and logout endpoints. */
export const authService = {
  /** Sends credentials; on success the server sets the httpOnly session cookie. */
  async login(input: LoginInput): Promise<AdminSession> {
    const response = await api.post<AdminSession>("/auth/login", input);
    return response.data;
  },

  /** Asks the server who the browser's session belongs to; rejects with 401 when there is none. */
  async fetchSession(): Promise<AdminSession> {
    const response = await api.get<AdminSession>("/auth/me");
    return response.data;
  },

  /** Ends the session on the server, which expires the session cookie. */
  async logout(): Promise<void> {
    await api.post("/auth/logout");
  },
};
