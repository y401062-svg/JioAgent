# Agent Speech Bubble UI/UX Design System

> **Document Version:** 1.0  
> **Author:** choi (UI/UX Designer)  
> **Date:** 2026-06-24  
> **Target:** team-runtime-graph.html (vis-network based agent graph)

---

## 1. Overview

에이전트 말풍선(Speech Bubble)은 Team Runtime Graph의 vis-network 캔버스 위에 **HTML 절대 위치(absolute position) div 오버레이**로 렌더링됩니다.
각 에이전트(또는 팀) 노드에 연결된 **Task 상태/아이콘**과 **Question 알림**을 시각적으로 표현하여, 사용자가 그래프만 보고도 현재 작업 현황을 직관적으로 파악할 수 있게 합니다.

### 1.1 Design Principles

| Principle | Description |
|-----------|-------------|
| Readability First | Max 2 lines per bubble, ellipsis (...) overflow |
| Non-interference | Does not block vis-network node/edge operations (drag, zoom) |
| Performance Optimized | Minimize DOM manipulation at 2-second refresh cycle |
| Consistency | Unified with existing CSS variables and color system |
| Accessibility | Sufficient contrast ratio (>=4.5:1), aria-label support |

---

## 2. Speech Bubble Types

### 2.1 Task Bubble

Displays the **Task currently assigned** to an agent.

| Property | Value |
|----------|-------|
| Icon | 🔧 (task) / 📋 (in-progress) / ⚡ (running) / ✅ (completed) |
| Background | `#eff6ff` (light) / `#1e3a5f` (dark) |
| Border | `#93c5fd` (light) / `#3b82f6` (dark) |
| Text | Task title (max 40 chars) |
| Position | **Above** agent node (8px gap) |

### 2.2 Question Bubble

Displays a **Question** arrived for the agent.

| Property | Value |
|----------|-------|
| Icon | ❓ (new) / 💬 (answered) / ⏳ (pending) |
| Background | `#fef3c7` (light) / `#5c4a1e` (dark) |
| Border | `#fcd34d` (light) / `#f59e0b` (dark) |
| Text | Question summary (max 40 chars) |
| Position | **Right side** of agent node (12px gap) |

### 2.3 Status Bubble

Shows the agent's **current status summary**.

| Property | Value |
|----------|-------|
| Icon | 🔵 (running) / ⚪ (idle) / 🟡 (waiting) / 🔴 (error) |
| Background | Matches status color scheme |
| Text | Agent status text |
| Position | **Below** agent node (6px gap) |

---

## 3. Bubble Layout & Positioning

### 3.1 Position Reference

```
         ┌─────────────────┐    <- Task Bubble (above, 8px)
         │  🔧 Task Title  │
         └─────────────────┘
                  ↑
            ┌─────────┐       <- Agent Node
            │  ● Agent │
            └─────────┘
                  ↓
         ┌─────────────────┐    <- Status Bubble (below, 6px)
         │  🔵 Running     │
         └─────────────────┘

                        ┌─────────────────┐  <- Question Bubble
                        │  ❓ Question    │      (right, 12px)
                        └─────────────────┘
```

### 3.2 Canvas-to-Screen Coordinate Conversion

```javascript
function canvasToScreen(canvasPos, network) {
  const viewPos = network.getViewPosition();
  const scale = network.getScale();
  const container = graphElement.getBoundingClientRect();
  return {
    x: (canvasPos.x - viewPos.x) * scale + container.width / 2,
    y: (canvasPos.y - viewPos.y) * scale + container.height / 2
  };
}
```

### 3.3 Position Calculation by Type

```javascript
function getBubblePosition(nodeId, type, network) {
  const pos = network.getPositions([nodeId])[nodeId];
  if (!pos) return null;
  const screenPos = canvasToScreen(pos, network);
  const w = 220, h = 36, gap = 8;

  switch (type) {
    case 'task':
      return { left: screenPos.x - w/2, top: screenPos.y - 18 - h - gap };
    case 'question':
      return { left: screenPos.x + 18 + gap, top: screenPos.y - h/2 };
    case 'status':
      return { left: screenPos.x - w/2, top: screenPos.y + 18 + gap };
  }
}
```

---

## 4. Detailed CSS Design

### 4.1 CSS Variables (Extended from Existing)

