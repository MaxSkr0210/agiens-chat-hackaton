"use client";

import { motion } from "framer-motion";
import {
  MessageSquare,
  Bot,
  Settings,
  Headphones,
  LogOut,
} from "lucide-react";
import { TelegramLoginButton } from "@advanceddev/telegram-login-react";
import type { Channel } from "@/types/chat";

const channels: Channel[] = [
  { id: "web", name: "Веб-чат", icon: "💬" },
  { id: "telegram", name: "Telegram", icon: "✈️" },
];

const TELEGRAM_BOT_USERNAME =
  process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME || "agienschatbot";

export type TelegramAuthUser = {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  auth_date: number;
  hash: string;
};

interface SidebarProps {
  activeChannel: string;
  onChannelChange: (id: string) => void;
  activeTab: string;
  onTabChange: (tab: string) => void;
  account?: {
    id: string;
    channel: string;
    externalId: string;
    zapierMcpServerUrl: string | null;
  };
  authError?: string | null;
  onLogout?: () => void;
  onTelegramAuth?: (user: TelegramAuthUser) => void;
}

const navItems = [
  { id: "chat", icon: MessageSquare, label: "Чат" },
  { id: "agents", icon: Bot, label: "Агенты" },
  { id: "prompts", icon: Settings, label: "Промпты" },
];

export function Sidebar({
  activeChannel,
  onChannelChange,
  activeTab,
  onTabChange,
  account,
  authError,
  onLogout,
  onTelegramAuth,
}: SidebarProps) {

  return (
    <div className="w-64 h-full flex flex-col glass-panel border-r border-border/50">
      <div className="p-4 border-b border-border/50">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center">
            <Headphones className="w-4 h-4 text-primary" />
          </div>
          <span className="font-semibold text-foreground">AI Chat Hub</span>
        </div>
      </div>

      <nav className="flex-1 p-3 space-y-1 overflow-y-auto scrollbar-thin">
        <p className="text-[10px] uppercase tracking-wider text-muted-foreground px-2 mb-2">
          Навигация
        </p>
        {navItems.map((item) => (
          <motion.button
            key={item.id}
            type="button"
            whileHover={{ x: 2 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onTabChange(item.id)}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
              activeTab === item.id
                ? "bg-primary/15 text-primary"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
            }`}
          >
            <item.icon className="w-4 h-4" />
            {item.label}
          </motion.button>
        ))}

        <div className="pt-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground px-2 mb-2">
            Каналы
          </p>
          {channels.map((ch) => (
            <motion.button
              key={ch.id}
              type="button"
              whileHover={{ x: 2 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onChannelChange(ch.id)}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                activeChannel === ch.id
                  ? "bg-primary/15 text-primary"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
              }`}
            >
              <span>{ch.icon}</span>
              <span className="flex-1 text-left">{ch.name}</span>
            </motion.button>
          ))}
        </div>
      </nav>

      <div className="p-3 border-t border-border/50">
        {account ? (
          <div className="flex items-center gap-2 px-2">
            <div className="w-7 h-7 rounded-full bg-primary/20 flex items-center justify-center text-xs">
              ✈️
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium truncate">
                Telegram: {account.externalId}
              </p>
              <p className="text-[10px] text-muted-foreground">
                Zapier для всех чатов
              </p>
            </div>
            {onLogout && (
              <button
                type="button"
                onClick={onLogout}
                className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                title="Выйти"
              >
                <LogOut className="w-4 h-4" />
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-2">
            <p className="text-[10px] text-muted-foreground px-2">
              Вход через Telegram
            </p>
            {authError && (
              <p
                className="text-xs text-destructive px-2 break-words"
                title={authError}
              >
                {authError}
              </p>
            )}
            {onTelegramAuth && (
              <div className="w-full flex justify-center">
                <TelegramLoginButton
                  botUsername={TELEGRAM_BOT_USERNAME}
                  onAuthCallback={onTelegramAuth}
                  requestAccess="write"
                  size="medium"
                  lang="ru"
                  className="[&>iframe]:!max-w-full"
                />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
