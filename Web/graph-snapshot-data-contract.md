# Graph Snapshot Data Contract — API 명세

> **문서 위치:** Web/graph-snapshot-data-contract.md  
> **최종 수정일:** 2026-06-24  
> **담당자:** rain (Technical Writer)  
> **대상:** C# MainWindow.xaml.cs → HTML team-runtime-graph.html (PostWebMessageAsJson)

---

## 1. 개요

C# 백엔드(MainWindow.xaml.cs)의 BuildTeamGraphSnapshotAsync() 메서드가 생성하는 JSON 객체를 CoreWebView2.PostWebMessageAsJson()을 통해 HTML 프론트엔드(	eam-runtime-graph.html)로 전송합니다.

---

## 2. 전체 JSON 구조

`json
{
  "generatedAt": "2026-06-24T15:00:00Z",

  "teams": [ ... ],
  "agents": [ ... ],
  "teamRuns": [ ... ],
  "diagnostics": { ... },

  "tasks": [ ... ],
  "questions": [ ... ],
  "taskSummary": "running 3 / draft 1",
  "questionSummary": "open 2 / answered 5",
  "tasksLoadFailed": false,
  "questionsLoadFailed": false
}
`

---

## 3. 필드 상세 명세

### 3.1 generatedAt

| 속성 | 타입 | 설명 |
|------|------|------|
| generatedAt | string (ISO 8601) | 스냅샷 생성 시각 (DateTimeOffset.Now). 예: "2026-06-24T15:00:00+09:00" |

---

### 3.2 	eams

팀 단위 요약 정보 배열.

| 필드 | 타입 | 설명 |
|------|------|------|
| 	eamId | string | 팀 고유 식별자 |
| 
ame | string | 팀 이름 |
| description | string | 팀 설명 |
| leaderAgentId | string | 리더 에이전트 ID |
| status | string | 현재 Run 상태 (예: "running", "idle") |
| currentRunId | string | 현재 활성 Run ID |
| memberAgentIds | string[] | 팀 멤버 에이전트 ID 목록 |

---

### 3.3 gents

에이전트 단위 요약 정보 배열.

| 필드 | 타입 | 설명 |
|------|------|------|
| gentName | string | 에이전트 이름 |
| status | string | 실행 상태 (예: "Running", "Not configured") |
| isRunning | boolean | 실행 중 여부 |
| description | string | 에이전트 역할 설명 (AgentArgumentProfile.AgentRole) |
| 	eamCount | number | 소속 팀 개수 |

---

### 3.4 	eamRuns

Run 요약 정보 배열.

| 필드 | 타입 | 설명 |
|------|------|------|
| id | string | Run 고유 식별자 |
| 	itle | string | Run 제목 |
| mode | string | 실행 모드 (예: "auto", "manual") |
| status | string | Run 상태 |

---

### 3.5 diagnostics

진단 정보 객체.

| 필드 | 타입 | 설명 |
|------|------|------|
| ppBaseDirectory | string | 애플리케이션 베이스 디렉터리 경로 |
| 	eamSettingsDirectory | string | 팀 설정 디렉터리 경로 |
| 	eamSettingsExists | boolean | 팀 설정 디렉터리 존재 여부 |
| 	eamSettingsFileCount | number | *.team.json 파일 개수 |
| 	eamSettingsFiles | string[] | 팀 설정 파일명 목록 |
| isualTeamCount | number | UI에 표시 중인 팀 개수 |
| snapshotTeamCount | number | 스냅샷에 포함된 팀 개수 |
| gentCount | number | 등록된 에이전트 인스턴스 개수 |

---

### 3.6 	asks (v1.1.0 신규)

활성 상태 Task 배열. ActiveTaskStatuses 필터 적용.

**필터 조건:** draft, unnable, ssigned, unning, locked 상태만 포함.

| 필드 | 타입 | 설명 |
|------|------|------|
| id | string | Task 고유 식별자 |
| 	itle | string | Task 제목 |
| status | string | Task 상태 (아래 상태표 참고) |
| ssignedAgentId | string | 담당 에이전트 ID |
| equesterAgentId | string | 요청 에이전트 ID |
| updatedAt | string (ISO 8601) | 최종 업데이트 시각 |

**정렬:** updatedAt 내림차순 (최신순).

---

### 3.7 questions (v1.1.0 신규)

활성 Question 배열. status == "open" 필터 적용.

