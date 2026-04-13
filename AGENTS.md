# AGENTS.md

이 파일은 이 repository 전용 Codex 운영 규칙이다.
이 repo는 pytoritas workspace factory 표준에서 생성되었으며, Home 전역 규칙보다 **이 repo 안의 규칙**이 더 우선한다.

## 0) 핵심 원칙

- 사용자는 **로컬에서 코딩하고**, GitHub에는 `commit / push / issue / PR / merge`로 기록을 남긴다.
- 비사소한 작업은 기본적으로 **Issue → Branch → Commit → PR → Merge → Validation** 흐름으로 다룬다.
- 작업 추적의 single source of truth는 GitHub Issue다.
- 사용자가 명시적으로 달리 요청하지 않으면, 구조를 뒤집는 리팩토링보다 **지금의 표준 구조 안에서 확장**하는 쪽을 우선한다.

## 1) 이 repo에서 먼저 확인할 것

작업 전 가능하면 아래 순서로 확인한다.

1. `README.md`
2. `docs/variable_glossary.md`
3. `docs/legacy_name_mapping.md` (있다면)
4. `pyproject.toml`
5. `.gitignore`
6. `scripts/`

## 2) Python 환경 표준

이 repo는 **pyenv(+ Windows면 pyenv-win) + Poetry**를 기본으로 사용한다.

### 기본 버전

- Python 버전: `3.12.3`
- Python 제약: `>=3.12,<3.13`

### 기본 부트스트랩 / 재부트스트랩 순서

1. `pyenv local 3.12.3`
2. `poetry config virtualenvs.in-project true --local`
3. `poetry install`

### 품질 게이트 기본값

- `poetry run pytest`
- `poetry run ruff check .`

가능하면 추가로 아래를 유지한다.

- `tools/naming_audit.py` 또는 동등한 naming 검증
- baseline regression test 1개
- representative smoke test 1개

## 3) repository 구조 계약

이 repo는 가능하면 아래 구조를 유지한다.

- `src/<package_name>/`: 핵심 코드
- `tests/`: 검증
- `docs/`: 설계/변수사전/결정 기록
- `scripts/`: 반복 실행 스크립트
- `configs/`: 실험 설정
- `data/`: 입력 데이터 설명 또는 샘플
- `artifacts/` 또는 `out/`: 생성물 (Git 추적 제외)

### Graph rendering contract

- 이 repo에서 **재사용 가능하거나 검증 산출물로 남는 그래프**는 기본적으로 `$plotkit-publication-graphs` 방식의 **spec-first Plotkit workflow**를 사용한다.
- 새 그래프 spec은 우선 `configs/plotkit/` 아래에 둔다. TOMICS tomato-facing figure는 `configs/plotkit/tomics/`를 기본 위치로 본다.
- 기본 theme는 `phytoritas_legacy_muted_botanical`로 두고, 별도 지시가 있을 때만 다른 theme를 선택한다.
- figure output은 `png` raster를 기준으로 하고, 아래 bundle을 함께 남긴다.
  - spec copy
  - resolved spec
  - tokens copy
  - metadata
  - 필요하면 derived/data CSV
- 이 repo의 기본 graph bundle은 **PDF를 생성하지 않는다**. 별도 지시가 없는 한 vector export를 추가하지 않는다.
- ad-hoc `matplotlib` 코드로 스크립트 안에서 바로 `savefig`하는 방식은 새 작업의 기본값으로 쓰지 않는다. 예외가 필요하면 최소한 thin-wrapper renderer 뒤에서 spec/tokens 계약을 먼저 고정한다.

### README 계약

`README.md` 첫 화면은 아래 순서를 유지한다.

1. Purpose
2. Inputs
3. Outputs
4. How to run
5. Current status
6. Next validation

## 4) 식물 모델링 변수명 표준

식물 모델링 관련 개념은 **동일 개념 = 동일 변수명**을 유지한다.

### 4.1. 레이어 규칙

- **수식/코어 모델 레이어**: short name 사용
- **파이프라인/입출력/UI 레이어**: full descriptive name 사용
- 변환은 경계에서 1회만 한다.

