// src/components/ui/ExpertModeSettings.tsx

import React, { useState, useRef, useEffect } from 'react';
import { useExpertMode } from '../../hooks/useExpertMode';
import './ExpertModeSettings.css';

const ExpertModeSettings: React.FC = () => {
  const {
    enabled,
    autoExpandQueries,
    showExecutionTrace,
    syntaxTheme,
    setAutoExpandQueries,
    setShowExecutionTrace,
    setSyntaxTheme,
  } = useExpertMode();

  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  // Don't render if expert mode is not enabled
  if (!enabled) {
    return null;
  }

  return (
    <div className="expert-mode-settings-container" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="expert-mode-settings-button"
        title="Expert Mode Settings"
        aria-label="Open Expert Mode Settings"
        aria-expanded={isOpen}
      >
        <svg
          className="settings-icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="3"></circle>
          <path d="M12 1v6m0 6v6m-5-7H1m6 0h6m6 0h6"></path>
        </svg>
      </button>

      {isOpen && (
        <div className="expert-mode-settings-dropdown">
          <div className="settings-header">
            <h3>Expert Mode Settings</h3>
          </div>

          <div className="settings-section">
            <label className="settings-item">
              <div className="settings-item-info">
                <span className="settings-item-label">Auto-expand Queries</span>
                <span className="settings-item-description">
                  Automatically expand Cypher query panels
                </span>
              </div>
              <input
                type="checkbox"
                checked={autoExpandQueries}
                onChange={(e) => setAutoExpandQueries(e.target.checked)}
                className="settings-checkbox"
              />
            </label>

            <label className="settings-item">
              <div className="settings-item-info">
                <span className="settings-item-label">Show Execution Trace</span>
                <span className="settings-item-description">
                  Display detailed agent execution timeline
                </span>
              </div>
              <input
                type="checkbox"
                checked={showExecutionTrace}
                onChange={(e) => setShowExecutionTrace(e.target.checked)}
                className="settings-checkbox"
              />
            </label>
          </div>

          <div className="settings-section">
            <div className="settings-item-info">
              <span className="settings-item-label">Syntax Theme</span>
              <span className="settings-item-description">
                Code highlighting theme for queries
              </span>
            </div>
            <div className="theme-selector">
              <button
                onClick={() => setSyntaxTheme('monokai')}
                className={`theme-option ${syntaxTheme === 'monokai' ? 'active' : ''}`}
                aria-pressed={syntaxTheme === 'monokai'}
              >
                Monokai
              </button>
              <button
                onClick={() => setSyntaxTheme('github')}
                className={`theme-option ${syntaxTheme === 'github' ? 'active' : ''}`}
                aria-pressed={syntaxTheme === 'github'}
              >
                GitHub
              </button>
              <button
                onClick={() => setSyntaxTheme('dracula')}
                className={`theme-option ${syntaxTheme === 'dracula' ? 'active' : ''}`}
                aria-pressed={syntaxTheme === 'dracula'}
              >
                Dracula
              </button>
            </div>
          </div>

          <div className="settings-footer">
            <small className="settings-hint">
              Tip: Press <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>E</kbd> to toggle Expert Mode
            </small>
          </div>
        </div>
      )}
    </div>
  );
};

export default ExpertModeSettings;
