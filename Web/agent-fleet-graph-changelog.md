# Agent Fleet Graph — 변경 이력 (CHANGELOG)

> **문서 위치:** Web/agent-fleet-graph-changelog.md  
> **최종 수정일:** 2026-06-24  
> **담당자:** rain (Technical Writer)

---

## v1.1.0 (2026-06-24)

### 개요

Task/Question 말풍선(Speech Bubble) 시스템을 vis-network 그래프에 추가하고, C# 백엔드의 스냅샷 생성을 async 패턴으로 마이그레이션했습니다.

---

### 변경 항목

#### 1. C# 백엔드 (MainWindow.xaml.cs)

| # | 변경 내용 | 설명 |
|---|-----------|------|
| 1.1 | BuildTeamGraphSnapshot() → BuildTeamGraphSnapshotAsync() | 동기 메서드를 async로 마이그레이션. Task<object> 반환 |
| 1.2 | SendTeamGraphSnapshot() → SendTeamGraphSnapshotAsync() | fire-and-forget 패턴 적용. 내부에서 wait BuildTeamGraphSnapshotAsync() 호출 |
| 1.3 | 호출부 5곳 _ = SendTeamGraphSnapshotAsync() 업데이트 | 모든 호출을 fire-and-forget discard로 통일 |
| 1.4 | GetCurrentTeamRunStateAsync() 공통 메서드 추출 | _cachedTeamRunState + 1초 캐싱(StateCacheDuration) 적용 |
| 1.5 | ActiveTaskStatuses static readonly HashSet 도입 | StringComparer.OrdinalIgnoreCase 사용, 값: draft, unnable, ssigned, unning, locked |
| 1.6 | 스냅샷 데이터 확장 | 	asks, questions, 	askSummary, questionSummary, 	asksLoadFailed, questionsLoadFailed 필드 추가 |
| 1.7 | 활성 Task 필터 | ActiveTaskStatuses.Contains(t.Status) 조건으로 활성 상태 Task만 전송 |
| 1.8 | 활성 Question 필터 | status == "open" 조건으로 미답변 Question만 전송 |
| 1.9 | taskSummary/questionSummary 집계 | 상태별 그룹핑 및 카운트 문자열 생성 (예: "running 3 / draft 1") |

#### 2. HTML 프론트엔드 (team-runtime-graph.html)

| # | 변경 내용 | 설명 |
|---|-----------|------|
| 2.1 | #speech-bubble-layer 컨테이너 추가 | position:absolute; inset:0; pointer-events:none; z-index:5 |
| 2.2 | CSS 변수 8개 추가 | --bubble-task-bg, --bubble-question-bg, --bubble-status-bg, --bubble-text, --bubble-font-size, --bubble-radius, --bubble-padding, --bubble-max-width |
| 2.3 | 다크테마 CSS 추가 | @media (prefers-color-scheme: dark) 내 변수 재정의 |
| 2.4 | 전역 함수 5개 구현 | canvasToScreen(), 	runcateText(), getTaskIcon(), getQuestionIcon(), updateSpeechBubbles() |
| 2.5 | bubble helper 함수 | createOrUpdateBubble() — DOM 노드 재사용으로 성능 최적화 |
| 2.6 | zoom debounce (50ms) | setTimeout으로 zoom 이벤트 50ms throttle |
| 2.7 | afterDrawing 최적화 | drawRunningPulse(ctx)만 호출 (bubble 업데이트 제거) |
| 2.8 | 이벤트 통합 | ender() 내 updateSpeechBubbles(), fterDrawing, dragEnd, zoom(debounced), nimationFinished |

---

### 마이그레이션 가이드 (Phase 2 대비)

#### C# 측면

`csharp
// [AS-IS] 동기 버전 (v1.0.x)
private object BuildTeamGraphSnapshot() { ... }
private void SendTeamGraphSnapshot() { ... }

// [TO-BE] 비동기 버전 (v1.1.0)
private async Task<object> BuildTeamGraphSnapshotAsync() { ... }
private async Task SendTeamGraphSnapshotAsync() { ... }

// 호출 패턴: fire-and-forget
_ = SendTeamGraphSnapshotAsync();
`

> **참고:** GetCurrentTeamRunStateAsync()는 1초 캐싱을 사용하므로 동일 Run 내 중복 호출 시 성능 오버헤드가 최소화됩니다.  
> Phase 2에서 캐시 무효화 전략 또는 더 긴 캐시 TTL 조정을 고려할 수 있습니다.

#### HTML 측면

`javascript
// render() 종료 시 bubble 업데이트
updateSpeechBubbles(snapshot);

// 네트워크 이벤트 바인딩 (v1.1.0 패턴)
network.on("afterDrawing", function(ctx) { drawRunningPulse(ctx); });
network.on("dragEnd", function() { updateSpeechBubbles(latestSnapshot); });
network.on("zoom", debounced(50, function() { updateSpeechBubbles(latestSnapshot); }));
network.on("animationFinished", function() { updateSpeechBubbles(latestSnapshot); });
`

