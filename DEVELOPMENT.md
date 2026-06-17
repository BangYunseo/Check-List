# Work CheckList — 개발 문서

항상 위에 떠 있는 가벼운 업무 체크리스트 위젯(`checklist.py`)의 개발 진행 내용·구조·설계 결정을 정리한 문서입니다. 사용자용 안내는 [README.md](README.md)를 참고하세요.

- 구현 언어: **Python 3.x**, 단일 파일(`checklist.py`, 약 1,090줄)
- 의존성: **표준 라이브러리만** (`tkinter`, `json`, `os`, `shutil`, `sys`, `ctypes`) — 외부 패키지 0, 외부 전송 0
- 저장: 같은 폴더의 `checklist_data.json` (로컬, UTF-8)

---

## 1. 개발 목표

Windows Sticky Notes로 일과를 관리할 때의 두 가지 불편을 해소한다.

1. 다른 창을 띄우면 메모가 뒤로 내려간다 → **항상 위(always-on-top)** 고정
2. 자유 메모는 일관성·누락 방지가 어렵다 → **체크리스트 + 프리셋** 구조

핵심 설계 원칙은 "의미를 분석해 자동 생성하는 똑똑한 도구"가 아니라 **일관성과 누락 방지**다. 기본은 비우고, 필요할 때 프리셋으로 채우고, 자유롭게 편집한다.

---

## 2. 전체 구조

단일 파일을 6개 섹션으로 나눠 구성했다.

| 섹션 | 책임 |
| --- | --- |
| **1. 프리셋 기본값** | `DEFAULT_COMMON_ITEMS`, `DEFAULT_CATEGORY_TEMPLATES`, `DEFAULT_CATEGORY_ORDER` 등 시드 상수. 실제 프리셋은 데이터 파일에 저장되고 [설정]에서 편집 |
| **2. 데이터 영속성 + 마이그레이션** | `load_data` / `save` / `ensure_task_fields` / `ensure_settings` / `ensure_presets` — JSON 로드·저장·복구, v1→v2·v2→v3 변환 |
| **3. 업무 다이얼로그** | `TaskDialog` — 제목·유형·카테고리·개수 입력 모달(카테고리 목록은 설정에서 편집한 값을 주입) |
| **4. 리스트 카드** | `TaskCard` — 업무 1건의 위젯/부분 갱신 |
| **5. 메인 애플리케이션** | `ChecklistApp` — UI 골격, 렌더링, 드래그 정렬, 진행률, 글꼴/테마 적용, 프리셋 접근자 |
| **6. 설정 다이얼로그** | `SettingsDialog` — 일반 설정(항상 위·글꼴·글자 크기·테마·데이터 폴더·프리셋 초기화) + 프리셋 관리(항목·카테고리 CRUD) |

UI 계층은 `Tk(root) → toolbar / 전체진행률 / Canvas(스크롤) → body(Frame) → 업무 카드 → 항목 블록 → 하위 항목` 순으로 중첩된다. 스크롤은 `Canvas` + `Scrollbar` + 내부 `Frame` 조합으로 구현.

---

## 3. 데이터 모델

`checklist_data.json` (현재 `version: 3`):

```json
{
  "version": 3,
  "next_id": 11,
  "always_on_top": true,
  "geometry": "384x983+1313+0",
  "settings": { "font_family": "Segoe UI", "font_size": 10, "theme": "vista" },
  "presets": {
    "common": ["요구사항 확인"],
    "category_order": ["화면개발", "DB작업"],
    "categories": { "화면개발": { "초기개발": ["화면 UI/UX 구현"], "유지보수": [] } }
  },
  "tasks": [
    {
      "id": 8, "title": "사원 화면 개발", "kind": "초기개발",
      "categories": ["화면개발"], "status": "진행", "collapsed": true,
      "next_item_id": 12,
      "items": [
        { "id": 5, "text": "화면 UI/UX 구현", "checked": false,
          "group": "화면개발", "subitems": [] }
      ]
    }
  ]
}
```

| 필드 | 의미 |
| --- | --- |
| `tasks[]` 순서 | 화면 표시 순서 = 우선순위(드래그로 변경) |
| `task.kind` | 유형: `초기개발` / `유지보수` / `""` |
| `task.status` | 상태: 진행 / 완료 / 중단 / 종료 / 제외 |
| `item.group` | 카테고리 칸 구분(`""`이면 자유 항목) |
| `item.subitems` | 2단계 하위 항목 |
| `geometry` | 마지막 창 크기·위치 복원용 |
| `settings` | 일반 설정(글꼴·글자 크기·테마). `ensure_settings`로 보정·시드 |
| `presets` | 편집 가능한 프리셋(`common`/`category_order`/`categories`). `ensure_presets`로 보정·시드 |

