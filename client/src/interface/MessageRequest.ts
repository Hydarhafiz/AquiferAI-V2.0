// src/interface/MessageRequest.ts (Updated to match backend's /chat/message endpoint expectations)

export interface MessageRequest {
    message: string;
    session_id?: string; // Optional, sent only if continuing an existing session
    // 'role' is determined by the backend based on whether it's user input or AI response
    // 'message_data' not explicitly used in your /chat/message endpoint (it's part of StoredBackendMessage metadata)
}