### 4.2. 코어 short name 고정 목록

#### Environment / time

- `t`, `dt`, `t_a`, `t_l`, `rh`, `vpd`, `r_abs`, `r_incom`

#### Photosynthesis / gas exchange

- `a_n`, `e`, `g_w`, `g_c`, `g_b`, `c_i`, `c_a`, `gamma_star`, `v_cmax`, `j_max`, `k_c`, `k_o`, `r_d`

#### Hydraulics / water potential

- `psi_l`, `psi_s`, `psi_rc`, `psi_rc0`, `psi_soil`, `psi_soil_by_layer`
- `k_l`, `k_sw`, `k_r`, `k_soil`

#### Carbon / growth

- `c_nsc`, `c_struct`, `la`, `h`, `w`, `d`, `g`, `g0`, `r_m`, `r_g`

#### Optimization / sensitivity

- `lambda_wue`, `chi_w`, `d_a_n_d_e`, `d_a_n_d_r_abs`

#### Turgor

- `p_turgor`, `p_turgor_crit`

### 4.3. Full-name 권장 목록

- `net_assimilation_rate`
- `transpiration_rate`
- `leaf_water_potential`
- `stem_water_potential`
- `root_collar_water_potential`
- `soil_water_potential`
- `soil_water_potential_by_layer`
- `marginal_wue`
- `nonstructural_carbon`
- `turgor_pressure`
- `turgor_pressure_threshold`

### 4.4. 금지 규칙

- 단독 `lambda`, `Lambda`, `Λ`
  - 대신 `lambda_wue` 또는 `lambda_aux`
- `P_x_l`, `P_x_s`, `P_x_r`, `p_x_l`, `p_x_s`, `p_x_r`
  - 대신 `psi_l`, `psi_s`, `psi_rc`
- `_vect`
  - 대신 `_vec`
- `_stor` 를 코드 변수명/필드명에 사용
  - `_stor`는 output key 문자열에서만 허용
- 의미 없는 단독 `k` 바인딩
  - 대신 `k_soil`, `k_c`, `layer_idx`, `model_idx` 등 의미를 담은 이름 사용

### 4.5. suffix 규칙

- 1D vector: `_vec`
- 2D matrix: `_mat`
- grid/mesh: `_grid`
- layer axis: `_by_layer`
- time series: `_ts`
- optimal: `_opt`
- critical: `_crit`

### 4.6. 새 개념 추가 규칙

1. 기존 glossary에 맞출 수 있는지 먼저 확인
2. 없으면 `docs/variable_glossary.md`에 새 개념을 먼저 정의
3. short / full name 둘 다 결정
4. 충돌(alias) 규칙을 같이 적음
5. 그 다음에만 코드에 반영

## 5) GitHub CLI 우선 원칙

사용자는 웹보다 **터미널에서 한 번에 끝내는 흐름**을 선호하므로, `gh`가 설치·인증되어 있으면 Codex는 웹보다 GitHub CLI를 우선 사용한다.

### 기본 설정값

- 기본 repo visibility: `private`
- 기본 remote 이름: `origin`
- 기본 base branch: `main`
- 기본 Project title: `Phytoritas's Portfolio`
- 기본 Project owner: `@me`

### GitHub 작업 전 확인

```bash
gh auth status
gh auth setup-git
```

Project 추가/편집이 필요하면 필요 시 아래를 실행한다.

```bash
gh auth refresh -s project
```

### 이 repo에서 우선 사용할 helper scripts

가능하면 아래를 우선 사용한다.

- `scripts/New-GitHubIssueBranch.ps1`
- `scripts/Set-GitHubProjectStatus.ps1`
- `scripts/Set-GitHubProjectField.ps1`
- `scripts/New-GitHubPullRequest.ps1`
- `scripts/Sync-GitHubLabels.ps1`

repo 안에 helper script가 없으면 상위 workspace script를 fallback으로 사용한다.

### 의미 있는 작업은 Issue 먼저

비사소한 작업(새 기능, 새 실험, 구조 변경, 버그 수정, 데이터 준비)은 **코드 수정 전에 Issue를 먼저 만든다.**

