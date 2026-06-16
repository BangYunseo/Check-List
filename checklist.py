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

import json
import os
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
# 1. 프리셋 정의 (선택적으로 불러오는 기본 항목 목록)
#    여기만 고치면 [프리셋 불러오기]에 반영된다. 새 업무는 기본적으로 비어 있다.
# ──────────────────────────────────────────────────────────────────────────

# 공통 프리셋 — 어떤 업무든 공통으로 쓸 만한 기본 항목
COMMON_ITEMS = [
    "요구사항 확인",
    "프로젝트 모델 확인",
    "주석 작성",
    "빌드 확인",
]

# 카테고리별 {초기개발, 유지보수} 프리셋
CATEGORY_TEMPLATES = {
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
CATEGORY_ORDER = ["화면개발", "DB작업", "API작업", "테스트",
                  "배포/운영", "문서화", "버그수정", "리팩토링", "기타"]
KIND_ORDER = ["초기개발", "유지보수"]
STATUS_ORDER = ["진행", "완료", "중단", "종료", "제외"]
NONE_LABEL = "(없음)"  # 카테고리 드롭다운의 '선택 안 함' 항목

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
DATA_VERSION = 2


def data_path():
    """프로그램과 같은 폴더에 데이터 파일을 둔다."""
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, DATA_FILENAME)


def default_data():
    return {"version": DATA_VERSION, "next_id": 1, "always_on_top": True,
            "geometry": None, "tasks": []}


def _legacy_auto_texts(categories):
    """v1 데이터 복원용: 옛 카테고리에서 공통+개발+수정 항목 텍스트를 순서대로."""
    texts = []
    seen = set()
    for t in COMMON_ITEMS:
        if t not in seen:
            texts.append(t)
            seen.add(t)
    for cat in CATEGORY_ORDER:
        if cat not in categories:
            continue
        tpl = CATEGORY_TEMPLATES.get(cat, {})
        for kind in KIND_ORDER:
            for t in tpl.get(kind, []):
                if t not in seen:
                    texts.append(t)
                    seen.add(t)
    return texts


