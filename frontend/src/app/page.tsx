"use client";

import { useState, useCallback, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Sidebar, type TelegramAuthUser } from "@/components/chat/Sidebar";
import { ChatArea } from "@/components/chat/ChatArea";
import { RightPanel } from "@/components/chat/RightPanel";
import { ConnectTelegramCard } from "@/components/chat/ConnectChannelCard";
import { api, getAuthToken, setAuthToken } from "@/lib/api";
import type { ChatSummary } from "@/types/chat";

export default function HomePage() {
  const queryClient = useQueryClient();
  const [activeChannel, setActiveChannel] = useState("web");
  const [activeTab, setActiveTab] = useState("chat");
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  useEffect(() => {
    setToken(getAuthToken());
  }, []);

  const { data: account } = useQuery({
    queryKey: ["account", token],
    queryFn: () => api.accounts.me(),
    enabled: !!token,
  });

  const { data: chatList = [], isLoading: listLoading } = useQuery({
    queryKey: ["chats", !!token],
    queryFn: () => api.chats.list(!!token),
    select: (data): ChatSummary[] =>
      data.map((c) => ({
        id: c.id,
        title: c.title,
        model: c.model,
        lastMessagePreview: c.lastMessagePreview,
        lastMessageAt: new Date(c.lastMessageAt),
      })),
  });

  const { data: currentChat, isLoading: chatLoading } = useQuery({
    queryKey: ["chat", activeChatId],
    queryFn: () => api.chats.getOne(activeChatId!),
    enabled: !!activeChatId,
  });

  const createMutation = useMutation({
    mutationFn: () => api.chats.create(),
    onSuccess: (newChat) => {
      queryClient.invalidateQueries({ queryKey: ["chats"] });
      setActiveChatId(newChat.id);
    },
  });

  useEffect(() => {
    if (listLoading || chatList.length > 0 || createMutation.isPending) return;
    createMutation.mutate();
  }, [listLoading, chatList.length, createMutation.isPending]);

  useEffect(() => {
    if (activeChatId == null && chatList[0]) setActiveChatId(chatList[0].id);
  }, [activeChatId, chatList]);

  const handleCreateChat = useCallback(() => {
    createMutation.mutate();
  }, [createMutation]);

  const handleSendMessage = useCallback(
    async (
      message: string,
      modelId: string,
      opts?: { signal?: AbortSignal; withVoice?: boolean },
    ) => {
      if (!activeChatId) return undefined;
      const res = await api.chats.send(activeChatId, message, modelId, opts);
      queryClient.invalidateQueries({ queryKey: ["chats"] });
      queryClient.invalidateQueries({ queryKey: ["chat", activeChatId] });
      return res;
    },
    [activeChatId, queryClient],
  );

  const handleSendVoice = useCallback(
    async (chatId: string, audioBlob: Blob, modelId: string) => {
      const result = await api.chats.sendVoice(chatId, audioBlob, modelId);
      queryClient.invalidateQueries({ queryKey: ["chats"] });
      queryClient.invalidateQueries({ queryKey: ["chat", chatId] });
      return result;
    },
    [queryClient],
  );

  const handleModelChange = useCallback(
    async (modelId: string) => {
      if (!activeChatId) return;
      await api.chats.setModel(activeChatId, modelId);
      queryClient.invalidateQueries({ queryKey: ["chat", activeChatId] });
      queryClient.invalidateQueries({ queryKey: ["chats"] });
    },
    [activeChatId, queryClient],
  );

  const handleSetAgent = useCallback(
    async (agentId: string) => {
      if (!activeChatId) return;
      await api.chats.setAgent(activeChatId, agentId);
      queryClient.invalidateQueries({ queryKey: ["chat", activeChatId] });
      queryClient.invalidateQueries({ queryKey: ["chats"] });
    },
    [activeChatId, queryClient],
  );

  const handleSaveMcp = useCallback(
    async (serverUrl: string, secret: string) => {
      await api.accounts.setMcp({ serverUrl, secret });
      queryClient.invalidateQueries({ queryKey: ["account", token] });
    },
    [queryClient, token],
  );

  const handleTelegramAuth = useCallback(
    async (user: TelegramAuthUser) => {
      setAuthError(null);
      try {
        const res = await api.auth.telegramLogin(user);
        setAuthToken(res.token);
        setToken(res.token);
        queryClient.setQueryData(["account", res.token], {
          id: res.accountId,
          channel: res.channel,
          externalId: res.externalId,
          zapierMcpServerUrl: null,
        });
        queryClient.invalidateQueries({ queryKey: ["account"] });
        queryClient.invalidateQueries({ queryKey: ["chats"] });
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Ошибка входа";
        setAuthError(msg);
        console.error("Telegram login failed:", e);
      }
    },
    [queryClient],
  );

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background">
      <Sidebar
        activeChannel={activeChannel}
        onChannelChange={setActiveChannel}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        account={account ?? undefined}
        authError={authError}
        onTelegramAuth={handleTelegramAuth}
        onLogout={() => {
          setAuthToken(null);
          setToken(null);
          setAuthError(null);
          queryClient.invalidateQueries({ queryKey: ["chats"] });
        }}
      />
      {activeChannel === "telegram" && <ConnectTelegramCard />}
      {activeChannel !== "telegram" && (
        <ChatArea
          chatId={activeChatId}
          messages={currentChat?.messages ?? []}
          modelId={currentChat?.modelId ?? "openrouter/auto"}
          account={account ?? undefined}
          isLoading={!!activeChatId && chatLoading}
          onSendMessage={handleSendMessage}
          onSendVoice={handleSendVoice}
          onModelChange={handleModelChange}
          onSaveMcp={handleSaveMcp}
          onInvalidateChat={() => {
            if (activeChatId) {
              queryClient.invalidateQueries({
                queryKey: ["chat", activeChatId],
              });
              queryClient.invalidateQueries({ queryKey: ["chats"] });
            }
          }}
        />
      )}
      <RightPanel
        activeTab={activeTab}
        chatList={chatList}
        activeChatId={activeChatId ?? undefined}
        activeAgentId={currentChat?.agentId ?? undefined}
        onSelectChat={setActiveChatId}
        onCreateChat={handleCreateChat}
        onSelectAgent={handleSetAgent}
      />
    </div>
  );
}
