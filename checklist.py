# -*- coding: utf-8 -*-
"""
Work CheckList — 업무 체크리스트 프로그램
- 항상 위에 떠 있는 가벼운 체크리스트 위젯 (Sticky Notes 보완용).
- 업무는 기본적으로 '빈 체크리스트'로 시작하고, 사용자가 항목/하위 항목을
  직접 추가하거나 [프리셋 불러오기]로 유형별(초기개발/유지보수) 기본 목록을 채운다.
- 항목은 자유롭게 추가·삭제·드래그 정렬할 수 있다.
- 순수 파이썬 표준 라이브러리(tkinter + json)만 사용. 외부 전송 없음.
- 기준 문서: checklist_spec.md
"""

import copy
import json
import os
import re
import shutil
import sys

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, simpledialog
    import tkinter.font as tkfont
except ImportError:  # tkinter 미설치 환경
    sys.stderr.write(
        "이 프로그램은 tkinter가 필요합니다. "
        "파이썬 표준 GUI 모듈(tkinter)이 설치된 환경에서 실행하세요.\n"
    )
    sys.exit(1)


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

# 태그 표시 색
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


def ensure_settings(data):
    """settings 블록을 보정한다(없으면 기본값으로 시드)."""
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


def load_data():
    """파일 없으면 빈 상태. 손상 시 백업 후 빈 상태로 복구. v1은 v2로 변환."""
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
        ensure_settings(data)   # v2 이하 → settings 블록 시드
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
# 3. 업무 추가/수정 다이얼로그 (제목 + 유형 + 카테고리)
# ──────────────────────────────────────────────────────────────────────────

class TaskDialog(tk.Toplevel):
    def __init__(self, master, title="업무 추가", name="", kind="",
                 categories=None, show_count=True, category_order=None):
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.transient(master)
        self.show_count = show_count
        self.result = None  # (name, kind, [categories], count) or None
        # 카테고리 드롭다운 목록(설정에서 편집 가능) — 미지정 시 코드 기본값.
        self.category_order = list(category_order or DEFAULT_CATEGORY_ORDER)

        categories = set(categories or [])

        body = ttk.Frame(self, padding=12)
        body.pack(fill="both", expand=True)

        ttk.Label(body, text="제목").grid(row=0, column=0, sticky="w")
        self.name_var = tk.StringVar(value=name)
        entry = ttk.Entry(body, textvariable=self.name_var, width=38)
        entry.grid(row=1, column=0, sticky="we", pady=(2, 10))

        ttk.Label(body, text="유형").grid(row=2, column=0, sticky="w")
        self.kind_var = tk.StringVar(value=kind)
        kind_frame = ttk.Frame(body)
        kind_frame.grid(row=3, column=0, sticky="w", pady=(2, 10))
        ttk.Radiobutton(kind_frame, text="지정 안 함", value="",
                        variable=self.kind_var).pack(side="left", padx=(0, 12))
        for k in KIND_ORDER:
            ttk.Radiobutton(kind_frame, text=k, value=k,
                            variable=self.kind_var).pack(side="left", padx=(0, 12))

        ttk.Label(body, text="카테고리").grid(row=4, column=0, sticky="w")
        row5 = ttk.Frame(body)
        row5.grid(row=5, column=0, sticky="we", pady=(2, 0))
        cur_cat = next(iter(categories), "")  # 단일 선택(드롭다운)
        # 카테고리 목록에 '기타'가 없으면 직접 입력 대체용으로 항상 노출한다.
        cat_values = list(self.category_order)
        has_etc = "기타" in cat_values
        if not has_etc:
            cat_values = cat_values + ["기타"]
        is_custom = bool(cur_cat) and cur_cat not in cat_values
        self.cat_var = tk.StringVar(
            value=("기타" if is_custom else (cur_cat or NONE_LABEL)))
        self.cat_cb = ttk.Combobox(row5, textvariable=self.cat_var, state="readonly",
                                   width=12, values=[NONE_LABEL] + cat_values)
        self.cat_cb.pack(side="left")
        self.cat_cb.bind("<<ComboboxSelected>>", lambda e: self._sync_etc())
        # 기타 선택 시 직접 입력칸 활성화
        self.etc_var = tk.StringVar(value=(cur_cat if is_custom else ""))
        self.etc_entry = ttk.Entry(row5, textvariable=self.etc_var, width=12)
        self.etc_entry.pack(side="left", padx=(6, 0))
        self.count_var = tk.IntVar(value=1)
        if show_count:
            ttk.Label(row5, text="개수").pack(side="left", padx=(10, 4))
            ttk.Spinbox(row5, from_=1, to=50, width=4,
                        textvariable=self.count_var).pack(side="left")
        self._sync_etc()

        btns = ttk.Frame(body)
        btns.grid(row=6, column=0, sticky="e", pady=(16, 0))
        ttk.Button(btns, text="저장", command=self._on_ok).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="취소", command=self._on_cancel).pack(side="left")

        self.bind("<Return>", lambda e: self._on_ok())
        self.bind("<Escape>", lambda e: self._on_cancel())

        entry.focus_set()
        self._center_on(master)
        self.grab_set()
        self.wait_window(self)

    def _sync_etc(self):
        """카테고리가 '기타'일 때만 직접 입력칸을 활성화한다."""
        if self.cat_var.get() == "기타":
            self.etc_entry.configure(state="normal")
        else:
            self.etc_var.set("")
            self.etc_entry.configure(state="disabled")

    def _center_on(self, master):
        self.update_idletasks()
        try:
            mx, my = master.winfo_rootx(), master.winfo_rooty()
            mw, mh = master.winfo_width(), master.winfo_height()
            w, h = self.winfo_width(), self.winfo_height()
            x = mx + (mw - w) // 2
            y = my + (mh - h) // 2
            self.geometry("+{}+{}".format(max(x, 0), max(y, 0)))
        except Exception:  # noqa: BLE001
            pass

    def _on_ok(self):
        name = self.name_var.get().strip()
        kind = self.kind_var.get()
        cat = self.cat_var.get()
        if cat == NONE_LABEL:
            cats = []
        elif cat == "기타":
            etc = self.etc_var.get().strip()
            cats = [etc] if etc else ["기타"]   # 직접 입력한 이름을 카테고리로
        else:
            cats = [cat]
        try:
            count = int(self.count_var.get()) if self.show_count else 1
        except (tk.TclError, ValueError):
            count = 1
        count = max(1, min(50, count))
        self.result = (name, kind, cats, count)
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()


# ──────────────────────────────────────────────────────────────────────────
# 4. 리스트 카드 (한 개의 업무를 책임지는 객체)
#    위젯을 한 번만 만들고, 이후엔 바뀐 부분만 스스로 갱신한다.
#    - 제목/진행률/순위 배지: 해당 위젯만 config (깜빡임 없음)
#    - 상태/접기/항목 변경: 자기 카드 '안'만 다시 그린다(rebuild) — 전체 화면을
#      destroy 후 재생성하지 않으므로 다른 카드는 그대로다.
# ──────────────────────────────────────────────────────────────────────────

