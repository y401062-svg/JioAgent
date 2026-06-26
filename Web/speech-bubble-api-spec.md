# Speech Bubble API 명세

> **문서 위치:** Web/speech-bubble-api-spec.md
> **최종 수정일:** 2026-06-24
> **담당자:** rain (Technical Writer)
> **적용 버전:** v1.1.1 (Zoom 버그 수정 + Drag 개선 + CSS 정리)

---

## 1. updateSpeechBubbles(snapshot)

### 개요
vis-network 그래프 위에 Task/Question 말풍선을 렌더링합니다.
snapshot 데이터를 기반으로 활성 말풍선을 생성/갱신/제거합니다.

### 시그니처
```javascript
function updateSpeechBubbles(snapshot)
```

### 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| snapshot | Object | Yes | Team Runtime Graph 스냅샷 객체 (C# 백엔드에서 JSON으로 전송) |

### snapshot.tasks 배열 — 처리 조건

| 조건 | 설명 |
|------|------|
| task.assignedAgentId | 빈 문자열이 아닌 값이어야 함 |
| task.status | "running" / "blocked" / "runnable" 중 하나여야 함 |
| 말풍선 위치 | network.getBoundingBox(nodeId)로 노드 바운딩 박스 조회 → 노드 상단 중앙(bbox.top - 8)에 배치 |

### snapshot.questions 배열 — 처리 조건

| 조건 | 설명 |
|------|------|
| question.targetAgentId | 빈 문자열이 아닌 값이어야 함 |
| question.status | "open"이어야 함 |
| 말풍선 위치 | network.getBoundingBox(nodeId)로 노드 바운딩 박스 조회 → 노드 우측 중앙(bbox.right + 8)에 배치 |

### v1.1.1 변경 사항

| 항목 | v1.1.0 (이전) | v1.1.1 (현재) |
|------|--------------|--------------|
| 노드 위치 참조 방식 | nodeRadius = 18 * scale 하드코딩 | network.getBoundingBox(nodeId) API 사용 |
| Task 말풍선 Y 기준 | node.y - nodeRadius - gap | bbox.top - 8 (canvas 좌표) |
| Question 말풍선 X 기준 | node.x + nodeRadius + gap | bbox.right + 8 (canvas 좌표) |
| 좌표 변환 | canvas -> screen 각각 변환 | canvas 단일 좌표계 계산 후 canvasToDOM() 1회 변환 |
| 불필요 연산 | invScale 재계산 로직 존재 | canvasToScreen() 단순화 (invScale 계산 제거) |

---

## 2. scheduleBubbleUpdate()

### 개요
requestAnimationFrame 기반 throttle로 updateSpeechBubbles() 호출을 스케줄링합니다.
dragging 이벤트처럼 짧은 시간에 다수 발생하는 이벤트에서 불필요한 연산을 방지합니다.

### 시그니처
```javascript
let bubbleUpdateFrame = null;

function scheduleBubbleUpdate() {
    if (bubbleUpdateFrame) return;
    bubbleUpdateFrame = requestAnimationFrame(function() {
        bubbleUpdateFrame = null;
        updateSpeechBubbles(latestSnapshot);
    });
}
```

### 동작 방식

1. **중복 호출 차단**: bubbleUpdateFrame이 null이 아닌 경우(이미 pending rAF가 있는 경우) 즉시 return
2. **프레임 단위 실행**: requestAnimationFrame으로 브라우저의 다음 리페인트 직전에 1회만 실행
3. **상태 초기화**: 콜백 실행 후 bubbleUpdateFrame = null로 재호출 가능 상태로 전환
4. **실제 실행 함수**: updateSpeechBubbles(latestSnapshot) - 최신 스냅샷 기준으로 말풍선 렌더링

### 호출 트리거 (v1.1.1)

| 이벤트 | 호출 방식 | 설명 |
|--------|-----------|------|
| network.on("dragging") | scheduleBubbleUpdate() | rAF throttle 적용, drag 중 실시간 위치 업데이트 |
| network.on("dragEnd") | updateSpeechBubbles() 직접 호출 | drag 종료 시 최종 위치 보장 |
| network.on("zoom") | setTimeout 50ms -> updateSpeechBubbles() | zoom 디바운스 |
| network.on("animationFinished") | updateSpeechBubbles() 직접 호출 | 애니메이션 완료 후 갱신 |

