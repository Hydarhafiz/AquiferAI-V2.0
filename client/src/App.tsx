// src/App.tsx
import React from 'react';
import ChatbotUI from './features/chatbot/ChatbotUI';
import './App.css';

const App: React.FC = () => {
  return (
    <div className="App">
      <ChatbotUI />
    </div>
  );
};

export default App;