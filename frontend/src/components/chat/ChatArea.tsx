"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Send,
  Mic,
  MicOff,
  Paperclip,
  Sparkles,
  Volume2,
  Pause,
  Square,
  Pencil,
  Link2,
} from "lucide-react";
import type { Message, LLMModel } from "@/types/chat";
import { ModelSelector } from "./ModelSelector";

/** Models aligned with backend (default: openrouter/auto) */
const OPENROUTER_MODELS: LLMModel[] = [
  {
    id: "openrouter/auto",
    name: "OpenRouter Auto",
    provider: "OpenRouter",
    badge: "🟢",
  },
  {
    id: "openrouter/free",
    name: "OpenRouter Free",
    provider: "OpenRouter",
    badge: "🟢",
  },
  {
    id: "nvidia/llama-nemotron-embed-vl-1b-v2:free",
    name: "Llama Nemotron Embed VL 1B",
    provider: "NVIDIA",
    badge: "🟠",
  },
  {
    id: "sourceful/riverflow-v2-pro",
    name: "riverflow",
    provider: "Sourceful",
    badge: "🔵",
  },
];

interface ChatAreaProps {
  chatId: string | null;
  messages: { id: string; role: string; content: string; createdAt: string }[];
  modelId: string;
  isLoading: boolean;
  account?: {
    id: string;
    channel: string;
    externalId: string;
    zapierMcpServerUrl: string | null;
  };
  onSendMessage: (
    message: string,
    modelId: string,
    opts?: { signal?: AbortSignal; withVoice?: boolean },
  ) => Promise<{ content: string; audioBase64?: string } | undefined>;
  onSendVoice?: (
    chatId: string,
    audioBlob: Blob,
    modelId: string,
    withVoice?: boolean,
  ) => Promise<{ content: string; audioBase64: string }>;
  onModelChange?: (modelId: string) => void;
  onSaveMcp?: (serverUrl: string, secret: string) => Promise<void>;
  onInvalidateChat?: () => void;
}

