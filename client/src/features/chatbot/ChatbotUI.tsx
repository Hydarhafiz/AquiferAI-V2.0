// src/features/chatbot/ChatbotUI.TSX

import React, { useRef, useState, useEffect } from 'react';
import './ChatbotUI.css';
import StatsVisualization from '../../components/StatsVisualization';
import MapVisualization from '../map/MapVisualization';
import RankingTable from '../../components/RankingTable';
import { useChatSession } from './hooks/useChatSession'; // Import the custom hook

const ChatbotUI: React.FC = () => {
    const {
        userInput,
        setUserInput,
        chatHistory,
        isLoading,
        currentSessionId,
        allSessions,
        isFetchingHistory,
        handleSendMessage,
        createNewChatSession,
        fetchChatHistoryForSession,
        handleDeleteSession,
        handleEditSessionTitle,
    } = useChatSession();

    const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(false);
    const chatHistoryRef = useRef<HTMLDivElement>(null);

    // Scroll to bottom when chatHistory updates
    useEffect(() => {
        if (chatHistoryRef.current) {
            chatHistoryRef.current.scrollTop = chatHistoryRef.current.scrollHeight;
        }
    }, [chatHistory]);

    const toggleHistoryMenu = () => {
        setIsHistoryOpen(prev => !prev);
    };

    const handleHistoryItemClick = async (session: { session_id: string }) => {
        if (session.session_id === currentSessionId) {
            setIsHistoryOpen(false); // Close sidebar if clicking active session
        } else {
            await fetchChatHistoryForSession(session.session_id); // Load history for clicked session
            setIsHistoryOpen(false); // Close sidebar after loading
        }
    };

    const handleNewChat = async () => {
        await createNewChatSession();
        setIsHistoryOpen(false); // Close sidebar after creating new chat
    };

    return (
        <div className={`chatbot-wrapper ${isHistoryOpen ? 'history-open' : ''}`}>
            <div className={`history-sidebar ${isHistoryOpen ? 'open' : ''}`}>
                <div className="history-header">
                    <h3>Chat History</h3>
                    <button className="history-close-button" onClick={toggleHistoryMenu}>✕</button>
                </div>
                <ul className="history-list">
                    {isFetchingHistory && <li className="history-item-placeholder">Loading sessions...</li>}
                    {!isFetchingHistory && allSessions.length === 0 && (
                        <li className="history-item-placeholder">No past chats. Start a new one!</li>
                    )}
                    {!isFetchingHistory && allSessions
                        .sort((a, b) => new Date(b.last_updated).getTime() - new Date(a.last_updated).getTime())
                        .map((session) => (
                            <li
                                key={session.session_id}
                                className={`history-item ${currentSessionId === session.session_id ? 'active' : ''}`}
                                onClick={() => handleHistoryItemClick(session)}
                            >
                                <span className="session-title">{session.title || `Chat ${session.session_id.substring(0, 8)}`}</span>
                                <span className="last-updated">{new Date(session.last_updated).toLocaleString()}</span>
                                <div className="session-actions">
                                    <button
                                        className="edit-session-title-button"
                                        onClick={(e) => handleEditSessionTitle(session.session_id, session.title, e)}
                                        title="Edit title"
                                        disabled={isLoading}
                                    >
                                        ✏️
                                    </button>
                                    <button
                                        className="delete-session-button"
                                        onClick={(e) => handleDeleteSession(session.session_id, e)}
                                        title="Delete session"
                                        disabled={isLoading}
                                    >
                                        🗑️
                                    </button>
                                </div>
                            </li>
                        ))}
                </ul>
                <button className="new-chat-button" onClick={handleNewChat} disabled={isLoading}>New Chat</button>
            </div>

            <div className="chatbot">
                <div className="chatbot-header">
                    <button className="history-toggle-button" onClick={toggleHistoryMenu}>☰</button>
                    <h1>CO₂ Storage Chatbot</h1>
                    {currentSessionId && <span className="current-session-display">Session: {currentSessionId.substring(0, 8)}...</span>}
                    <div style={{ width: '40px' }}></div> {/* Spacer for alignment */}
                </div>

                <div className="chat-history-main" ref={chatHistoryRef}>
                    {isFetchingHistory && (
                        <div className="welcome-message">
                            <p>Loading chat history...</p>
                        </div>
                    )}

                    {!isFetchingHistory && chatHistory.length === 0 && !isLoading && (
                        <div className="welcome-message">
                            <p>Hello! I'm your CO₂ Storage Suitability Assistant. Ask me anything about aquifer properties, risk assessments, or potential storage sites.</p>
                            <p>Try questions like:</p>
                            <ul>
                                <li>"What are the most porous aquifers?"</li>
                                <li>"Show me aquifers with high permeability in North America."</li>
                                <li>"Analyze the risk factors for OBJECTID 12345."</li>
                            </ul>
                        </div>
                    )}

                    {!isFetchingHistory && chatHistory.length > 0 && chatHistory.map((messagePair, index) => (
                        <div key={index} className="message-container">
                            {messagePair.user && (
                                <div className="user-message">
                                    <strong>You:</strong>
                                    <p>{messagePair.user}</p>
                                </div>
                            )}
                            {messagePair.bot && messagePair.bot.text && (
                                <div className="bot-message">
                                    <p dangerouslySetInnerHTML={{
                                        __html: messagePair.bot.text.replace(/\n/g, '<br />')
                                    }}></p>

                                    {messagePair.bot.stats && (
                                        <StatsVisualization stats={messagePair.bot.stats} />
                                    )}

                                    {messagePair.bot.ranking_data && Object.keys(messagePair.bot.ranking_data).length > 0 && (
                                        <div className="ranking-container">
                                            {Object.entries(messagePair.bot.ranking_data).map(([chunk, data], idx) => (
                                                <div key={idx} className="ranking-section">
                                                    <h4>Ranking for: {chunk}</h4>
                                                    <RankingTable rankingData={data} />
                                                </div>
                                            ))}
                                        </div>
                                    )}

                                    {messagePair.bot.spatialData && (
                                        <>
                                            {console.log("ChatbotUI: messagePair.bot.spatialData is present:", messagePair.bot.spatialData)}
                                            <div className="map-container">
                                                <MapVisualization
                                                    geojson={messagePair.bot.spatialData}
                                                    height="600px"
                                                />
                                            </div>
                                        </>
                                    )}
                                    {messagePair.bot.cypherQueries && messagePair.bot.cypherQueries.length > 0 && (
                                        <div className="cypher-query-container">
                                            <h4>Cypher Query:</h4>
                                            {messagePair.bot.cypherQueries.map((query, queryIndex) => (
                                                <pre key={queryIndex} className="cypher-code">
                                                    <code>{query}</code>
                                                </pre>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    ))}

                    {isLoading && (
                        <div className="bot-message loading-message">
                            <div className="loading-indicator">
                                <div className="loading-dot"></div>
                                <div className="loading-dot"></div>
                                <div className="loading-dot"></div>
                            </div>
                        </div>
                    )}
                </div>

                <div className="input-area">
                    <textarea
                        value={userInput}
                        onChange={(e) => setUserInput(e.target.value)}
                        placeholder="Ask about CO₂ storage suitability (e.g., 'What are the most porous aquifers?')..."
                        disabled={isLoading} // Removed !currentSessionId from here
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                handleSendMessage();
                            }
                        }}
                    />
                    <button
                        onClick={handleSendMessage}
                        disabled={isLoading || !userInput.trim()} // Removed !currentSessionId from here
                    >
                        {isLoading ? 'Processing...' : 'Send'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ChatbotUI;
