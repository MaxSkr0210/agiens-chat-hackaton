// Пустая строка = запросы на тот же origin (нужен proxy в next.config для /api). Так работает за ngrok (HTTPS).
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
  if (typeof window !== "undefined") {
    if (token) window.localStorage.setItem("agiens_token", token);
    else window.localStorage.removeItem("agiens_token");
  }
}

export function getAuthToken(): string | null {
  if (authToken) return authToken;
  if (typeof window !== "undefined")
    return window.localStorage.getItem("agiens_token");
  return null;
}

type RequestOptions = {
  method?: string;
  headers?: HeadersInit;
  body?: unknown;
  signal?: AbortSignal;
};

async function request<T>(path: string, options?: RequestOptions): Promise<T> {
  const base =
    API_URL || (typeof window !== "undefined" ? "" : "http://localhost:3001");
  const url = path.startsWith("http") ? path : `${base}${path}`;
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...options?.headers,
  };
  const token = getAuthToken();
  if (token)
    (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  const res = await fetch(url, {
    method: options?.method,
    headers,
    body: options?.body != null ? JSON.stringify(options.body) : undefined,
    signal: options?.signal,
  });
  if (!res.ok) throw new Error(await res.text());
  const contentType = res.headers.get("content-type");
  const hasBody =
    res.status !== 204 && res.headers.get("content-length") !== "0";
  if (hasBody && contentType?.includes("application/json")) {
    return res.json() as Promise<T>;
  }
  return undefined as T;
}

export interface SendVoiceResponse {
  content: string;
  audioBase64: string;
}

export interface SendMessageResponse {
  content: string;
  audioBase64?: string; // when withVoice: true (Level 2: TTS response to text)
}

export interface ChatSummaryDto {
  id: string;
  title: string;
  model: string;
  lastMessagePreview: string;
  lastMessageAt: string;
}

export interface ChatWithMessagesDto {
  id: string;
  title: string;
  modelId: string;
  agentId?: string | null;
  messages: { id: string; role: string; content: string; createdAt: string }[];
}

export interface AccountMeDto {
  id: string;
  channel: string;
  externalId: string;
  zapierMcpServerUrl: string | null;
}

export interface AgentDto {
  id: string;
  name: string;
  description: string;
  icon: string;
  systemPrompt: string;
  modelId?: string | null;
  supportedCategories?: string | null;
}

export interface TicketDto {
  id: string;
  chatId: string;
  status: string;
  category: string;
  assignedAgentId: string | null;
  priority: number;
  createdAt: string;
  updatedAt: string;
}

/** Backend: POST /api/chats body (create chat, optional modelId) */
export interface CreateChatBody {
  modelId?: string;
}

/** Backend: POST /api/chats/:id/send body */
export interface SendMessageBody {
  message: string;
  modelId?: string | null;
  withVoice?: boolean;
}

/** Backend: POST /api/chats/:id/model body */
export interface SetModelBody {
  modelId: string;
}

/** Backend: PATCH /api/chats/:id/agent body */
export interface SetAgentBody {
  agentId: string;
}

/** Backend: PATCH /api/accounts/me/mcp body — Zapier at account level */
export interface SetMcpBody {
  serverUrl: string;
  secret: string;
}

export const api = {
  auth: {
    telegramLogin: (data: {
      id: number;
      first_name?: string;
      last_name?: string;
      username?: string;
      photo_url?: string;
      auth_date: number;
      hash: string;
    }) =>
      request<{
        token: string;
        accountId: string;
        channel: string;
        externalId: string;
      }>("/api/auth/telegram", { method: "POST", body: data }),
  },
  accounts: {
    me: () => request<AccountMeDto>("/api/accounts/me"),
    setMcp: (body: SetMcpBody) =>
      request<void>("/api/accounts/me/mcp", { method: "PATCH", body }),
  },
  agents: {
    list: () => request<AgentDto[]>("/api/agents"),
    getOne: (id: string) => request<AgentDto>(`/api/agents/${id}`),
    create: (
      body: Pick<AgentDto, "name" | "description" | "systemPrompt"> & {
        icon?: string;
        supportedCategories?: string | null;
      },
    ) => request<AgentDto>("/api/agents", { method: "POST", body }),
    update: (
      id: string,
      body: Partial<
        Pick<
          AgentDto,
          | "name"
          | "description"
          | "icon"
          | "systemPrompt"
          | "modelId"
          | "supportedCategories"
        >
      >,
    ) => request<AgentDto>(`/api/agents/${id}`, { method: "PATCH", body }),
  },
  chats: {
    list: (forMe?: boolean) =>
      request<ChatSummaryDto[]>(forMe ? "/api/chats?for_me=1" : "/api/chats"),
    create: (body?: CreateChatBody) =>
      request<ChatSummaryDto>("/api/chats", {
        method: "POST",
        body: body ?? {},
      }),
    getOne: (id: string) => request<ChatWithMessagesDto>(`/api/chats/${id}`),
    send: (
      id: string,
      message: string,
      modelId?: string | null,
      opts?: { signal?: AbortSignal; withVoice?: boolean },
    ) =>
      request<SendMessageResponse>(`/api/chats/${id}/send`, {
        method: "POST",
        body: {
          message,
          modelId: modelId ?? undefined,
          withVoice: opts?.withVoice ?? false,
        },
        signal: opts?.signal,
      }),
    sendVoice: async (
      id: string,
      audioBlob: Blob,
      modelId?: string,
    ): Promise<SendVoiceResponse> => {
      const form = new FormData();
      form.append("audio", audioBlob, "audio.webm");
      if (modelId) form.append("modelId", modelId);
      const res = await fetch(`${API_URL}/api/chats/${id}/send-voice`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
    setModel: (id: string, modelId: string) =>
      request<void>(`/api/chats/${id}/model`, {
        method: "POST",
        body: { modelId },
      }),
    setAgent: (id: string, agentId: string) =>
      request<void>(`/api/chats/${id}/agent`, {
        method: "PATCH",
        body: { agentId },
      }),
    getTicket: (chatId: string) =>
      request<TicketDto | null>(`/api/chats/${chatId}/ticket`),
  },
  tickets: {
    list: (status?: string) =>
      request<TicketDto[]>(
        status
          ? `/api/tickets?status=${encodeURIComponent(status)}`
          : "/api/tickets",
      ),
    getOne: (id: string) => request<TicketDto>(`/api/tickets/${id}`),
    update: (
      id: string,
      body: {
        status?: string;
        category?: string;
        assignedAgentId?: string | null;
        priority?: number;
      },
    ) => request<TicketDto>(`/api/tickets/${id}`, { method: "PATCH", body }),
    escalate: (id: string) =>
      request<TicketDto>(`/api/tickets/${id}/escalate`, { method: "PATCH" }),
  },
};
