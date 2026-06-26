# -*- coding: utf-8 -*-
"""
Work CheckList — 공통 로직 (core)

UI(툴킷)와 무관한 부분만 모은 모듈이다: 상수·데이터 모델·영속성(JSON)·
마이그레이션·진행률 집계. tkinter 등 GUI 라이브러리를 일절 import 하지 않으므로,
화면을 다른 스택(예: 웹/HTML)으로 다시 만들더라도 이 파일은 그대로 재사용할 수
있다. 화면 그리기·위젯·이벤트 처리는 여기 없다(그건 checklist.py 가 담당).

기준 문서: checklist_spec.md
"""

import copy
import json
import os
import shutil


# ──────────────────────────────────────────────────────────────────────────
# 1. 프리셋 '기본값' 정의 (최초 실행 시 데이터 파일에 복사되는 시드)
#    실제 사용되는 프리셋은 데이터 파일(presets)에 저장되며 [설정 → 프리셋 관리]
#    에서 편집한다. 여기를 고치면 '프리셋 초기화'를 눌렀을 때의 기본값이 바뀐다.
#    새 업무는 기본적으로 비어 있다.
# ──────────────────────────────────────────────────────────────────────────

# 공통 프리셋 — 어떤 업무든 공통으로 쓸 만한 기본 항목
DEFAULT_COMMON_ITEMS = [
    "요구사항 확인",
    "프로젝트 모델 확인",
    "주석 작성",
    "빌드 확인",
]

# 카테고리별 {초기개발, 유지보수} 프리셋
DEFAULT_CATEGORY_TEMPLATES = {
    "화면개발": {
        "초기개발": [
            "화면 UI/UX 구현",
            "컴포넌트 재사용 가능성 검토",
            "입력값 유효성 검사 처리",
            "로딩 / 빈 데이터 / 에러 상태 화면 처리",
            "반응형 / 해상도 대응 확인",
            "화면 QC (레이아웃·동작)",
        ],
        "유지보수": [
            "변경 영향 범위 점검 (연관 화면 확인)",
            "기존 동작 회귀 테스트",
            "변경 전/후 화면 비교 확인",
        ],
    },
    "DB작업": {
        "초기개발": [
            "테이블 / 컬럼 설계 확인",
            "쿼리 작성",
            "인덱스 / 성능 점검",
            "트랜잭션 처리 확인",
            "더미 데이터로 동작 검증",
        ],
        "유지보수": [
            "스키마 변경 영향 범위 점검",
            "마이그레이션 / 롤백 방안 확인",
            "기존 쿼리 호환성 회귀 테스트",
            "데이터 정합성 확인",
        ],
    },
    "API작업": {
        "초기개발": [
            "엔드포인트 / 요청·응답 명세 정의",
            "요청 파라미터 유효성 검증",
            "인증 / 권한 처리",
            "에러 응답 / 예외 처리",
            "응답 포맷 확인",
        ],
        "유지보수": [
            "하위 호환성(Breaking Change) 점검",
            "연동 클라이언트 영향 범위 확인",
            "기존 호출 회귀 테스트",
            "변경 명세 문서 갱신",
        ],
    },
    "테스트": {
        "초기개발": [
            "테스트 케이스 작성",
            "정상 / 예외 / 경계값 검증",
            "테스트 결과 기록",
        ],
        "유지보수": [
            "회귀 테스트",
            "수정 범위 재검증",
        ],
    },
    "배포/운영": {
        "초기개발": [
            "배포 스크립트 / 절차 확인",
            "환경 변수 / 설정 점검",
            "롤백 방안 확인",
        ],
        "유지보수": [
            "배포 영향 범위 점검",
            "모니터링 / 로그 확인",
        ],
    },
    "문서화": {
        "초기개발": [
            "기능 명세 / 사용법 문서 작성",
            "주석 / 코드 정리",
        ],
        "유지보수": [
            "변경 내역 문서 갱신",
        ],
    },
    "버그수정": {
        "초기개발": [
            "재현 경로 확인",
            "원인 분석",
            "수정 후 재현 테스트",
        ],
        "유지보수": [
            "연관 기능 회귀 테스트",
            "재발 방지 점검",
        ],
    },
    "리팩토링": {
        "초기개발": [
            "변경 전 동작 기준 확보",
            "구조 / 네이밍 개선",
            "동작 동일성 검증",
        ],
        "유지보수": [
            "성능 / 가독성 비교",
        ],
    },
    "기타": {
        "초기개발": [
            "작업 목표 / 완료 기준 정의",
            "결과물 동작 확인",
        ],
        "유지보수": [
            "변경 영향 범위 점검",
            "기존 동작 회귀 테스트",
        ],
    },
}

# 카테고리 / 유형 / 상태 선택지
DEFAULT_CATEGORY_ORDER = ["화면개발", "DB작업", "API작업", "테스트",
                          "배포/운영", "문서화", "버그수정", "리팩토링", "기타"]