class TaskCard:
    def __init__(self, app, task):
        self.app = app
        self.task = task
        self.position = 0
        self.frame = None          # 카드 바깥 프레임 (app.body 에 pack)
        self.rank_lbl = None       # 순위 배지 (#N, 색)
        self.title_lbl = None      # 제목 라벨
        self.prog_lbl = None       # 진행률 (n/m)
        self.item_blocks = {}      # {item_id: block Frame} — 항목 드래그 정렬용
        # 편집 모드: 켜면 각 항목의 +세부·✕ 버튼이 보인다(평소엔 숨김 → 깔끔).
        # 카드 객체가 들고 있어 rebuild 후에도 유지된다(전체 render 때만 초기화).
        self.edit_mode = False
        self._snapshot = None      # 편집 진입 시 항목 상태 사본(취소 시 복구용)
        self._edit_new = None      # rebuild 후 인라인 입력할 대상 ("item"/"sub", id)
        self._item_cbs = {}        # {("item"|"sub", id): Checkbutton} — 인라인 편집용
        self._last_title_fit = None  # (폭, 제목) 캐시 — 같은 값이면 재계산 생략

    # ---- 생성 / 재생성 ----------------------------------------------------
    def build(self, position):
        """카드 바깥 프레임을 만들어 body 에 붙이고 내용을 채운다."""
        self.frame = ttk.Frame(self.app.body, relief="solid",
                               borderwidth=1, padding=6)
        self.frame.pack(fill="x", pady=(0, 8))
        self._populate(position)
        return self.frame

    def rebuild(self, position=None):
        """프레임은 그 자리에 두고 내용만 새로 그린다(이 카드 1개만 잠깐 바뀜).
        상태/접기/항목처럼 카드 내부 구조가 달라질 때 호출한다."""
        if self.frame is None or not self.frame.winfo_exists():
            return
        if position is None:
            position = self.position
        for child in self.frame.winfo_children():
            child.destroy()
        self.item_blocks = {}
        self._populate(position)
        # 높이 변화 → body <Configure> 가 scrollregion 을 알아서 갱신.

    @staticmethod
    def _rank_color(priority, dimmed):
        # 우선순위 1 빨강 / 2 주황 / 3 노랑. 종료·제외(dimmed)면 회색.
        if dimmed:
            return "#9aa0a6"
        return {1: "#d9342b", 2: "#e8821e", 3: "#caa200"}.get(priority, "#caa200")

    def _priority(self):
        p = self.task.get("priority", 3)
        return p if p in (1, 2, 3) else 3

    def _populate(self, position):
        self.position = position
        app, task = self.app, self.task
        self._item_cbs = {}
        self._last_title_fit = None   # 새 제목 라벨이므로 캐시 초기화

        header = ttk.Frame(self.frame)
        header.pack(fill="x")

        # 업무 드래그 핸들 (카드 순서 정렬 — 우선순위 배지와는 별개)
        handle = ttk.Label(header, text="↕", cursor="fleur", foreground="#999")
        handle.pack(side="left", padx=(0, 2))
        handle.bind("<ButtonPress-1>", lambda e: app._drag_start(task))
        handle.bind("<B1-Motion>", app._drag_motion)
        handle.bind("<ButtonRelease-1>", app._drag_end)

        arrow = "▶" if task.get("collapsed") else "▼"
        ttk.Button(header, text=arrow, width=2,
                   command=lambda: app.toggle_collapse(task)).pack(side="left")

        dimmed = task.get("status") in STATUS_DIMMED
        # '제외'면 잠금: 상태 변경과 드래그만 허용하고 내부 편집은 전부 막는다.
        locked = task.get("status") == "제외"
        if locked:
            self.edit_mode = False   # 잠긴 카드는 편집 모드 자체가 꺼져 있어야 한다.
        # 우선순위 배지(1/2/3) — 클릭하면 메뉴로 변경(상태 버튼과 동일한 방식).
        # 드래그 순서와는 독립.
        priority = self._priority()
        self.rank_lbl = tk.Menubutton(header, text=str(priority),
                                      bg=self._rank_color(priority, dimmed), fg="white",
                                      font=app.card_font(-1, bold=True), padx=6,
                                      relief="raised", cursor="hand2", takefocus=0)
        pmenu = tk.Menu(self.rank_lbl, tearoff=0)
        for v in (1, 2, 3):
            pmenu.add_command(label="우선순위 {}".format(v),
                              foreground=self._rank_color(v, False),
                              command=lambda val=v: self.set_priority(val))
        self.rank_lbl["menu"] = pmenu
        self.rank_lbl.pack(side="left", padx=(6, 4))

        # 제목 라벨은 생성만 해두고 '맨 마지막에' pack 한다. 그래야 폭이 좁아질 때
        # 고정 버튼들이 먼저 자리를 차지하고, 남는 가운데 공간만 제목이 차지한다
        # (= 제목이 잘릴지언정 버튼은 절대 가려지지 않음). 길면 '…'로 줄인다.
        self.title_lbl = ttk.Label(header, text=task.get("title") or "(제목 없음)",
                                   font=app.title_font, cursor="hand2", anchor="w",
                                   foreground=("#999" if dimmed else "#000"))
        # 제목 더블클릭 → 이름 바로 수정 (잠금 시 비활성)
        if not locked:
            self.title_lbl.bind(
                "<Double-Button-1>",
                lambda e: app.rename_task(task, self.title_lbl))

        # 오른쪽: 삭제 / 수정 / 상태 / 진행률 / 유형 (오른쪽 끝부터 차례로)
        ttk.Button(header, text="🗑", width=3,
                   command=lambda: app.delete_task(task)).pack(side="right")
        ttk.Button(header, text="✎", width=3,
                   state=("disabled" if locked else "normal"),
                   command=lambda: app.edit_task(task)).pack(side="right", padx=(0, 4))
        # 수정 토글: 켜면 각 항목의 +세부·✕ 버튼이 보인다(Toolbutton = 눌린 모양).
        self.edit_var = tk.BooleanVar(value=self.edit_mode)
        ttk.Checkbutton(header, text="수정", style="Toolbutton",
                        variable=self.edit_var, takefocus=0,
                        state=("disabled" if locked else "normal"),
                        command=self._toggle_edit).pack(side="right", padx=(0, 4))
        status = task.get("status", "진행")
        smb = tk.Menubutton(header, text=status,
                            bg=STATUS_COLORS.get(status, "#666"),
                            fg="white", font=app.card_font(-2, bold=True),
                            relief="raised", padx=6, takefocus=0)
        smenu = tk.Menu(smb, tearoff=0)
        for s in STATUS_ORDER:
            smenu.add_command(label=s, foreground=STATUS_COLORS.get(s, "#000"),
                              command=lambda val=s: app.set_status(task, val))
        smb["menu"] = smenu
        smb.pack(side="right", padx=(0, 6))
        done, total = app.task_progress(task)
        self.prog_lbl = ttk.Label(header, text="{}/{}".format(done, total),
                                  foreground="#555")
        self.prog_lbl.pack(side="right", padx=(0, 8))
        if task.get("kind"):
            ttk.Label(header, text=task["kind"],
                      foreground=KIND_COLORS.get(task["kind"], "#666"),
                      font=app.card_font(-2)).pack(side="right", padx=(6, 0))

        # 남는 가운데 공간을 제목이 차지(잘리면 '…'). Configure 마다 다시 맞춘다.
        self.title_lbl.pack(side="left", fill="x", expand=True)
        self.title_lbl.bind("<Configure>", self._refit_title)

        if task.get("collapsed"):
            return

        # 본문 컨트롤: 항목 추가 + 프리셋 불러오기
        controls = ttk.Frame(self.frame)
        controls.pack(fill="x", pady=(6, 2))
        ttk.Button(controls, text="+ 항목",
                   state=("disabled" if locked else "normal"),
                   command=self.begin_add_item).pack(side="left")
        self._build_preset_menu(controls, locked)

        items = task.setdefault("items", [])
        if not items:
            ttk.Label(self.frame, text="항목 없음 — [+ 항목] 또는 [프리셋 불러오기]",
                      foreground="#999").pack(anchor="w", padx=(4, 0), pady=(2, 0))
            self._maybe_start_inline_edit()
            return

        # 카테고리(group)별로 묶어서 표시. 그룹이 2개 이상일 때만 칸 헤더를 보인다
        # (단일 카테고리/자유 항목이면 헤더 없이 평탄하게).
        cat_order = self.app.category_order()

        def group_rank(g):
            if g == "공통":
                return (0, 0)
            if g in cat_order:
                return (1, cat_order.index(g))
            if g == "":
                return (3, 0)
            return (2, 0)

        present = []
        for it in items:
            g = it.get("group", "")
            if g not in present:
                present.append(g)
        present.sort(key=group_rank)
        multi = len(present) > 1

        for g in present:
            if multi:
                label = "[{}]".format(g) if g else "[직접 작성]"
                ttk.Label(self.frame, text=label, foreground="#3a6ea5",
                          font=self.app.card_font(-1, bold=True)).pack(anchor="w", pady=(6, 1))
            for item in [it for it in items if it.get("group", "") == g]:
                self._render_item_block(item, locked)

        self._maybe_start_inline_edit()

    def _build_preset_menu(self, parent, locked=False):
        mb = ttk.Menubutton(parent, text="프리셋 불러오기 ▾",
                            state=("disabled" if locked else "normal"))
        menu = tk.Menu(mb, tearoff=0)
        # 메뉴는 '열릴 때마다' 최신 프리셋으로 다시 채운다(postcommand).
        # → [설정]에서 프리셋을 편집해도 전체 화면을 다시 그릴 필요가 없다.
        menu.configure(postcommand=lambda m=menu: self._populate_preset_menu(m))
        mb["menu"] = menu
        mb.pack(side="left", padx=(6, 0))

    def _populate_preset_menu(self, menu):
        """프리셋 메뉴 항목을 현재 데이터 기준으로 다시 만든다(메뉴 열 때 호출)."""
        app, task = self.app, self.task
        menu.delete(0, "end")
        common = app.common_items()
        templates = app.category_templates()
        menu.add_command(
            label="공통",
            state=("normal" if common else "disabled"),
            command=lambda: app.load_preset(task, common, "공통"))
        # 업무의 카테고리를 위에, 나머지 카테고리를 아래에 — 어떤 칸이든 불러올 수 있게.
        cats = list(task.get("categories", []))
        for c in app.category_order():
            if c not in cats:
                cats.append(c)
        for cat in cats:
            tpl = templates.get(cat)
            if not tpl:
                continue
            menu.add_separator()
            for kind in KIND_ORDER:
                texts = tpl.get(kind, [])
                if texts:
                    menu.add_command(
                        label="{} · {}".format(cat, kind),
                        command=lambda x=texts, g=cat: app.load_preset(task, x, g))

    def _render_item_block(self, item, locked=False):
        """항목 1개 + 그 하위 항목들을 하나의 블록으로 묶는다(드래그 정렬 단위).
        locked(제외)면 체크·추가·삭제는 막고 드래그 정렬만 허용한다."""
        app, task = self.app, self.task
        st = "disabled" if locked else "normal"
        block = ttk.Frame(self.frame)
        block.pack(fill="x")
        self.item_blocks[item["id"]] = block

        row = ttk.Frame(block)
        row.pack(fill="x")

        # 항목 드래그 핸들 (업무 내부 정렬) — 잠금 상태에서도 드래그는 허용
        ih = ttk.Label(row, text="↕", cursor="fleur", foreground="#bbb")
        ih.pack(side="left", padx=(2, 2))
        ih.bind("<ButtonPress-1>",
                lambda e, it=item: app._item_drag_start(e, task, it))
        ih.bind("<B1-Motion>", app._item_drag_motion)
        ih.bind("<ButtonRelease-1>", app._item_drag_end)

        var = tk.BooleanVar(value=bool(item.get("checked")))
        cb = ttk.Checkbutton(row, text=item["text"], variable=var, state=st,
                             command=lambda it=item, v=var: app.toggle_item(it, v))
        cb.pack(side="left")
        self._item_cbs[("item", item["id"])] = cb
        # +세부·✕ 는 '수정' 토글이 켜졌을 때만 보인다(평소엔 만들지 않음 → 깔끔).
        # 수정 모드 안에서는 확인창 없이 바로 처리한다(취소는 모드 종료 시 일괄 복구).
        if self.edit_mode:
            ttk.Button(row, text="✕", width=2, state=st,
                       command=lambda it=item: self.remove_item(it)
                       ).pack(side="right")
            ttk.Button(row, text="+세부", width=5, state=st,
                       command=lambda it=item: self.begin_add_subitem(it)
                       ).pack(side="right", padx=(0, 4))
            # 그룹(카테고리) 변경 드롭다운 — 고르면 해당 칸으로 항목을 옮긴다.
            cur = item.get("group", "")
            cur_label = GROUP_NONE_LABEL if cur == "" else cur
            values = [GROUP_NONE_LABEL, "공통"] + self.app.category_order()
            if cur_label not in values:          # 사용자 지정(직접 입력) 그룹 보존
                values.append(cur_label)
            gvar = tk.StringVar(value=cur_label)
            combo = ttk.Combobox(row, textvariable=gvar, values=values, width=10,
                                 state=("disabled" if locked else "readonly"))
            combo.pack(side="right", padx=(0, 4))
            combo.bind("<<ComboboxSelected>>",
                       lambda e, it=item, v=gvar: self.set_item_group(it, v.get()))

        for sub in item.get("subitems", []):
            srow = ttk.Frame(block)
            srow.pack(fill="x", padx=(28, 0))
            svar = tk.BooleanVar(value=bool(sub.get("checked")))
            scb = ttk.Checkbutton(srow, text=sub["text"], variable=svar, state=st,
                                  command=lambda s=sub, v=svar: app.toggle_subitem(s, v))
            scb.pack(side="left")
            self._item_cbs[("sub", sub["id"])] = scb
            if self.edit_mode:
                ttk.Button(srow, text="✕", width=2, state=st,
                           command=lambda it=item, s=sub: self.remove_subitem(it, s)
                           ).pack(side="right")

    # ---- 편집 모드 토글 (트랜잭션: 종료 시 저장/취소) --------------------
    def _toggle_edit(self):
        """'수정' 버튼 → 켜면 항목 편집 버튼이 보이고, 끌 때 바뀐 게 있으면
        저장/취소를 묻는다. 취소하면 진입 시점 상태로 되돌린다."""
        turning_on = bool(self.edit_var.get())
        if turning_on:
            # 진입 시점의 항목 상태를 사본으로 보관(취소 시 복구용).
            self._snapshot = {
                "items": copy.deepcopy(self.task.get("items", [])),
                "next_item_id": self.task.get("next_item_id", 1),
            }
            self.edit_mode = True
            self.rebuild()
            return

        # 편집 모드 종료
        self.edit_mode = False
        changed = (self._snapshot is not None and
                   self.task.get("items", []) != self._snapshot["items"])
        if changed:
            keep = messagebox.askyesno(
                "수정 저장", "수정한 내용을 저장하시겠습니까?", parent=self.app.root)
            if not keep:
                # 취소 → 진입 시점으로 복구
                self.task["items"] = self._snapshot["items"]
                self.task["next_item_id"] = self._snapshot["next_item_id"]
            self.app.save()
        self._snapshot = None
        self.rebuild()
        self.app._refresh_overall()

    # ---- 수정 모드 안의 항목 추가/삭제 (확인창·입력창 없이 인라인) -------
    def begin_add_item(self):
        """빈 항목을 추가하고, 그 자리에서 제목을 바로 입력하도록 한다."""
        task = self.task
        nid = self.app._new_item_id(task)
        task.setdefault("items", []).append(
            {"id": nid, "text": "", "checked": False, "group": "", "subitems": []})
        self.app.save()
        self._edit_new = ("item", nid)
        self.rebuild()

    def begin_add_subitem(self, item):
        """빈 세부 항목을 추가하고, 그 자리에서 내용을 바로 입력하도록 한다."""
        nid = self.app._new_item_id(self.task)
        item.setdefault("subitems", []).append(
            {"id": nid, "text": "", "checked": False})
        self.app.save()
        self._edit_new = ("sub", nid)
        self.rebuild()

    def set_item_group(self, item, label):
        """수정 모드 드롭다운에서 항목의 그룹(카테고리)을 변경한다.
        수정 트랜잭션(저장/취소)에 자동 포함되며, 변경 후 새 칸으로 재배치한다.
        Combobox 콜백 안에서 위젯을 재생성하면 위험하므로 rebuild 는 idle 로 미룬다."""
        new_group = "" if label == GROUP_NONE_LABEL else label
        if item.get("group", "") == new_group:
            return
        item["group"] = new_group
        self.app.save()
        self.app.root.after_idle(self.rebuild)

    def remove_item(self, item):
        self.task["items"] = [it for it in self.task.get("items", [])
                              if it is not item]
        self.app.save()
        self.rebuild()
        self.app._refresh_overall()

    def remove_subitem(self, item, sub):
        item["subitems"] = [s for s in item.get("subitems", []) if s is not sub]
        self.app.save()
        self.rebuild()
        self.app._refresh_overall()

    # ---- 새 항목 제목 인라인 입력 ----------------------------------------
    def _find_obj(self, key):
        kind, oid = key
        if kind == "item":
            return next((it for it in self.task.get("items", [])
                         if it["id"] == oid), None)
        for it in self.task.get("items", []):
            for s in it.get("subitems", []):
                if s["id"] == oid:
                    return s
        return None

    def _drop_obj(self, key):
        """빈 채로 취소된 새 항목/세부 항목을 제거한다."""
        kind, oid = key
        if kind == "item":
            self.task["items"] = [it for it in self.task.get("items", [])
                                  if it["id"] != oid]
            return
        for it in self.task.get("items", []):
            subs = it.get("subitems", [])
            if any(s["id"] == oid for s in subs):
                it["subitems"] = [s for s in subs if s["id"] != oid]
                return

    def _maybe_start_inline_edit(self):
        key = self._edit_new
        if key is None:
            return
        cb = self._item_cbs.get(key)
        if cb is None or not cb.winfo_exists():
            self._edit_new = None
            return
        row = cb.master
        row.update_idletasks()
        x, y, h = cb.winfo_x(), cb.winfo_y(), cb.winfo_height()
        entry = ttk.Entry(row, width=24)
        entry.place(x=x, y=y, height=h)
        entry.focus_set()
        done = {"closed": False}

        def commit(event=None):
            if done["closed"]:
                return
            done["closed"] = True
            val = entry.get().strip()
            entry.destroy()
            self._edit_new = None
            obj = self._find_obj(key)
            if val and obj is not None:
                obj["text"] = val
                self.app.save()
                if cb.winfo_exists():
                    cb.config(text=val)       # 체크박스 글자만 갱신(재생성 불필요)
            else:
                self._drop_obj(key)           # 빈 값 → 방금 추가한 항목 취소
                self.app.save()
                self.app.root.after_idle(self.rebuild)
            self.app._refresh_overall()

        def cancel(event=None):
            if done["closed"]:
                return
            done["closed"] = True
            entry.destroy()
            self._edit_new = None
            self._drop_obj(key)
            self.app.save()
            self.app.root.after_idle(self.rebuild)

        entry.bind("<Return>", commit)
        entry.bind("<KP_Enter>", commit)
        entry.bind("<Escape>", cancel)
        entry.bind("<FocusOut>", commit)

    # ---- 부분 갱신 (깜빡임 없음) -----------------------------------------
    def _refit_title(self, event=None):
        """라벨에 할당된 폭에 맞춰 제목을 '…'로 줄인다(폭이 좁아도 버튼 안 가림)."""
        lbl = self.title_lbl
        if lbl is None or not lbl.winfo_exists():
            return
        avail = lbl.winfo_width()
        if avail <= 1:        # 아직 배치 전 — 폭이 정해지면 Configure 가 다시 부른다.
            return
        full = self.task.get("title") or "(제목 없음)"
        # 폭·제목이 그대로면 다시 계산하지 않는다(리사이즈 중 중복 호출 방지).
        if self._last_title_fit == (avail, full):
            return
        self._last_title_fit = (avail, full)
        font = self.app.title_font
        if font.measure(full) <= avail:
            text = full
        else:
            text = full
            while text and font.measure(text + "…") > avail:
                text = text[:-1]
            text = (text + "…") if text else "…"
        if lbl.cget("text") != text:
            lbl.config(text=text)

    def update_title(self):
        if self.title_lbl is not None and self.title_lbl.winfo_exists():
            self._refit_title()

    def update_progress(self):
        if self.prog_lbl is not None and self.prog_lbl.winfo_exists():
            done, total = self.app.task_progress(self.task)
            self.prog_lbl.config(text="{}/{}".format(done, total))

    def set_priority(self, value):
        """우선순위 변경 → 배지 글자·색만 갱신(재생성 없음). 드래그 순서엔 영향 없음."""
        self.task["priority"] = value
        self.app.save()
        if self.rank_lbl is not None and self.rank_lbl.winfo_exists():
            dimmed = self.task.get("status") in STATUS_DIMMED
            self.rank_lbl.config(text=str(value), bg=self._rank_color(value, dimmed))

    def set_drag_highlight(self, on):
        """드래그 중 강조 — 테두리 두께는 그대로 두고 relief 만 바꿔 밀림 방지."""
        if self.frame is not None and self.frame.winfo_exists():
            self.frame.configure(relief="raised" if on else "solid")


