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
# 4. 메인 애플리케이션
# ──────────────────────────────────────────────────────────────────────────

class ChecklistApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Check-List")
        self.root.geometry("360x460")
        # 크기 조절 허용 + 너비는 최소/최대로 제한(너무 넓어지지 않게).
        # 높이는 항목이 많아질 수 있으니 화면 높이까지 허용.
        self.root.resizable(True, True)
        self.root.minsize(320, 360)
        self.root.maxsize(560, self.root.winfo_screenheight())

        self.data, load_warn = load_data()
        self.save_error_shown = False
        self._geo_after = None       # 창 크기/위치 저장 디바운스 핸들
        self._drag = None            # 업무(카드) 드래그 상태
        self._item_drag = None       # 항목 드래그 상태
        self._card_widgets = {}      # {task_id: card Frame}
        self._item_blocks = {}       # {(task_id, item_id): block Frame}
        self._progress_labels = {}
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
        toolbar = ttk.Frame(self.root, padding=(8, 6))
        toolbar.pack(fill="x")

        ttk.Button(toolbar, text="+ 리스트", command=self.add_task).pack(side="right")
        self.top_var = tk.BooleanVar(value=bool(self.data.get("always_on_top", True)))
        ttk.Checkbutton(toolbar, text="항상 위", variable=self.top_var,
                        command=self.toggle_always_on_top).pack(side="right", padx=(0, 8))

        ttk.Separator(self.root).pack(fill="x")

        overall = ttk.Frame(self.root, padding=(8, 4))
        overall.pack(fill="x")
        self.overall_var = tk.StringVar(value="전체 진행률  0/0  (0%)")
        ttk.Label(overall, textvariable=self.overall_var,
                  font=("Segoe UI", 9)).pack(anchor="w")
        self.overall_bar = ttk.Progressbar(overall, maximum=100)
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
        self.render()

    def rename_task(self, task):
        """제목 더블클릭 → 이름만 바로 수정."""
        name = simpledialog.askstring("제목 수정", "제목:", parent=self.root,
                                      initialvalue=task.get("title", ""))
        if name is None:
            return
        task["title"] = name.strip()
        self.save()
        self.render()

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
        # 렌더는 메뉴가 완전히 닫힌 뒤로 미룬다. 메뉴 콜백 안에서 곧장 render()를
        # 호출하면 닫히는 중인 메뉴/메뉴버튼을 파괴해 Tk가 꼬이고 팅긴다.
        self.root.after_idle(self.render)

    def toggle_collapse(self, task):
        task["collapsed"] = not task.get("collapsed", False)
        self.save()
        self.render()

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
        self.render()

    def add_subitem(self, task, item):
        text = simpledialog.askstring("세부 항목 추가", "세부 내용:", parent=self.root)
        if not text or not text.strip():
            return
        item.setdefault("subitems", []).append(
            {"id": self._new_item_id(task), "text": text.strip(), "checked": False})
        self.save()
        self.render()

    def delete_item(self, task, item):
        if not messagebox.askyesno("항목 삭제",
                                   "'{}' 삭제 (복구 불가)".format(item["text"])):
            return
        task["items"] = [it for it in task.get("items", []) if it is not item]
        self.save()
        self.render()

    def delete_subitem(self, item, sub):
        if not messagebox.askyesno("세부 항목 삭제",
                                   "'{}' 삭제 (복구 불가)".format(sub["text"])):
            return
        item["subitems"] = [s for s in item.get("subitems", []) if s is not sub]
        self.save()
        self.render()

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
        self.render()

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
        for task in self.data["tasks"]:
            lbl = self._progress_labels.get(task["id"])
            if lbl is not None:
                done, total = self.task_progress(task)
                lbl.config(text="{}/{}".format(done, total))
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
        for child in self.body.winfo_children():
            child.destroy()
        self._progress_labels = {}
        self._card_widgets = {}
        self._item_blocks = {}
        self._refresh_overall()

        if not self.data["tasks"]:
            ttk.Label(self.body,
                      text="등록된 리스트 없음.\n오른쪽 위 [+ 리스트]로 추가.",
                      foreground="#777", justify="center").pack(pady=40)
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            return

        for position, task in enumerate(self.data["tasks"], start=1):
            self._render_task(task, position)
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

    def _render_task(self, task, position):
        card = ttk.Frame(self.body, relief="solid", borderwidth=1, padding=6)
        card.pack(fill="x", pady=(0, 8))
        self._card_widgets[task["id"]] = card

        header = ttk.Frame(card)
        header.pack(fill="x")

        # 업무 드래그 핸들 (우선순위 정렬)
        handle = ttk.Label(header, text="↕", cursor="fleur", foreground="#999")
        handle.pack(side="left", padx=(0, 2))
        handle.bind("<ButtonPress-1>", lambda e, t=task: self._drag_start(t))
        handle.bind("<B1-Motion>", self._drag_motion)
        handle.bind("<ButtonRelease-1>", self._drag_end)

        arrow = "▶" if task.get("collapsed") else "▼"
        ttk.Button(header, text=arrow, width=2,
                   command=lambda t=task: self.toggle_collapse(t)).pack(side="left")

        dimmed = task.get("status") in STATUS_DIMMED
        # '제외'면 잠금: 상태 변경과 드래그만 허용하고 내부 편집은 전부 막는다.
        locked = task.get("status") == "제외"
        # 위로 끌수록 높은 우선순위. 상위 3개를 색 배지로 구분.
        rank_color = ("#9aa0a6" if dimmed else
                      {1: "#d9342b", 2: "#e8821e", 3: "#caa200"}.get(position, "#9aa0a6"))
        tk.Label(header, text=str(position), bg=rank_color, fg="white",
                 font=("Segoe UI", 9, "bold"), padx=6).pack(side="left", padx=(6, 4))
        title_lbl = ttk.Label(header, text=task.get("title") or "(제목 없음)",
                              font=("Segoe UI", 10, "bold"), cursor="hand2",
                              foreground=("#999" if dimmed else "#000"))
        title_lbl.pack(side="left")
        # 제목 더블클릭 → 이름 바로 수정 (잠금 시 비활성)
        if not locked:
            title_lbl.bind("<Double-Button-1>", lambda e, t=task: self.rename_task(t))
        if task.get("kind"):
            ttk.Label(header, text=task["kind"],
                      foreground=KIND_COLORS.get(task["kind"], "#666"),
                      font=("Segoe UI", 8)).pack(side="left", padx=(6, 0))

        # 오른쪽: 삭제 / 수정 / 상태 / 진행률
        ttk.Button(header, text="🗑", width=3,
                   command=lambda t=task: self.delete_task(t)).pack(side="right")
        ttk.Button(header, text="✎", width=3,
                   state=("disabled" if locked else "normal"),
                   command=lambda t=task: self.edit_task(t)).pack(side="right", padx=(0, 4))
        status = task.get("status", "진행")
        smb = tk.Menubutton(header, text=status, bg=STATUS_COLORS.get(status, "#666"),
                            fg="white", font=("Segoe UI", 8, "bold"),
                            relief="raised", padx=6, takefocus=0)
        smenu = tk.Menu(smb, tearoff=0)
        for s in STATUS_ORDER:
            smenu.add_command(label=s, foreground=STATUS_COLORS.get(s, "#000"),
                              command=lambda t=task, val=s: self.set_status(t, val))
        smb["menu"] = smenu
        smb.pack(side="right", padx=(0, 6))
        done, total = self.task_progress(task)
        prog = ttk.Label(header, text="{}/{}".format(done, total), foreground="#555")
        prog.pack(side="right", padx=(0, 8))
        self._progress_labels[task["id"]] = prog

        if task.get("collapsed"):
            return

        # 본문 컨트롤: 항목 추가 + 프리셋 불러오기
        controls = ttk.Frame(card)
        controls.pack(fill="x", pady=(6, 2))
        ttk.Button(controls, text="+ 항목",
                   state=("disabled" if locked else "normal"),
                   command=lambda t=task: self.add_item(t)).pack(side="left")
        self._build_preset_menu(controls, task, locked)

        items = task.setdefault("items", [])
        if not items:
            ttk.Label(card, text="항목 없음 — [+ 항목] 또는 [프리셋 불러오기]",
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
                ttk.Label(card, text=label, foreground="#3a6ea5",
                          font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(6, 1))
            for item in [it for it in items if it.get("group", "") == g]:
                self._render_item_block(card, task, item, locked)

    def _build_preset_menu(self, parent, task, locked=False):
        mb = ttk.Menubutton(parent, text="프리셋 불러오기 ▾",
                            state=("disabled" if locked else "normal"))
        menu = tk.Menu(mb, tearoff=0)
        menu.add_command(
            label="공통",
            command=lambda t=task: self.load_preset(t, COMMON_ITEMS, "공통"))
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
                        command=lambda t=task, x=texts, g=cat: self.load_preset(t, x, g))
        mb["menu"] = menu
        mb.pack(side="left", padx=(6, 0))

    def _render_item_block(self, card, task, item, locked=False):
        """항목 1개 + 그 하위 항목들을 하나의 블록으로 묶는다(드래그 정렬 단위).
        locked(제외)면 체크·추가·삭제는 막고 드래그 정렬만 허용한다."""
        st = "disabled" if locked else "normal"
        block = ttk.Frame(card)
        block.pack(fill="x")
        self._item_blocks[(task["id"], item["id"])] = block

        row = ttk.Frame(block)
        row.pack(fill="x")

        # 항목 드래그 핸들 (업무 내부 정렬) — 잠금 상태에서도 드래그는 허용
        ih = ttk.Label(row, text="↕", cursor="fleur", foreground="#bbb")
        ih.pack(side="left", padx=(2, 2))
        ih.bind("<ButtonPress-1>",
                lambda e, t=task, it=item: self._item_drag_start(e, t, it))
        ih.bind("<B1-Motion>", self._item_drag_motion)
        ih.bind("<ButtonRelease-1>", self._item_drag_end)

        var = tk.BooleanVar(value=bool(item.get("checked")))
        ttk.Checkbutton(row, text=item["text"], variable=var, state=st,
                        command=lambda it=item, v=var: self.toggle_item(it, v)
                        ).pack(side="left")
        ttk.Button(row, text="✕", width=2, state=st,
                   command=lambda t=task, it=item: self.delete_item(t, it)
                   ).pack(side="right")
        ttk.Button(row, text="+세부", width=5, state=st,
                   command=lambda t=task, it=item: self.add_subitem(t, it)
                   ).pack(side="right", padx=(0, 4))

        for sub in item.get("subitems", []):
            srow = ttk.Frame(block)
            srow.pack(fill="x", padx=(28, 0))
            svar = tk.BooleanVar(value=bool(sub.get("checked")))
            ttk.Checkbutton(srow, text=sub["text"], variable=svar, state=st,
                            command=lambda s=sub, v=svar: self.toggle_subitem(s, v)
                            ).pack(side="left")
            ttk.Button(srow, text="✕", width=2, state=st,
                       command=lambda it=item, s=sub: self.delete_subitem(it, s)
                       ).pack(side="right")

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
        card = self._card_widgets.get(task["id"])
        if card and card.winfo_exists():
            # 테두리 두께는 그대로 두고 relief만 바꿔 강조(크기 변화로 밀림 방지).
            card.configure(relief="raised")
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
            card = self._card_widgets.get(tid)
            if not card or not card.winfo_exists():
                continue
            if y > card.winfo_rooty() + card.winfo_height() / 2:
                target += 1
        new_order = others[:target] + [drag_id] + others[target:]
        if new_order != [t["id"] for t in tasks]:
            id_to_task = {t["id"]: t for t in tasks}
            self.data["tasks"] = [id_to_task[i] for i in new_order]
            for tid in new_order:
                card = self._card_widgets.get(tid)
                if card and card.winfo_exists():
                    card.pack_forget()
                    card.pack(fill="x", pady=(0, 8))
            self.body.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _drag_end(self, event):
        if not self._drag:
            return
        self._kill_ghost(self._drag.get("ghost"))
        card = self._card_widgets.get(self._drag["id"])
        if card and card.winfo_exists():
            card.configure(relief="solid")
        self._drag = None
        self.save()
        self.render()  # 표시 번호(#N)·우선순위 색 재계산

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
        others = [it["id"] for it in items if it["id"] != drag_id]
        target = 0
        for iid in others:
            block = self._item_blocks.get((task["id"], iid))
            if not block or not block.winfo_exists():
                continue
            if y > block.winfo_rooty() + block.winfo_height() / 2:
                target += 1
        new_order = others[:target] + [drag_id] + others[target:]
        if new_order != [it["id"] for it in items]:
            id_to_item = {it["id"]: it for it in items}
            task["items"] = [id_to_item[i] for i in new_order]
            for iid in new_order:
                block = self._item_blocks.get((task["id"], iid))
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
        self._item_drag = None
        self.save()
        self.render()  # 그룹(칸) 정렬을 다시 맞춤


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
