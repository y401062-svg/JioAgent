# JioAgent

JioAgent는 여러 AI 에이전트를 한 PC에서 실행하고, 팀 단위 작업을 관리하기 위한 .NET 8 기반 에이전트 런타임입니다. 단일 콘솔 채팅, 로컬 API 프록시, 에이전트 관리 GUI, 팀 작업 상태 저장소, Skill 및 MCP 서버 확장을 한 배포 폴더 안에서 함께 다룹니다.

## 데모 영상

![JioAgent demo](assets/jioagent-demo.gif)

## 주요 기능

- `AgentConsole.exe`: 개별 에이전트와 대화하는 콘솔 앱입니다.
- `AgentFleetManager.exe`: 여러 에이전트와 팀을 시작/중지/관리하는 GUI 앱입니다.
- `ApiProxy.exe`: LLM API 호출을 중계하는 로컬 프록시입니다.
- TeamRuntime: 팀 작업, 질문, 보고, 작업 상태를 파일 기반으로 관리합니다.
- Team Monitor: 팀 런타임 그래프와 에이전트별 채팅 상태를 확인합니다.
- Skill 시스템: `Skills/` 아래의 `SKILL.md` 기반 기능 확장을 로딩합니다.
- MCP 서버 연동: `McpServers/` 아래의 외부 도구 서버를 로딩해 브라우저 자동화, 파일시스템 작업 같은 도구를 연결합니다.
- 메모리 압축: 긴 대화가 누적될 때 최근 맥락과 요약 메모리를 함께 유지합니다.

## 포함된 실행 파일

| 파일 | 역할 |
| --- | --- |
| `AgentConsole.exe` | 개별 에이전트 콘솔 런타임 |
| `AgentFleetManager.exe` | 에이전트/팀 관리 GUI |
| `ApiProxy/ApiProxy.exe` | 로컬 LLM API 프록시 |
| `AgentRuntime.dll` | 에이전트 실행 공통 런타임 |
| `TeamRuntime.dll` | 팀 작업 상태와 협업 흐름 |
| `BuiltInMcpServer.dll` | 내장 도구 서버 |
| `McpClient.dll` | 외부 MCP 서버 클라이언트 |

## 요구 사항

- Windows
- .NET 8 Desktop Runtime 또는 .NET 8 SDK
- LLM API 키
- Python 3.11 이상: Python 기반 MCP 서버를 사용할 때 필요
- Playwright 브라우저 설치: Playwright MCP를 사용할 때 필요

.NET 8 Desktop Runtime 설치 예:

```powershell
winget install Microsoft.DotNet.DesktopRuntime.8
```

SDK까지 필요한 경우:

```powershell
winget install Microsoft.DotNet.SDK.8
```

설치 확인:

```powershell
dotnet --list-runtimes
```

## 빠른 실행

저장소를 받은 뒤 배포 폴더에서 실행합니다.

```powershell
cd JioAgent
.\AgentFleetManager.exe
```

콘솔 에이전트를 직접 실행할 수도 있습니다.

```powershell
cd JioAgent
.\AgentConsole.exe
```

특정 런타임 설정 파일을 지정하려면:

```powershell
.\AgentConsole.exe --runtime-config .\config\agent.runtime.json
```

GUI 없이 시작 가능 여부만 확인하려면:

```powershell
.\AgentFleetManager.exe --startup-smoke
```

## API 키와 모델 설정

LLM 연결 설정은 `ApiProxy/appsettings.json`에서 관리합니다.

```json
{
  "ApiProxy": {
    "BaseUrl": "https://api.deepseek.com",
    "ApiKey": "",
    "ApiKeyEnvironmentVariable": "",
    "DefaultModel": "deepseek-v4-flash"
  },
  "Urls": "http://localhost:5058"
}
```

사용 방식은 둘 중 하나를 선택하면 됩니다.

1. `ApiKey`에 직접 키를 넣기
2. `ApiKeyEnvironmentVariable`에 환경변수 이름을 넣고 PowerShell에서 키 설정하기

환경변수 방식 예:

```powershell
$env:DEEPSEEK_API_KEY = "your-api-key"
```

그리고 `ApiProxy/appsettings.json`:

```json
"ApiKeyEnvironmentVariable": "DEEPSEEK_API_KEY"
```

공개 저장소에 실제 API 키를 커밋하지 마세요.

## 기본 포트

기본 포트는 `config/agent.endpoints.json`에서 관리합니다.

```json
{
  "proxyUrl": "http://localhost:5058",
  "controlUrl": "http://localhost:5068",
  "fleet": {
    "firstControlPort": 5068,
    "instanceCount": 20
  }
}
```

- `proxyUrl`: AgentConsole이 호출하는 로컬 ApiProxy 주소
- `controlUrl`: 첫 번째 AgentConsole 제어 서버 주소
- `fleet.firstControlPort`: Fleet Manager가 관리하는 에이전트 포트 시작 번호
- `fleet.instanceCount`: Fleet Manager가 관리할 수 있는 에이전트 수

## 주요 폴더 구조

```text
JioAgent/
  AgentConsole.exe
  AgentFleetManager.exe
  ApiProxy/
    ApiProxy.exe
    appsettings.json
  AgentSettings/
    *.agentconsole.args.json
  TeamSettings/
    *.team.json
  config/
    agent.endpoints.json
    agent.runtime.json
    team-worker-agents.json
  Skills/
    agent/
      external-mcp-server-setup/
      skill-creator/
  McpServers/
    playwright_mcp/
    python_filesystem_mcp/
  Web/
    team-runtime-graph.html
    vis-network.min.js
  assets/
    jioagent-demo.gif
```