# ──────────────────────────────────────────────────────────────────────────
# 5. 메인 애플리케이션
# ──────────────────────────────────────────────────────────────────────────

class ChecklistApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Check-List")
        self.root.geometry("400x460")
        # 크기 조절 허용 + 최대 크기는 '데스크톱 작업 영역'(작업 표시줄 제외)으로
        # 제한한다. 너비는 위젯 설계상 560 이하로 두되, 작업 영역보다 넓힐 수는
        # 없다. 화면보다 크게 늘리려 하면 자동으로 작업 영역 크기에 맞춰진다.
        self.root.resizable(True, True)
        self._max_w = 560            # _apply_size_limits 에서 작업 영역에 맞춰 보정
        self._max_h = self.root.winfo_screenheight()
        self._apply_size_limits()

        self.data, load_warn = load_data()
        self.save_error_shown = False
        # 글꼴/글자 크기/테마는 설정(settings)에서 읽어 적용한다. 제목 라벨용
        # 폰트(카드 공유)는 폭이 좁을 때 제목을 '…'로 줄이는 데도 쓰인다.
        ensure_settings(self.data)
        ensure_presets(self.data)
        s = self.data["settings"]
        self.font_family = s.get("font_family", DEFAULT_SETTINGS["font_family"])
        self.font_size = int(s.get("font_size", DEFAULT_SETTINGS["font_size"]))
        self.title_font = tkfont.Font(
            family=self.font_family, size=self.font_size, weight="bold")
        self._apply_fonts()
        self._apply_theme(s.get("theme", DEFAULT_SETTINGS["theme"]))
        self._geo_after = None       # 창 크기/위치 저장 디바운스 핸들
        self._drag = None            # 업무(카드) 드래그 상태
        self._item_drag = None       # 항목 드래그 상태
        self.cards = {}              # {task_id: TaskCard} — 리스트 카드 객체들
        self._width_after = None     # 폭 갱신 디바운스 핸들
        self._last_canvas_w = None
        self._scroll_after = None    # scrollregion 갱신 디바운스 핸들

        self._build_ui()
        saved_geo = self.data.get("geometry")
        if saved_geo:
            try:
                # 다른(더 큰) 모니터에서 저장된 크기/위치라도 현재 작업 영역
                # 안으로 보정해서 복원한다(화면 밖으로 나가거나 넘치지 않게).
                self.root.geometry(self._clamp_geometry(saved_geo))
            except Exception:  # noqa: BLE001
                pass
        self.apply_always_on_top()
        self.render()

        self.root.bind("<Configure>", self._on_root_configure)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        # Windows: 최대화 버튼/제목줄 더블클릭 최대화 비활성화 (크기 조절은 유지)
        self.root.after(50, self._disable_maximize)

        if load_warn and load_warn[0] == "load_corrupt":
            _, msg, backup = load_warn
            extra = ("\n손상된 파일은 다음 위치에 백업했습니다:\n{}".format(backup)
                     if backup else "")
            messagebox.showwarning(
                "데이터 복구",
                "저장 파일을 읽지 못해 빈 상태로 시작합니다.\n사유: {}{}".format(msg, extra),
            )

    # ---- 설정 / 프리셋 접근자 --------------------------------------------
    def settings(self):
        return self.data.setdefault("settings", dict(DEFAULT_SETTINGS))

    def presets(self):
        return self.data.setdefault("presets", default_presets())

    def common_items(self):
        return self.presets().setdefault("common", [])

    def category_order(self):
        return self.presets().setdefault("category_order", [])

    def category_templates(self):
        return self.presets().setdefault("categories", {})

    # ---- 글꼴 / 테마 적용 -------------------------------------------------
    def card_font(self, delta=0, bold=False):
        """카드 안의 작은 라벨/배지 폰트 — 기준 글자 크기에서 delta 만큼 조정."""
        size = max(7, self.font_size + delta)
        return (self.font_family, size, "bold") if bold else (self.font_family, size)

    def _apply_fonts(self):
        """Tk 기본 명명 폰트를 설정값으로 바꿔 ttk 위젯 전반에 글꼴을 적용한다."""
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            try:
                tkfont.nametofont(name).configure(
                    family=self.font_family, size=self.font_size)
            except Exception:  # noqa: BLE001
                pass
        try:
            self.title_font.configure(family=self.font_family, size=self.font_size)
        except Exception:  # noqa: BLE001
            pass

    def _apply_theme(self, theme):
        try:
            ttk.Style().theme_use(theme)
        except Exception:  # noqa: BLE001
            pass

    def apply_settings(self, font_family=None, font_size=None, theme=None):
        """설정 변경을 즉시 반영한다(저장 + 화면 다시 그리기)."""
        s = self.settings()
        if font_family is not None:
            s["font_family"] = self.font_family = font_family
        if font_size is not None:
            s["font_size"] = self.font_size = int(font_size)
        if theme is not None:
            s["theme"] = theme
            self._apply_theme(theme)
        if font_family is not None or font_size is not None:
            self._apply_fonts()
        self.save()
        self.render()   # 새 글꼴/테마로 카드(배지 포함)를 다시 그린다.

    def open_data_folder(self):
        """데이터 파일이 있는 폴더를 탐색기로 연다(파일 선택된 상태로)."""
        path = data_path()
        folder = os.path.dirname(path)
        try:
            if sys.platform.startswith("win"):
                # 파일이 있으면 선택해서, 없으면 폴더만 연다.
                if os.path.exists(path):
                    os.startfile(os.path.dirname(path))  # noqa: S606
                else:
                    os.startfile(folder)  # noqa: S606
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", folder])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("폴더 열기 실패",
                                 "데이터 폴더를 열지 못했습니다.\n\n{}\n\n사유: {}"
                                 .format(folder, e), parent=self.root)

    def reset_presets(self):
        """프리셋을 코드 기본값으로 되돌린다(업무/항목 데이터는 건드리지 않음)."""
        if not messagebox.askyesno(
                "프리셋 초기화",
                "편집한 프리셋을 기본값으로 되돌립니다.\n"
                "(이미 만든 업무·항목은 그대로 유지됩니다.)\n\n계속할까요?",
                parent=self.root):
            return False
        self.data["presets"] = default_presets()
        self.save()
        self.render()
        return True

    def open_settings(self):
        SettingsDialog(self)

    # ---- UI 골격 ----------------------------------------------------------
    def _build_ui(self):
        overall = ttk.Frame(self.root, padding=(8, 6))
        overall.pack(fill="x")

        # 상단 글자줄: 왼쪽 '전체 진행률' 텍스트, 오른쪽 [⚙ 설정][+ 리스트].
        # '항상 위' 토글은 [설정 → 일반 설정]으로 옮겼다.
        toprow = ttk.Frame(overall)
        toprow.pack(fill="x")
        ttk.Button(toprow, text="+ 리스트",
                   command=self.add_task).pack(side="right")
        ttk.Button(toprow, text="⚙ 설정",
                   command=self.open_settings).pack(side="right", padx=(0, 6))
        self.overall_var = tk.StringVar(value="전체 진행률  0/0  (0%)")
        ttk.Label(toprow, textvariable=self.overall_var,
                  font=("Segoe UI", 9)).pack(side="left")

        # 진행 바: 글자줄 아래, 전체 폭.
        self.overall_bar = ttk.Progressbar(overall, maximum=100)
        self.overall_bar.pack(fill="x", pady=(4, 0))

        ttk.Separator(self.root).pack(fill="x")

        container = ttk.Frame(self.root)
        container.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(container, highlightthickness=0)
        vbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vbar.set)
        vbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.body = ttk.Frame(self.canvas, padding=8)
        self.body_window = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        # 리사이즈 중 본문 Configure 가 연속으로 쏟아질 때 scrollregion 재계산을
        # 매번 하면 무겁다. 50ms로 합쳐 마지막 한 번만 계산한다(디바운스).
        self.body.bind("<Configure>", self._queue_scrollregion)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _queue_scrollregion(self, event=None):
        if self._scroll_after is not None:
            self.root.after_cancel(self._scroll_after)
        self._scroll_after = self.root.after(50, self._apply_scrollregion)

    def _apply_scrollregion(self):
        self._scroll_after = None
        try:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except Exception:  # noqa: BLE001
            pass

    def _on_canvas_configure(self, event):
        # 폭이 바뀔 때마다 본문 전체를 재배치하면 무겁다. 같은 폭이면 건너뛰고,
        # 연속된 리사이즈 이벤트는 60ms로 합쳐 재배치 횟수를 줄인다(디바운스).
        w = event.width
        if w == self._last_canvas_w:
            return
        self._last_canvas_w = w
        if self._width_after is not None:
            self.root.after_cancel(self._width_after)
        self._width_after = self.root.after(
            60, lambda: self.canvas.itemconfigure(self.body_window, width=w))

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ---- 항상 위 ----------------------------------------------------------
    def apply_always_on_top(self):
        self.root.attributes("-topmost", bool(self.data.get("always_on_top", True)))

    def set_always_on_top(self, value):
        self.data["always_on_top"] = bool(value)
        self.apply_always_on_top()
        self.save()

    def rename_category_refs(self, old, new):
        """카테고리 이름 변경 시 기존 업무들의 참조(categories·item.group)도 함께 갱신."""
        for task in self.data.get("tasks", []):
            task["categories"] = [new if c == old else c
                                  for c in task.get("categories", [])]
            for it in task.get("items", []):
                if it.get("group") == old:
                    it["group"] = new

    # ---- 창 크기 제한 (데스크톱 작업 영역) -------------------------------
    def _workarea(self):
        """작업 표시줄을 뺀 '데스크톱 작업 영역' (left, top, right, bottom).
        Windows는 SPI_GETWORKAREA로 구하고, 실패하면 전체 화면으로 폴백한다."""
        try:
            if sys.platform.startswith("win"):
                import ctypes
                from ctypes import wintypes
                rect = wintypes.RECT()
                SPI_GETWORKAREA = 0x0030
                if ctypes.windll.user32.SystemParametersInfoW(
                        SPI_GETWORKAREA, 0, ctypes.byref(rect), 0):
                    return (rect.left, rect.top, rect.right, rect.bottom)
        except Exception:  # noqa: BLE001
            pass
        return (0, 0, self.root.winfo_screenwidth(),
                self.root.winfo_screenheight())

    def _apply_size_limits(self):
        """최대 크기를 작업 영역으로 제한한다. 너비는 설계상 560을 넘지 않되,
        작업 영역이 더 좁으면 거기에 맞춘다(좁은 화면 대응). 높이는 작업 영역까지."""
        left, top, right, bottom = self._workarea()
        wa_w, wa_h = right - left, bottom - top
        self._max_w = min(560, wa_w)
        self._max_h = wa_h
        # 최소 크기가 최대보다 커지지 않도록 보정(아주 작은 화면 대응).
        self.root.minsize(min(400, self._max_w), min(360, self._max_h))
        self.root.maxsize(self._max_w, self._max_h)

    def _clamp_geometry(self, geo):
        """저장된 geometry('WxH+X+Y')를 작업 영역 안으로 보정한다(크기·위치)."""
        m = re.match(r"^(\d+)x(\d+)\+(-?\d+)\+(-?\d+)$", (geo or "").strip())
        if not m:
            return geo
        w, h, x, y = (int(v) for v in m.groups())
        left, top, right, bottom = self._workarea()
        w = max(1, min(w, self._max_w))         # 너비를 작업 영역(·560)에 맞춤
        h = max(1, min(h, self._max_h))         # 높이를 작업 영역에 맞춤
        x = max(left, min(x, right - w))        # 좌우로 화면 밖으로 나가지 않게
        y = max(top, min(y, bottom - h))        # 위아래로 화면 밖으로 나가지 않게
        return "{}x{}+{}+{}".format(w, h, x, y)

    # ---- 창 크기/위치 기억 ------------------------------------------------
    def _on_root_configure(self, event):
        if event.widget is not self.root:
            return
        self.data["geometry"] = self.root.geometry()
        if self._geo_after is not None:
            self.root.after_cancel(self._geo_after)
        self._geo_after = self.root.after(600, self.save)

    def _on_close(self):
        self.data["geometry"] = self.root.geometry()
        self.save()
        self.root.destroy()

    def _disable_maximize(self):
        """Windows에서 최대화 버튼/더블클릭 최대화만 끈다(테두리 리사이즈는 유지)."""
        try:
            import ctypes
            GWL_STYLE = -16
            WS_MAXIMIZEBOX = 0x00010000
            SWP_NOSIZE, SWP_NOMOVE = 0x0001, 0x0002
            SWP_NOZORDER, SWP_FRAMECHANGED = 0x0004, 0x0020
            user32 = ctypes.windll.user32
            hwnd = user32.GetParent(self.root.winfo_id())
            style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            user32.SetWindowLongW(hwnd, GWL_STYLE, style & ~WS_MAXIMIZEBOX)
            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                                SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_FRAMECHANGED)
        except Exception:  # noqa: BLE001
            pass

    # ---- 저장 -------------------------------------------------------------
    def save(self):
        path = data_path()
        tmp = path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
            self.save_error_shown = False
        except Exception as e:  # noqa: BLE001
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:  # noqa: BLE001
                pass
            if not self.save_error_shown:
                self.save_error_shown = True
                messagebox.showerror(
                    "저장 실패",
                    "데이터를 파일에 저장하지 못했습니다.\n"
                    "메모리의 내용은 유지되지만, 종료 시 사라질 수 있습니다.\n\n사유: {}".format(e))

    # ---- 업무 추가/수정/삭제 ---------------------------------------------
    def add_task(self):
        dlg = TaskDialog(self.root, title="리스트 추가",
                         category_order=self.category_order())
        if dlg.result is None:
            return
        name, kind, cats, count = dlg.result
        for i in range(count):
            # 개수>1이고 제목이 있으면 1,2,3 … 을 붙여 구별
            title = "{} {}".format(name, i + 1) if (count > 1 and name) else name
            # 우선순위 기본값: 생성 순서대로 1,2,3 … 4번째부터는 고정 3.
            priority = min(len(self.data["tasks"]) + 1, 3)
            self.data["tasks"].append({
                "id": self.data["next_id"],
                "title": title,
                "kind": kind,
                "categories": list(cats),
                "status": "진행",
                "collapsed": False,
                "priority": priority,
                "items": [],            # 빈 체크리스트로 시작
                "next_item_id": 1,
            })
            self.data["next_id"] += 1
        self.save()
        self.render()

    def edit_task(self, task):
        dlg = TaskDialog(
            self.root, title="리스트 수정",
            name=task.get("title", ""), kind=task.get("kind", ""),
            categories=task.get("categories", []), show_count=False,
            category_order=self.category_order())
        if dlg.result is None:
            return
        name, kind, cats, _count = dlg.result
        task["title"] = name
        task["kind"] = kind
        task["categories"] = cats  # 항목(items)은 사용자 소유이므로 건드리지 않음
        self.save()
        self._rebuild_card(task)

    def _rebuild_card(self, task):
        """카드 1개만 다시 그린다(없으면 전체 render 로 폴백)."""
        card = self.cards.get(task["id"])
        if card is not None:
            card.rebuild()
        else:
            self.render()

    def rename_task(self, task, label):
        """제목 더블클릭 → 라벨 자리에 입력창을 띄워 바로 수정 (다이얼로그 없이)."""
        header = label.master
        header.update_idletasks()
        x, y, h = label.winfo_x(), label.winfo_y(), label.winfo_height()

        entry = ttk.Entry(header, width=30, font=("Segoe UI", 10, "bold"))
        entry.insert(0, task.get("title", ""))
        entry.select_range(0, "end")
        entry.place(x=x, y=y, height=h)
        entry.focus_set()

        done = {"closed": False}

        def commit(event=None):
            if done["closed"]:
                return
            done["closed"] = True
            name = entry.get().strip()
            entry.destroy()
            if name and name != task.get("title", ""):
                task["title"] = name
                self.save()
                card = self.cards.get(task["id"])
                if card is not None:
                    card.update_title()  # 제목 라벨만 갱신 (깜빡임 없음)

        def cancel(event=None):
            if done["closed"]:
                return
            done["closed"] = True
            entry.destroy()

        entry.bind("<Return>", commit)
        entry.bind("<KP_Enter>", commit)
        entry.bind("<Escape>", cancel)
        entry.bind("<FocusOut>", commit)

    def delete_task(self, task):
        position = next((i for i, t in enumerate(self.data["tasks"], start=1)
                         if t["id"] == task["id"]), task["id"])
        label = task.get("title") or "#{}".format(position)
        if not messagebox.askyesno("리스트 삭제",
                                   "'{}' 삭제 (복구 불가)".format(label)):
            return
        self.data["tasks"] = [t for t in self.data["tasks"]
                              if t["id"] != task["id"]]
        self.save()
        self.render()

    def set_status(self, task, value):
        task["status"] = value
        # '완료'로 바꾸면 항목들을 접어 숨긴다(▶). 완료 업무는 전체 진행률에서
        # 항목 전부가 완료로 집계되므로(task_progress 참조) 펼쳐 둘 이유가 적다.
        if value == "완료":
            task["collapsed"] = True
        self.save()
        # 갱신은 메뉴가 완전히 닫힌 뒤로 미룬다. 메뉴 콜백 안에서 곧장 다시 그리면
        # 닫히는 중인 메뉴/메뉴버튼을 파괴해 Tk가 꼬이고 팅긴다.
        def apply():
            self._rebuild_card(task)   # 상태에 따라 잠금/흐림/색이 달라져 카드 재구성
            self._refresh_overall()    # 종료/제외는 전체 진행률에서 빠지므로 갱신
        self.root.after_idle(apply)

    def toggle_collapse(self, task):
        task["collapsed"] = not task.get("collapsed", False)
        self.save()
        self._rebuild_card(task)

    # ---- 항목 / 하위 항목 -------------------------------------------------
    def _new_item_id(self, task):
        nid = task.get("next_item_id", 1)
        task["next_item_id"] = nid + 1
        return nid

    # 항목 추가/삭제는 카드의 '수정' 모드 안에서 TaskCard 가 직접 처리한다
    # (begin_add_item / begin_add_subitem / remove_item / remove_subitem).

    def toggle_item(self, item, var):
        item["checked"] = bool(var.get())
        self.save()
        self._refresh_progress()

    def toggle_subitem(self, sub, var):
        sub["checked"] = bool(var.get())
        self.save()
        self._refresh_progress()

    def load_preset(self, task, texts, group=""):
        """프리셋 텍스트들을 항목으로 추가(이미 있는 텍스트는 건너뜀).
        group으로 카테고리 칸을 구분한다(여러 카테고리 프리셋을 부르면 칸이 갈림)."""
        existing = {it.get("text") for it in task.get("items", [])}
        for text in texts:
            if text in existing:
                continue
            task.setdefault("items", []).append(
                {"id": self._new_item_id(task), "text": text,
                 "checked": False, "group": group, "subitems": []})
            existing.add(text)
        self.save()
        self._rebuild_card(task)
        self._refresh_overall()

    # ---- 진행률 -----------------------------------------------------------
    @staticmethod
    def task_progress(task):
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

    def _refresh_progress(self):
        for card in self.cards.values():
            card.update_progress()
        self._refresh_overall()

    def _refresh_overall(self):
        """종료/제외 업무를 뺀 나머지 업무의 항목을 합산한 전체 진행률."""
        total_done = total_all = 0
        for task in self.data["tasks"]:
            if task.get("status") in STATUS_DIMMED:
                continue
            done, total = self.task_progress(task)
            total_done += done
            total_all += total
        pct = int(round(total_done / total_all * 100)) if total_all else 0
        self.overall_var.set("전체 진행률  {}/{}  ({}%)".format(total_done, total_all, pct))
        self.overall_bar["value"] = pct

    # ---- 렌더링 -----------------------------------------------------------
    def render(self):
        """전체 화면을 처음부터 다시 그린다. 리스트 추가/삭제처럼 카드 '구성'이
        바뀔 때만 호출한다. 카드 내부 변경(상태·제목·항목 등)은 카드 객체가
        스스로 갱신하므로 이 메서드를 거치지 않는다 → 평소엔 깜빡임이 없다."""
        for child in self.body.winfo_children():
            child.destroy()
        self.cards = {}
        self._refresh_overall()

        if not self.data["tasks"]:
            ttk.Label(self.body,
                      text="등록된 리스트 없음.\n오른쪽 위 [+ 리스트]로 추가.",
                      foreground="#777", justify="center").pack(pady=40)
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            return

        for position, task in enumerate(self.data["tasks"], start=1):
            card = TaskCard(self, task)
            card.build(position)
            self.cards[task["id"]] = card
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.root.after_idle(self._clamp_scroll)

    def _clamp_scroll(self):
        """내용이 화면에 다 들어오면 스크롤을 맨 위로 — 모두 접었을 때 위쪽
        빈 공간이 남아 카드가 아래로 쏠려 보이는 현상 방지."""
        try:
            self.canvas.update_idletasks()
            bbox = self.canvas.bbox("all")
            if bbox and (bbox[3] - bbox[1]) <= self.canvas.winfo_height():
                self.canvas.yview_moveto(0)
        except Exception:  # noqa: BLE001
            pass

    # ---- 드래그 고스트 (커서를 따라다니는 떠 있는 라벨) -------------------
    def _make_ghost(self, text, color="#d9342b"):
        g = tk.Toplevel(self.root)
        g.overrideredirect(True)
        try:
            g.attributes("-topmost", True)
            g.attributes("-alpha", 0.9)
        except Exception:  # noqa: BLE001
            pass
        tk.Label(g, text=text, bg=color, fg="white", padx=8, pady=3,
                 font=("Segoe UI", 9, "bold")).pack()
        return g

    def _move_ghost(self, ghost, event):
        if ghost is not None and ghost.winfo_exists():
            ghost.geometry("+{}+{}".format(event.x_root + 14, event.y_root + 10))

    def _kill_ghost(self, ghost):
        if ghost is not None:
            try:
                ghost.destroy()
            except Exception:  # noqa: BLE001
                pass

    # ---- 업무(카드) 드래그 정렬 ------------------------------------------
    def _drag_start(self, task):
        self._drag = {"id": task["id"]}
        card = self.cards.get(task["id"])
        if card is not None:
            card.set_drag_highlight(True)
        label = task.get("title") or "(제목 없음)"
        self._drag["ghost"] = self._make_ghost("↕  " + label)

    def _drag_motion(self, event):
        if not self._drag:
            return
        self._move_ghost(self._drag.get("ghost"), event)
        tasks = self.data["tasks"]
        drag_id = self._drag["id"]
        y = event.y_root
        others = [t["id"] for t in tasks if t["id"] != drag_id]
        target = 0
        for tid in others:
            card = self.cards.get(tid)
            if card is None or not card.frame.winfo_exists():
                continue
            if y > card.frame.winfo_rooty() + card.frame.winfo_height() / 2:
                target += 1
        new_order = others[:target] + [drag_id] + others[target:]
        if new_order != [t["id"] for t in tasks]:
            id_to_task = {t["id"]: t for t in tasks}
            self.data["tasks"] = [id_to_task[i] for i in new_order]
            for tid in new_order:
                card = self.cards.get(tid)
                if card is not None and card.frame.winfo_exists():
                    card.frame.pack_forget()
                    card.frame.pack(fill="x", pady=(0, 8))
            self.body.update_idletasks()
            # scrollregion 은 여기서 건드리지 않는다. 순서만 바뀌어 전체 높이는
            # 그대로인데, 드래그 중 매번 재설정하면 canvas 가 스크롤 위치를 보정하며
            # 위쪽에 빈칸을 만드는 현상이 생긴다(특히 위로 끌 때).

    def _drag_end(self, event):
        if not self._drag:
            return
        self._kill_ghost(self._drag.get("ghost"))
        card = self.cards.get(self._drag["id"])
        if card is not None:
            card.set_drag_highlight(False)
        self._drag = None
        self.save()
        # 정렬이 끝난 뒤 한 번만 scrollregion 재계산 + 위쪽 빈칸 방지.
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._clamp_scroll()

    # ---- 항목 드래그 정렬 (업무 내부) ------------------------------------
    def _item_drag_start(self, event, task, item):
        # 핸들 색만 강조 — 블록 크기를 바꾸지 않아 다른 항목이 밀리지 않는다.
        handle = event.widget
        self._item_drag = {"task": task, "id": item["id"], "handle": handle,
                           "ghost": self._make_ghost("↕  " + item.get("text", ""),
                                                     color="#3a6ea5")}
        try:
            handle.configure(foreground="#d9342b")
        except Exception:  # noqa: BLE001
            pass

    def _item_drag_motion(self, event):
        if not self._item_drag:
            return
        self._move_ghost(self._item_drag.get("ghost"), event)
        task = self._item_drag["task"]
        items = task.get("items", [])
        drag_id = self._item_drag["id"]
        y = event.y_root
        card = self.cards.get(task["id"])
        blocks = card.item_blocks if card is not None else {}
        others = [it["id"] for it in items if it["id"] != drag_id]
        target = 0
        for iid in others:
            block = blocks.get(iid)
            if not block or not block.winfo_exists():
                continue
            if y > block.winfo_rooty() + block.winfo_height() / 2:
                target += 1
        new_order = others[:target] + [drag_id] + others[target:]
        if new_order != [it["id"] for it in items]:
            id_to_item = {it["id"]: it for it in items}
            task["items"] = [id_to_item[i] for i in new_order]
            for iid in new_order:
                block = blocks.get(iid)
                if block and block.winfo_exists():
                    block.pack_forget()
                    block.pack(fill="x")
            self.body.update_idletasks()
            # 항목 순서만 바뀌어 전체 높이는 그대로 — scrollregion 은 건드리지 않는다
            # (드래그 중 재설정 시 위쪽 빈칸이 생기는 현상 방지).

    def _item_drag_end(self, event):
        if not self._item_drag:
            return
        self._kill_ghost(self._item_drag.get("ghost"))
        handle = self._item_drag.get("handle")
        if handle is not None:
            try:
                handle.configure(foreground="#bbb")
            except Exception:  # noqa: BLE001
                pass
        task = self._item_drag["task"]
        self._item_drag = None
        self.save()
        self._rebuild_card(task)  # 그룹(칸) 정렬을 다시 맞춤 (이 카드만)


