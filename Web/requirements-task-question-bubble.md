# Task/Question 말풍선 요구사항 정의서

## 1. 개요

**목적**: Team Runtime Graph(vis-network)에서 각 에이전트 노드 주변에 Task/Question 정보를 말풍선(bubble)으로 표시하여 현재 워크플로우 상태를 시각화한다.

**관련 Task**:
- task-20260624155840275: hyori (요구분석) - 본 문서
- task-20260624155846128: jaeseok (아키텍처) - 데이터 설계 및 스냅샷 확장
- task-20260624155852541: choi (UI/UX) - 말풍선 디자인 시스템

---

## 2. 현재 그래프의 누락 정보 분석

### 2.1 BuildTeamGraphSnapshot() 현재 출력 데이터
| 항목 | 포함 여부 | 비고 |
|------|----------|------|
| teams (팀 정보) | O | teamId, name, description, leaderAgentId, status, currentRunId, memberAgentIds |
| agents (에이전트 정보) | O | agentName, status, isRunning, description, teamCount |
| teamRuns (런 정보) | O | id, title, mode, status |
| diagnostics | O | 디렉토리/파일/카운트 정보 |
| Tasks (작업) | X 누락 | TeamRunState.Tasks에 존재하나 스냅샷 미포함 |
| Questions (질문) | X 누락 | TeamRunState.Questions에 존재하나 스냅샷 미포함 |
| Notifications | X 누락 | TeamRunState.Notifications에 존재하나 스냅샷 미포함 |
| Events | X 누락 | TeamRunState.Events에 존재하나 스냅샷 미포함 |

### 2.2 접근 가능한 데이터 소스
- fleetService.TryLoadTeamRunStateAsync(teamRunId) -> TeamRunState 반환
- TeamRunState 구조: Run + Tasks[] + Entries[] + Questions[] + Notifications[] + Events[]

---

## 3. 데이터 범위 정의

### 3.1 말풍선에 표시할 Task 정보 (우선순위: 상)

**TeamTask 모델 주요 필드**:
- Id, TeamRunId (필수)
- Title (필수) - 말풍선에 표시
- Status (draft/runnable/assigned/running/blocked/completed/failed/canceled/interrupted)
- AssignedAgentId (담당 에이전트)
- RequesterAgentId (요청 에이전트)
- DependsOnTaskIds (의존 Task 목록)
- BlockedByQuestionIds (차단 Question 목록)
- UpdatedAt (업데이트 시간)

**말풍선 표시 필드 우선순위**:
1순위: Task 제목(Title), 상태(Status) - 필수
2순위: 담당 에이전트(AssignedAgentId), 요청 에이전트(RequesterAgentId)
3순위: 의존 관계(DependsOnTaskIds), 차단 Question(BlockedByQuestionIds) - 상세 모드

### 3.2 말풍선에 표시할 Question 정보 (우선순위: 중)

**TeamQuestion 모델 주요 필드**:
- Id, TeamRunId (필수)
- FromAgentId (발신 에이전트)
- TargetAgentId (수신 에이전트)
- Question (질문 내용)
- Answer (답변)
- Status (open/answered/canceled/failed/interrupted)
- Blocking (차단 여부)
- RelatedTaskId (관련 Task)
- CreatedAt, AnsweredAt

**말풍선 표시 필드 우선순위**:
1순위: 질문 내용(Question), 상태(Status) - 필수
2순위: 발신 에이전트(FromAgentId), 수신 에이전트(TargetAgentId), 차단 여부(Blocking)
3순위: 답변(Answer), 관련 Task(RelatedTaskId) - 상세 모드

---

## 4. 말풍선 표시 조건 및 규칙

### 4.1 표시 조건
- Running Task (status=running): 항상 표시 (말풍선 상단)
- Runnable/Assigned Task: 항상 표시 (말풍선 중간)
- Blocked Task: 항상 표시 + 차단 아이콘
- Completed Task: 표시 안함 (히스토리는 상세 dialog)
- Open Question (status=open): 항상 표시 (말풍선 하단)
- Blocking Question (blocking=true): 강조 표시
- Answered Question: 표시 안함 (히스토리는 상세 dialog)

### 4.2 최대 길이 제한
- Task 제목: 최대 50자 (초과 시 ...)
- Question 내용: 최대 80자 (초과 시 ...)
- 에이전트당 최대 Task 말풍선: 3개 (최신 UpdatedAt 순)
- 에이전트당 최대 Question 말풍선: 2개 (최신 UpdatedAt 순)

