---
name: dev-to-pr
description: '작업 하나를 워크트리 1개에서 PR 까지 끌고 가는 단일 스킬. 워크트리 생성 → PLAN.md 작성 → 플랜 승인 → 커밋 루프(개발, code-review, 린트, 커밋 1개) → base 브랜치 merge → 보안 점검 → push 와 PR 과 워크트리 정리. 워크트리는 항상 1개이고 세부 태스크는 순차로 처리하며 세부 태스크 1개가 커밋 1개다. 다른 스킬을 부르지 않고 직접 수행하며, 예외는 PR 직전의 repo-security-review 하나다. 코딩 컨벤션은 다루지 않는다. 승인 게이트는 플랜, 충돌 해결, PR 세 곳이고 무인 실행에서는 자동 승인으로 통과한다. 인자 — issueKey(예 PFP-4761), base(기본 develop). 사용 시점 — "/dev-to-pr", "이 작업 브랜치 파서 커밋 나눠서 PR까지 해줘". 여러 스킬로 나눠 지휘하는 방식을 원하면 workflow-developer 를 쓴다.'
---

# dev-to-pr

작업 하나(보통 이슈 1개)를 워크트리 1개에서 PR 까지 끌고 간다.

- 워크트리는 1개다. 병렬로 나누지 않는다.
- 세부 태스크는 순차로 처리하고, 세부 태스크 1개가 커밋 1개다.
- push 는 마지막 PR 단계에서만 한다.
- 다른 스킬을 부르지 않는다. 예외는 `repo-security-review` 하나다.
- 코딩 컨벤션은 다루지 않는다. 레포에 컨벤션 스킬이나 문서가 있으면 그건 그쪽 몫이다.

## 레포 설정

### platform-service-server

- base 브랜치: `develop`
- 브랜치명: `feature/<이슈키>-<base>` (예: `feature/PFP-4761-develop`)
- 커밋 제목: `[<이슈키>][<service>/<app>] <요약>` (예: `[PFP-4761][gadget-service/presenter] 조회 필터 추가`)

### platform-fe-gadget

- base 브랜치: `develop`
- 브랜치명: `<이슈키>_<base>` (예: `PFP-4761_develop`). 언더바 오른쪽이 base 다. `platform-fe-user` 계열과 같은 규칙이고 `feature/` 접두사를 붙이지 않는다.
- 커밋 제목: `<type> : [<이슈키>] <요약>` (예: `feature : [PFP-4761] 언어 목록 정렬 적용`). type 은 브랜치 속성에 따라 `feature` 또는 `fix` 다.
- `worktrees/` 와 `.skills-result-file/` 을 gitignore 하지 않고, PR 템플릿과 `repo-security-review` 가이드도 없다. Step 1, 2, 6, 7 의 대안 경로를 쓴다.

### 그 외 레포

설정이 없으면 사용자에게 물어 채우고, 이 문서에 항목을 추가한다. base 와 브랜치명과 커밋 제목 형식은 레포마다 다르므로 추론하지 않는다.

## 절차

### Step 0 — 입력

- 이슈 키(예: `PFP-4761`). 없으면 묻고 멈춘다. 커밋 제목과 PR 제목에 쓴다.
- base 브랜치. 위 설정을 쓰고, 설정에 없으면 묻는다.
- 할 일. 커밋 단위로 쪼갤 수 있을 만큼 이해한다. 모호하면 묻는다.

### Step 1 — 워크트리 생성

브랜치명은 위 설정의 형식을 쓴다. 워크트리 경로는 `<repo-root>/worktrees/<브랜치명의 / 를 - 로 치환>`.

```bash
git fetch origin <base>
git worktree add -b <branch> "<repo-root>/worktrees/<sanitized>" "origin/<base>"
```

- `origin/<base>` 에서 분기한다. 로컬 base 를 pull 하지 않으므로 현재 디렉터리가 dirty 해도 무방하다.
- 브랜치명이나 경로가 이미 있으면 지우지 않고 묻는다.
- 메인 레포의 `.env.local` 들을 같은 상대 경로로 복사한다. gitignore 라서 워크트리에 안 따라오고, 없으면 서버가 부팅에서 죽는다.
- `git check-ignore worktrees` 로 확인한다. 무시되지 않는 레포에서 워크트리를 레포 안에 만들면 메인 레포가 dirty 해지므로, 그때는 `<repo-root>/../<repo>-worktrees/<sanitized>` 에 만든다.

### Step 2 — PLAN.md 작성

할 일을 커밋 단위로 쪼개 `<worktree>/.skills-result-file/PLAN.md` 에 쓴다. 항목마다 작업 내용과 완료 조건을 적는다.

`.skills-result-file` 은 gitignore 라서 커밋에 안 섞이고 마지막 `worktree remove` 도 막지 않는다. `git check-ignore` 로 확인하고, 무시되지 않는 레포면 워크트리 밖의 세션 임시 디렉터리에 쓴다. 이 파일을 넣으려고 `.gitignore` 를 고치지 않는다.

### Step 3 — 플랜 승인 (게이트)

PLAN.md 와 브랜치명, 워크트리 경로를 사용자에게 보여주고 승인받는다. 승인 전에 개발을 시작하지 않는다.

