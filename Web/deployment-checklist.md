# 배포 체크리스트 (Deployment Checklist)

> **문서 위치:** Web/deployment-checklist.md  
> **최종 수정일:** 2026-06-24  
> **담당자:** rain (Technical Writer)  
> **적용 버전:** v1.1.0 (Speech Bubble + Async Migration)

---

## 1. 배포 위치 목록

| # | 위치 | 설명 | 파일 |
|---|------|------|------|
| 1 | **AgentFleetManager** (C#) | WPF 애플리케이션 메인 프로젝트 | AgentFleetManager/MainWindow.xaml.cs |
| 2 | **Web (HTML 리소스)** | WebView2가 렌더링하는 정적 HTML | AgentFleetManager/Web/team-runtime-graph.html |
| 3 | **Web (설계 문서)** | UI/UX 디자인 시스템 문서 | AgentFleetManager/Web/speech-bubble-design-system.md |
| 4 | **Web (요구사항 문서)** | 요구사항 정의서 | AgentFleetManager/Web/requirements-task-question-bubble.md |

> **중요:** 위 4개 위치 중 **1(C#)과 2(HTML)** 는 실제 실행에 직접 영향을 미칩니다.  
> 3과 4는 설계/참조 문서로, 배포 시 함께 버전 관리되어야 합니다.

---

## 2. 파일별 동기화 필요 사항

### 2.1 MainWindow.xaml.cs — 수정 시 확인 사항

| 체크 항목 | 설명 |
|-----------|------|
| ✅ BuildTeamGraphSnapshotAsync() 시그니처 | private async Task<object> — 반환 타입 변경 시 HTML 호환성 깨짐 |
| ✅ SendTeamGraphSnapshotAsync() 시그니처 | private async Task — fire-and-forget 패턴 유지 |
| ✅ 호출부 패턴 일관성 | 모든 호출이 _ = SendTeamGraphSnapshotAsync(); 형식인지 확인 |
| ✅ GetCurrentTeamRunStateAsync() | 1초 캐싱 로직 유지. 캐시 TTL 변경 시 성능/신선도 트레이드오프 검토 |
| ✅ ActiveTaskStatuses | 필터 조건(draft, unnable, ssigned, unning, locked) 일관성 유지 |
| ✅ JSON 필드명 | HTML 측 updateSpeechBubbles()에서 참조하는 필드명과 일치하는지 확인 |
| ✅ TeamGraphJsonOptions | JsonSerializerOptions 설정 유지 (camelCase, 인코딩 등) |

### 2.2 team-runtime-graph.html — 수정 시 확인 사항

| 체크 항목 | 설명 |
|-----------|------|
| ✅ CSS 변수 8개 | :root 내 --bubble-* 변수 8개 모두 정의 확인 |
| ✅ 다크테마 | @media (prefers-color-scheme: dark) 블록 내 변수 재정의 확인 |
| ✅ #speech-bubble-layer | pointer-events:none, z-index:5 유지 (vis-network 조작 보호) |
| ✅ canvasToScreen() | 
etwork.canvasToDOM() 사용 — 고해상도 디스플레이 대응 |
| ✅ 	runcateText() | 최대 길이 파라미터와 일관된 호출 확인 |
| ✅ getTaskIcon() / getQuestionIcon() | 상태 문자열 매핑 누락 확인 |
| ✅ updateSpeechBubbles() | task는 위쪽, question은 오른쪽 배치 로직 확인 |
| ✅ createOrUpdateBubble() | DOM 재사용 로직 — 불필요한 노드 생성 방지 |
| ✅ Zoom debounce | 50ms setTimeout — 너무 짧으면 불필요한 호출, 너무 길면 반응성 저하 |
| ✅ fterDrawing | drawRunningPulse(ctx)만 호출 — bubble 업데이트는 별도 이벤트에서 처리 |
| ✅ indNetworkEvents() | dragEnd, zoom, nimationFinished에 updateSpeechBubbles() 연결 확인 |

### 2.3 설계 문서 — 수정 시 확인 사항

| 체크 항목 | 설명 |
|-----------|------|
| ✅ speech-bubble-design-system.md | 말풍선 타입(Task/Question/Status), CSS 변수, 애니메이션 명세 일치 |
| ✅ requirements-task-question-bubble.md | Task/Question 데이터 범위, 상태값, 필터 조건 일치 |

---

## 3. 빌드 확인 사항

### 3.1 C# 빌드

`powershell
# Visual Studio 솔루션 빌드 (Release)
dotnet build AgentFleetManager.sln --configuration Release

# 확인 사항
# - 0 Error, 0 Warning (권장)
# - 모든 async 메서드가 적절한 Task 반환
# - JSON 직렬화 오류 없음
`

### 3.2 HTML 유효성 검사

`ash
# HTML 구문 검사 (선택사항)
# - 모든 script 태그 닫힘 확인
# - CSS 변수 참조 오류 없음
# - ES6 문법 호환성 확인 (WebView2 기반이므로 최신 JS 지원)
`

### 3.3 통합 테스트

| 테스트 항목 | 예상 결과 |
|------------|-----------|
| 앱 실행 시 그래프 로드 | 팀/에이전트 노드 정상 표시 |
| Task 말풍선 표시 | 활성 Task가 에이전트 노드 위쪽에 표시 |
| Question 말풍선 표시 | Open 상태 Question이 에이전트 노드 오른쪽에 표시 |
| 줌 동작 | 줌 시 말풍선 위치 정상 업데이트 (50ms 디바운스) |
| 드래그 동작 | 드래그 후 말풍선 위치 즉시 업데이트 |
| 다크모드 | OS 다크모드 전환 시 말풍선 색상 변경 |
| 펄스 애니메이션 | Running 상태 에이전트에 파란색 펄스 원 표시 |
| Task 완료 시 말풍선 제거 | completed/failed/canceled Task 말풍선 사라짐 |
| Question 답변 시 말풍선 제거 | answered/failed/canceled Question 말풍선 사라짐 |

---

## 4. 배포 절차

`mermaid
flowchart LR
    A[코드 수정] --> B[로컬 빌드 확인]
    B --> C[통합 테스트]
    C --> D[문서 동기화]
    D --> E[Git 커밋]
    E --> F[릴리즈 태그 v1.1.0]
    F --> G[배포]
`

### 단계별 체크리스트

- [ ] **Step 1:** MainWindow.xaml.cs 수정 후 빌드 (0 Error)
- [ ] **Step 2:** 	eam-runtime-graph.html 구문 검증
- [ ] **Step 3:** 설계 문서(speech-bubble-design-system.md, equirements-task-question-bubble.md) 최신화
- [ ] **Step 4:** 변경 이력(gent-fleet-graph-changelog.md) 업데이트
- [ ] **Step 5:** API 명세(graph-snapshot-data-contract.md) 동기화
- [ ] **Step 6:** 통합 테스트 수행 (위 3.3 항목)
- [ ] **Step 7:** Git 커밋 및 v1.1.0 태그
- [ ] **Step 8:** 배포 후 운영 환경 스모크 테스트

---

## 5. 롤백 계획

| 상황 | 롤백 방법 |
|------|-----------|
| C# 빌드 실패 | 이전 버전 MainWindow.xaml.cs로 복원 |
| HTML 렌더링 오류 | 이전 버전 	eam-runtime-graph.html로 복원 |
| 말풍선 미표시 | PostWebMessageAsJson 데이터 확인 → 필드명 일치 검증 |
| 성능 저하 | GetCurrentTeamRunStateAsync() 캐시 TTL 조정 또는 updateSpeechBubbles() 호출 간격 최적화 |

---

## v1.1.1 추가 사항 (2026-06-24)

### 변경 개요

| 항목 | 설명 |
|------|------|
| Zoom 버그 수정 | nodeRadius 하드코딩 제거 -> getBoundingBox() API 적용 |
| Drag 개선 | dragging 이벤트 + rAF throttle(scheduleBubbleUpdate) 추가 |
| CSS 정리 | --bubble-status-bg 제거, --bubble-max-width 중복 제거, --bubble-padding 정의 추가 |
| Hotfix | scheduleBubbleUpdate() 함수 정의 누락 수정 |

### 배포 경로

| # | 경로 | 유형 | 비고 |
|---|------|------|------|
| 1 | Web/team-runtime-graph.html | 소스 | 수정 대상 원본 |
| 2 | bin/Debug/net8.0-windows/Web/team-runtime-graph.html | Debug 빌드 출력 | csproj의 Content 복사 대상 |
| 3 | bin/Release/net8.0-windows/Web/team-runtime-graph.html | Release 빌드 출력 | csproj의 Content 복사 대상 |

> **참고:** v1.1.1 변경은 HTML 파일(team-runtime-graph.html)에만 적용됩니다.
> C# 백엔드(MainWindow.xaml.cs)는 v1.1.0과 동일합니다.

### 추가 체크리스트

| # | 체크 항목 | 확인 방법 |
|---|-----------|-----------|
| 1 | getBoundingBox() API 호출 정상 | Debug 콘솔에서 network.getBoundingBox() 반환값 확인 |
| 2 | dragging 중 말풍선 실시간 이동 | 그래프 노드 drag 시 bubble이 노드 따라가는지 육안 확인 |
| 3 | scheduleBubbleUpdate() ReferenceError 없음 | dragging 시 콘솔 에러 미발생 확인 |
| 4 | CSS 변수 7개만 존재(--bubble-status-bg 제거 확인) | :root 블록 내 --bubble-* 변수 7개 확인 |
| 5 | --bubble-max-width 단일 선언 | grep -c "bubble-max-width" = 1 |
| 6 | --bubble-padding: 4px 8px 정의 확인 | CSS 변수 선언 값 일치 확인 |
| 7 | Debug 빌드 0 Error 0 Warning | dotnet build --configuration Debug |
| 8 | Release 빌드 0 Error 0 Warning | dotnet build --configuration Release |
| 9 | 3개 경로 파일 내용 일치 | fc /b or Get-FileHash 비교 |
