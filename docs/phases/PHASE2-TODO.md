# Phase 2: The Expert Interface - Todo List

**Objective:** Build frontend components for Expert Mode and enhanced visualizations.

**Estimated Duration:** 4-6 working sessions

**Prerequisites:**
- Phase 1 complete (LangGraph workflow functional)
- Neo4j seeded with test data
- API server running at localhost:8000

---

## Task 2.1: Expert Mode Toggle & State ✅ COMPLETE

Create the Expert Mode state management with persistence.

**Files Created/Updated:**
- ✅ `client/src/stores/expertModeStore.ts`
- ✅ `client/src/components/ui/ExpertModeToggle.tsx`
- ✅ `client/src/components/ui/ExpertModeToggle.css`
- ✅ `client/src/components/ui/ExpertModeSettings.tsx`
- ✅ `client/src/components/ui/ExpertModeSettings.css`
- ✅ `client/src/components/ui/ThemeToggle.tsx` ⭐ **NEW**
- ✅ `client/src/components/ui/ThemeToggle.css`
- ✅ `client/src/components/ui/index.ts`
- ✅ `client/src/hooks/useExpertMode.ts`
- ✅ `client/src/theme.css` ⭐ **NEW - Global theme system with comprehensive color variables**
- ✅ `client/src/App.css` ⭐ **UPDATED - Theme variables applied**
- ✅ `client/src/features/chatbot/ChatbotUI.css` ⭐ **UPDATED - 76+ colors converted to CSS variables**
- ✅ `client/src/components/StatsVisualization.css` ⭐ **UPDATED - 40+ colors converted to CSS variables**
- ✅ `client/src/features/map/MapVisualization.css` ⭐ **UPDATED - 30+ colors converted to CSS variables**

- [x] **2.1a** Create Zustand store for Expert Mode state
  - `enabled: boolean` - Master toggle
  - `autoExpandQueries: boolean` - Auto-expand query panels
  - `showExecutionTrace: boolean` - Show detailed agent timeline
  - `syntaxTheme: 'monokai' | 'github' | 'dracula'` - Editor theme
  - `theme: 'light' | 'dark'` - App-wide theme ⭐ **NEW**
  - Persist state to localStorage ✅

- [x] **2.1b** Create Expert Mode toggle component
  - Toggle switch in header/navbar ✅
  - Visual indicator when enabled (icon/badge) ✅
  - Keyboard shortcut (Ctrl+Shift+E) ✅

- [x] **2.1c** Create Expert Mode settings panel
  - Dropdown or modal for additional settings ✅
  - Theme selector for code display ✅
  - Auto-expand toggle ✅
  - Execution trace toggle ✅

- [x] **2.1d** Integration with ChatbotUI
  - Added Expert Mode components to header ✅
  - Created `header-controls` CSS class for layout ✅

- [x] **2.1e** Light/Dark Theme Toggle ⭐ **NEW**
  - Created ThemeToggle component with sun/moon icons ✅
  - Implemented global CSS variables for theming ✅
  - Theme persists across page reloads ✅
  - All Expert Mode components support both themes ✅
  - Smooth theme transitions ✅

- [x] **2.1f** App-wide Theme Implementation ⭐ **NEW**
  - Updated `theme.css` with comprehensive color variables:
    - Background colors (primary, secondary, tertiary, chat, hover)
    - Text colors (primary, secondary, tertiary, inverse, muted)
    - Border colors (color, hover, light)
    - Accent colors (bg, color, border, hover)
    - Primary/Success/Error/Warning/Info semantic colors
    - User message gradient colors
    - Bot message colors
    - Scrollbar colors
    - Table colors (header, row alt, hover)
    - Code block colors
    - Shadow variants
    - Overlay backgrounds
  - Updated ChatbotUI.css (76+ hardcoded colors → CSS variables)
  - Updated StatsVisualization.css (40+ hardcoded colors → CSS variables)
  - Updated MapVisualization.css (30+ hardcoded colors → CSS variables)
  - Updated App.css (gradient background → CSS variables)
  - Fixed remaining hardcoded colors in ExpertModeToggle.css
  - Fixed remaining hardcoded colors in ExpertModeSettings.css
  - Added smooth theme transition animations ✅