```css
:root {
  /* Existing */
  --text: #111827;
  --muted: #6b7280;
  --panel: #ffffff;
  --line: #d1d5db;
  --soft: #f3f4f6;
  --blue: #2563eb;

  /* New - Bubble colors */
  --bubble-task-bg: #eff6ff;
  --bubble-task-border: #93c5fd;
  --bubble-task-text: #1e3a8a;
  --bubble-question-bg: #fef3c7;
  --bubble-question-border: #fcd34d;
  --bubble-question-text: #92400e;
  --bubble-status-bg: #f0fdf4;
  --bubble-status-border: #86efac;
  --bubble-status-text: #166534;
  --bubble-radius: 12px;
  --bubble-shadow: 0 2px 8px rgba(15, 23, 42, 0.12);
  --bubble-font-size: 12px;
  --bubble-max-width: 240px;
}
```

### 4.2 Base Bubble Styles

```css
.speech-bubble {
  position: absolute;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--bubble-radius);
  box-shadow: var(--bubble-shadow);
  font-size: var(--bubble-font-size);
  font-family: "Segoe UI", Arial, sans-serif;
  line-height: 1.4;
  max-width: var(--bubble-max-width);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  pointer-events: none;
  user-select: none;
  z-index: 5;
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.speech-bubble--task {
  background: var(--bubble-task-bg);
  border: 1px solid var(--bubble-task-border);
  color: var(--bubble-task-text);
}

.speech-bubble--question {
  background: var(--bubble-question-bg);
  border: 1px solid var(--bubble-question-border);
  color: var(--bubble-question-text);
}

.speech-bubble--status {
  background: var(--bubble-status-bg);
  border: 1px solid var(--bubble-status-border);
  color: var(--bubble-status-text);
}

/* Bubble arrow (tail) */
.speech-bubble::after {
  content: '';
  position: absolute;
  width: 0;
  height: 0;
  border: 6px solid transparent;
}

.speech-bubble--task::after {
  bottom: -12px;
  left: 50%;
  transform: translateX(-50%);
  border-top-color: var(--bubble-task-border);
}

.speech-bubble--question::after {
  left: -12px;
  top: 50%;
  transform: translateY(-50%);
  border-right-color: var(--bubble-question-border);
}

.speech-bubble--status::after {
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  border-bottom-color: var(--bubble-status-border);
}
```

### 4.3 Icon & Text Styles

```css
.bubble-icon {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  line-height: 1;
}

.bubble-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bubble-text--multiline {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  white-space: normal;
  word-break: break-all;
}
```

---

## 5. Text Length & Ellipsis Rules

| Element | Max Characters | Handling |
|---------|---------------|----------|
| Task Title | 40 (35 for 2-line) | `...` ellipsis |
| Question Summary | 40 | `...` ellipsis |
| Status Text | 20 | `...` ellipsis |
| Icon | 1-2 emoji chars | No change |

```javascript
function truncateText(text, maxLength) {
  if (!text) return '';
  const str = String(text).trim();
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength - 1) + '\u2026';
}
```

---

## 6. Multiple Task/Question Display

### 6.1 Stack Layout (Recommended)

```
+---------------------------+  <- First task (full display)
| 🔧 Refactoring...         |
+---------------------------+  <- Subsequent tasks (summarized)
|   +2 more tasks           |
+---------------------------+
```

**Rules:**
- Max 3 items shown (1 full + 2 counted)
- Beyond 3: show "+N more tasks" text
- Stack shadow darkens downward
- Same layout for Questions

```css
.speech-bubble--stacked::before {
  content: '';
  position: absolute;
  top: -4px;
  left: 2px;
  right: 2px;
  height: 4px;
  background: var(--bubble-task-bg);
  border: 1px solid var(--bubble-task-border);
  border-bottom: none;
  border-radius: var(--bubble-radius) var(--bubble-radius) 0 0;
  opacity: 0.6;
}
```

### 6.2 Slide Layout (Alternative)

```html
<div class="speech-bubble-slider">
  <button class="slider-btn slider-btn--prev"><</button>
  <div class="slider-content">
    <span class="bubble-icon">🔧</span>
    <span class="bubble-text">Task 1 of 3: Refactoring...</span>
  </div>
  <button class="slider-btn slider-btn--next">></button>
</div>
```

> **Decision:** Stack layout is the **default** for simplicity and performance.
> Slide layout is an optional future enhancement.