# ──────────────────────────────────────────────────────────────────────────
# 6. 설정 다이얼로그 (일반 설정 / 프리셋 관리)
#    상단 [⚙ 설정]에서 띄운다. 변경은 즉시 데이터에 저장되고 본 화면에 반영된다.
# ──────────────────────────────────────────────────────────────────────────

COMMON_GROUP = "공통"   # 프리셋 관리 좌측 목록에서 '공통'을 가리키는 예약 이름


class SettingsDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title("설정")
        self.transient(app.root)
        self.resizable(False, False)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=(10, 6))
        general = ttk.Frame(nb, padding=12)
        presets = ttk.Frame(nb, padding=12)
        nb.add(general, text="일반 설정")
        nb.add(presets, text="프리셋 관리")
        self._build_general(general)
        self._build_presets(presets)

        ttk.Button(self, text="닫기", command=self.destroy).pack(
            side="right", padx=10, pady=(0, 10))

        self.bind("<Escape>", lambda e: self.destroy())
        # 폼 크기를 '열린 시점'의 자연 크기로 고정한다. 테마마다 위젯 여백/글꼴이
        # 달라 자동 맞춤 크기가 들쭉날쭉하므로, 고정해 두면 테마를 바꿔도(또는
        # 그룹/유형을 바꿔도) 폼이 커지거나 줄지 않는다.
        self._lock_w = self._lock_h = None
        self._lock_size()
        self._center_on(app.root)
        self.grab_set()

    def _lock_size(self):
        """현재 내용에 맞는 크기를 측정해 최소=최대=고정 크기로 못 박는다."""
        self.update_idletasks()
        self._lock_w = self.winfo_reqwidth()
        self._lock_h = self.winfo_reqheight()
        self.minsize(self._lock_w, self._lock_h)
        self.maxsize(self._lock_w, self._lock_h)
        self.geometry("{}x{}".format(self._lock_w, self._lock_h))

    def _reassert_size(self):
        """테마 변경 등으로 내용 요청 크기가 바뀌어도 고정 크기를 다시 강제한다."""
        if self._lock_w is None:
            return
        self.maxsize(self._lock_w, self._lock_h)   # 자동 확대 방지
        self.geometry("{}x{}".format(self._lock_w, self._lock_h))

    def _relock_size(self):
        """캡을 풀고 현재 내용의 자연 크기로 다시 측정해 고정한다(글자 크기 변경 등)."""
        self.minsize(1, 1)
        self.maxsize(self.winfo_screenwidth(), self.winfo_screenheight())
        self._lock_size()

    def _change_theme(self):
        """테마를 적용한 뒤 폼 크기가 따라 커지지 않도록 고정 크기를 복원한다."""
        self.app.apply_settings(theme=self.theme_var.get())
        self._reassert_size()

    def _center_on(self, master):
        self.update_idletasks()
        try:
            mx, my = master.winfo_rootx(), master.winfo_rooty()
            mw, mh = master.winfo_width(), master.winfo_height()
            w, h = self.winfo_width(), self.winfo_height()
            x = mx + (mw - w) // 2
            y = my + (mh - h) // 2
            self.geometry("+{}+{}".format(max(x, 0), max(y, 0)))
        except Exception:  # noqa: BLE001
            pass

    # ---- 일반 설정 -------------------------------------------------------
    def _build_general(self, parent):
        app = self.app

        self.aot_var = tk.BooleanVar(value=bool(app.data.get("always_on_top", True)))
        ttk.Checkbutton(parent, text="항상 위에 표시 (always on top)",
                        variable=self.aot_var,
                        command=lambda: app.set_always_on_top(self.aot_var.get())
                        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        ttk.Label(parent, text="글꼴").grid(row=1, column=0, sticky="w", pady=4)
        self.font_var = tk.StringVar(value=app.font_family)
        families = sorted(set(tkfont.families()))
        fcb = ttk.Combobox(parent, textvariable=self.font_var, values=families,
                           width=26, state="readonly")
        fcb.grid(row=1, column=1, sticky="w", pady=4)
        fcb.bind("<<ComboboxSelected>>",
                 lambda e: app.apply_settings(font_family=self.font_var.get()))

        ttk.Label(parent, text="글자 크기").grid(row=2, column=0, sticky="w", pady=4)
        self.size_var = tk.IntVar(value=app.font_size)
        sp = ttk.Spinbox(parent, from_=FONT_SIZE_MIN, to=FONT_SIZE_MAX, width=5,
                         textvariable=self.size_var, command=self._on_size)
        sp.grid(row=2, column=1, sticky="w", pady=4)
        sp.bind("<Return>", lambda e: self._on_size())
        sp.bind("<FocusOut>", lambda e: self._on_size())

        ttk.Label(parent, text="테마").grid(row=3, column=0, sticky="w", pady=4)
        self.theme_var = tk.StringVar(
            value=app.settings().get("theme", DEFAULT_SETTINGS["theme"]))
        themes = list(ttk.Style().theme_names())
        tcb = ttk.Combobox(parent, textvariable=self.theme_var, values=themes,
                           width=26, state="readonly")
        tcb.grid(row=3, column=1, sticky="w", pady=4)
        tcb.bind("<<ComboboxSelected>>", lambda e: self._change_theme())

        ttk.Separator(parent, orient="horizontal").grid(
            row=4, column=0, columnspan=2, sticky="we", pady=12)

        ttk.Button(parent, text="📂 데이터 폴더 열기", command=app.open_data_folder
                   ).grid(row=5, column=0, columnspan=2, sticky="we", pady=3)
        ttk.Button(parent, text="↺ 프리셋 기본값으로 초기화",
                   command=self._reset_presets
                   ).grid(row=6, column=0, columnspan=2, sticky="we", pady=3)

        ttk.Label(parent, foreground="#888",
                  text="데이터 파일: {}".format(os.path.basename(data_path()))
                  ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(12, 0))

    def _on_size(self):
        try:
            size = int(self.size_var.get())
        except (tk.TclError, ValueError):
            return
        size = max(FONT_SIZE_MIN, min(FONT_SIZE_MAX, size))
        if size != self.size_var.get():
            self.size_var.set(size)
        if size != self.app.font_size:
            self.app.apply_settings(font_size=size)
            # 글자 크기는 폼 크기에 실제로 영향을 주므로, 새 크기에 맞춰 다시 고정한다
            # (테마와 달리 '의도된' 크기 변화 → 1회 재맞춤 후 그 크기로 못 박음).
            self._relock_size()

    def _reset_presets(self):
        if self.app.reset_presets():
            self._reload_groups()

    # ---- 프리셋 관리 -----------------------------------------------------
    def _build_presets(self, parent):
        app = self.app
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=1)

        # 왼쪽: 그룹(공통 + 카테고리) 목록
        left = ttk.Frame(parent)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        ttk.Label(left, text="그룹", font=app.card_font(0, bold=True)).pack(anchor="w")
        self.group_list = tk.Listbox(left, height=12, width=14, exportselection=False)
        self.group_list.pack(fill="y", expand=True)
        self.group_list.bind("<<ListboxSelect>>", self._on_group_select)
        gbtns = ttk.Frame(left)
        gbtns.pack(fill="x", pady=(4, 0))
        ttk.Button(gbtns, text="+추가", width=5, command=self._add_category
                   ).pack(side="left")
        ttk.Button(gbtns, text="이름", width=4, command=self._rename_category
                   ).pack(side="left", padx=(2, 0))
        ttk.Button(gbtns, text="삭제", width=4, command=self._delete_category
                   ).pack(side="left", padx=(2, 0))

        # 오른쪽: 유형 선택 + 항목 목록 + 항목 버튼
        right = ttk.Frame(parent)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(2, weight=1)
        right.columnconfigure(0, weight=1)

        # 유형 선택 줄은 '공통'일 때도 자리를 비우지 않는다(숨기면 폼 높이가 바뀜).
        # 대신 '공통'에서는 라디오를 비활성화만 한다 → 폼 크기 고정.
        self.kind_frame = ttk.Frame(right)
        self.kind_frame.grid(row=0, column=0, sticky="w")
        self.kind_var = tk.StringVar(value=KIND_ORDER[0])
        self._kind_radios = []
        for k in KIND_ORDER:
            rb = ttk.Radiobutton(self.kind_frame, text=k, value=k,
                                 variable=self.kind_var, command=self._reload_items)
            rb.pack(side="left", padx=(0, 10))
            self._kind_radios.append(rb)

        self.items_hint = ttk.Label(right, foreground="#888", text="")
        self.items_hint.grid(row=1, column=0, sticky="w", pady=(2, 2))

        self.item_list = tk.Listbox(right, height=12, exportselection=False)
        self.item_list.grid(row=2, column=0, sticky="nsew")
        self.item_list.bind("<Double-Button-1>", lambda e: self._edit_item())

        ibtns = ttk.Frame(right)
        ibtns.grid(row=3, column=0, sticky="w", pady=(4, 0))
        ttk.Button(ibtns, text="추가", width=5, command=self._add_item
                   ).pack(side="left")
        ttk.Button(ibtns, text="수정", width=5, command=self._edit_item
                   ).pack(side="left", padx=(2, 0))
        ttk.Button(ibtns, text="삭제", width=5, command=self._delete_item
                   ).pack(side="left", padx=(2, 0))
        ttk.Button(ibtns, text="▲", width=3, command=lambda: self._move_item(-1)
                   ).pack(side="left", padx=(8, 0))
        ttk.Button(ibtns, text="▼", width=3, command=lambda: self._move_item(1)
                   ).pack(side="left", padx=(2, 0))

        self._reload_groups()

    # ---- 프리셋 관리: 상태/조회 -----------------------------------------
    def _selected_group(self):
        sel = self.group_list.curselection()
        return self.group_list.get(sel[0]) if sel else None

    def _target_list(self):
        """현재 선택된 그룹/유형이 가리키는 실제 항목 리스트(편집 대상)."""
        group = self._selected_group()
        if group is None:
            return None
        if group == COMMON_GROUP:
            return self.app.common_items()
        tpl = self.app.category_templates().get(group)
        if tpl is None:
            return None
        return tpl.setdefault(self.kind_var.get(), [])

    def _reload_groups(self, select=None):
        self.group_list.delete(0, "end")
        groups = [COMMON_GROUP] + list(self.app.category_order())
        for g in groups:
            self.group_list.insert("end", g)
        idx = groups.index(select) if (select in groups) else 0
        self.group_list.selection_clear(0, "end")
        self.group_list.selection_set(idx)
        self.group_list.see(idx)
        self._on_group_select()

    def _on_group_select(self, event=None):
        # 라디오 줄은 항상 자리에 두고 활성/비활성만 토글한다(폼 크기 고정).
        state = "disabled" if self._selected_group() == COMMON_GROUP else "normal"
        for rb in self._kind_radios:
            rb.configure(state=state)
        self._reload_items()

    def _reload_items(self, select=None):
        self.item_list.delete(0, "end")
        lst = self._target_list()
        group = self._selected_group()
        if lst is None:
            self.items_hint.config(text="")
            return
        if group == COMMON_GROUP:
            self.items_hint.config(text="공통 · 모든 업무 공용 프리셋")
        else:
            self.items_hint.config(
                text="{} · {} 프리셋".format(group, self.kind_var.get()))
        for t in lst:
            self.item_list.insert("end", t)
        if select is not None and 0 <= select < self.item_list.size():
            self.item_list.selection_clear(0, "end")
            self.item_list.selection_set(select)
            self.item_list.see(select)

    def _commit_items(self, select=None):
        """프리셋 항목 변경을 저장한다. 본 화면의 프리셋 메뉴는 열릴 때마다
        최신값으로 다시 채워지므로(postcommand) 전체 render 가 필요 없다.
        (카테고리 추가·이름변경·삭제처럼 '구조'가 바뀔 때만 render 한다.)"""
        self.app.save()
        self._reload_items(select=select)

    # ---- 프리셋 관리: 항목 편집 -----------------------------------------
    def _add_item(self):
        lst = self._target_list()
        if lst is None:
            return
        text = simpledialog.askstring("항목 추가", "추가할 항목 내용:", parent=self)
        if not text or not text.strip():
            return
        text = text.strip()
        if text in lst:
            messagebox.showinfo("중복", "이미 있는 항목입니다.", parent=self)
            return
        lst.append(text)
        self._commit_items(select=len(lst) - 1)

    def _edit_item(self):
        lst = self._target_list()
        sel = self.item_list.curselection()
        if lst is None or not sel:
            return
        idx = sel[0]
        cur = lst[idx]
        text = simpledialog.askstring("항목 수정", "항목 내용:",
                                      initialvalue=cur, parent=self)
        if text is None or not text.strip():
            return
        text = text.strip()
        if text != cur and text in lst:
            messagebox.showinfo("중복", "이미 있는 항목입니다.", parent=self)
            return
        lst[idx] = text
        self._commit_items(select=idx)

    def _delete_item(self):
        lst = self._target_list()
        sel = self.item_list.curselection()
        if lst is None or not sel:
            return
        idx = sel[0]
        del lst[idx]
        self._commit_items(select=(min(idx, len(lst) - 1) if lst else None))

    def _move_item(self, delta):
        lst = self._target_list()
        sel = self.item_list.curselection()
        if lst is None or not sel:
            return
        i = sel[0]
        j = i + delta
        if j < 0 or j >= len(lst):
            return
        lst[i], lst[j] = lst[j], lst[i]
        self._commit_items(select=j)

    # ---- 프리셋 관리: 카테고리 편집 -------------------------------------
    def _add_category(self):
        name = simpledialog.askstring("카테고리 추가", "새 카테고리 이름:", parent=self)
        if not name or not name.strip():
            return
        name = name.strip()
        if name == COMMON_GROUP:
            messagebox.showinfo("사용 불가", "'공통'은 예약된 이름입니다.", parent=self)
            return
        cats = self.app.category_templates()
        if name in cats:
            messagebox.showinfo("중복", "이미 있는 카테고리입니다.", parent=self)
            return
        cats[name] = {k: [] for k in KIND_ORDER}
        self.app.category_order().append(name)
        self.app.save()
        self.app.render()
        self._reload_groups(select=name)

    def _rename_category(self):
        group = self._selected_group()
        if group is None or group == COMMON_GROUP:
            messagebox.showinfo("안내", "이름을 바꿀 카테고리를 선택하세요.", parent=self)
            return
        new = simpledialog.askstring("카테고리 이름 변경", "새 이름:",
                                     initialvalue=group, parent=self)
        if new is None:
            return
        new = new.strip()
        if not new or new == group:
            return
        if new == COMMON_GROUP:
            messagebox.showinfo("사용 불가", "'공통'은 예약된 이름입니다.", parent=self)
            return
        cats = self.app.category_templates()
        if new in cats:
            messagebox.showinfo("중복", "이미 있는 카테고리입니다.", parent=self)
            return
        cats[new] = cats.pop(group)
        order = self.app.category_order()
        order[:] = [new if c == group else c for c in order]
        self.app.rename_category_refs(group, new)  # 기존 업무 참조도 함께 변경
        self.app.save()
        self.app.render()
        self._reload_groups(select=new)

    def _delete_category(self):
        group = self._selected_group()
        if group is None or group == COMMON_GROUP:
            messagebox.showinfo("안내",
                                "삭제할 카테고리를 선택하세요.\n('공통'은 삭제할 수 없습니다.)",
                                parent=self)
            return
        if not messagebox.askyesno(
                "카테고리 삭제",
                "'{}' 카테고리 프리셋을 삭제합니다.\n"
                "(이미 만든 업무·항목은 그대로 유지됩니다.)\n\n계속할까요?".format(group),
                parent=self):
            return
        self.app.category_templates().pop(group, None)
        order = self.app.category_order()
        order[:] = [c for c in order if c != group]
        self.app.save()
        self.app.render()
        self._reload_groups()


def main():
    root = tk.Tk()
    ChecklistApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
