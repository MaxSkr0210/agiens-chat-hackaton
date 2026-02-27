"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Bot,
  FileText,
  MessageSquare,
  Mic,
  MicOff,
  Plus,
  Zap,
  Ticket,
  Check,
  X,
  ArrowUpCircle,
} from "lucide-react";
import { api, type AgentDto } from "@/lib/api";
import type { ChatSummary } from "@/types/chat";

interface Props {
  activeTab: string;
  chatList?: ChatSummary[];
  activeChatId?: string;
  activeAgentId?: string | null;
  onSelectChat?: (id: string) => void;
  onCreateChat?: () => void;
  onSelectAgent?: (agentId: string) => void;
}

const automations = [
  {
    id: "1",
    name: "Приветствие",
    trigger: "Новый пользователь",
    action: "Отправить приветствие",
    active: true,
  },
  {
    id: "2",
    name: "Эскалация",
    trigger: "Нет ответа 5 мин",
    action: "Перевод на оператора",
    active: true,
  },
  {
    id: "3",
    name: "FAQ",
    trigger: "Частый вопрос",
    action: "Автоответ из базы",
    active: false,
  },
];

export function RightPanel({
  activeTab,
  chatList = [],
  activeChatId,
  activeAgentId,
  onSelectChat,
  onCreateChat,
  onSelectAgent,
}: Props) {
  return (
    <div className="w-72 h-full glass-panel border-l border-border/50 flex flex-col overflow-hidden">
      {activeTab === "chat" && (
        <ChatHistoryPanel
          chats={chatList}
          activeChatId={activeChatId}
          onSelectChat={onSelectChat}
          onCreateChat={onCreateChat}
        />
      )}
      {activeTab === "agents" && (
        <AgentsPanel
          activeChatId={activeChatId}
          activeAgentId={activeAgentId ?? null}
          onSelectAgent={onSelectAgent}
        />
      )}
      {activeTab === "prompts" && <PromptsPanel />}
    </div>
  );
}

function ChatHistoryPanel({
  chats,
  activeChatId,
  onSelectChat,
  onCreateChat,
}: {
  chats: ChatSummary[];
  activeChatId?: string;
  onSelectChat?: (id: string) => void;
  onCreateChat?: () => void;
}) {
  const formatTime = (d: Date) => {
    const date = d instanceof Date ? d : new Date(d);
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    if (isToday)
      return date.toLocaleTimeString("ru", {
        hour: "2-digit",
        minute: "2-digit",
      });
    return (
      date.toLocaleDateString("ru", { day: "2-digit", month: "2-digit" }) +
      " " +
      date.toLocaleTimeString("ru", { hour: "2-digit", minute: "2-digit" })
    );
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-border/50">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-primary" />
          <span className="font-semibold text-sm">История чатов</span>
        </div>
        {onCreateChat && (
          <motion.button
            type="button"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={onCreateChat}
            className="mt-3 w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-primary/15 hover:bg-primary/25 text-primary text-sm font-medium transition-colors border border-primary/30"
          >
            <Plus className="w-4 h-4" />
            Новый чат
          </motion.button>
        )}
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-2 scrollbar-thin">
        {chats.length === 0 ? (
          <p className="text-xs text-muted-foreground px-2">Пока нет чатов</p>
        ) : (
          chats.map((chat) => (
            <motion.button
              key={chat.id}
              type="button"
              whileHover={{ x: 2 }}
              onClick={() => onSelectChat?.(chat.id)}
              className={`w-full text-left p-3 rounded-lg transition-colors ${
                activeChatId === chat.id
                  ? "bg-primary/15 border border-primary/30"
                  : "bg-secondary/30 hover:bg-secondary/50 border border-transparent"
              }`}
            >
              <p className="text-xs font-medium text-foreground truncate mb-0.5">
                {chat.title}
              </p>
              <p className="text-[10px] text-primary mb-1">{chat.model}</p>
              <p className="text-[11px] text-muted-foreground line-clamp-2 mb-1">
                {chat.lastMessagePreview}
              </p>
              <p className="text-[10px] text-muted-foreground/80">
                {formatTime(chat.lastMessageAt)}
              </p>
            </motion.button>
          ))
        )}
      </div>
    </div>
  );
}