**Definition of Done:**
- [x] Toggle persists across page reloads (via Zustand persist middleware)
- [x] Settings UI accessible in header (dropdown component created)
- [x] State accessible throughout app via hook (useExpertMode hook)
- [x] Keyboard shortcut works (Ctrl+Shift+E listener implemented)
- [x] Light/Dark theme toggle works app-wide ⭐ **COMPLETE**
- [x] All app components properly themed (ChatbotUI, Stats, Map, etc.) ⭐ **COMPLETE**

**Implementation Notes:**
- Used Zustand with persist middleware for state management
- Components integrated into ChatbotUI header
- Responsive design with mobile-friendly layouts
- Accessible UI with ARIA labels and keyboard navigation
- Settings panel auto-closes when clicking outside
- **Global theme system using CSS custom properties (variables)**
- **Theme toggle applies `data-theme` attribute to document root**
- **All components use CSS variables for seamless theme switching**
- **Comprehensive color system with semantic naming (primary, success, error, info, etc.)**
- **Smooth 0.2s-0.3s transitions on background, border, and box-shadow changes**
- **Dark mode optimized with appropriate contrast ratios and muted colors**

---

## Task 2.2: Cypher Query Panel Component

Display generated Cypher queries with syntax highlighting.

**Files to create:**
- `client/src/components/expert-mode/CypherQueryPanel.tsx`
- `client/src/components/expert-mode/index.ts`

**Dependencies to install:**
```bash
npm install react-syntax-highlighter @types/react-syntax-highlighter
```

- [ ] **2.2a** Create collapsible query panel component
  - Collapsed by default (shows "View Query" button)
  - Expands to show Cypher code
  - Respects `autoExpandQueries` setting

- [ ] **2.2b** Add syntax highlighting for Cypher
  - Use react-syntax-highlighter with vscDarkPlus theme
  - Line numbers enabled
  - Custom styling for dark mode

- [ ] **2.2c** Add query metadata display
  - Execution time (ms)
  - Row count returned
  - Self-healing indicator (retry count, "Self-Healed" badge)
  - Status icon (checkmark for success, X for error)

- [ ] **2.2d** Add action buttons
  - Copy to clipboard button
  - Edit button (opens Query Editor modal)

- [ ] **2.2e** Add query explanation section
  - Natural language explanation of what query does
  - Collapsible for long explanations

**Definition of Done:**
- [ ] Panel shows/hides based on Expert Mode toggle
- [ ] Syntax highlighting works for Cypher keywords
- [ ] Copy button copies query to clipboard
- [ ] Self-healing indicator shows retry count when applicable
- [ ] Execution time displayed in milliseconds

**Test Cases:**
- Panel hidden when expert mode disabled
- Panel visible when expert mode enabled
- Copy button copies correct query text
- Self-healing badge appears for healed queries
- Execution time displays correctly

---

## Task 2.3: Query Editor Modal (Monaco)

Full-featured Cypher editor with validation and execution.

**Files to create:**
- `client/src/components/expert-mode/QueryEditorModal.tsx`
- `client/src/lib/cypher-language.ts` (Monaco language config)

**Dependencies to install:**
```bash
npm install @monaco-editor/react
```

- [ ] **2.3a** Create modal wrapper component
  - Backdrop with close on outside click
  - Close button (X)
  - Escape key to close

- [ ] **2.3b** Configure Monaco Editor for Cypher
  - Register Cypher language with Monaco
  - Define token rules for syntax highlighting:
    - Keywords: MATCH, WHERE, RETURN, ORDER, BY, LIMIT, etc.
    - Labels: :Aquifer, :Basin, :Country (colon prefix)
    - Properties: .name, .porosity, .depth (dot prefix)
    - Strings, numbers, comments
  - Dark theme (vs-dark)

- [ ] **2.3c** Add schema-aware autocomplete (basic)
  - Suggest labels on `:` trigger
  - Suggest properties on `.` trigger
  - Use schema from `/api/v2/schema` endpoint

- [ ] **2.3d** Add validation and execution buttons
  - "Validate" button - syntax check only
  - "Run Query" button - executes against Neo4j
  - Loading states for both
  - Error display inline

