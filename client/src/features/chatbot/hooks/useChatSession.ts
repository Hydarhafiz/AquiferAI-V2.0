// src/features/chatbot/hooks/useChatSession.ts

import { useState, useEffect, useCallback } from 'react';
import type { ChatMessage } from '../../../interface/ChatMessage';
import type { ChatSessionMetadata } from '../../../interface/ChatSessionMetadata';
import { sendChatMessage, createChatSession, getAllChatSessions, getChatHistory, deleteChatSession, updateChatSessionTitle } from '../../../services/chatService';
import { fetchSpatialData } from '../../../services/MapService';

interface UseChatSessionResult {
    userInput: string;
    setUserInput: React.Dispatch<React.SetStateAction<string>>;
    chatHistory: ChatMessage[];
    isLoading: boolean;
    currentSessionId: string | null;
    allSessions: ChatSessionMetadata[];
    isFetchingHistory: boolean;
    handleSendMessage: () => Promise<void>;
    fetchAllChatSessions: () => Promise<void>;
    createNewChatSession: () => Promise<string | null>;
    fetchChatHistoryForSession: (sessionId: string) => Promise<boolean>;
    handleDeleteSession: (sessionId: string, event: React.MouseEvent) => Promise<void>;
    handleEditSessionTitle: (sessionId: string, currentTitle: string, event: React.MouseEvent) => Promise<void>;
}