가능하면 아래 형식을 사용한다.

```bash
gh issue create \
  --title "[<Type>] <short summary>" \
  --body-file <issue-body-file> \
  --label "<label1>" \
  --label "<label2>" \
  --project "Phytoritas's Portfolio"
```

### issue에서 branch 바로 만들기

가능하면 `gh issue develop` 또는 repo-local helper script를 우선 사용한다.

```bash
gh issue develop <issue-number> --checkout --name <branch-name>
```

branch 이름 규칙:

- `feat/<issue-number>-<slug>`
- `fix/<issue-number>-<slug>`
- `exp/<issue-number>-<slug>`
- `data/<issue-number>-<slug>`
- `docs/<issue-number>-<slug>`

### PR 생성

가능하면 repo-local helper script를 우선 사용한다.

직접 `gh`를 쓸 때는 아래를 기본으로 본다.

```bash
gh pr create \
  --fill \
  --body-file <pr-body-file> \
  --project "Phytoritas's Portfolio"
```

PR 본문에는 반드시 아래 줄을 포함한다.

```text
Closes #<issue-number>
```

### Project field / Status 자동화

Project 보드의 built-in automation(`Item added`, `Item closed`, `Pull request merged`)은 그대로 활용한다.
그 외의 중간 상태는 `gh project item-edit`를 직접 치기보다, repo-local script 또는 workspace script를 우선 사용한다.

## 6) GitHub Project 상태 운영

기본 Status 흐름은 아래를 따른다.

- `Inbox`
- `Ready`
- `Running`
- `Blocked`
- `Validating`
- `Done`

기본 원칙:

- 새 이슈는 `Inbox`
- 오늘 실제로 손대는 것만 `Running`
- 검증이 남아 있으면 `Validating`
- 이슈가 닫히면 `Done`
- 끝난 뒤 같은 범위가 미완성이면 `reopen`
- 새 요구사항이면 새 issue
- 새 부작용이면 새 bug issue

## 7) GitHub label 표준

새 repo는 아래 label 세트를 기본으로 갖는다. model과 crop의 경우에는 아키텍쳐에 맞게 추가한 뒤 표준으로 설정한다.

### type

- `type:hypothesis`
- `type:experiment`
- `type:model-change`
- `type:data`
- `type:bug`
- `type:doc`

### priority

- `prio:p0`
- `prio:p1`
- `prio:p2`

### model

- `model:gosm`
- `model:thorp`
- `model:tdgm`
- `model:load-cell`
- `model:general`

### crop

- `crop:tomato`
- `crop:cucumber`
- `crop:general`

가능하면 초기화 직후 `scripts/Sync-GitHubLabels.ps1`로 label 세트를 맞춘다.

## 8) issue 타입 표준

작업은 아래 타입 중 하나로 시작한다.

- `Hypothesis`
- `Experiment Run`
- `Model Change`
- `Data Prep`
- `Bug`
- `Doc`

### 최소 내용

#### Experiment Run

- dataset
- config
- metric
- output path
- decision

#### Model Change

- why
- affected model
- validation method
- comparison target

#### Bug

- repro
- expected / actual
- scope
- fix idea
- test

## 9) Git 위생 규칙

- `.venv/`, `__pycache__/`, `*.pyc`, `artifacts/`, `out/`, `runs/`, `results/`는 기본적으로 Git 추적 대상이 아니다.
- 로컬 전용 `config.local.*`, `.env`, 개인 경로가 들어간 설정, 임시 노트는 커밋하지 않는다.
- 생성물과 소스 변경은 한 커밋에 되도록 섞지 않는다.

## 10) 완료 정의

작업이 끝났다고 판단하려면 아래 중 하나 이상의 검증 흔적이 있어야 한다.

- 테스트 결과
- 실행 로그
- 스크린샷
- 대표 출력 경로
- README 갱신
- 결정 문서 갱신

완료 시 가능하면 아래 3줄을 남긴다.

- 무엇이 바뀌었는가
- 무엇으로 확인했는가
- 다음 액션은 무엇인가