- [ ] **2.3e** Display results after execution
  - Table view for results
  - Row count
  - Execution time

**Definition of Done:**
- [ ] Monaco Editor loads with Cypher syntax highlighting
- [ ] Autocomplete suggests labels and properties
- [ ] Validate button checks query syntax
- [ ] Execute button runs query and displays results
- [ ] Errors displayed inline with helpful messages

**Test Cases:**
- Modal opens when Edit clicked
- Cypher keywords highlighted correctly
- Autocomplete shows labels on `:` press
- Validate shows error for invalid syntax
- Execute returns results for valid query

---

## Task 2.4: Execution Trace Timeline

Visualize the agent execution pipeline for debugging.

**Files to create:**
- `client/src/components/expert-mode/ExecutionTrace.tsx`

- [ ] **2.4a** Create timeline progress bar
  - Horizontal bar showing relative time for each agent
  - Color-coded segments (purple=planner, blue=cypher, green=validator, orange=analyst)
  - Total execution time display

- [ ] **2.4b** Create agent detail cards
  - Card for each agent with:
    - Agent name and icon
    - Duration in ms
    - Status (success/error)
    - Retry count (if applicable)
  - Expand to show additional details

- [ ] **2.4c** Add trace visibility toggle
  - Respects `showExecutionTrace` setting
  - Collapsible section
  - Only shown when `execution_trace` exists in response

- [ ] **2.4d** Add agent-specific details (optional expansion)
  - Planner: Show complexity classification, sub-task count
  - Cypher Specialist: Show generated query pattern
  - Validator: Show retry attempts, error messages
  - Analyst: Show insight count, recommendation count

**Definition of Done:**
- [ ] Timeline shows proportional time for each agent
- [ ] Color coding distinguishes agents
- [ ] Total time accurately calculated
- [ ] Retry information displayed for validator

**Test Cases:**
- Timeline renders with correct proportions
- Agent cards show correct timing
- Trace hidden when setting disabled
- Trace hidden when no execution_trace in response

---

## Task 2.5: Integration with Chat Interface

Connect Expert Mode components to existing chat UI.

**Files to update:**
- `client/src/components/chat/ChatMessage.tsx` (or equivalent)
- `client/src/components/chat/ChatContainer.tsx`
- `client/src/hooks/useChat.ts` (or equivalent)

- [ ] **2.5a** Update chat message type to include expert mode data
  - Add `cypherQuery?: string`
  - Add `cypherExplanation?: string`
  - Add `executionTrace?: ExecutionTrace`
  - Add `retryCount?: number`
  - Add `executionTimeMs?: number`

- [ ] **2.5b** Render CypherQueryPanel in assistant messages
  - Only show for assistant messages
  - Only show when expert mode enabled
  - Pass execution data from response

- [ ] **2.5c** Render ExecutionTrace below query panel
  - Only show when `showExecutionTrace` enabled
  - Collapsible by default

- [ ] **2.5d** Add Expert Mode indicator to header
  - Badge or icon when enabled
  - Quick toggle access

- [ ] **2.5e** Handle query editing flow
  - Open QueryEditorModal when Edit clicked
  - Execute edited query
  - Display results inline or in new message

**Definition of Done:**
- [ ] Query panel appears in chat messages when expert mode on
- [ ] Execution trace shows below query panel when enabled
- [ ] Edited queries execute and display results
- [ ] All components responsive on mobile

**Test Cases:**
- Expert mode toggle shows/hides query panels
- Query panel displays correct Cypher from response
- Execution trace timeline accurate
- Edit opens modal with pre-populated query

---

## Task 2.6: Mobile Responsiveness

Ensure Expert Mode components work on smaller screens.

- [ ] **2.6a** Query panel responsive design
  - Full width on mobile
  - Scrollable code area
  - Touch-friendly copy button

- [ ] **2.6b** Query editor modal responsive
  - Full screen on mobile
  - Adequate editor height
  - Toolbar remains accessible

- [ ] **2.6c** Execution trace responsive
  - Vertical layout on mobile
  - Collapsible agent cards
  - Touch-friendly expansion

