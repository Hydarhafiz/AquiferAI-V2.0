// src/api_services/chatService.ts

import type { ChatSessionMetadata } from '../interface/ChatSessionMetadata';
import type { CreateSessionResponse } from '../interface/CreateSessionResponse';
import type { MessageRequest } from '../interface/MessageRequest';
import type { StoredBackendMessage } from '../interface/StoredBackendMessage';
import { postRequest, getRequest } from '../services/httpService';

/**
 * Creates a new chat session.
 * The backend returns an object with session_id, title, created_at, last_updated.
 */
export const createChatSession = async (): Promise<CreateSessionResponse | { error: string }> => {
    // The backend endpoint is /chat/sessions and expects no body or a body with 'title'.
    // It returns an object: {"session_id": "...", "title": "...", "created_at": "...", "last_updated": "..."}
    const response = await postRequest<{ title: string }, CreateSessionResponse>('/chat/sessions', { title: "New Chat" });
    return response;
};

interface SendMessageResponse {
    session_id: string;
    ai_response: string;
    full_history: StoredBackendMessage[];
}

/**
 * Sends a user message to the chat and gets an AI response.
 * Handles new sessions if no sessionId is provided.
 * @param sessionId - The current chat session ID (optional, for new chats).
 * @param message - The user's message content.
 * @returns An object containing the session_id, AI's response, and full chat history.
 */
export const sendChatMessage = async (
    sessionId: string | null, // Can be null for a new chat
    messageContent: string
): Promise<SendMessageResponse | { error: string }> => {
    const requestBody: MessageRequest = { message: messageContent };
    if (sessionId) {
        requestBody.session_id = sessionId;
    }
    // The backend endpoint is /chat/message
    return postRequest<MessageRequest, SendMessageResponse>('/chat/message', requestBody);
};


/**
 * Fetches the history for a specific chat session.
 * Backend endpoint: GET /chat/sessions/{session_id}/history
 * Backend returns: {"session_id": "...", "history": [...]}
 */
interface GetChatHistoryResponse {
    session_id: string;
    history: StoredBackendMessage[];
}

export const getChatHistory = async (sessionId: string): Promise<GetChatHistoryResponse | { error: string }> => {
    return getRequest<GetChatHistoryResponse>(`/chat/sessions/${sessionId}/history`);
};

/**
 * Fetches all chat sessions metadata.
 * Backend endpoint: GET /chat/sessions
 * Backend returns: {"sessions": [...]}
 */
interface GetAllChatSessionsResponse {
    sessions: ChatSessionMetadata[];
}

export const getAllChatSessions = async (): Promise<GetAllChatSessionsResponse | { error: string }> => {
    return getRequest<GetAllChatSessionsResponse>('/chat/sessions');
};

/**
 * Updates the title of a specific chat session.
 * Backend endpoint: PUT /chat/sessions/{session_id}/title
 * Backend expects: {"new_title": "..."}
 * Backend returns: {"message": "..."}
 */
export const updateChatSessionTitle = async (
    sessionId: string,
    newTitle: string
): Promise<{ message: string } | { error: string }> => {
    return postRequest<{ new_title: string }, { message: string }>(
        `/chat/sessions/${sessionId}/title`,
        { new_title: newTitle }
    );
};

/**
 * Deletes a specific chat session.
 * Backend endpoint: DELETE /chat/sessions/{session_id}
 * Backend returns: {"message": "..."}
 */
export const deleteChatSession = async (
    sessionId: string
): Promise<{ message: string } | { error: string }> => {
    // Note: DELETE requests generally don't send a body, so postRequest works here.
    // However, a dedicated deleteRequest or using fetch directly might be clearer.
    // For simplicity, we'll use postRequest with an empty body or just remove the body.
    // FastAPI's DELETE allows empty body, so this should work.
    return postRequest<object, { message: string }>(`/chat/sessions/${sessionId}`, {});
};