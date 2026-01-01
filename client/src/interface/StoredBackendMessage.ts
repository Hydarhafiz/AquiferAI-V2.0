export interface StoredBackendMessage {
    role: 'user' | 'assistant' | 'tool' | 'system';
    content: string; // JSON.stringify(ChatMessage.bot) for assistant, raw string for user
    timestamp?: string;
    metadata?: any; // RENAMED FROM metadata
}