ID 관리: 업무는 전역 `next_id`, 항목/하위 항목은 업무별 `next_item_id`로 단조 증가시켜 충돌을 막는다.

---

## 4. 주요 기능별 구현

### 4.1 창 동작 (always-on-top · 크기 제한 · 최대화 차단)
- `attributes("-topmost", ...)`로 항상 위 토글(`apply_always_on_top`).
- 최대 크기는 **데스크톱 작업 영역**(작업 표시줄 제외)으로 제한(`_apply_size_limits` + `_workarea`, Windows는 `SPI_GETWORKAREA`). 너비는 설계상 ≤560이되 작업 영역이 더 좁으면 거기에 맞춘다. 저장된 geometry는 복원 시 `_clamp_geometry`로 작업 영역 안(크기·위치)으로 보정 → 다른 모니터에서 켜도 화면 밖으로 나가지 않는다.
- **최대화만 비활성화**: `ctypes`로 `WS_MAXIMIZEBOX` 스타일 비트를 제거(`_disable_maximize`). 테두리 리사이즈는 유지해, 위젯이 화면을 덮지 않게 했다.
- 창 크기/위치는 `<Configure>` 이벤트를 600ms 디바운스해 저장(`_on_root_configure`), 종료 시에도 한 번 저장.

### 4.2 진행률 집계
- 업무별 `task_progress`: 항목 + 하위 항목을 모두 1개로 세어 `done/total` 산출.
- 전체 진행률(`_refresh_overall`): `종료`/`제외` 상태 업무는 합산에서 제외.
- 체크 시에는 전체 렌더 없이 `_refresh_progress`로 라벨/바만 갱신(가벼움).

### 4.3 프리셋 (편집 가능)
- 새 업무는 항상 **빈 체크리스트**로 시작.
- 프리셋은 데이터 파일의 `presets` 블록에 저장되고, `ChecklistApp`의 접근자(`common_items` / `category_order` / `category_templates`)로 읽는다. 코드 상수 `DEFAULT_*`는 시드/초기화용.
- `[프리셋 불러오기]`는 `공통` + 카테고리별 `초기개발`/`유지보수` 목록을 메뉴로 제공(`_build_preset_menu`). 업무의 카테고리를 상단, 나머지를 하단에 배치해 어떤 칸이든 불러올 수 있다.
- `load_preset`는 **이미 존재하는 텍스트는 건너뛰어** 중복을 막고, `group`으로 카테고리 칸을 구분한다.
- **편집은 [⚙ 설정 → 프리셋 관리]**(`SettingsDialog`): 항목 추가·수정·삭제·정렬, 카테고리 추가·이름변경(`rename_category_refs`로 기존 업무 참조 동기화)·삭제.
- **갱신 비용 최적화**: 프리셋 드롭다운은 `tk.Menu`의 `postcommand`(`_populate_preset_menu`)로 **열릴 때마다 현재 데이터로 다시 채운다.** 따라서 항목 편집은 `save()`만 하면 되고 전체 `render()`가 불필요(`_commit_items`). **카테고리 구조 변경**(추가/이름변경/삭제)은 그룹 정렬·`TaskDialog` 카테고리 목록·`item.group` 표시에 영향을 주므로 `render()`를 유지한다.

### 4.3.1 글꼴 / 테마
- `settings`의 `font_family`·`font_size`를 Tk 명명 폰트(`TkDefaultFont` 등)에 적용(`_apply_fonts`)해 ttk 위젯 전반에 반영. 카드 내 작은 배지는 `card_font(delta, bold)`로 기준 크기에서 상대 조정.
- 테마는 `ttk.Style().theme_use`(`_apply_theme`). 변경은 `apply_settings`에서 저장 후 `render()`로 다시 그린다.

