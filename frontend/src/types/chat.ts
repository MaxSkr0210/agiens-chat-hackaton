export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  model?: string;
}

export interface Channel {
  id: string;
  name: string;
  icon: string;
  unread: number;
}

export interface LLMModel {
  id: string;
  name: string;
  provider: string;
  badge?: string;
}

export interface Feature {
  name: string;
  category: string;
  level: number;
  points: number;
  enabled: boolean;
}

export interface ChatSummary {
  id: string;
  title: string;
  model: string;
  lastMessagePreview: string;
  lastMessageAt: Date;
}