### 4.3 상태별 색상 매핑

**Task Status**:
| 상태 | 색상 | 의미 |
|------|------|------|
| draft | #e5e7eb (회색) | 생성만 됨 |
| runnable | #bfdbfe (하늘색) | 실행 가능 |
| assigned | #93c5fd (파란색) | 할당됨 |
| running | #3b82f6 (진한 파랑) + 펄스 | 실행 중 |
| blocked | #fef3c7 (노란색) | 차단됨 |
| completed | #bbf7d0 (초록색) | 완료 |
| failed | #fecaca (빨간색) | 실패 |
| canceled | #e5e7eb (회색) | 취소됨 |
| interrupted | #fed7aa (주황색) | 중단됨 |

**Question Status**:
| 상태 | 색상 | 의미 |
|------|------|------|
| open | #fef3c7 (노란색) | 대기 중 |
| answered | #bbf7d0 (초록색) | 답변 완료 |
| canceled | #e5e7eb (회색) | 취소됨 |
| failed | #fecaca (빨간색) | 실패 |
| interrupted | #fed7aa (주황색) | 중단됨 |

### 4.4 말풍선 유형 및 위치
- Task 말풍선: 에이전트 노드 상단
- Question 말풍선: 에이전트 노드 하단
- 혼합 말풍선: 상/하단 분할 표시

### 4.5 애니메이션 규칙
- 신규 Task 도착: fade-in (300ms)
- Task 상태 변경: 배경색 transition (200ms)
- 신규 Question 도착: bounce (400ms)
- Running Task 지속: 펄스 효과 (기존 runningAgentNodeIds와 통합)
- Question answered: fade-out 후 제거 (500ms)

---

## 5. BuildTeamGraphSnapshot() 확장 제안

### 5.1 스냅샷에 추가할 데이터 구조 (안)

```json
{
  // 기존 필드 유지

  "agentTasks": {
    "agentName1": [
      {
        "taskId": "task-xxx",
        "title": "Task 제목",
        "status": "running",
        "requesterAgentId": "CodingTeamLeader",
        "updatedAt": "2026-06-24T15:00:00Z"
      }
    ]
  },
  "agentQuestions": {
    "agentName1": [
      {
        "questionId": "question-xxx",
        "question": "질문 내용",
        "fromAgentId": "CodingTeamLeader",
        "targetAgentId": "hyori",
        "status": "open",
        "blocking": true,
        "relatedTaskId": "task-yyy",
        "createdAt": "2026-06-24T14:00:00Z"
      }
    ]
  }
}
```

### 5.2 데이터 로드 전략
- 각 TeamRun별 TryLoadTeamRunStateAsync() 호출
- state.Tasks를 AssignedAgentId 기준 그룹핑
- state.Questions를 TargetAgentId 기준 그룹핑
- CurrentRunId에 해당하는 Run만 대상으로 함

---

## 6. 의존성 및 우선순위

### 6.1 Task 의존 관계
[hyori] 요구분석 (본 문서)
  -> [jaeseok] 데이터 설계 및 스냅샷 확장 방안
    -> (Task/Question 데이터를 스냅샷에 추가하는 C# 코드 수정)
  -> [choi] 말풍선 디자인 시스템 (HTML/CSS 디자인)
    -> (병렬 진행 가능)
      -> [jio/kiyoon] 구현 (C# 스냅샷 + HTML 렌더링)
        -> [hanroro/hipi] 코드 리뷰
          -> [rain] 문서화

### 6.2 우선순위
- P0 (필수): 말풍선 기본 구조 - Task 제목/상태 표시
- P1 (중요): Question 정보 표시, Blocking 표시
- P2 (개선): 애니메이션, 상세 모드, 히스토리 dialog

---

## 7. 요약

| 항목 | 내용 |
|------|------|
| 목표 | 그래프 에이전트 노드에 Task/Question 말풍선 표시 |
| 핵심 데이터 | TeamRunState.Tasks, TeamRunState.Questions |
| 우선 표시 | Running/Blocked Task, Open/Blocking Question |
| 최대 길이 | Task 50자, Question 80자 |
| 말풍선 수 | Task 최대 3개, Question 최대 2개 (에이전트당) |
| 애니메이션 | fade-in/out, 상태 변경 transition, 펄스 |
| 구현 순서 | 데이터 수집(C#) -> HTML 렌더링(JS) -> 디자인(CSS) |