---

## 7. Entry/Exit Animations

### 7.1 Fade In

```css
@keyframes bubbleFadeIn {
  from { opacity: 0; transform: translateY(8px) scale(0.92); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}
```

### 7.2 Fade Out

```css
@keyframes bubbleFadeOut {
  from { opacity: 1; transform: translateY(0) scale(1); }
  to   { opacity: 0; transform: translateY(-8px) scale(0.92); }
}
```

### 7.3 Slide Up

```css
@keyframes bubbleSlideUp {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

### 7.4 Animation Policy

| Situation | Animation | Duration |
|-----------|-----------|----------|
| New Task arrives | bubbleFadeIn | 0.3s |
| New Question arrives | bubbleSlideUp | 0.35s |
| Status change | bubbleFadeIn | 0.25s |
| Task completed/removed | bubbleFadeOut | 0.2s |
| Full refresh (2s cycle) | **No animation** | - |

> **Performance note:** Skip animations during full 2-second refresh cycles.
> Apply animations only for event-based individual updates.

---

## 8. Dark Theme Support

### 8.1 Dark Theme Variables

```css
[data-theme="dark"] {
  --bubble-task-bg: #1e3a5f;
  --bubble-task-border: #3b82f6;
  --bubble-task-text: #bfdbfe;
  --bubble-question-bg: #5c4a1e;
  --bubble-question-border: #f59e0b;
  --bubble-question-text: #fde68a;
  --bubble-status-bg: #14532d;
  --bubble-status-border: #22c55e;
  --bubble-status-text: #bbf7d0;
  --bubble-shadow: 0 2px 8px rgba(0, 0, 0, 0.35);
}
```

### 8.2 Theme Toggle

```javascript
function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('team-graph-theme', theme);
}
```

> **Note:** Current graph supports light theme only. Dark theme is proposed for **Phase 2** implementation with a toggle button in the toolbar.

---

## 9. Performance Optimization Guide

| Item | Recommendation |
|------|---------------|
| DOM node count | Max 30 bubble divs (remove off-screen) |
| Minimize reflow | Use `position: absolute` + `transform` (avoid left/top) |
| requestAnimationFrame | Throttle position updates with rAF |
| Animations | `opacity` + `transform` only (GPU accelerated) |
| Refresh cycle | Replace `textContent` instead of recreating DOM nodes |
| Pointer events | `pointer-events: none` to protect vis-network operations |

---

## 10. Implementation Checklist

### Phase 1 — Core Bubbles (Priority: High)
- [ ] HTML: Add bubble container div (`#bubble-layer`)
- [ ] CSS: Base bubble styles (`.speech-bubble--task/question/status`)
- [ ] CSS: Add CSS variables to `:root`
- [ ] CSS: Entry/exit animations
- [ ] JS: `canvasToScreen()` coordinate conversion
- [ ] JS: `updateBubbles()` function
- [ ] JS: Hook into `render()` for bubble updates
- [ ] JS: Update positions on zoom/drag/resize

### Phase 2 — Data Integration (Priority: High)
- [ ] Map Task data to Task Bubble
- [ ] Map Question data to Question Bubble
- [ ] Text truncation (`truncateText`)
- [ ] Dynamic status icon mapping

### Phase 3 — Stack/Multi (Priority: Medium)
- [ ] Stack display for multiple tasks
- [ ] "+N more" summary text
- [ ] Question count badge

### Phase 4 — Animation & Polish (Priority: Low)
- [ ] Individual fadeIn/fadeOut on event updates
- [ ] Dark theme CSS variables
- [ ] Theme toggle UI
- [ ] Accessibility (aria-label) improvements

---

## 11. Implementation Code Snippets

### 11.1 Bubble Container (HTML)

```html
<div id="bubble-layer" style="position:absolute;inset:0;pointer-events:none;z-index:5;"></div>
```

### 11.2 Bubble Creation (JavaScript)

```javascript
function createBubbleElement(agentId, type, icon, text) {
  const el = document.createElement('div');
  el.className = 'speech-bubble speech-bubble--' + type;
  el.dataset.agentId = agentId;
  el.dataset.bubbleType = type;
  el.innerHTML = '<span class="bubble-icon">' + icon + '</span>'
    + '<span class="bubble-text">' + escapeHtml(truncateText(text, 40)) + '</span>';
  return el;
}
```