## 에이전트와 팀

이 배포본에는 여러 역할별 에이전트 설정이 포함되어 있습니다.

- `CodingTeamLeader`: 작업 분배와 팀 진행 관리
- `jio`, `kiyoon`: 코드 작성 담당
- `hanroro`, `hipi`: 코드 리뷰 담당
- `hyori`: 요구사항 분석 담당
- `jaeseok`: 아키텍처 담당
- `baeksoo`: 테스트 담당
- `rain`: 문서화 담당
- 기타 업무팀 예제 에이전트: 인사팀, 생산팀, 총괄장 등

에이전트별 실행 인자는 `AgentSettings/*.agentconsole.args.json`에 저장됩니다. 팀 구성은 `TeamSettings/*.team.json`과 `config/team-worker-agents.json`에서 확인할 수 있습니다.

## Team Monitor

Fleet Manager의 Team Monitor 화면은 팀 실행 상태를 그래프로 보여줍니다.

- 팀/에이전트 관계 시각화
- 팀 런 수, 에이전트 수, 팀 수 확인
- 에이전트별 채팅 패널 열기
- 팀 작업 보고와 질문 흐름 확인
- 실행 중/대기/이슈 상태 구분

그래프 UI 리소스는 `Web/team-runtime-graph.html`과 `Web/vis-network.min.js`에 포함되어 있습니다.

## MCP 서버

`McpServers/` 아래에 MCP 서버를 배치하면 AgentConsole이 외부 도구로 사용할 수 있습니다.

현재 포함된 서버:

- `playwright_mcp`: Python Playwright 기반 브라우저 자동화 MCP 서버
- `python_filesystem_mcp`: 허용된 루트 안에서 파일 작업을 수행하는 Python MCP 서버

각 서버 폴더의 `README.md`와 `mcp-server.json`을 참고해 Python 의존성, 실행 명령, 허용 경로를 조정하세요.

예: Playwright MCP 준비

```powershell
python -m pip install mcp playwright pydantic
python -m playwright install chromium
```

예: Filesystem MCP 준비

```powershell
cd .\McpServers\python_filesystem_mcp
python -m pip install .
```

## Skill 확장

Skill은 `Skills/` 아래에 폴더 단위로 배치됩니다. 각 Skill은 `SKILL.md`를 진입점으로 사용합니다.

현재 포함된 Skill:

- `agent/external-mcp-server-setup`
- `agent/skill-creator`

새 Skill을 추가할 때는 다음 형태를 권장합니다.

```text
Skills/
  category/
    my-skill/
      SKILL.md
      scripts/
      references/
```

## 런타임 설정

`config/agent.runtime.json`은 에이전트 런타임 동작을 설정합니다.

주요 항목:

- `apiProxyExecutablePath`: ApiProxy 실행 파일 경로
- `skillsRoot`: Skill 루트
- `mcpServersRoot`: MCP 서버 루트
- `requestTimeoutSeconds`: 요청 제한 시간
- `maxToolRounds`: 도구 호출 라운드 제한값
- `toolRoundLimitEnabled`: 도구 라운드 제한 사용 여부
- `memoryCompaction`: 긴 대화 메모리 압축 설정

## 공개 저장소에서 제외된 데이터

이 저장소는 실행 이력과 개인 대화 내용을 공개하지 않도록 아래 항목을 제외합니다.

```gitignore
logs/
TeamRuntimeStore/
AgentSettings/*.conversation.json
*.log
__pycache__/
*.pyc
```

특히 `TeamRuntimeStore/`, `logs/`, `*.conversation.json`에는 작업 내용, 대화 이력, 내부 보고서, 실험 데이터가 들어갈 수 있으므로 공개 저장소에 올리지 않는 것을 권장합니다.

## 문제 해결

### .NET 런타임 오류가 나는 경우

```powershell
dotnet --list-runtimes
```

`Microsoft.WindowsDesktop.App 8.x`가 없으면 .NET 8 Desktop Runtime을 설치하세요.

### API 호출이 실패하는 경우

1. `ApiProxy/appsettings.json`의 `BaseUrl`, `DefaultModel`, API 키 설정을 확인합니다.
2. `ApiProxy` 포트가 `config/agent.endpoints.json`의 `proxyUrl`과 맞는지 확인합니다.
3. `http://localhost:5058/health`가 응답하는지 확인합니다.

### Fleet Manager가 에이전트를 못 찾는 경우

1. `AgentSettings/*.agentconsole.args.json` 파일이 있는지 확인합니다.
2. `config/team-worker-agents.json`을 확인합니다.
3. 실행 폴더가 `JioAgent` 배포 루트인지 확인합니다.

### MCP 도구가 안 보이는 경우

1. `McpServers/<server-id>/mcp-server.json`이 있는지 확인합니다.
2. manifest의 `command`, `args`, `workingDirectory`가 현재 PC에 맞는지 확인합니다.
3. Python/Playwright 같은 외부 런타임 의존성이 설치되어 있는지 확인합니다.

## 개발/배포 참고

원본 개발 트리에서는 다음 스크립트로 배포 폴더를 다시 만들 수 있습니다.

```powershell
D:\src\jio_agent\jio_agent\deploy\publish-deploy.ps1
```

실행 중인 `AgentConsole.exe`, `AgentFleetManager.exe`, `ApiProxy.exe`가 배포 파일을 잠글 수 있으므로, 재배포 전에는 관련 프로세스를 종료하는 것이 좋습니다.
