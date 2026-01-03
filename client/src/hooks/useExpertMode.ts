// src/hooks/useExpertMode.ts

import { useExpertModeStore } from '../stores/expertModeStore';

/**
 * Custom hook for accessing Expert Mode state and actions
 * Provides a convenient interface to the Expert Mode store
 */
export const useExpertMode = () => {
  const enabled = useExpertModeStore((state) => state.enabled);
  const autoExpandQueries = useExpertModeStore((state) => state.autoExpandQueries);
  const showExecutionTrace = useExpertModeStore((state) => state.showExecutionTrace);
  const syntaxTheme = useExpertModeStore((state) => state.syntaxTheme);
  const theme = useExpertModeStore((state) => state.theme);

  const toggleExpertMode = useExpertModeStore((state) => state.toggleExpertMode);
  const setAutoExpandQueries = useExpertModeStore((state) => state.setAutoExpandQueries);
  const setShowExecutionTrace = useExpertModeStore((state) => state.setShowExecutionTrace);
  const setSyntaxTheme = useExpertModeStore((state) => state.setSyntaxTheme);
  const toggleTheme = useExpertModeStore((state) => state.toggleTheme);
  const setTheme = useExpertModeStore((state) => state.setTheme);

  return {
    enabled,
    autoExpandQueries,
    showExecutionTrace,
    syntaxTheme,
    theme,
    toggleExpertMode,
    setAutoExpandQueries,
    setShowExecutionTrace,
    setSyntaxTheme,
    toggleTheme,
    setTheme,
  };
};