### 11.3 Bubble Update Loop

```javascript
function updateBubbles(snapshot, network) {
  const layer = document.getElementById('bubble-layer');
  if (!layer || !network) return;

  const agents = Array.isArray(snapshot?.agents) ? snapshot.agents : [];
  const activeIds = new Set();

  for (const agent of agents) {
    const nodeId = 'agent:' + agent.agentName;
    const tasks = agent.tasks || [];
    const questions = agent.questions || [];

    if (tasks.length > 0) {
      const taskId = nodeId + ':task';
      activeIds.add(taskId);
      let bubble = layer.querySelector('[data-bubble-id="' + taskId + '"]');
      const mainTask = tasks[0];
      const extraCount = tasks.length - 1;
      const displayText = extraCount > 0
        ? truncateText(mainTask.title, 30) + ' (+' + extraCount + ' more)'
        : truncateText(mainTask.title, 40);
      const icon = getTaskIcon(mainTask.status);

      if (!bubble) {
        bubble = createBubbleElement(agent.agentName, 'task', icon, displayText);
        bubble.dataset.bubbleId = taskId;
        layer.appendChild(bubble);
      } else {
        bubble.querySelector('.bubble-icon').textContent = icon;
        bubble.querySelector('.bubble-text').textContent = displayText;
      }
      positionBubble(bubble, nodeId, 'task', network);
    }

    if (questions.length > 0) {
      // Same pattern for Question bubbles
    }
  }

  // Remove stale bubbles
  const existing = layer.querySelectorAll('[data-bubble-id]');
  for (const el of existing) {
    if (!activeIds.has(el.dataset.bubbleId)) {
      el.classList.add('speech-bubble--exit');
      el.addEventListener('animationend', function() { this.remove(); });
      setTimeout(function() { if (el.parentNode) el.remove(); }, 300);
    }
  }
}
```

### 11.4 Position Update on Zoom/Drag

```javascript
network.on('zoom', function() { scheduleBubbleUpdate(); });
network.on('dragEnd', function() { scheduleBubbleUpdate(); });
network.on('animationFinished', function() { scheduleBubbleUpdate(); });

var bubbleUpdatePending = false;
function scheduleBubbleUpdate() {
  if (bubbleUpdatePending) return;
  bubbleUpdatePending = true;
  requestAnimationFrame(function() {
    updateBubbles(latestSnapshot, network);
    bubbleUpdatePending = false;
  });
}
```

---

## 12. Task/Question Status Icon Map

### 12.1 Task Icons

| Status | Icon | Description |
|--------|------|-------------|
| draft | 📄 | Draft state |
| runnable / dispatched | ⚡ | Runnable / Dispatched |
| running / in_progress | 🔧 | In progress |
| completed | ✅ | Completed |
| failed | ❌ | Failed |
| blocked | 🚧 | Blocked |
| canceled | 🚫 | Canceled |

### 12.2 Question Icons

| Status | Icon | Description |
|--------|------|-------------|
| pending / new | ❓ | New question (awaiting answer) |
| answered | 💬 | Answered |
| canceled | 🗑️ | Canceled |
| failed | ⚠️ | Delivery failed |

---

## 13. Agent-Bubble Spatial Relationship

When both Task and Question bubbles are displayed simultaneously, maintain clear spatial separation around the agent node to prevent visual confusion.

```
          +--------------------------+
          |  🔧 Task In Progress     |  <- (above)
          +--------------------------+

              +------------+
              |  ● Agent   |
              +------------+
          +--------------------------+    +--------------------------+
          |  🔵 Running              |    |  ❓ Question Arrived     |
          +--------------------------+    +--------------------------+
              (below)                              (right)
```

---

## 14. Integration Points with Existing Code

| Integration Point | File | Description |
|-------------------|------|-------------|
| CSS Variables | team-runtime-graph.html :root | Add bubble color variables |
| render() function | team-runtime-graph.html | Add updateBubbles() call |
| Network events | team-runtime-graph.html bindNetworkEvents() | Zoom/drag bubble refresh |
| Snapshot data | MainWindow.xaml.cs BuildTeamGraphSnapshot() | Add tasks/questions arrays |
| Existing shortText() | team-runtime-graph.html | Extend to 40 chars for bubbles |

---

*End of Document*