export const useChatSession = (): UseChatSessionResult => {
    const [userInput, setUserInput] = useState<string>('');
    const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
    const [allSessions, setAllSessions] = useState<ChatSessionMetadata[]>([]);
    const [isFetchingHistory, setIsFetchingHistory] = useState<boolean>(true);

    useEffect(() => {
        console.log("Current isLoading state:", isLoading);
    }, [isLoading]);
    
    // Fetches all chat sessions metadata from the backend
    const fetchAllChatSessions = useCallback(async () => {
        setIsFetchingHistory(true);
        try {
            const sessionsResponse = await getAllChatSessions();
            if ('error' in sessionsResponse) {
                console.error("Error fetching all chat sessions:", sessionsResponse.error);
                setAllSessions([]);
            } else {
                setAllSessions(sessionsResponse.sessions);
            }
        } catch (error) {
            console.error("Unexpected error fetching all chat sessions:", error);
        } finally {
            setIsFetchingHistory(false);
        }
    }, []);

    // Creates a new chat session
    const createNewChatSession = useCallback(async (shouldSetCurrent: boolean = true) => {
        setIsLoading(true);
        try {
            const response = await createChatSession();
            if ('error' in response) {
                console.error("Error creating new session from backend:", response.error);
                return null;
            }
            const newSessionId = response.session_id;
            if (shouldSetCurrent) { // Only set as current if explicitly requested
                setCurrentSessionId(newSessionId);
                localStorage.setItem('currentChatSessionId', newSessionId);
                setChatHistory([]); // Clear history for the new session
            }
            await fetchAllChatSessions(); // Refresh session list to include the new one
            console.log("New chat session created:", newSessionId);
            return newSessionId;
        } catch (error) {
            console.error("Error creating new session:", error);
            return null;
        } finally {
            setIsLoading(false);
        }
    }, [fetchAllChatSessions]);

    // Fetches and converts chat history for a given session ID
    const fetchChatHistoryForSession = useCallback(async (sessionId: string): Promise<boolean> => {
        setIsLoading(true);
        try {
            const backendMessagesResponse = await getChatHistory(sessionId);

            console.log("Raw backendMessagesResponse from history:", backendMessagesResponse);

            if ('error' in backendMessagesResponse) {
                console.error(`Error fetching history for session ${sessionId}:`, backendMessagesResponse.error);
                setChatHistory([]); // Clear chat history on error
                return false;
            }

            const backendMessages = backendMessagesResponse.history;
            const convertedHistory: ChatMessage[] = [];

            for (let i = 0; i < backendMessages.length; i++) {
                const currentMsg = backendMessages[i];

                if (currentMsg.role === 'user') {
                    const nextMsg = backendMessages[i + 1];
                    if (nextMsg && nextMsg.role === 'assistant') {
                        let botContent: ChatMessage['bot'] = { text: "" };
                        try {
                            if (nextMsg.metadata) {
                                botContent = {
                                    text: nextMsg.content || "",
                                    stats: nextMsg.metadata.statistics,
                                    ranking_data: nextMsg.metadata.ranking_data,
                                    cypherQueries: nextMsg.metadata.cypher_queries,

                                };

                                if (nextMsg.metadata.objectids && nextMsg.metadata.objectids.length > 0) {
                                    console.log("Fetching spatial data from history for objectids:", nextMsg.metadata.objectids);
                                    const spatialDataFetched = await fetchSpatialData(nextMsg.metadata.objectids.map(String));
                                    if (spatialDataFetched) {
                                        console.log("Spatial data retrieved from history for map display:", spatialDataFetched);
                                        botContent.spatialData = spatialDataFetched;
                                    } else {
                                        console.warn("Failed to fetch spatial data from history or received null.");
                                    }
                                }
                            } else {
                                botContent.text = nextMsg.content;
                            }
                        } catch (parseError) {
                            botContent.text = nextMsg.content;
                            console.warn("Assistant message content or metadata was not as expected during history load:", nextMsg.content, parseError);
                        }
                        convertedHistory.push({
                            user: currentMsg.content,
                            bot: botContent
                        });
                        i++; // Increment to skip the assistant message as it's paired with the user message
                    } else {
                        // If user message is not followed by an assistant message (e.g., ongoing conversation)
                        convertedHistory.push({
                            user: currentMsg.content,
                            bot: { text: "Awaiting response..." }
                        });
                    }
                } else if (currentMsg.role === 'assistant') {
                    // This case handles standalone assistant messages or if a user message wasn't paired correctly
                    let botContent: ChatMessage['bot'] = { text: "" };
                    try {
                        if (currentMsg.metadata) {
                            botContent = {
                                text: currentMsg.content || "",
                                stats: currentMsg.metadata.statistics,
                                ranking_data: currentMsg.metadata.ranking_data,
                                cypherQueries: currentMsg.metadata.cypher_queries,

                            };
                            if (currentMsg.metadata.objectids && currentMsg.metadata.objectids.length > 0) {
                                console.log("Fetching spatial data from standalone assistant message for objectids:", currentMsg.metadata.objectids);
                                const spatialDataFetched = await fetchSpatialData(currentMsg.metadata.objectids.map(String));
                                if (spatialDataFetched) {
                                    console.log("Spatial data retrieved from standalone for map display:", spatialDataFetched);
                                    botContent.spatialData = spatialDataFetched;
                                } else {
                                    console.warn("Failed to fetch spatial data from standalone or received null.");
                                }
                            }
                        } else {
                            botContent.text = currentMsg.content;
                        }
                    } catch (parseError) {
                        botContent.text = currentMsg.content;
                        console.warn("Standalone assistant message content or metadata was not as expected:", parseError);
                    }
                    console.warn("Found an assistant message without a preceding user message. Displaying standalone.");
                    convertedHistory.push({ user: "...", bot: botContent }); // Use "..." for user part for standalone bot message
                }
            }
            setChatHistory(convertedHistory);
            console.log(`History loaded for session ${sessionId}:`, convertedHistory);
            // After successfully loading history, set this session as the current one
            setCurrentSessionId(sessionId);
            localStorage.setItem('currentChatSessionId', sessionId);
            return true;
        } catch (error) {
            console.error(`Unexpected error fetching history for session ${sessionId}:`, error);
            setChatHistory([]); // Clear chat history on unexpected error
            return false;
        } finally {
            setIsLoading(false);
        }
    }, []);

    // Handles sending a new message to the chatbot
    const handleSendMessage = useCallback(async () => {
        if (!userInput.trim()) return; // Allow sending message even if currentSessionId is null initially

        let sessionToUse = currentSessionId;

        // If there's no current session, create one first before sending the message
        if (!sessionToUse) {
            setIsLoading(true); // Set loading state while creating session
            const newSessionId = await createNewChatSession(); // Create a new session
            if (!newSessionId) {
                console.error("Failed to create a new session. Cannot send message.");
                setIsLoading(false);
                return;
            }
            sessionToUse = newSessionId;
            setCurrentSessionId(newSessionId); // Ensure currentSessionId is updated
        }


        const userMessageContent = userInput;
        setUserInput('');
        setIsLoading(true);

        // Optimistically add only the user message
        setChatHistory(prev => [...prev, { user: userMessageContent, bot: { text: "..." } }]);

        try {
            const chatResponse = await sendChatMessage(sessionToUse, userMessageContent); // Use sessionToUse

            console.log("Raw chatResponse from backend:", chatResponse);

            if ('error' in chatResponse) {
                throw new Error(chatResponse.error);
            }

            // After a successful send, immediately fetch the updated history from the backend
            // This will ensure the chatHistory state is always in sync with the backend
            await fetchChatHistoryForSession(sessionToUse); // Use sessionToUse

            // Refresh the list of all chat sessions to update 'last_updated' timestamp
            await fetchAllChatSessions();

        } catch (error) {
            console.error('Error sending message:', error);
            const errorMessageText = `Sorry, I encountered an error processing your request: ${(error as Error).message || "Unknown error"}. Please try again.`;

            // Update chat history with an error message, replacing the "..." placeholder
            setChatHistory(prev => {
                const updatedHistory = [...prev];
                const lastEntry = updatedHistory[updatedHistory.length - 1];
                if (lastEntry && lastEntry.user === userMessageContent && lastEntry.bot.text === "...") {
                    lastEntry.bot = { text: errorMessageText };
                } else {
                    // Fallback: If for some reason the placeholder wasn't found (unlikely here), add it as a new entry
                    updatedHistory.push({ user: userMessageContent, bot: { text: errorMessageText } });
                }
                return updatedHistory;
            });
        } finally {
            setIsLoading(false);
        }
    }, [userInput, currentSessionId, fetchChatHistoryForSession, fetchAllChatSessions, createNewChatSession]);


    // Deletes a chat session
    const handleDeleteSession = useCallback(async (sessionId: string, event: React.MouseEvent) => {
        event.stopPropagation(); // Prevent navigation if part of a clickable item
        if (window.confirm("Are you sure you want to delete this chat session? This action cannot be undone.")) {
            setIsLoading(true);
            try {
                const response = await deleteChatSession(sessionId);
                if ('error' in response) {
                    console.error("Error deleting session:", response.error);
                    alert(`Failed to delete session: ${response.error}`);
                } else {
                    console.log(`Session ${sessionId} deleted:`, response.message);
                    await fetchAllChatSessions(); // Refresh list of sessions
                    if (currentSessionId === sessionId) {
                        // If the current session was deleted, clear current session and history
                        setCurrentSessionId(null);
                        localStorage.removeItem('currentChatSessionId');
                        setChatHistory([]);
                        // Optionally, create a new chat session immediately after deleting the active one
                        // await createNewChatSession(true); // Pass true to set it as current
                    }
                }
            } catch (error) {
                console.error("Unexpected error deleting session:", error);
                alert("Failed to delete chat session due to a network error.");
            } finally {
                setIsLoading(false);
            }
        }
    }, [fetchAllChatSessions, currentSessionId]); // Removed createNewChatSession from dependencies here, as it's now optional

    // Edits a chat session title
    const handleEditSessionTitle = useCallback(async (sessionId: string, currentTitle: string, event: React.MouseEvent) => {
        event.stopPropagation(); // Prevent navigation
        const newTitle = prompt("Enter new title for this chat:", currentTitle);
        if (newTitle && newTitle.trim() !== currentTitle) { // Ensure title is not empty and actually changed
            setIsLoading(true);
            try {
                const response = await updateChatSessionTitle(sessionId, newTitle.trim());
                if ('error' in response) {
                    console.error("Error updating title:", response.error);
                    alert(`Failed to update title: ${response.error}`);
                } else {
                    console.log(`Session ${sessionId} title updated:`, response.message);
                    await fetchAllChatSessions(); // Refresh list of sessions to reflect new title
                }
            } catch (error) {
                console.error("Unexpected error updating title:", error);
                alert("Failed to update chat title due to a network error.");
            } finally {
                setIsLoading(false);
            }
        }
    }, [fetchAllChatSessions]);

    // Initial data load effect: Checks for a stored session or ensures a clean state
    useEffect(() => {
        const loadInitialData = async () => {
            setIsFetchingHistory(true);
            const storedSessionId = localStorage.getItem('currentChatSessionId');

            let sessionSuccessfullyLoaded = false;

            if (storedSessionId) {
                console.log(`Attempting to load history for stored session: ${storedSessionId}`);
                sessionSuccessfullyLoaded = await fetchChatHistoryForSession(storedSessionId);
                if (!sessionSuccessfullyLoaded) {
                    console.warn(`Stored session ${storedSessionId} not found or invalid. Clearing local storage.`);
                    localStorage.removeItem('currentChatSessionId'); // Clear invalid ID
                }
            }

            // Only create a new session if no valid one was loaded AND there are no existing sessions
            // This prevents creating a new session on every refresh if the user simply closed the tab
            // and had no prior chats. It also handles the case where a stored ID was invalid.
            if (!sessionSuccessfullyLoaded) {
                // Fetch all sessions to determine if there are *any* existing sessions
                const allSessionsResponse = await getAllChatSessions();
                if ('error' in allSessionsResponse) {
                    console.error("Error fetching all chat sessions for initial check:", allSessionsResponse.error);
                    // Handle error, maybe display a message to the user
                } else if (allSessionsResponse.sessions.length > 0) {
                    // If there are existing sessions, but the stored one was invalid,
                    // just set the currentSessionId to null and clear history.
                    // The user can then select an existing session or start a new one manually.
                    setCurrentSessionId(null);
                    setChatHistory([]);
                } else {
                    // If no valid session was loaded AND no existing sessions at all, create a new one.
                    console.log("No valid stored session found and no existing sessions. Creating new session.");
                    const newSessionId = await createNewChatSession(true); // Pass true to make it current
                    if (!newSessionId) {
                        console.error("Failed to create a new session on initial load.");
                    }
                }
            }

            // Always fetch all sessions to populate the sidebar regardless of initial load success
            await fetchAllChatSessions();
            setIsFetchingHistory(false);
        };
        loadInitialData();
    }, [fetchChatHistoryForSession, fetchAllChatSessions, createNewChatSession]);


    return {
        userInput,
        setUserInput,
        chatHistory,
        isLoading,
        currentSessionId,
        allSessions,
        isFetchingHistory,
        handleSendMessage,
        fetchAllChatSessions,
        createNewChatSession,
        fetchChatHistoryForSession,
        handleDeleteSession,
        handleEditSessionTitle,
    };
};