- [ ] **2.6d** Expert Mode toggle mobile placement
  - Accessible in mobile header/menu
  - Large enough touch target

**Definition of Done:**
- [ ] All components usable on 375px width screens
- [ ] Touch targets minimum 44x44px
- [ ] No horizontal scroll required

**Test Cases:**
- Query panel readable on mobile
- Editor modal usable on mobile
- Trace readable on mobile
- Toggle accessible on mobile

---

## New/Updated Files Summary

```
client/src/
├── stores/
│   └── expertModeStore.ts              # NEW - Zustand store
├── components/
│   ├── ui/
│   │   └── ExpertModeToggle.tsx        # NEW - Header toggle
│   ├── expert-mode/
│   │   ├── index.ts                    # NEW - Module exports
│   │   ├── CypherQueryPanel.tsx        # NEW - Query display
│   │   ├── QueryEditorModal.tsx        # NEW - Monaco editor
│   │   └── ExecutionTrace.tsx          # NEW - Timeline
│   └── chat/
│       ├── ChatMessage.tsx             # UPDATE - Add query panel
│       └── ChatContainer.tsx           # UPDATE - Expert mode integration
├── lib/
│   └── cypher-language.ts              # NEW - Monaco Cypher config
└── hooks/
    └── useExpertMode.ts                # NEW - Hook for easy access
```

---

## Dependencies to Add

```json
{
  "dependencies": {
    "@monaco-editor/react": "^4.6.0",
    "react-syntax-highlighter": "^15.5.0",
    "zustand": "^4.4.0"
  },
  "devDependencies": {
    "@types/react-syntax-highlighter": "^15.5.0"
  }
}
```

**Installation:**
```bash
cd client
npm install @monaco-editor/react react-syntax-highlighter zustand
npm install -D @types/react-syntax-highlighter
```

---

## API Endpoints Used

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v2/chat/message` | POST | Send message with `expert_mode: true` |
| `/api/v2/queries/execute` | POST | Execute custom Cypher query |
| `/api/v2/queries/validate` | POST | Validate query syntax |
| `/api/v2/schema` | GET | Get Neo4j schema for autocomplete |

**Note:** Some endpoints may need to be created in backend if not exists.

---

## Zero-Cost Workarounds

| Challenge | Workaround |
|-----------|------------|
| Monaco Editor bundle size | Dynamic import with React.lazy() |
| Cypher language support | Custom Monarch tokenizer (minimal) |
| No real-time validation | Validate on button click, not keystroke |
| Schema autocomplete | Fetch once and cache in store |

---

## Test Queries for Validation

```
Test Query Panel:
- Send any query with expert_mode: true
- Verify query appears in response

Test Self-Healing Display:
- Force a broken query (if possible via API)
- Verify retry badge shows

Test Query Editor:
- Click Edit on any query
- Modify and execute
- Verify results appear

Test Execution Trace:
- Enable showExecutionTrace setting
- Send query with expert_mode: true
- Verify timeline appears with agent timings
```

---

## Progress Tracking

| Task | Status | Notes |
|------|--------|-------|
| 2.1 Expert Mode Toggle | ✅ **COMPLETE** | Zustand store + toggle + settings + app-wide theming |
| 2.2 Cypher Query Panel | ⬜ Not Started | Syntax highlighting + metadata |
| 2.3 Query Editor Modal | ⬜ Not Started | Monaco editor + Cypher config |
| 2.4 Execution Trace | ⬜ Not Started | Timeline visualization |
| 2.5 Chat Integration | ⬜ Not Started | Connect components to chat |
| 2.6 Mobile Responsive | ⬜ Not Started | Responsive design pass |

---

## Definition of Done (Phase 2)

- [x] Expert Mode toggle in header ✅
- [x] Light/Dark theme works across entire app ✅
- [ ] Query panel shows below AI responses
- [ ] Query editor modal with Monaco
- [ ] Execution trace timeline visualization
- [ ] All components responsive on mobile
- [ ] Integration tests pass
- [ ] No console errors in browser

**Last Updated:** January 4, 2026 (Task 2.1 app-wide theme implementation completed)