- 수정 요청은 PLAN.md 에 반영하고 다시 확인받는다.
- 진행하지 않기로 하면 워크트리를 제거한다.

### Step 4 — 커밋 루프

PLAN.md 의 항목을 위에서부터 하나씩 처리한다. 항목마다 다음 순서를 지킨다.

1. 개발. 그 항목의 완료 조건만 충족한다. 다른 항목이나 무관한 파일을 겸사겸사 고치지 않는다.
2. `code-review` 로 그 변경분을 리뷰하고 반영한다.
3. 린트. 리뷰 반영으로 깨질 수 있으니 리뷰 뒤에 돌린다. 이 항목이 바꾼 파일만 대상으로 하고, 워크트리 전체나 서비스 전체를 돌리지 않는다.
4. 커밋 1개. 위 설정의 제목 형식을 쓴다. 미리보기 승인은 받지 않는다. push 하지 않는다.

린트나 빌드가 `Cannot find module` 로 죽으면 워크트리에 `node_modules` 가 없어서다. 설치하지 말고 메인 레포의 같은 경로를 심볼릭 링크한다.

```bash
MAIN=$(git -C "<worktree>" worktree list --porcelain | head -1 | sed 's/^worktree //')
ln -s "$MAIN/<루트 상대경로>/node_modules" "<worktree>/<루트 상대경로>/node_modules"
```

메인 레포에도 없으면 임의로 설치하지 않고, 그 부분 검증을 건너뛰었다고 알린다.

한 항목의 변경이 명백히 두 가지 이상이면 커밋을 더 쪼갠다. 서로 다른 항목을 한 커밋에 합치지는 않는다.

### Step 5 — base merge

모든 커밋이 끝난 뒤 base 의 최신 변경을 받아온다. rebase 가 아니라 merge 다.

```bash
git -C "<worktree>" fetch origin <base>
git -C "<worktree>" merge origin/<base>
```

- 이미 base 를 포함하면 아무것도 하지 않는다. 빈 머지 커밋을 만들지 않는다.
- 충돌이 나면 해결안을 파일별로 보여주고 승인받은 뒤 머지 커밋한다. 로직 충돌을 임의로 판단하지 않는다.
- 여기서 push 하지 않는다. 보안 점검이 push 앞에 있어야 한다.

### Step 6 — 보안 점검

`repo-security-review` 를 `--diff` 모드로 부른다. base 대비 전체 변경분과 충돌 해결분을 함께 본다.

그 스킬이나 `.github/claude/repo-security-review/` 가이드가 없는 레포에서는 내장 `/security-review` 를 쓴다. 아래 판정 규칙은 그대로 적용한다.

- Critical 또는 Major 가 1건이라도 있으면 PR 을 만들지 않는다. 보완하고 커밋한 뒤 이 단계를 다시 돌린다.
- Minor 와 Nit 만 있으면 보여주고 그대로 갈지 먼저 보완할지 확인한다.
- 오탐을 임의로 넘기지 않는다. `repo-security-review` 가 안내하는 `ignore.yml` 절차를 따른다.

### Step 7 — PR (게이트)

```bash
git -C "<worktree>" push -u origin <branch>
gh pr create --draft --base <base> --head <branch> --title "..." --body-file ...
```

- PR 은 항상 draft 로 만든다. ready 전환은 사람이 한다.
- 제목은 위 설정의 커밋 제목 형식을 따르되 작업 전체를 요약한다. 본문은 `.github/PULL_REQUEST_TEMPLATE.md` 를 채우고, 템플릿이 없는 레포에서는 변경 요약과 검증 방법을 적는다.
- assignee 는 본인, 라벨은 변경된 서비스만 붙인다. 리뷰 상태 라벨은 자동으로 붙이지 않는다.
- 제목, 본문, base, 라벨을 한 번에 보여주고 승인받은 뒤 push 와 PR 생성을 한다.
- `git worktree remove` 로 워크트리를 제거한다. 로컬 브랜치는 남긴다. untracked 파일이 막으면 무엇이 남았는지 보여주고 `--force` 여부를 묻는다.

### Step 8 — 보고

브랜치, 커밋 목록(요약과 짧은 해시), 보안 점검 결과, PR 링크를 한 번에 적는다. 로컬 브랜치 정리 명령을 남은 일로 안내한다.

## 동작 규칙

- 승인 게이트는 플랜, 충돌 해결, PR 세 곳이다. 커밋 메시지 미리보기는 받지 않는다.
- 무인 실행(`task-queue-scheduler` 등)에서는 세 게이트를 자동 승인으로 간주하고 PR 까지 진행한다. 도중에 막히면 그 맥락의 실패 처리에 사유 한 줄을 남긴다.
- 모든 작업은 그 워크트리 경로 안에서 한다. 메인 작업트리와 다른 워크트리를 건드리지 않는다.
- push 는 Step 7 에서만 한다.
- 커밋 1개짜리 작업도 같은 경로를 탄다. 지름길을 만들지 않는다.
- 스펙이 모호하면 추측해서 범위를 넓히지 않고 멈추고 묻는다.
- 같은 문제로 두 번 실패하면 세 번째를 시도하지 않고 후보 방향을 정리해 묻는다.