### v1.1.1 변경 사항

| 항목 | v1.1.0 (이전) | v1.1.1 (현재) |
|------|--------------|--------------|
| dragging 핸들러 | 없음 (dragEnd에서만 업데이트) | scheduleBubbleUpdate() 호출 - drag 중 실시간 업데이트 |
| throttle 방식 | 없음 | requestAnimationFrame 기반 throttle |
| [Hotfix] 함수 정의 | 누락 (ReferenceError 발생) | bubbleUpdateFrame 선언 직후 함수 본문 추가 |

---

## 3. canvasToScreen(canvasPos)

### 개요
vis-network의 canvas 좌표를 DOM 화면 좌표로 변환합니다.
network.canvasToDOM()을 래핑하여 안전한 호출을 보장합니다.

### 시그니처
```javascript
function canvasToScreen(canvasPos) {
    if (!network || !canvasPos) return null;
    try {
        return network.canvasToDOM(canvasPos);
    } catch (e) {
        return null;
    }
}
```

### 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| canvasPos | Object | Yes | {x: number, y: number} - canvas 좌표계의 위치 |

### 반환값

| 조건 | 반환값 |
|------|--------|
| 정상 변환 | {x: number, y: number} - DOM 화면 좌표 (px) |
| network null 또는 canvasPos null | null |
| 변환 중 예외 발생 | null (catch 후 silent fail) |

### 사용처

- updateSpeechBubbles() 내부: canvas 좌표 -> DOM 좌표 변환 후 말풍선의 style.left/style.top 설정

### v1.1.1 변경 사항

| 항목 | v1.1.0 (이전) | v1.1.1 (현재) |
|------|--------------|--------------|
| invScale 계산 | 함수 내부에서 const invScale = 1 / Math.max(scale, 0.1) 별도 계산 | 불필요한 invScale 계산 제거 - 순수 좌표 변환만 수행 |
| 역할 | canvas -> DOM 변환 + 스케일 보정 | canvas -> DOM 순수 좌표 변환 (스케일 보정은 updateSpeechBubbles()에서 처리) |

---

## 4. CSS 변수 명세 (v1.1.1)

```css
:root {
    --bubble-task-bg: #1e40af;      /* Task 말풍선 배경색 (파랑) */
    --bubble-question-bg: #92400e;  /* Question 말풍선 배경색 (주황) */
    --bubble-text: #ffffff;         /* 말풍선 텍스트 색상 */
    --bubble-font-size: 11px;       /* 말풍선 폰트 크기 */
    --bubble-radius: 10px;          /* 말풍선 모서리 둥글기 */
    --bubble-max-width: 200px;      /* 말풍선 최대 너비 */
    --bubble-padding: 4px 8px;      /* 말풍선 내부 여백 */
}

@media (prefers-color-scheme: dark) {
    :root {
        --bubble-task-bg: #1e3a5f;      /* 다크모드 Task 배경 */
        --bubble-question-bg: #5c4a1e;  /* 다크모드 Question 배경 */
    }
}
```

### v1.1.1 CSS 정리 내역

| 변수 | 변경 | 사유 |
|------|------|------|
| --bubble-status-bg | 제거 | 미사용 변수 (Status Bubble 미구현) |
| --bubble-max-width | 중복 제거 | 2회 선언된 변수를 1개로 통일 |
| --bubble-padding | 정의 추가 (4px 8px) | 선언만 있고 값이 누락된 상태 보완 |

---

## 5. 함수 호출 관계도

```
render(snapshot)
  +-- updateSpeechBubbles(snapshot)         <- 초기 렌더링
  |     +-- network.getBoundingBox(nodeId)  <- 노드 위치 조회 (v1.1.1 신규)
  |     +-- canvasToScreen(canvasPos)       <- 좌표 변환
  |     +-- createOrUpdateBubble(...)       <- DOM 노드 생성/재사용
  |
  +-- bindNetworkEvents()
        +-- dragging ----> scheduleBubbleUpdate()
        |                   +-- requestAnimationFrame
        |                         +-- updateSpeechBubbles(latestSnapshot)
        +-- dragEnd -----> updateSpeechBubbles(latestSnapshot)
        +-- zoom --------> setTimeout(50ms)
        |                   +-- updateSpeechBubbles(latestSnapshot)
        +-- animationFinished --> updateSpeechBubbles(latestSnapshot)
```