export function ChatArea({
  chatId,
  messages,
  modelId,
  isLoading,
  account,
  onSendMessage,
  onSendVoice,
  onModelChange,
  onSaveMcp,
  onInvalidateChat,
}: ChatAreaProps) {
  const [input, setInput] = useState("");
  const [replyWithVoice, setReplyWithVoice] = useState(false);
  const [mcpUrl, setMcpUrl] = useState("");
  const [mcpSecret, setMcpSecret] = useState("");
  const [mcpSaving, setMcpSaving] = useState(false);
  const [mcpSaved, setMcpSaved] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSendingVoice, setIsSendingVoice] = useState(false);
  const [optimisticUserMessage, setOptimisticUserMessage] = useState<
    string | null
  >(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const [voiceAudioByMessageId, setVoiceAudioByMessageId] = useState<
    Record<string, string>
  >({});
  const [pendingVoiceAudioUrl, setPendingVoiceAudioUrl] = useState<
    string | null
  >(null);
  const [playingMessageId, setPlayingMessageId] = useState<string | null>(null);
  const [playError, setPlayError] = useState<string | null>(null);
  const voiceAudioRef = useRef<HTMLAudioElement | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const modelIdRef = useRef(modelId);
  modelIdRef.current = modelId;
  const selectedModel =
    OPENROUTER_MODELS.find((m) => m.id === modelId) ?? OPENROUTER_MODELS[0];

  const messageList: Message[] = messages.map((m) => ({
    id: m.id,
    role: m.role as "user" | "assistant" | "system",
    content: m.content,
    timestamp: new Date(m.createdAt),
    model: m.role === "assistant" ? modelId : undefined,
  }));
  const lastAssistantId = [...messageList]
    .reverse()
    .find((m) => m.role === "assistant")?.id;
  const prevLastAssistantIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (account?.zapierMcpServerUrl != null)
      setMcpUrl(account.zapierMcpServerUrl);
  }, [account?.zapierMcpServerUrl]);

  const handleSaveMcp = async () => {
    if (!onSaveMcp || !mcpUrl.trim()) return;
    setMcpSaving(true);
    setMcpSaved(false);
    try {
      await onSaveMcp(mcpUrl.trim(), mcpSecret);
      setMcpSaved(true);
      onInvalidateChat?.();
      setTimeout(() => setMcpSaved(false), 2000);
    } catch {
      setMcpSaved(false);
    } finally {
      setMcpSaving(false);
    }
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messageList.length]);

  useEffect(() => {
    if (!playError) return;
    const t = setTimeout(() => setPlayError(null), 5000);
    return () => clearTimeout(t);
  }, [playError]);

  useEffect(() => {
    if (!pendingVoiceAudioUrl && lastAssistantId)
      prevLastAssistantIdRef.current = lastAssistantId;
  }, [pendingVoiceAudioUrl, lastAssistantId]);

  useEffect(() => {
    if (
      pendingVoiceAudioUrl &&
      lastAssistantId &&
      prevLastAssistantIdRef.current !== lastAssistantId &&
      !voiceAudioByMessageId[lastAssistantId]
    ) {
      setVoiceAudioByMessageId((prev) => ({
        ...prev,
        [lastAssistantId]: pendingVoiceAudioUrl,
      }));
      setPendingVoiceAudioUrl(null);
      prevLastAssistantIdRef.current = lastAssistantId;
    }
  }, [pendingVoiceAudioUrl, lastAssistantId, voiceAudioByMessageId]);

  // Start/stop voice recording when isListening toggles
  useEffect(() => {
    if (!chatId || !onSendVoice) return;

    if (isListening) {
      chunksRef.current = [];
      navigator.mediaDevices
        .getUserMedia({ audio: true })
        .then((stream) => {
          streamRef.current = stream;
          const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
            ? "audio/webm;codecs=opus"
            : "audio/webm";
          const recorder = new MediaRecorder(stream);
          recorderRef.current = recorder;
          recorder.ondataavailable = (e) => {
            if (e.data.size) chunksRef.current.push(e.data);
          };
          recorder.onstop = async () => {
            stream.getTracks().forEach((t) => t.stop());
            streamRef.current = null;
            recorderRef.current = null;
            const blob = new Blob(chunksRef.current, { type: mime });
            if (blob.size === 0 || !onSendVoice) {
              setIsSendingVoice(false);
              return;
            }
            try {
              const result = await onSendVoice(
                chatId,
                blob,
                modelIdRef.current ?? "openrouter/auto",
                replyWithVoice,
              );
              if (voiceAudioRef.current) {
                voiceAudioRef.current.pause();
                voiceAudioRef.current = null;
              }
              setPlayingMessageId(null);
              if (result.audioBase64?.length) {
                setPendingVoiceAudioUrl(
                  `data:audio/mp3;base64,${result.audioBase64}`,
                );
              }
              setPlayingMessageId(null);
            } catch (err) {
              console.error("Voice send failed:", err);
            } finally {
              setIsSendingVoice(false);
              setIsListening(false);
            }
          };
          recorder.start(100);
        })
        .catch((err) => {
          console.error("Microphone access failed:", err);
          setIsListening(false);
        });
    } else {
      if (recorderRef.current?.state === "recording") {
        setIsSendingVoice(true);
        recorderRef.current.stop();
      }
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
  }, [isListening, chatId, onSendVoice, replyWithVoice]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || !chatId || isSending) return;
    if (abortControllerRef.current) abortControllerRef.current.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;
    setOptimisticUserMessage(text);
    setInput("");
    setIsSending(true);
    try {
      const res = await onSendMessage(text, selectedModel.id, {
        signal: controller.signal,
        withVoice: replyWithVoice,
      });
      if (res?.audioBase64 && res.audioBase64.length > 0) {
        setPendingVoiceAudioUrl(`data:audio/mp3;base64,${res.audioBase64}`);
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") throw err;
    } finally {
      setOptimisticUserMessage(null);
      setIsSending(false);
      abortControllerRef.current = null;
      onInvalidateChat?.();
    }
  };

  const handleStopSend = () => {
    abortControllerRef.current?.abort();
  };

  const handleEditAndResend = () => {
    if (optimisticUserMessage != null) {
      abortControllerRef.current?.abort();
      setInput(optimisticUserMessage);
      setOptimisticUserMessage(null);
      setIsSending(false);
      abortControllerRef.current = null;
      onInvalidateChat?.();
    }
  };

  const toggleVoicePlayback = (messageId: string, url: string) => {
    setPlayError(null);
    if (playingMessageId === messageId && voiceAudioRef.current) {
      voiceAudioRef.current.pause();
      setPlayingMessageId(null);
      return;
    }
    if (voiceAudioRef.current) {
      voiceAudioRef.current.pause();
      voiceAudioRef.current = null;
    }
    if (!url || !url.includes(",")) {
      setPlayError("Нет аудио для воспроизведения");
      return;
    }
    const audio = new Audio(url);
    voiceAudioRef.current = audio;
    audio.onended = () => {
      setPlayingMessageId(null);
      voiceAudioRef.current = null;
    };
    audio.onerror = () => {
      setPlayError("Ошибка загрузки аудио");
      setPlayingMessageId(null);
      voiceAudioRef.current = null;
    };
    setPlayingMessageId(messageId);
    audio.play().catch((e) => {
      console.warn("Play failed:", e);
      setPlayError(
        "Воспроизведение заблокировано браузером (разрешите звук на сайте)",
      );
      setPlayingMessageId(null);
      voiceAudioRef.current = null;
    });
  };

  const displayMessages: Message[] = optimisticUserMessage
    ? [
        ...messageList,
        {
          id: "optimistic",
          role: "user" as const,
          content: optimisticUserMessage,
          timestamp: new Date(),
          model: undefined,
        },
      ]
    : messageList;

  if (!chatId) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        <p className="text-sm">Выберите чат или создайте новый</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full">
      <div className="h-14 px-4 flex items-center justify-between border-b border-border/50 glass-panel">
        <div className="flex items-center gap-3">
          <Sparkles className="w-4 h-4 text-primary" />
          <span className="font-medium text-sm">AI Чат (OpenRouter)</span>
        </div>
        <ModelSelector
          models={OPENROUTER_MODELS}
          selected={selectedModel}
          onSelect={(m) => onModelChange?.(m.id)}
        />
      </div>

      {isLoading ? (
        <div className="flex-1 flex items-center justify-center text-muted-foreground">
          <p className="text-sm">Загрузка...</p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin">
          <AnimatePresence initial={false}>
            {displayMessages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground rounded-br-md"
                      : "glass-panel rounded-bl-md"
                  }`}
                >
                  {msg.model && msg.role === "assistant" && (
                    <span className="text-[10px] text-primary font-medium block mb-1">
                      {msg.model}
                    </span>
                  )}
                  <div className="chat-markdown">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        p: ({ children }: { children?: React.ReactNode }) => (
                          <p className="mb-2 last:mb-0">{children}</p>
                        ),
                        strong: ({
                          children,
                        }: {
                          children?: React.ReactNode;
                        }) => (
                          <strong className="font-semibold">{children}</strong>
                        ),
                        ul: ({ children }: { children?: React.ReactNode }) => (
                          <ul className="list-disc list-inside mb-2 space-y-0.5">
                            {children}
                          </ul>
                        ),
                        ol: ({ children }: { children?: React.ReactNode }) => (
                          <ol className="list-decimal list-inside mb-2 space-y-0.5">
                            {children}
                          </ol>
                        ),
                        li: ({ children }: { children?: React.ReactNode }) => (
                          <li className="leading-relaxed">{children}</li>
                        ),
                        code: ({
                          className,
                          children,
                          ...props
                        }: {
                          className?: string;
                          children?: React.ReactNode;
                        }) => {
                          const isBlock = className?.includes("language-");
                          return isBlock ? (
                            <code
                              className={`block p-2 rounded bg-black/10 text-xs overflow-x-auto ${className ?? ""}`}
                              {...props}
                            >
                              {children}
                            </code>
                          ) : (
                            <code
                              className="px-1 py-0.5 rounded bg-black/10 text-xs"
                              {...props}
                            >
                              {children}
                            </code>
                          );
                        },
                        pre: ({ children }: { children?: React.ReactNode }) => (
                          <pre className="mb-2 overflow-x-auto">{children}</pre>
                        ),
                        blockquote: ({
                          children,
                        }: {
                          children?: React.ReactNode;
                        }) => (
                          <blockquote className="border-l-2 border-primary/30 pl-3 my-2 text-muted-foreground">
                            {children}
                          </blockquote>
                        ),
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                  {msg.role === "assistant" &&
                    voiceAudioByMessageId[msg.id] && (
                      <div className="mt-2">
                        <button
                          type="button"
                          onClick={() =>
                            toggleVoicePlayback(
                              msg.id,
                              voiceAudioByMessageId[msg.id],
                            )
                          }
                          className="flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
                        >
                          {playingMessageId === msg.id ? (
                            <>
                              <Pause className="w-3.5 h-3.5" />
                              Пауза
                            </>
                          ) : (
                            <>
                              <Volume2 className="w-3.5 h-3.5" />
                              Озвучить
                            </>
                          )}
                        </button>
                        {playError && (
                          <p
                            className="mt-1 text-[10px] text-amber-600"
                            role="alert"
                          >
                            {playError}
                          </p>
                        )}
                      </div>
                    )}
                  {msg.id === "optimistic" && isSending && (
                    <div className="flex items-center gap-2 mt-2">
                      <button
                        type="button"
                        onClick={handleStopSend}
                        className="flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs bg-destructive/10 text-destructive hover:bg-destructive/20"
                      >
                        <Square className="w-3.5 h-3.5" />
                        Остановить
                      </button>
                      <button
                        type="button"
                        onClick={handleEditAndResend}
                        className="flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs bg-primary/10 text-primary hover:bg-primary/20"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                        Изменить
                      </button>
                    </div>
                  )}
                  <span className="block text-[10px] mt-1.5 opacity-50">
                    {msg.timestamp.toLocaleTimeString("ru", {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {isSendingVoice && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex gap-1.5 px-4 py-3"
            >
              <span className="w-2 h-2 rounded-full bg-primary animate-pulse-glow" />
              <span className="w-2 h-2 rounded-full bg-primary animate-pulse-glow [animation-delay:0.3s]" />
              <span className="w-2 h-2 rounded-full bg-primary animate-pulse-glow [animation-delay:0.6s]" />
            </motion.div>
          )}
          <div ref={bottomRef} />
        </div>
      )}

      <div className="p-4 border-t border-border/50 space-y-3">
        {account && onSaveMcp ? (
          <div className="rounded-xl border border-border/50 bg-muted/30 px-3 py-2.5 space-y-2">
            <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
              <Link2 className="w-3.5 h-3.5" />
              Zapier MCP — для всех ваших чатов (в т.ч. в Telegram)
            </div>
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                type="url"
                value={mcpUrl}
                onChange={(e) => setMcpUrl(e.target.value)}
                placeholder="https://mcp.zapier.com/..."
                className="flex-1 min-w-0 rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/30"
              />
              <input
                type="password"
                value={mcpSecret}
                onChange={(e) => setMcpSecret(e.target.value)}
                placeholder="Секрет (Bearer)"
                className="flex-1 min-w-0 rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/30"
              />
              <button
                type="button"
                onClick={handleSaveMcp}
                disabled={mcpSaving || !mcpUrl.trim()}
                className="rounded-lg bg-primary/15 text-primary hover:bg-primary/25 px-3 py-2 text-sm font-medium disabled:opacity-50 transition-colors"
              >
                {mcpSaving
                  ? "Сохранение…"
                  : mcpSaved
                    ? "Сохранено"
                    : "Сохранить"}
              </button>
            </div>
            {account.zapierMcpServerUrl && (
              <p className="text-[10px] text-muted-foreground">
                Подключено:{" "}
                {account.zapierMcpServerUrl.length > 50
                  ? `${account.zapierMcpServerUrl.slice(0, 50)}…`
                  : account.zapierMcpServerUrl}
              </p>
            )}
            <p className="text-[10px] text-muted-foreground">
              URL и секрет берите с{" "}
              <a
                href="https://mcp.zapier.com"
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-foreground"
              >
                mcp.zapier.com
              </a>
              . После сохранения просто пишите в чате — модель сама вызовет нужные инструменты (Drive, Sheets и т.д.).
            </p>
          </div>
        ) : (
          <p className="text-[10px] text-muted-foreground">
            Войдите через Telegram в сайдбаре, чтобы настроить Zapier для всех
            чатов.
          </p>
        )}
        <div className="flex items-center gap-2 glass-panel rounded-xl px-3 py-2">
          <button
            type="button"
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors"
          >
            <Paperclip className="w-4 h-4" />
          </button>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            placeholder="Введите сообщение..."
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            disabled={isSending}
          />
          <button
            type="button"
            onClick={() => setReplyWithVoice((v) => !v)}
            title={
              replyWithVoice
                ? "Ответ голосом (TTS) включён"
                : "Ответить голосом (TTS)"
            }
            className={`p-1.5 rounded-lg transition-colors ${
              replyWithVoice
                ? "bg-primary/20 text-primary"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
            }`}
          >
            <Volume2 className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => onSendVoice && setIsListening(!isListening)}
            disabled={!onSendVoice || isSendingVoice}
            title={
              onSendVoice
                ? isListening
                  ? "Остановить запись"
                  : "Голосовое сообщение (ElevenLabs)"
                : "Голос недоступен"
            }
            className={`p-1.5 rounded-lg transition-colors ${
              isListening
                ? "bg-destructive/20 text-destructive"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
            } disabled:opacity-50`}
          >
            {isSendingVoice ? (
              <span className="w-4 h-4 block rounded-full bg-primary animate-pulse" />
            ) : isListening ? (
              <MicOff className="w-4 h-4" />
            ) : (
              <Mic className="w-4 h-4" />
            )}
          </button>
          <motion.button
            type="button"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleSend}
            disabled={!input.trim() || isSending}
            className="p-2 rounded-lg bg-primary text-primary-foreground disabled:opacity-30 transition-opacity"
          >
            <Send className="w-4 h-4" />
          </motion.button>
        </div>
      </div>
    </div>
  );
}
