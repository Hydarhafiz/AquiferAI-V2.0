// src/components/ui/ExpertModeToggle.tsx

import React, { useEffect } from 'react';
import { useExpertMode } from '../../hooks/useExpertMode';
import './ExpertModeToggle.css';

const ExpertModeToggle: React.FC = () => {
  const { enabled, toggleExpertMode } = useExpertMode();

  // Keyboard shortcut: Ctrl+Shift+E
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.ctrlKey && event.shiftKey && event.key === 'E') {
        event.preventDefault();
        toggleExpertMode();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [toggleExpertMode]);

  return (
    <div className="expert-mode-toggle-container">
      <button
        onClick={toggleExpertMode}
        className={`expert-mode-toggle ${enabled ? 'active' : ''}`}
        title="Toggle Expert Mode (Ctrl+Shift+E)"
        aria-label="Toggle Expert Mode"
      >
        <svg
          className="expert-mode-icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="16 18 22 12 16 6"></polyline>
          <polyline points="8 6 2 12 8 18"></polyline>
        </svg>
        <span className="expert-mode-label">Expert Mode</span>
        {enabled && (
          <span className="expert-mode-badge" aria-label="Expert Mode enabled">
            ●
          </span>
        )}
      </button>
    </div>
  );
};

export default ExpertModeToggle;