KIND_ORDER = ["초기개발", "유지보수"]
STATUS_ORDER = ["진행", "완료", "중단", "종료", "제외"]
NONE_LABEL = "(없음)"  # 카테고리 드롭다운의 '선택 안 함' 항목
GROUP_NONE_LABEL = "직접 작성"  # 항목 group="" 을 가리키는 드롭다운 표시 라벨

# 태그 표시 색 (순수 데이터 — 어떤 UI 스택이든 그대로 매핑해 쓸 수 있다)
KIND_COLORS = {"초기개발": "#2f6fb0", "유지보수": "#a06a00"}
STATUS_COLORS = {
    "진행": "#2f6fb0", "완료": "#2d8a4e", "중단": "#b03a3a",
    "종료": "#777777", "제외": "#999999",
}
# 진행률 집계에서 빼는 상태 (완료된/대상 아닌 업무)
STATUS_DIMMED = {"종료", "제외"}


# ──────────────────────────────────────────────────────────────────────────
# 2. 데이터 영속성 (JSON) + 마이그레이션
# ──────────────────────────────────────────────────────────────────────────

DATA_FILENAME = "checklist_data.json"
DATA_VERSION = 3

# 일반 설정 기본값 — 데이터 파일의 settings 블록 시드.
DEFAULT_SETTINGS = {
    "font_family": "Segoe UI",
    "font_size": 10,
    "theme": "vista",
}
# 글자 크기 허용 범위 (스핀박스).
FONT_SIZE_MIN, FONT_SIZE_MAX = 8, 18


def data_path():
    """프로그램과 같은 폴더에 데이터 파일을 둔다."""
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, DATA_FILENAME)


def default_presets():
    """코드 기본값에서 '편집 가능한 프리셋' 구조를 새로 만든다(깊은 복사)."""
    return {
        "common": list(DEFAULT_COMMON_ITEMS),
        "category_order": list(DEFAULT_CATEGORY_ORDER),
        "categories": copy.deepcopy(DEFAULT_CATEGORY_TEMPLATES),
    }


def ensure_presets(data):
    """presets 블록을 v3 구조로 보정한다(없으면 기본값으로 시드)."""
    presets = data.get("presets")
    if not isinstance(presets, dict):
        data["presets"] = default_presets()
        return
    presets.setdefault("common", list(DEFAULT_COMMON_ITEMS))
    cats = presets.setdefault("categories", {})
    # category_order 는 categories 의 키와 어긋나지 않도록 보정한다.
    order = presets.get("category_order")
    if not isinstance(order, list):
        order = list(DEFAULT_CATEGORY_ORDER)
    order = [c for c in order if c in cats]           # 사라진 카테고리 제거
    for c in cats:                                    # 누락된 카테고리 끝에 추가
        if c not in order:
            order.append(c)
    presets["category_order"] = order
    for cat, tpl in cats.items():
        if not isinstance(tpl, dict):
            cats[cat] = {k: [] for k in KIND_ORDER}
            continue
        for k in KIND_ORDER:
            tpl.setdefault(k, [])


def ensure_settings(data, valid_themes=None):
    """settings 블록을 보정한다(없으면 기본값으로 시드).

    valid_themes 가 주어지면(예: 현재 시스템에 실제 존재하는 ttk 테마 목록)
    저장된 테마가 그 목록에 없을 때 기본 테마로 보정한다. None 이면 테마 검증은
    건너뛴다(GUI 없이 데이터만 다룰 때 — core 가 toolkit 에 의존하지 않도록).
    """
    settings = data.get("settings")
    if not isinstance(settings, dict):
        settings = {}
    for key, val in DEFAULT_SETTINGS.items():
        settings.setdefault(key, val)
    try:
        size = int(settings.get("font_size", DEFAULT_SETTINGS["font_size"]))
    except (TypeError, ValueError):
        size = DEFAULT_SETTINGS["font_size"]
    settings["font_size"] = max(FONT_SIZE_MIN, min(FONT_SIZE_MAX, size))
    # 노출에서 제외한 테마가 저장돼 있으면(옛 설정 등) 유효 목록으로 보정한다.
    if valid_themes:
        if settings.get("theme") not in valid_themes:
            settings["theme"] = (DEFAULT_SETTINGS["theme"]
                                 if DEFAULT_SETTINGS["theme"] in valid_themes
                                 else valid_themes[0])
    data["settings"] = settings


def default_data():
    return {"version": DATA_VERSION, "next_id": 1, "always_on_top": True,
            "geometry": None, "settings": dict(DEFAULT_SETTINGS),
            "presets": default_presets(), "tasks": []}


def _legacy_auto_texts(categories):
    """v1 데이터 복원용: 옛 카테고리에서 공통+개발+수정 항목 텍스트를 순서대로."""
    texts = []
    seen = set()
    for t in DEFAULT_COMMON_ITEMS:
        if t not in seen:
            texts.append(t)
            seen.add(t)
    for cat in DEFAULT_CATEGORY_ORDER:
        if cat not in categories:
            continue
        tpl = DEFAULT_CATEGORY_TEMPLATES.get(cat, {})
        for kind in KIND_ORDER:
            for t in tpl.get(kind, []):
                if t not in seen:
                    texts.append(t)
                    seen.add(t)
    return texts