| 필드 | 타입 | 설명 |
|------|------|------|
| id | string | Question 고유 식별자 |
| romAgentId | string | 발신 에이전트 ID |
| 	argetAgentId | string | 수신(대상) 에이전트 ID |
| question | string | 질문 내용 |
| locking | boolean | 차단(Blocking) Question 여부 |
| elatedTaskId | string | 관련 Task ID (없으면 빈 문자열) |
| updatedAt | string (ISO 8601) | 최종 업데이트 시각 |

**정렬:** updatedAt 내림차순 (최신순).

---

### 3.8 	askSummary (v1.1.0 신규)

전체 Task 상태별 집계 문자열.

- 포맷: "{상태명} {개수} / {상태명} {개수} / ..."
- 정렬: 개수 내림차순, 동순위는 상태명 오름차순
- 예: "running 3 / draft 1 / completed 5"

---

### 3.9 questionSummary (v1.1.0 신규)

전체 Question 상태별 집계 문자열.

- 포맷: "{상태명} {개수} / {상태명} {개수} / ..."
- 정렬: 개수 내림차순, 동순위는 상태명 오름차순
- 예: "open 2 / answered 5 / canceled 1"

---

### 3.10 	asksLoadFailed / questionsLoadFailed (v1.1.0 신규)

| 필드 | 타입 | 설명 |
|------|------|------|
| 	asksLoadFailed | boolean | TeamRunState 로드 실패 시 	rue (tasks 배열은 빈 배열) |
| questionsLoadFailed | boolean | TeamRunState 로드 실패 시 	rue (questions 배열은 빈 배열) |

> state is null일 때 두 필드 모두 	rue가 됩니다.

---

## 4. 상태값 Enum

### 4.1 Task 상태

| 값 | 설명 | 말풍선 표시 |
|----|------|-------------|
| draft | 초안 상태, 아직 실행 준비 안 됨 | ✅ 표시 (회색) |
| unnable | 실행 가능 상태 | ✅ 표시 (파랑) |
| ssigned | 특정 에이전트에 할당됨 | ✅ 표시 (파랑) |
| unning | 실행 중 | ✅ 표시 (파랑 + 펄스) |
| locked | Question/Task에 의해 차단됨 | ✅ 표시 (노랑) |
| completed | 완료됨 | ❌ 미표시 |
| ailed | 실패 | ❌ 미표시 |
| canceled | 취소됨 | ❌ 미표시 |

> 말풍선 필터는 ActiveTaskStatuses (draft, unnable, ssigned, unning, locked)를 기준으로 합니다.

### 4.2 Question 상태

| 값 | 설명 | 말풍선 표시 |
|----|------|-------------|
| open | 답변 대기 중 | ✅ 표시 (주황) |
| nswered | 답변 완료 | ❌ 미표시 |
| ailed | 전송 실패 | ❌ 미표시 |
| canceled | 취소됨 | ❌ 미표시 |

> 말풍선 필터는 status == "open" 조건을 기준으로 합니다.

---

## 5. C# 데이터 소스 매핑

| JSON 필드 | C# 소스 | 메서드 |
|-----------|---------|--------|
| 	eams | TeamSummaryViewModel[] | Teams.ToArray() 또는 LoadTeamDefinitions() |
| gents | memberNames + Instances + gentDescriptions | 조인 |
| 	eamRuns | TeamRuns | TeamRuns.Select() |
| diagnostics | leetService | 각종 프로퍼티 |
| 	asks | TeamRunState.Tasks | GetCurrentTeamRunStateAsync() → ActiveTaskStatuses 필터 |
| questions | TeamRunState.Questions | GetCurrentTeamRunStateAsync() → status == "open" 필터 |
| 	askSummary | TeamRunState.Tasks | GroupBy(t => t.Status) 집계 |
| questionSummary | TeamRunState.Questions | GroupBy(q => q.Status) 집계 |

---

## 6. 전송 방식

`csharp
// C# → HTML (WebView2)
var json = JsonSerializer.Serialize(await BuildTeamGraphSnapshotAsync(), TeamGraphJsonOptions);
TeamGraphWebView.CoreWebView2.PostWebMessageAsJson(json);
`

`javascript
// HTML 수신 (C# → window.chrome.webview)
window.chrome.webview.addEventListener('message', function(e) {
  const snapshot = e.data;  // 위 JSON 구조와 동일
  render(snapshot);
});
`

---

## 7. 버전 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| v1.0.0 | 2026-06-21 | 초기 데이터 계약: 	eams, gents, 	eamRuns, diagnostics |
| v1.1.0 | 2026-06-24 | 	asks, questions, 	askSummary, questionSummary, 	asksLoadFailed, questionsLoadFailed 추가 |
