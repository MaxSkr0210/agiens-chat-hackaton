'use client';

import { motion } from 'framer-motion';
import { ExternalLink, MessageCircle } from 'lucide-react';

const TELEGRAM_BOT_USERNAME = process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME || '';
const TELEGRAM_LINK = TELEGRAM_BOT_USERNAME ? `https://t.me/${TELEGRAM_BOT_USERNAME}` : null;

export function ConnectTelegramCard() {
  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-md w-full rounded-2xl border border-border/50 bg-card p-6 shadow-lg"
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 rounded-xl bg-[#0088cc]/20 flex items-center justify-center text-2xl">
            ✈️
          </div>
          <div>
            <h2 className="font-semibold text-lg">Telegram</h2>
            <p className="text-sm text-muted-foreground">Чат и голосовые в одном боте</p>
          </div>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          Напишите боту в Telegram — для этого диалога будет создан отдельный чат. Поддерживаются текст и голосовые сообщения (входящие и исходящие).
        </p>
        {TELEGRAM_LINK ? (
          <a
            href={TELEGRAM_LINK}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-xl bg-[#0088cc] text-white px-4 py-2.5 text-sm font-medium hover:opacity-90 transition-opacity"
          >
            <MessageCircle className="w-4 h-4" />
            Открыть бота в Telegram
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        ) : (
          <p className="text-sm text-amber-600 dark:text-amber-400">
            Задайте NEXT_PUBLIC_TELEGRAM_BOT_USERNAME в .env (username бота без @).
          </p>
        )}
      </motion.div>
    </div>
  );
}