def ensure_task_fields(task, index=0):
    """업무 한 건의 필드를 v2 구조로 보정한다(필요 시 v1 → v2 마이그레이션)."""
    task.setdefault("title", task.pop("subtitle", ""))  # subtitle → title
    task.setdefault("kind", "")
    task.setdefault("categories", [])
    task.setdefault("status", "진행")
    task.setdefault("collapsed", False)
    # 우선순위(1/2/3): 기존 데이터는 순서대로 1,2,3 … 4번째부터는 고정 3.
    task.setdefault("priority", min(index + 1, 3))

    if "items" not in task:
        # v1: checks(자동) + manual(수동)을 실제 항목으로 변환(데이터 보존).
        checks = task.pop("checks", {}) or {}
        manual = task.pop("manual", []) or []
        items = []
        nid = 1

        def add(text, checked):
            nonlocal nid
            items.append({"id": nid, "text": text, "checked": bool(checked),
                          "group": "", "subitems": []})
            nid += 1

        # 기본 정책은 '빈 체크리스트'. 따라서 옛 자동 항목 중 실제로 체크돼
        # 있던 것(=사용자의 진행 상태)과 수동 항목만 보존하고, 체크 안 된
        # 템플릿 항목은 버린다. 필요하면 [프리셋 불러오기]로 다시 채운다.
        checked_texts = {key.split("::", 1)[1]
                         for key, val in checks.items() if val and "::" in key}
        for text in _legacy_auto_texts(task.get("categories", [])):
            if text in checked_texts:
                add(text, True)
        for m in manual:
            add(m.get("text", ""), m.get("checked", False))

        task["items"] = items
        task["next_item_id"] = nid
    else:
        # v2: 항목 구조 보정
        nid = task.get("next_item_id", 1)
        for it in task["items"]:
            it.setdefault("checked", False)
            it.setdefault("group", "")
            it.setdefault("subitems", [])
            if "id" not in it:
                it["id"] = nid
                nid += 1
            for sub in it["subitems"]:
                sub.setdefault("checked", False)
                if "id" not in sub:
                    sub["id"] = nid
                    nid += 1
        task["next_item_id"] = max(nid, task.get("next_item_id", 1))


def load_data(valid_themes=None):
    """파일 없으면 빈 상태. 손상 시 백업 후 빈 상태로 복구. v1은 v2로 변환.

    valid_themes 는 ensure_settings 로 전달돼 저장된 테마 보정에 쓰인다(UI 가
    현재 시스템의 ttk 테마 목록을 넘겨 준다). 없으면 테마 검증은 건너뛴다.
    """
    path = data_path()
    if not os.path.exists(path):
        return default_data(), None

    try:
        with open(path, "r", encoding="utf-8") as f:   # UTF-8 고정
            data = json.load(f)
        if not isinstance(data, dict) or "tasks" not in data:
            raise ValueError("형식이 올바르지 않습니다.")
        data.setdefault("next_id", _infer_next_id(data))
        data.setdefault("always_on_top", True)
        data.setdefault("geometry", None)
        data.setdefault("tasks", [])
        ensure_settings(data, valid_themes)  # v2 이하 → settings 블록 시드
        ensure_presets(data)    # v2 이하 → presets 블록 시드(코드 기본값 복사)
        for idx, task in enumerate(data["tasks"]):
            ensure_task_fields(task, idx)
        data["version"] = DATA_VERSION
        return data, None
    except Exception as e:  # noqa: BLE001  (손상/파싱 실패 전부 복구 대상)
        backup = None
        try:
            backup = path + ".corrupt.bak"
            shutil.copy2(path, backup)
        except Exception:  # noqa: BLE001
            backup = None
        return default_data(), ("load_corrupt", str(e), backup)


def _infer_next_id(data):
    max_id = 0
    for t in data.get("tasks", []):
        try:
            max_id = max(max_id, int(t.get("id", 0)))
        except (TypeError, ValueError):
            pass
    return max_id + 1


# ──────────────────────────────────────────────────────────────────────────
# 3. 진행률 집계 (UI 무관 순수 로직)
# ──────────────────────────────────────────────────────────────────────────

def task_progress(task):
    """업무 하나의 (완료 수, 전체 수)를 센다. 하위 항목도 1개로 집계한다."""
    done = total = 0
    for it in task.get("items", []):
        total += 1
        if it.get("checked"):
            done += 1
        for sub in it.get("subitems", []):
            total += 1
            if sub.get("checked"):
                done += 1
    # '완료' 업무는 개별 체크 여부와 무관하게 전부 완료로 집계한다
    # (수동으로 다 체크할 필요 없음). 체크 상태 자체는 보존하므로
    # 상태를 다시 '진행' 등으로 되돌리면 원래 진행률로 복귀한다.
    if task.get("status") == "완료":
        return total, total
    return done, total