### 4.4 드래그 정렬 (업무 · 항목 공통 패턴)
- 핸들(↕) `ButtonPress / B1-Motion / ButtonRelease` 3단계로 처리.
- 커서를 따라다니는 **고스트 라벨**(`_make_ghost`, 반투명 `Toplevel`)로 끌리는 대상을 표시.
- 드래그 중에는 전체 렌더 대신 `pack_forget()` + `pack()`으로 해당 위젯만 재배치(`_drag_motion` / `_item_drag_motion`)해 부드럽게 동작.
- 강조는 크기를 바꾸지 않는 방식(카드는 `relief`만, 항목은 핸들 색만)으로 처리해 다른 항목이 밀리지 않게 했다.
- 놓는 순간(`_drag_end`)에만 `save()` + `render()`로 표시 번호(#N)·우선순위 색을 재계산.

### 4.5 상태 / 잠금
- 상위 우선순위 3개는 카드 번호 배지에 빨강·주황·노랑 색을 입힌다.
- `종료`/`제외`는 진행률 집계에서 빠지고 흐리게 표시(dimmed).
- **`제외`는 잠금**: 상태 변경과 드래그만 허용하고 항목 체크·추가·삭제 등 내부 편집은 모두 비활성화(`locked`).

---

## 5. 안정성·내구성 설계

- **원자적 저장**: `*.tmp`에 쓴 뒤 `os.replace`로 교체해, 저장 중 중단 시에도 기존 파일이 깨지지 않음.
- **손상 복구**: 로드 실패 시 `*.corrupt.bak`로 백업하고 빈 상태로 시작, 사용자에게 경고 안내.
- **저장 실패 안내**: 디스크 오류 등으로 저장 실패 시 1회 경고(메모리 데이터는 유지).
- **인코딩 고정**: 읽기/쓰기 모두 UTF-8.
- **버전 마이그레이션**: `ensure_task_fields`가 v1(`checks`/`manual` 구조) 데이터를 v2(`items`)로 자동 변환. 이때 **체크돼 있던 항목과 직접 작성한 항목만 보존**하고, 체크 안 된 자동 템플릿 항목은 비운다(기본 빈 정책).
- **tkinter 미설치 환경**: 임포트 실패 시 안내 메시지 출력 후 종료.

---

## 6. 성능을 위한 디테일

| 처리 | 기법 |
| --- | --- |
| 창 리사이즈 폭 갱신 | 같은 폭이면 무시 + 60ms 디바운스(`_on_canvas_configure`) |
| 창 위치 저장 | 600ms 디바운스 |
| 체크 토글 | 전체 렌더 대신 라벨/바만 부분 갱신 |
| 드래그 중 재배치 | `pack_forget`/`pack`으로 해당 위젯만 이동 |
| 메뉴 콜백 후 렌더 | `after_idle`로 미뤄, 닫히는 중인 메뉴 파괴로 인한 크래시 방지 |
| 전부 접었을 때 | `_clamp_scroll`로 스크롤을 위로 고정해 빈 공간 쏠림 방지 |

---

## 7. 설계 변경 이력 (요지)

- **초기**: 카테고리 선택 시 항목을 자동 생성하는 규칙 기반 방식.
- **현재**: 실사용에서 자동 항목이 부담스럽고 업무마다 필요한 항목이 달라, **기본 빈 → 필요 시 프리셋 → 자유 편집** 구조로 전환. 데이터 구조도 v1(자동/수동 분리)에서 v2(단일 `items` 리스트 + group)로 통합.

---

## 8. 비범위 (의도적으로 하지 않는 것)

- 입력 문장의 의미 분석 / 자동 분해
- 외부 서버 전송 / 클라우드 동기화 (전부 로컬)
- 다중 사용자 / 협업
- 되돌리기(undo) — 삭제는 확인 다이얼로그 후 진행

---

## 9. 확장 가이드

- **프리셋/카테고리 추가·수정**: 사용자는 **[⚙ 설정 → 프리셋 관리]**에서 직접 편집. 기본값(시드)을 바꾸려면 `DEFAULT_COMMON_ITEMS` / `DEFAULT_CATEGORY_TEMPLATES` / `DEFAULT_CATEGORY_ORDER` 수정 후 [프리셋 초기화].
- **일반 설정 항목 추가**: `DEFAULT_SETTINGS`에 키를 추가하고 `ensure_settings` 보정 + `SettingsDialog._build_general`에 위젯 추가.
- **상태/유형 추가**: `STATUS_ORDER`/`KIND_ORDER`와 대응 색상 딕셔너리(`STATUS_COLORS`/`KIND_COLORS`) 갱신.
- **데이터 구조 변경 시**: `DATA_VERSION`을 올리고 `ensure_task_fields`/`ensure_settings`/`ensure_presets`에 변환 분기를 추가.
- **단일 실행 파일 배포**: `pyinstaller --onefile --windowed checklist.py`.
