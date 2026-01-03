// src/stores/expertModeStore.ts

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ExpertModeState {
  // State
  enabled: boolean;
  autoExpandQueries: boolean;
  showExecutionTrace: boolean;
  syntaxTheme: 'monokai' | 'github' | 'dracula';
  theme: 'light' | 'dark';

  // Actions
  toggleExpertMode: () => void;
  setAutoExpandQueries: (value: boolean) => void;
  setShowExecutionTrace: (value: boolean) => void;
  setSyntaxTheme: (theme: 'monokai' | 'github' | 'dracula') => void;
  toggleTheme: () => void;
  setTheme: (theme: 'light' | 'dark') => void;
}

export const useExpertModeStore = create<ExpertModeState>()(
  persist(
    (set) => ({
      // Initial state
      enabled: false,
      autoExpandQueries: true,
      showExecutionTrace: false,
      syntaxTheme: 'monokai',
      theme: 'light',

      // Actions
      toggleExpertMode: () => set((state) => ({ enabled: !state.enabled })),
      setAutoExpandQueries: (value) => set({ autoExpandQueries: value }),
      setShowExecutionTrace: (value) => set({ showExecutionTrace: value }),
      setSyntaxTheme: (theme) => set({ syntaxTheme: theme }),
      toggleTheme: () => set((state) => ({ theme: state.theme === 'light' ? 'dark' : 'light' })),
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: 'expert-mode-storage', // localStorage key
    }
  )
);