function AgentsPanel({
  activeChatId,
  activeAgentId,
  onSelectAgent,
}: {
  activeChatId?: string;
  activeAgentId: string | null;
  onSelectAgent?: (agentId: string) => void;
}) {
  const { data: agents = [] } = useQuery({
    queryKey: ["agents"],
    queryFn: () => api.agents.list(),
  });

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-border/50">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-primary" />
          <span className="font-semibold text-sm">Агенты</span>
        </div>
        {activeChatId && (
          <p className="text-[10px] text-muted-foreground mt-1">
            Выберите агента для текущего чата
          </p>
        )}
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-2 scrollbar-thin">
        {agents.map((a) => {
          const isSelected = activeAgentId === a.id;
          return (
            <motion.button
              key={a.id}
              type="button"
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
              onClick={() => activeChatId && onSelectAgent?.(a.id)}
              disabled={!activeChatId}
              className={`w-full text-left p-3 rounded-lg transition-colors border ${
                isSelected
                  ? "bg-primary/15 border-primary/50"
                  : "bg-secondary/30 hover:bg-secondary/50 border-transparent"
              } ${!activeChatId ? "opacity-60 cursor-not-allowed" : "cursor-pointer"}`}
            >
              <div className="flex items-center gap-2 mb-1">
                <span>{a.icon}</span>
                <span className="text-sm font-medium">{a.name}</span>
                {isSelected && (
                  <span className="text-[10px] text-primary ml-auto">✓</span>
                )}
              </div>
              <p className="text-[11px] text-muted-foreground">
                {a.description}
              </p>
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}

function PromptsPanel() {
  const queryClient = useQueryClient();
  const { data: agents = [] } = useQuery({
    queryKey: ["agents"],
    queryFn: () => api.agents.list(),
  });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editPrompt, setEditPrompt] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newIcon, setNewIcon] = useState("🤖");
  const [newSystemPrompt, setNewSystemPrompt] = useState("");

  const updateMutation = useMutation({
    mutationFn: ({ id, systemPrompt }: { id: string; systemPrompt: string }) =>
      api.agents.update(id, { systemPrompt }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents"] });
      setEditingId(null);
      setEditPrompt("");
    },
  });

  const createMutation = useMutation({
    mutationFn: () =>
      api.agents.create({
        name: newName.trim() || "Новый промпт",
        description: newDescription.trim() || "—",
        icon: newIcon || "🤖",
        systemPrompt: newSystemPrompt.trim() || "Ты — полезный помощник.",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents"] });
      setIsCreating(false);
      setNewName("");
      setNewDescription("");
      setNewIcon("🤖");
      setNewSystemPrompt("");
    },
  });

  const startEdit = (a: AgentDto) => {
    setEditingId(a.id);
    setEditPrompt(a.systemPrompt);
  };
  const cancelEdit = () => {
    setEditingId(null);
    setEditPrompt("");
  };
  const saveEdit = () => {
    if (editingId && editPrompt.trim()) {
      updateMutation.mutate({ id: editingId, systemPrompt: editPrompt.trim() });
    }
  };
  const handleCreateSubmit = () => {
    createMutation.mutate();
  };
  const cancelCreate = () => {
    setIsCreating(false);
    setNewName("");
    setNewDescription("");
    setNewIcon("🤖");
    setNewSystemPrompt("");
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-border/50">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-primary" />
          <span className="font-semibold text-sm">Управление промптами</span>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-2 scrollbar-thin">
        {isCreating ? (
          <div className="p-3 rounded-lg bg-secondary/30 border border-primary/30 space-y-2">
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Название"
              className="w-full text-xs px-2 py-1.5 rounded bg-background/50 border border-border/50 focus:outline-none focus:ring-1 focus:ring-primary/50"
            />
            <input
              type="text"
              value={newDescription}
              onChange={(e) => setNewDescription(e.target.value)}
              placeholder="Описание"
              className="w-full text-xs px-2 py-1.5 rounded bg-background/50 border border-border/50 focus:outline-none focus:ring-1 focus:ring-primary/50"
            />
            <input
              type="text"
              value={newIcon}
              onChange={(e) => setNewIcon(e.target.value)}
              placeholder="Иконка (эмодзи)"
              className="w-full text-xs px-2 py-1.5 rounded bg-background/50 border border-border/50 focus:outline-none focus:ring-1 focus:ring-primary/50"
            />
            <textarea
              value={newSystemPrompt}
              onChange={(e) => setNewSystemPrompt(e.target.value)}
              placeholder="Системный промпт"
              className="w-full min-h-[80px] text-[11px] font-mono px-2 py-1.5 rounded bg-background/50 border border-border/50 resize-y focus:outline-none focus:ring-1 focus:ring-primary/50"
            />
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleCreateSubmit}
                disabled={createMutation.isPending}
                className="flex-1 py-1.5 rounded text-xs font-medium bg-primary/20 text-primary hover:bg-primary/30 transition-colors"
              >
                {createMutation.isPending ? "Создание…" : "Сохранить"}
              </button>
              <button
                type="button"
                onClick={cancelCreate}
                className="py-1.5 px-2 rounded text-xs text-muted-foreground hover:bg-secondary/50"
              >
                Отмена
              </button>
            </div>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setIsCreating(true)}
            className="w-full p-2.5 rounded-lg border border-dashed border-border/80 text-xs text-muted-foreground hover:text-foreground hover:border-primary/50 hover:bg-primary/5 transition-colors flex items-center justify-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Создать промпт
          </button>
        )}
        {agents.map((a) => (
          <div key={a.id} className="p-3 rounded-lg bg-secondary/30">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium">
                {a.icon} {a.name}
              </span>
              {editingId === a.id ? (
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={saveEdit}
                    disabled={updateMutation.isPending || !editPrompt.trim()}
                    className="p-1 rounded text-primary hover:bg-primary/20"
                    title="Сохранить"
                  >
                    <Check className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={cancelEdit}
                    className="p-1 rounded text-muted-foreground hover:bg-secondary/50"
                    title="Отмена"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => startEdit(a)}
                  className="text-[10px] text-primary hover:underline"
                >
                  Изменить
                </button>
              )}
            </div>
            {editingId === a.id ? (
              <textarea
                value={editPrompt}
                onChange={(e) => setEditPrompt(e.target.value)}
                className="w-full min-h-[100px] text-[11px] font-mono bg-background/50 rounded p-2 border border-border/50 resize-y focus:outline-none focus:ring-1 focus:ring-primary/50"
                placeholder="Системный промпт агента"
              />
            ) : (
              <p className="text-[11px] text-muted-foreground font-mono bg-background/50 rounded p-2 whitespace-pre-wrap line-clamp-4">
                {a.systemPrompt}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function TicketsPanel({
  chatList = [],
  activeChatId,
  onSelectChat,
}: {
  chatList?: ChatSummary[];
  activeChatId?: string;
  onSelectChat?: (id: string) => void;
}) {
  const queryClient = useQueryClient();
  const { data: tickets = [] } = useQuery({
    queryKey: ["tickets"],
    queryFn: () => api.tickets.list(),
  });
  const { data: agents = [] } = useQuery({
    queryKey: ["agents"],
    queryFn: () => api.agents.list(),
  });
  const escalateMutation = useMutation({
    mutationFn: (id: string) => api.tickets.escalate(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tickets"] }),
  });

  const getAgentName = (id: string | null) => {
    if (!id) return "—";
    const a = agents.find((x) => x.id === id);
    return a ? `${a.icon} ${a.name}` : id;
  };

  const statusLabel: Record<string, string> = {
    open: "Открыт",
    assigned: "Назначен",
    in_progress: "В работе",
    resolved: "Решён",
    escalated: "Эскалирован",
  };
  const categoryLabel: Record<string, string> = {
    general: "Общий",
    technical: "Технический",
    billing: "Оплата / возврат",
    other: "Другое",
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-border/50">
        <div className="flex items-center gap-2">
          <Ticket className="w-4 h-4 text-primary" />
          <span className="font-semibold text-sm">Очередь тикетов</span>
        </div>
        <p className="text-[10px] text-muted-foreground mt-1">
          Маршрутизация по категориям
        </p>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-2 scrollbar-thin">
        {tickets.length === 0 ? (
          <p className="text-xs text-muted-foreground px-2">
            Пока нет тикетов. Отправьте сообщение в чате — тикет создастся
            автоматически.
          </p>
        ) : (
          tickets.map((t) => {
            const chat = chatList.find((c) => c.id === t.chatId);
            const isActive = activeChatId === t.chatId;
            return (
              <div
                key={t.id}
                className={`p-3 rounded-lg border transition-colors ${
                  isActive
                    ? "bg-primary/10 border-primary/40"
                    : "bg-secondary/30 border-transparent hover:bg-secondary/50"
                }`}
              >
                <button
                  type="button"
                  onClick={() => onSelectChat?.(t.chatId)}
                  className="w-full text-left"
                >
                  <p className="text-[10px] text-muted-foreground mb-0.5">
                    {statusLabel[t.status] ?? t.status} ·{" "}
                    {categoryLabel[t.category] ?? t.category}
                  </p>
                  <p className="text-xs font-medium truncate">
                    {chat?.title ?? t.chatId.slice(0, 8)}
                  </p>
                  <p className="text-[10px] text-muted-foreground mt-0.5">
                    Агент: {getAgentName(t.assignedAgentId)}
                  </p>
                </button>
                {t.status !== "escalated" && t.status !== "resolved" && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      escalateMutation.mutate(t.id);
                    }}
                    disabled={escalateMutation.isPending}
                    className="mt-2 flex items-center gap-1 text-[10px] text-amber-600 hover:text-amber-500"
                  >
                    <ArrowUpCircle className="w-3.5 h-3.5" />
                    Эскалировать
                  </button>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

function VoicePanel() {
  const [speaking, setSpeaking] = useState(false);

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-border/50">
        <div className="flex items-center gap-2">
          <Mic className="w-4 h-4 text-primary" />
          <span className="font-semibold text-sm">Голосовой виджет</span>
        </div>
      </div>
      <div className="flex-1 flex flex-col items-center justify-center p-6 gap-6">
        <motion.button
          type="button"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setSpeaking(!speaking)}
          className={`w-24 h-24 rounded-full flex items-center justify-center transition-colors ${
            speaking
              ? "bg-destructive/20 text-destructive"
              : "bg-primary/20 text-primary"
          }`}
        >
          <motion.div
            animate={speaking ? { scale: [1, 1.2, 1] } : {}}
            transition={{ repeat: Infinity, duration: 1.5 }}
          >
            {speaking ? (
              <MicOff className="w-8 h-8" />
            ) : (
              <Mic className="w-8 h-8" />
            )}
          </motion.div>
        </motion.button>
        {speaking && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-1"
          >
            {[...Array(5)].map((_, i) => (
              <motion.div
                key={i}
                animate={{ height: [8, 24, 8] }}
                transition={{
                  repeat: Infinity,
                  duration: 0.8,
                  delay: i * 0.15,
                }}
                className="w-1 rounded-full bg-primary"
              />
            ))}
          </motion.div>
        )}
        <div className="text-center">
          <p className="text-xs font-medium">
            {speaking ? "Слушаю..." : "Нажмите для записи"}
          </p>
          <p className="text-[10px] text-muted-foreground mt-1">
            ElevenLabs Voice Widget
          </p>
        </div>
        <div className="w-full space-y-2">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
            Голосовой ответ на текст
          </p>
          <div className="p-3 rounded-lg bg-secondary/30 text-xs text-muted-foreground">
            🔊 AI может озвучивать свои ответы используя TTS
          </div>
        </div>
      </div>
    </div>
  );
}

function AutomationPanel() {
  const [items, setItems] = useState(automations);

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-border/50">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-primary" />
          <span className="font-semibold text-sm">Автоматизация</span>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-2 scrollbar-thin">
        {items.map((a) => (
          <div key={a.id} className="p-3 rounded-lg bg-secondary/30">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium">{a.name}</span>
              <button
                type="button"
                onClick={() =>
                  setItems((prev) =>
                    prev.map((x) =>
                      x.id === a.id ? { ...x, active: !x.active } : x,
                    ),
                  )
                }
                className={`w-8 h-4 rounded-full transition-colors relative ${a.active ? "bg-primary" : "bg-muted"}`}
              >
                <div
                  className={`w-3 h-3 rounded-full bg-foreground absolute top-0.5 transition-all ${
                    a.active ? "left-4" : "left-0.5"
                  }`}
                />
              </button>
            </div>
            <p className="text-[10px] text-muted-foreground">
              ⚡ {a.trigger} → {a.action}
            </p>
          </div>
        ))}
        <button
          type="button"
          className="w-full p-2.5 rounded-lg border border-dashed border-border/80 text-xs text-muted-foreground hover:text-foreground hover:border-primary/50 transition-colors"
        >
          + Добавить правило
        </button>
      </div>
    </div>
  );
}