> **참고:** 새로운 말풍선 타입(Status Bubble) 추가 시 speech-bubble--status CSS 클래스와 배치 로직만 확장하면 됩니다.

---

### 이전 버전

| 버전 | 날짜 | 주요 변경 |
|------|------|-----------|
| v1.0.0 | 2026-06-21 | 초기 Team Runtime Graph 구현. Material Design 리팩터링 |

## v1.1.1 (2026-06-24)


### 개요

말풍선(Speech Bubble)의 zoom 스케일 버그를 근본 수정하고, dragging 중 말풍선이 노드를 따라다니지 않는 버벅거림을 개선했습니다. CSS 데드코드를 정리하여 유지보수성을 높였습니다.

---

### 변경 항목

#### 1. updateSpeechBubbles() — getBoundingBox() API 적용 (nodeRadius 하드코딩 제거)

| # | 변경 내용 | 설명 |
|---|-----------|------|
| 1.1 | nodeRadius = 18 * scale 하드코딩 제거 | size: 18만 가정한 하드코딩으로 size: 22(공유 에이전트) 노드에서 위치가 틀어지는 버그 수정 |
| 1.2 | network.getBoundingBox(nodeId) API 도입 | vis-network의 실제 노드 바운딩 박스를 조회하여 모든 노드 크기에 정확히 대응 |
| 1.3 | Task 말풍선 위치 계산 | canvasCenterX = (bbox.left + bbox.right) / 2 → bbox.top - 8 (노드 상단 중앙) |
| 1.4 | Question 말풍선 위치 계산 | canvasNodeRight = bbox.right → canvasCenterY = (bbox.top + bbox.bottom) / 2 (노드 우측 중앙) |
| 1.5 | 좌표계 단일화 | canvas 좌표계에서만 계산 후 canvasToDOM()으로 1회 변환 |

#### 2. dragging 이벤트 핸들러 + rAF throttle 추가

| # | 변경 내용 | 설명 |
|---|-----------|------|
| 2.1 | network.on("dragging") 핸들러 추가 | drag 중 말풍선이 노드를 실시간으로 따라다니도록 개선 (기존 dragEnd에서만 업데이트) |
| 2.2 | scheduleBubbleUpdate() 함수 도입 | requestAnimationFrame 기반 throttle — 불필요한 연산 방지, 프레임 단위로만 updateSpeechBubbles() 실행 |
| 2.3 | bubbleUpdateFrame 변수 추가 | rAF ID 저장으로 중복 호출 차단, 콜백 내에서 bubbleUpdateFrame = null 초기화 |
| 2.4 | dragEnd 유지 | drag 종료 시 추가 업데이트 보장 |
| 2.5 | [Hotfix] 함수 정의 누락 수정 | 리뷰 단계에서 scheduleBubbleUpdate() 참조 에러(ReferenceError) 발견 → 즉시 핫픽스로 함수 본문 추가 |

#### 3. CSS 데드코드 정리

| # | 변경 내용 | 설명 |
|---|-----------|------|
| 3.1 | --bubble-status-bg: #065f46 제거 | 미사용 변수 (Status Bubble 타입은 아직 구현되지 않음) |
| 3.2 | --bubble-max-width: 200px 중복 제거 | 2회 선언된 변수를 1개로 통일 |
| 3.3 | --bubble-padding 정의 추가 | 변수는 선언되었으나 값이 누락된 상태 → 4px 8px로 정의 |

---

### Hotfix 내역

| Hotfix | 발견자 | 내용 |
|--------|--------|------|
| scheduleBubbleUpdate() 정의 누락 | hanroro (SE 리뷰), hipi (유지보수성 리뷰) | dragging 핸들러에서 scheduleBubbleUpdate() 호출 시 ReferenceError 발생. bubbleUpdateFrame 변수 선언 직후 함수 본문 추가 |

---

### 빌드 및 배포

- Debug 빌드: 0 Error, 0 Warning
- Release 빌드: 0 Error, 0 Warning
- 배포 경로 3곳 동기화 완료 (소스, Debug, Release)

---

### 이전 버전

| 버전 | 날짜 | 주요 변경 |
|------|------|-----------|
| v1.1.1 | 2026-06-24 | 말풍선 zoom 버그 수정(getBoundingBox), drag 실시간 업데이트(throttle), CSS 데드코드 정리 |
| v1.1.0 | 2026-06-24 | Task/Question 말풍선 시스템 추가, C# async 마이그레이션 |
| v1.0.0 | 2026-06-21 | 초기 Team Runtime Graph 구현. Material Design 리팩터링 |
