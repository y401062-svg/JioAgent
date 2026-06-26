# 컨텍스트 유지 기능 - 사용자 경험(UI/UX) 분석

> **분석자:** choi (UI/UX Designer)
> **날짜:** 2026-06-24
> **관련 태스크:** [분석-4] UI/UX Designer: 사용자 경험 분석
> **대상 시스템:** AgentConsole (C# Console Application)

---

## 1. 현재 UI 패턴 분석

### 1.1 ConsoleUi 클래스 출력 메서드

AgentConsole은 ConsoleUi 클래스를 통해 콘솔 출력을 처리합니다.

| 메서드 | 색상 | 용도 | 사용 예 |
|--------|------|------|---------|
| Header(title, subtitle) | Cyan | 섹션 제목 | 앱 시작 시 "AgentConsole" |
| Section(title) | Cyan | 중간 제목 | "/help" 명령어 목록 |
| Success(message) | Green | 성공 메시지 | "Conversation reset." |
| Warning(message) | Yellow | 경고 메시지 | "Cancellation requested." |
| Error(message) | Red | 오류 메시지 | "Briefing failed: ..." |
| Info(message) | Gray | 정보 메시지 | "AgentConsole ended." |
| KeyValue(key, value) | DarkGray | 키-값 표시 | Memory 상태 |
| Status(label, enabled) | Green/Yellow | 상태 On/Off | Control server |
| Command(cmd, desc) | Green | 명령어 도움말 | "/reset" |
| Prompt(label, color) | Green | 입력 프롬프트 | "You> " |

### 1.2 현재 컨텍스트 관련 흐름

`
[시작]  → PrintStartup() → Header("AgentConsole") + Control 서버 상태
[입력]  → Prompt("You> ") → 사용자 입력
[/reset] → host.ResetConversation() → Success("Conversation reset.")
[/exit]  → Environment.Exit(0) → Info("AgentConsole ended.")
[/memory] → PrintMemory() → KeyValue 목록 출력
`

**문제점:**
- /reset 시 확인 절차 **없음** → 실수로 초기화 위험
- /exit 시 컨텍스트 저장 **없음** → 대화 내용 소실
- 시작 시 컨텍스트 복원 상태 **미표시**
- 저장/복원 실패 시 피드백 **없음**
- /memory에 컨텍스트 파일 정보 **미포함**

---

## 2. 분석 항목별 UI/UX 설계

### 2.1 사용자가 컨텍스트 유지 상태를 인지할 수 있는 UI 표시 방안

#### 방안 A: 프롬프트 라벨 활용 (권장)
프롬프트에 컨텍스트 상태를 시각적으로 표시합니다.

**설계:**
`
# 컨텍스트가 복원된 경우 (초록색)
You>                                    ← 현재와 동일

# 컨텍스트가 없는 경우 (회색)
You [new session]>                      ← "new session" 표시

# 컨텍스트 저장이 활성화된 경우 (청록색)
You [ctx: auto-save]>                   ← 저장 기능 ON 상태
`

**구현 제안:**
`csharp
// GetPromptLabel() 변경
static string GetPromptLabel(ContextStatus context)
{
    var label = briefMode.Mode switch
    {
        BriefMode.Once => "You [brief once]> ",
        BriefMode.Auto => "You [brief auto]> ",
        _ => context.HasRestoredContext
            ? "You> "  // 복원됨 → 기본 색상(녹색) 유지
            : "You [new session]> "
    };
    // 저장 활성화 시 추가 표시
    if (context.IsPersistenceEnabled)
        label = label.Replace("> ", " [ctx]> ");
    return label;
}
`

#### 방안 B: 시작 시 컨텍스트 상태 영역 추가
PrintStartup()에서 컨텍스트 상태를 별도 영역으로 표시합니다.

**설계:**
`
━━━ AgentConsole ━━━━━━━━━━━━━━━━━━━━━━━━━
Type /help for commands. Press Ctrl+C during a response to cancel the active turn.

  Context persistence  : enabled (auto-save)   ← 초록색
  Context source       : loaded from file      ← 노란색 (파일 경로)
  Conversation messages: 12                    ← 회색 (복원된 메시지 수)
  Control server       : enabled
  Control URL          : http://localhost:...
─────────────────────────────────────────────
`

**상태별 메시지:**
| 상황 | 출력 |
|------|------|
| 복원 성공 | ui.Success("✓ Previous conversation context restored (12 messages).") |
| 처음 실행 | ui.Info("○ No previous conversation context found. Starting fresh session.") |
| 복원 실패 | ui.Warning("⚠ Failed to restore previous context. Starting fresh session. See log for details.") |
| 저장 비활성화 | ui.Status("Context persistence", false, "disabled") |

#### 방안 C: /context 명령어에 컨텍스트 상태 통합
현재 /context 명령어는 토큰 사용량만 표시합니다. 여기에 컨텍스트 저장 상태를 추가합니다.

`
━━━ Context ━━━━━━━━━━━━━━━━━━━━
  Conversation messages : 12
  Payload messages      : 8
  Persistence file      : deploy/JioAgent/AgentSettings/choi.conversation.json
  Last saved            : 2026-06-24 19:30:22
  Auto-save             : enabled
─────────────────────────────────
`

---

### 2.2 /reset 명령 시 확인 메시지 설계

#### 현재 문제
`csharp
case "/reset":
    host.ResetConversation();
    ui.Success("Conversation reset.");
    return true;
`
→ 한 줄 메시지 후 즉시 실행, **확인 절차 없음**

#### 설계: 확인 대화상자 (Y/N)

**프롬프트 스타일 (간결형, 권장):**
`
You> /reset

  ⚠ 대화가 초기화됩니다. 저장된 컨텍스트도 함께 삭제됩니다.
  계속하시겠습니까? [y/N]:
`
- y 또는 Y 입력 시에만 실행
- 그 외 입력(Enter 포함) 시 취소
- N 입력 시: ui.Info("Reset canceled.")

**PowerShell 승인 스타일 (고급형):**
`
  ┌─────────────────────────────────────────────┐
  │  [O] Reset conversation and saved context   │
  │  [ ] Cancel                                 │
  │  Use Up/Down or Space to choose, Enter.     │
  └─────────────────────────────────────────────┘
`
→ ConsoleUi의 승인 선택 UI 패턴(ReadApprovalSelection) 재사용

**구현 제안:**
`csharp
case "/reset":
    ui.Warning("⚠ 대화가 초기화됩니다. 저장된 컨텍스트도 함께 삭제됩니다.");
    ui.Info("계속하시겠습니까? [y/N]: ");
    var key = Console.ReadKey(intercept: true);
    Console.WriteLine();
    if (key.Key == ConsoleKey.Y)
    {
        host.ResetConversation();
        // 저장된 컨텍스트 파일도 삭제
        TryDeleteContextFile(host);
        ui.Success("✓ Conversation and saved context have been reset.");
    }
    else
    {
        ui.Info("Reset canceled.");
    }
    return true;
`

**UX 고려사항:**
- ⚠ 이모지/아이콘으로 파괴적 작업임을 직관적 전달
- [y/N] 표기로 **기본값이 No**임을 명시 (실수 방지)
- 확인 후 성공 메시지에 "saved context"도 함께 삭제되었음을 명시
- 취소 시 "Reset canceled." 메시지로 명확한 피드백

---

### 2.3 시작 시 컨텍스트 복원 상태 표시 설계

#### PrintStartup() 확장

**현재:**
`csharp
static void PrintStartup(ConsoleUi ui, AgentControlServer? controlServer)
{
    ui.Header("AgentConsole", "Type /help for commands. ...");
    if (controlServer is null) { ui.Status(...); return; }
    ui.Status("Control server", enabled: true);
    ui.KeyValue("Control URL", ...);
}
`

**설계 (확장 후):**
`csharp
static async Task PrintStartupAsync(
    ConsoleUi ui,
    AgentControlServer? controlServer,
    AgentHost host)
{
    ui.Header("AgentConsole",
        "Type /help for commands. Press Ctrl+C during a response to cancel the active turn.");

    // 1) 컨텍스트 복원 상태 표시
    var restoreResult = await TryRestoreContextAsync(host);
    switch (restoreResult.Status)
    {
        case ContextRestoreStatus.Restored:
            ui.Success($"✓ Previous conversation context restored ({restoreResult.MessageCount} messages, {restoreResult.AgentName}).");
            break;
        case ContextRestoreStatus.NotFound:
            ui.Info("○ No previous conversation context found. Starting fresh session.");
            break;
        case ContextRestoreStatus.Failed:
            ui.Warning($"⚠ Failed to restore previous context: {restoreResult.ErrorMessage}");
            ui.Info("  Starting fresh session. See diagnostics log for details.");
            break;
    }

    // 2) 저장 설정 상태 표시
    ui.Status("Context persistence", enabled: host.Options.EnableContextPersistence);

    // 3) Control 서버 상태 (기존)
    if (controlServer is null)
    {
        ui.Status("Control server", enabled: false, disabledText: "disabled (--no-control-server)");
        return;
    }
    ui.Status("Control server", enabled: true);
    ui.KeyValue("Control URL",
        $"{controlServer.ControlUrl} (localhost-only development control server)");
}
`

**상태 표시 규칙:**
| 조건 | 표시 방식 | 색상 | 예시 메시지 |
|------|-----------|------|-------------|
| 복원 성공 | Success | 초록 | ✓ Previous conversation context restored (12 messages, choi). |
| 처음 실행 | Info | 회색 | ○ No previous conversation context found. |
| 복원 실패 | Warning + Info | 노랑+회색 | ⚠ Failed to restore previous context... Starting fresh session. |
| 저장 비활성화 | Status | 노랑 | Context persistence : disabled |

---

### 2.4 저장/복원 실패 시 사용자 피드백 설계

#### 저장 실패 시나리오

**파일 쓰기 실패 (디스크 부족, 권한 없음, 파일 Lock):**
`
  ⚠ Failed to save conversation context.
    Path: deploy/JioAgent/AgentSettings/choi.conversation.json
    Error: Access to the path is denied.
    → The current conversation will continue in memory only.
    → Use /memory to check status and /save to retry.
`
- Warning 레벨 (앱 중단 아님)
- 파일 경로를 포함하여 사용자가 직접 문제 해결 가능
- "메모리에서만 계속" → 안전한 폴백(fallback) 안내
- 재시도 방법 제시 (/save 명령어)

**프로그램 종료 중 저장 실패:**
`
  ⚠ Conversation context could not be saved before exit.
    Error: {exception.Message}
    → This conversation will be lost on restart.
`
- Warning 레벨
- 결과의 명확한 전달 ("재시작 시 대화 내용 손실")

#### 복원 실패 시나리오

**파일 읽기 실패 (파일 손상, JSON 파싱 오류):**
`
  ⚠ Failed to restore previous conversation context.
    Path: deploy/JioAgent/AgentSettings/choi.conversation.json
    Error: JSON deserialization failed: 'Unexpected character...'
    → Starting a fresh session.
    → The corrupted file has been backed up to: deploy/JioAgent/AgentSettings/choi.conversation.json.bak
`
- Warning 레벨
- 파일 경로 + 구체적 오류 메시지
- **자동 백업** 생성 안내 (파일 덮어쓰기 방지)
- 새 세션 시작 안내

**파일 버전 불일치 (이전 버전 포맷):**
`
  ⚠ Saved context format is incompatible with the current version.
    File version: 1.0, Expected: 2.0
    → Starting a fresh session.
    → The old file has been preserved at: ...json.old
`
- Warning 레벨
- 버전 정보를 포함한 명확한 메시지
- 구버전 파일 보존 안내

#### 저장 재시도 UI

/save 명령어 추가 (또는 /memory save):
`
  ━━━ Memory save ━━━━━━━━━━━━━━━━━
  ✓ Conversation context saved successfully.
    File: deploy/JioAgent/AgentSettings/choi.conversation.json
    Messages: 12 | Last saved: 2026-06-24 19:35:22
  ─────────────────────────────────
`

`
  ━━━ Memory save ━━━━━━━━━━━━━━━━━
  ⚠ Save skipped: context persistence is disabled.
    Enable with --persist flag on startup.
  ─────────────────────────────────
`

---

### 2.5 /memory 명령어와의 연동 표시 설계

#### 현재 /memory 출력
`
━━━ Memory status ━━━━━━━━━━━━━━━
  conversation messages     : 12
  payload messages          : 8
  tools                     : 3
  rough estimated tokens    : 4520
  enabled                   : True
  required                  : False
  reason                    : estimated tokens 4520 >= trigger 4096
  ...
─────────────────────────────────
`

#### 설계: Context Persistence 정보 통합

`
━━━ Memory & Context ━━━━━━━━━━━━━━━━━━━
  ◈ Conversation
    messages                : 12
  ◈ Context Persistence
    auto-save               : enabled
    context file            : deploy/JioAgent/AgentSettings/choi.conversation.json
    last saved              : 2026-06-24 19:35:22 (2 min ago)
    last restored           : 2026-06-24 19:30:00 (7 min ago)
  ◈ Memory Compaction
    enabled                 : True
    required                : False
    compactable messages    : 5
    ...
─────────────────────────────────────────
`

**UX 개선 포인트:**
1. **Section 분리**: "Memory & Context"로 통합 섹션
2. **아이콘 활용**: ◈, ◇ 등으로 시각적 구분
3. **시간 표시**: "2 min ago" 같은 상대적 시간 (가독성 향상)
4. **파일 경로**: Config의 KeyValue 패턴 재사용 (노란색 파일 경로)
5. **바로가기 안내**: 푸터에 명령어 힌트 추가

**명령어 힌트 (푸터):**
`
─────────────────────────────────────────
  💡 Tip: /memory compact → Force memory compaction
         /memory save     → Save context now
         /reset           → Reset all (with confirmation)
`

#### /memory save 하위 명령어

| 명령어 | 설명 |
|--------|------|
| /memory | 현재 상태 표시 (컨텍스트 + 메모리) |
| /memory compact | 메모리 컴팩션 강제 실행 |
| /memory save | 컨텍스트 즉시 저장 |
| /memory status | 컨텍스트 파일 존재 여부 등 상세 상태 |

---

## 3. 통합 UX 설계 요약

### 3.1 사용자 시나리오별 흐름

#### 시나리오 A: 처음 실행 (컨텍스트 없음)
`
━━━ AgentConsole ━━━━━━━━━━━━━━━━━━━━━━━━━
Type /help for commands. ...

  ○ No previous conversation context found. Starting fresh session.
  Context persistence  : enabled
  Control server       : enabled
  Control URL          : http://localhost:...
─────────────────────────────────────────────

You [new session]>
`

#### 시나리오 B: 재실행 (컨텍스트 복원 성공)
`
━━━ AgentConsole ━━━━━━━━━━━━━━━━━━━━━━━━━
Type /help for commands. ...

  ✓ Previous conversation context restored (12 messages, choi).
  Context persistence  : enabled
  Control server       : enabled
  Control URL          : http://localhost:...
─────────────────────────────────────────────

You>
`

#### 시나리오 C: /reset 실행
`
You> /reset

  ⚠ 대화가 초기화됩니다. 저장된 컨텍스트도 함께 삭제됩니다.
  계속하시겠습니까? [y/N]: y

  ✓ Conversation and saved context have been reset.

You [new session]>
`

#### 시나리오 D: 종료 시 저장 실패
`
You> /exit

  ⚠ Conversation context could not be saved before exit.
    Error: Disk full.
    → This conversation will be lost on restart.

  AgentConsole ended.
`

#### 시나리오 E: 저장된 컨텍스트 파일 보기
`
You> /memory

━━━ Memory & Context ━━━━━━━━━━━━━━━━━━━
  ◈ Conversation
    messages                : 12
  ◈ Context Persistence
    auto-save               : enabled
    context file            : deploy/JioAgent/AgentSettings/choi.conversation.json
    last saved              : 2026-06-24 19:35:22 (2 min ago)
    last restored           : 2026-06-24 19:30:00
  ◈ Memory Compaction
    enabled                 : True
    ...
─────────────────────────────────────────
  💡 Tip: /memory save → Save context now
`

---

### 3.2 ConsoleUi 확장 메서드 제안

새로운 출력 패턴을 위해 ConsoleUi에 다음 메서드를 추가합니다:

| 메서드 | 설명 |
|--------|------|
| ContextStatus(status, detail) | 컨텍스트 상태 표시 (복원/없음/실패) |
| ConfirmAction(warning, prompt) | Y/N 확인 프롬프트 |
| Timestamped(key, value) | 시간 정보 포함 KeyValue |
| Tip(message) | 💡 팁 표시 |
| SectionWithIcon(icon, title) | 아이콘 포함 섹션 제목 |

### 3.3 새로운/변경되는 명령어 목록

| 명령어 | 변경 사항 |
|--------|-----------|
| /reset | 확인 메시지 추가, 컨텍스트 파일도 삭제 |
| /memory | Context Persistence 섹션 통합 표시 |
| /memory save | (신규) 컨텍스트 즉시 저장 |
| /context | (선택) 컨텍스트 파일 정보 포함 |
| /help | /memory save 설명 추가 |

---

## 4. 우선순위 및 구현 제안

| 우선순위 | 항목 | 영향 | 난이도 |
|----------|------|------|--------|
| **P0 (핵심)** | /reset 확인 메시지 | 데이터 손실 방지 | 낮음 |
| **P0 (핵심)** | 시작 시 복원 상태 표시 | 사용자 인지 필수 | 낮음 |
| **P0 (핵심)** | 저장/복원 실패 피드백 | 오류 인지 필수 | 낮음 |
| **P1 (중요)** | /memory에 컨텍스트 정보 통합 | 정보 접근성 | 낮음 |
| **P2 (개선)** | 프롬프트 상태 라벨 ([new session]) | 시각적 인지 향상 | 중간 |
| **P2 (개선)** | /memory save 명령어 | 사용자 제어권 | 중간 |
| **P3 (선택)** | 프롬프트 색상 변화 | 고급 UX | 낮음 |

---

## 5. 참조: 기존 UI 패턴

본 설계는 다음 기존 패턴을 재사용합니다:

1. **ConsoleUi 클래스**의 색상 체계 (Cyan/Green/Yellow/Red/Gray)
2. **Prompt + ReadMessage** 패턴 (사용자 입력 처리)
3. **KeyValue + Status** 패턴 (설정/상태 표시)
4. **PowerShell 승인 UI**의 커서 기반 선택 패턴 (선택적 적용)
5. **Markdown 렌더링**을 통한 Assistant 응답 표시