def ensure_task_fields(task):
    """업무 한 건의 필드를 v2 구조로 보정한다(필요 시 v1 → v2 마이그레이션)."""
    task.setdefault("title", task.pop("subtitle", ""))  # subtitle → title
    task.setdefault("kind", "")
    task.setdefault("categories", [])
    task.setdefault("status", "진행")
    task.setdefault("collapsed", False)

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
        for task in data["tasks"]:
            ensure_task_fields(task)
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
                 categories=None, show_count=True):
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.transient(master)
        self.show_count = show_count
        self.result = None  # (name, kind, [categories], count) or None

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
        is_custom = bool(cur_cat) and cur_cat not in CATEGORY_ORDER
        self.cat_var = tk.StringVar(
            value=("기타" if is_custom else (cur_cat or NONE_LABEL)))
        self.cat_cb = ttk.Combobox(row5, textvariable=self.cat_var, state="readonly",
                                   width=12, values=[NONE_LABEL] + CATEGORY_ORDER)
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
    def _rank_color(position, dimmed):
        if dimmed:
            return "#9aa0a6"
        return {1: "#d9342b", 2: "#e8821e", 3: "#caa200"}.get(position, "#9aa0a6")

    def _populate(self, position):
        self.position = position
        app, task = self.app, self.task

        header = ttk.Frame(self.frame)
        header.pack(fill="x")

        # 업무 드래그 핸들 (우선순위 정렬)
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
        # 위로 끌수록 높은 우선순위. 상위 3개를 색 배지로 구분.
        self.rank_lbl = tk.Label(header, text=str(position),
                                 bg=self._rank_color(position, dimmed), fg="white",
                                 font=("Segoe UI", 9, "bold"), padx=6)
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
        status = task.get("status", "진행")
        smb = tk.Menubutton(header, text=status,
                            bg=STATUS_COLORS.get(status, "#666"),
                            fg="white", font=("Segoe UI", 8, "bold"),
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
                      font=("Segoe UI", 8)).pack(side="right", padx=(6, 0))

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
                   command=lambda: app.add_item(task)).pack(side="left")
        self._build_preset_menu(controls, locked)

        items = task.setdefault("items", [])
        if not items:
            ttk.Label(self.frame, text="항목 없음 — [+ 항목] 또는 [프리셋 불러오기]",
                      foreground="#999").pack(anchor="w", padx=(4, 0), pady=(2, 0))
            return

        # 카테고리(group)별로 묶어서 표시. 그룹이 2개 이상일 때만 칸 헤더를 보인다
        # (단일 카테고리/자유 항목이면 헤더 없이 평탄하게).
        def group_rank(g):
            if g == "공통":
                return (0, 0)
            if g in CATEGORY_ORDER:
                return (1, CATEGORY_ORDER.index(g))
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
                          font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(6, 1))
            for item in [it for it in items if it.get("group", "") == g]:
                self._render_item_block(item, locked)

    def _build_preset_menu(self, parent, locked=False):
        app, task = self.app, self.task
        mb = ttk.Menubutton(parent, text="프리셋 불러오기 ▾",
                            state=("disabled" if locked else "normal"))
        menu = tk.Menu(mb, tearoff=0)
        menu.add_command(
            label="공통",
            command=lambda: app.load_preset(task, COMMON_ITEMS, "공통"))
        # 업무의 카테고리를 위에, 나머지 카테고리를 아래에 — 어떤 칸이든 불러올 수 있게.
        cats = list(task.get("categories", []))
        for c in CATEGORY_ORDER:
            if c not in cats:
                cats.append(c)
        for cat in cats:
            tpl = CATEGORY_TEMPLATES.get(cat)
            if not tpl:
                continue
            menu.add_separator()
            for kind in KIND_ORDER:
                texts = tpl.get(kind, [])
                if texts:
                    menu.add_command(
                        label="{} · {}".format(cat, kind),
                        command=lambda x=texts, g=cat: app.load_preset(task, x, g))
        mb["menu"] = menu
        mb.pack(side="left", padx=(6, 0))

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
        ttk.Checkbutton(row, text=item["text"], variable=var, state=st,
                        command=lambda it=item, v=var: app.toggle_item(it, v)
                        ).pack(side="left")
        ttk.Button(row, text="✕", width=2, state=st,
                   command=lambda it=item: app.delete_item(task, it)
                   ).pack(side="right")
        ttk.Button(row, text="+세부", width=5, state=st,
                   command=lambda it=item: app.add_subitem(task, it)
                   ).pack(side="right", padx=(0, 4))

        for sub in item.get("subitems", []):
            srow = ttk.Frame(block)
            srow.pack(fill="x", padx=(28, 0))
            svar = tk.BooleanVar(value=bool(sub.get("checked")))
            ttk.Checkbutton(srow, text=sub["text"], variable=svar, state=st,
                            command=lambda s=sub, v=svar: app.toggle_subitem(s, v)
                            ).pack(side="left")
            ttk.Button(srow, text="✕", width=2, state=st,
                       command=lambda it=item, s=sub: app.delete_subitem(task, it, s)
                       ).pack(side="right")

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

    def update_position(self, position):
        """드래그 정렬 후 순위 배지(#N·색)만 갱신."""
        self.position = position
        if self.rank_lbl is not None and self.rank_lbl.winfo_exists():
            dimmed = self.task.get("status") in STATUS_DIMMED
            self.rank_lbl.config(text=str(position),
                                 bg=self._rank_color(position, dimmed))

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
        # 크기 조절 허용 + 너비는 최소/최대로 제한(너무 넓어지지 않게).
        # 최소 너비는 헤더 버튼들이 가려지지 않을 만큼 확보한다(너무 좁히면 잘림).
        # 높이는 항목이 많아질 수 있으니 화면 높이까지 허용.
        self.root.resizable(True, True)
        self.root.minsize(400, 360)
        self.root.maxsize(560, self.root.winfo_screenheight())
        # 제목 라벨 폭 측정용 폰트(같은 글꼴을 카드들이 공유) — 폭이 좁으면 제목을
        # '…'로 줄여 버튼을 밀어내지 않게 한다.
        self.title_font = tkfont.Font(family="Segoe UI", size=10, weight="bold")

        self.data, load_warn = load_data()
        self.save_error_shown = False
        self._geo_after = None       # 창 크기/위치 저장 디바운스 핸들
        self._drag = None            # 업무(카드) 드래그 상태
        self._item_drag = None       # 항목 드래그 상태
        self.cards = {}              # {task_id: TaskCard} — 리스트 카드 객체들
        self._width_after = None     # 폭 갱신 디바운스 핸들
        self._last_canvas_w = None

        self._build_ui()
        saved_geo = self.data.get("geometry")
        if saved_geo:
            try:
                self.root.geometry(saved_geo)
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

    # ---- UI 골격 ----------------------------------------------------------
    def _build_ui(self):
        # 전체 진행률 행: 왼쪽엔 진행률 텍스트+바, 오른쪽엔 [항상 위][+ 리스트].
        overall = ttk.Frame(self.root, padding=(8, 6))
        overall.pack(fill="x")

        # 오른쪽 컨트롤 (먼저 pack 해야 왼쪽 영역이 남은 폭을 채운다)
        controls = ttk.Frame(overall)
        controls.pack(side="right", padx=(8, 0))
        ttk.Button(controls, text="+ 리스트",
                   command=self.add_task).pack(side="right")
        self.top_var = tk.BooleanVar(value=bool(self.data.get("always_on_top", True)))
        ttk.Checkbutton(controls, text="항상 위", variable=self.top_var,
                        command=self.toggle_always_on_top).pack(side="right", padx=(0, 8))

        # 왼쪽 진행률 영역 (텍스트 위, 바 아래)
        meter = ttk.Frame(overall)
        meter.pack(side="left", fill="x", expand=True)
        self.overall_var = tk.StringVar(value="전체 진행률  0/0  (0%)")
        ttk.Label(meter, textvariable=self.overall_var,
                  font=("Segoe UI", 9)).pack(anchor="w")
        self.overall_bar = ttk.Progressbar(meter, maximum=100)
        self.overall_bar.pack(fill="x", pady=(2, 0))

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
        self.body.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

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

    def toggle_always_on_top(self):
        self.data["always_on_top"] = bool(self.top_var.get())
        self.apply_always_on_top()
        self.save()

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
        dlg = TaskDialog(self.root, title="리스트 추가")
        if dlg.result is None:
            return
        name, kind, cats, count = dlg.result
        for i in range(count):
            # 개수>1이고 제목이 있으면 1,2,3 … 을 붙여 구별
            title = "{} {}".format(name, i + 1) if (count > 1 and name) else name
            self.data["tasks"].append({
                "id": self.data["next_id"],
                "title": title,
                "kind": kind,
                "categories": list(cats),
                "status": "진행",
                "collapsed": False,
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
            categories=task.get("categories", []), show_count=False)
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

    def add_item(self, task):
        text = simpledialog.askstring("항목 추가", "항목 내용:", parent=self.root)
        if not text or not text.strip():
            return
        task.setdefault("items", []).append(
            {"id": self._new_item_id(task), "text": text.strip(),
             "checked": False, "group": "", "subitems": []})
        self.save()
        self._rebuild_card(task)
        self._refresh_overall()

    def add_subitem(self, task, item):
        text = simpledialog.askstring("세부 항목 추가", "세부 내용:", parent=self.root)
        if not text or not text.strip():
            return
        item.setdefault("subitems", []).append(
            {"id": self._new_item_id(task), "text": text.strip(), "checked": False})
        self.save()
        self._rebuild_card(task)
        self._refresh_overall()

    def delete_item(self, task, item):
        if not messagebox.askyesno("항목 삭제",
                                   "'{}' 삭제 (복구 불가)".format(item["text"])):
            return
        task["items"] = [it for it in task.get("items", []) if it is not item]
        self.save()
        self._rebuild_card(task)
        self._refresh_overall()

    def delete_subitem(self, task, item, sub):
        if not messagebox.askyesno("세부 항목 삭제",
                                   "'{}' 삭제 (복구 불가)".format(sub["text"])):
            return
        item["subitems"] = [s for s in item.get("subitems", []) if s is not sub]
        self.save()
        self._rebuild_card(task)
        self._refresh_overall()

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

    def _reindex(self):
        """드래그 정렬 뒤, 각 카드의 순위 배지(#N·색)만 갱신한다(재생성 없음)."""
        for position, task in enumerate(self.data["tasks"], start=1):
            card = self.cards.get(task["id"])
            if card is not None:
                card.update_position(position)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

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
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _drag_end(self, event):
        if not self._drag:
            return
        self._kill_ghost(self._drag.get("ghost"))
        card = self.cards.get(self._drag["id"])
        if card is not None:
            card.set_drag_highlight(False)
        self._drag = None
        self.save()
        self._reindex()  # 표시 번호(#N)·우선순위 색만 갱신 (전체 재생성 없음)

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
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

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


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except Exception:  # noqa: BLE001
        pass
    ChecklistApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
