'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown } from 'lucide-react';
import type { LLMModel } from '@/types/chat';

interface Props {
  models: LLMModel[];
  selected: LLMModel;
  onSelect: (m: LLMModel) => void;
}

export function ModelSelector({ models, selected, onSelect }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-secondary/50 hover:bg-secondary text-sm transition-colors"
      >
        <span>{selected.badge}</span>
        <span className="font-medium">{selected.name}</span>
        <ChevronDown className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="absolute right-0 top-full mt-1 w-48 glass-panel rounded-lg p-1 z-50 border border-border/50"
          >
            {models.map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => {
                  onSelect(m);
                  setOpen(false);
                }}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
                  selected.id === m.id ? 'bg-primary/15 text-primary' : 'hover:bg-secondary/50'
                }`}
              >
                <span>{m.badge}</span>
                <div className="text-left">
                  <p className="font-medium">{m.name}</p>
                  <p className="text-[10px] text-muted-foreground">{m.provider}</p>
                </div>
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
