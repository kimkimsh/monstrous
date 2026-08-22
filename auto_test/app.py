#!/usr/bin/env python3
"""AI:GO 스쿼드 자동 테스트 — 문항 선택, 실행, 채점, 토큰 집계를 한 창에서.

Run with:  uv run python app.py

The window owns no run state of its own. It holds a list of Sample, a set of
checked ids, and a dict of ItemResult keyed by id; everything else is derived.
Work happens on a QThread that emits plain dataclasses, because a worker that
touches a widget does not crash where it happened, it crashes somewhere else
later.
"""
import os
import sys
import threading
from pathlib import Path

from PySide6.QtCore import (QAbstractTableModel, QModelIndex, QSortFilterProxyModel,
                            Qt, QThread, Signal)
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox,
                               QSpinBox,
                               QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QMainWindow, QMessageBox, QProgressBar,
                               QPushButton, QSplitter, QTabWidget, QTableView,
                               QTextEdit, QVBoxLayout, QWidget)

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.grading import HAVE_MATH_VERIFY
from core.runner import DISCUSSION_STRATEGIES, AigoClient
from core.samples import load_report
from core.session import (ITEM_TIMEOUT_SECONDS, MODE_AGENT, MODE_SQUAD,
                          RunLog, run_items, summarize)

ROOT = Path(__file__).resolve().parent
SAMPLE_ROOT = ROOT / "test_sample"
RUN_ROOT = ROOT / "runs"
DEFAULT_ENDPOINT = os.environ.get("BACKEND_AI_GO_ENDPOINT", "http://127.0.0.1:8001")
DEFAULT_TOKEN = os.environ.get("BACKEND_AI_GO_TOKEN", "")

TRACKS = ("math", "generic", "coding")
COLUMNS = ("문항", "트랙", "종류", "상태", "토큰 in/out", "시간", "상세")

def mono_font(size=11):
    """QFont's constructor takes one family name, not a CSS-style fallback list —
    passing "SF Mono, Menlo, monospace" asks for a family with that literal name
    and silently falls back to the UI font."""
    font = QFont()
    font.setFamilies(["SF Mono", "Menlo", "Monaco", "Courier New"])
    font.setStyleHint(QFont.Monospace)
    font.setPointSize(size)
    return font


OK_GREEN = QColor(46, 160, 67)
FAIL_RED = QColor(209, 69, 59)
MUTED = QColor(140, 140, 145)


def functional_livecodebench(sample):
    """These cannot pass locally: grade.py runs the file as a program and compares
    stdout, but a functional case carries a call argument and a return value. A
    FAIL on one of these says nothing about the answer."""
    return sample.expected.get("evaluation_mode") == "functional"


class SampleTableModel(QAbstractTableModel):
    """Rows are samples; results arrive later and are merged in by id."""

    def __init__(self, samples):
        super().__init__()
        self.mono = mono_font()
        self.samples = samples
        self.checked = set()
        self.results = {}
        self.running_id = None

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.samples)

    def columnCount(self, parent=QModelIndex()):
        return len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return COLUMNS[section]
        return None

    def flags(self, index):
        base = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        return base | Qt.ItemIsUserCheckable if index.column() == 0 else base

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        sample = self.samples[index.row()]
        result = self.results.get(sample.id)
        column = index.column()

        if role == Qt.CheckStateRole and column == 0:
            return Qt.Checked if sample.id in self.checked else Qt.Unchecked

        if role == Qt.DisplayRole:
            if column == 0:
                return sample.id
            if column == 1:
                return sample.track
            if column == 2:
                if not sample.gradable:
                    return f"{sample.kind} · 채점 불가"
                if functional_livecodebench(sample):
                    return f"{sample.kind} · functional"
                return sample.kind
            if column == 3:
                if sample.id == self.running_id:
                    return "실행 중…"
                return result.label if result else "대기"
            if column == 4 and result:
                return f"{result.prompt_tokens or 0:,} / {result.completion_tokens or 0:,}"
            if column == 5 and result:
                return f"{result.seconds:.1f}s"
            if column == 6 and result:
                return result.detail
            return ""

        if role == Qt.ForegroundRole and result and column == 3:
            if result.status in ("error", "no_reply", "cancelled") or not result.gradable:
                return MUTED
            if result.outcome == "extraction_failed" or result.correct is False:
                return FAIL_RED
            if result.correct:
                return OK_GREEN

        if role == Qt.FontRole and column in (0, 4, 5):
            return self.mono
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.CheckStateRole and index.column() == 0:
            sample_id = self.samples[index.row()].id
            if Qt.CheckState(value) == Qt.Checked:
                self.checked.add(sample_id)
            else:
                self.checked.discard(sample_id)
            self.dataChanged.emit(index, index, [Qt.CheckStateRole])
            return True
        return False

    def set_checked(self, ids, checked):
        if checked:
            self.checked |= set(ids)
        else:
            self.checked -= set(ids)
        self.refresh_all()

    def apply_result(self, result):
        self.running_id = None
        self.results[result.item_id] = result
        self.refresh_row(result.item_id)

    def mark_running(self, sample_id):
        previous, self.running_id = self.running_id, sample_id
        for changed in (previous, sample_id):
            if changed:
                self.refresh_row(changed)

    def refresh_row(self, sample_id):
        for row, sample in enumerate(self.samples):
            if sample.id == sample_id:
                self.dataChanged.emit(self.index(row, 0),
                                      self.index(row, len(COLUMNS) - 1))
                return

    def refresh_all(self):
        if self.samples:
            self.dataChanged.emit(self.index(0, 0),
                                  self.index(len(self.samples) - 1, len(COLUMNS) - 1))

    def clear_results(self):
        self.results.clear()
        self.running_id = None
        self.refresh_all()


class TrackFilter(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.tracks = set(TRACKS)
        self.needle = ""

    def set_tracks(self, tracks):
        self.tracks = set(tracks)
        self.invalidateFilter()

    def set_needle(self, needle):
        self.needle = needle.strip().lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, row, parent):
        sample = self.sourceModel().samples[row]
        if sample.track not in self.tracks:
            return False
        return not self.needle or self.needle in sample.id.lower()


class RunWorker(QThread):
    """Emits data only. Every widget touch happens on the main thread."""

    started_item = Signal(object)
    finished_item = Signal(object)
    run_done = Signal(object, object)   # results, run_log_path
    failed = Signal(str)

    def __init__(self, client, squad_id, agent_id, model_id, samples,
                 mode, turn_budget, strategy, conclude):
        super().__init__()
        self.client = client
        self.squad_id = squad_id
        self.agent_id = agent_id
        self.model_id = model_id
        self.samples = samples
        self.mode = mode
        self.turn_budget = turn_budget
        self.strategy = strategy
        self.conclude = conclude
        self.cancel = threading.Event()

    def run(self):
        run_log = RunLog(RUN_ROOT)
        try:
            results = run_items(
                self.client, self.squad_id, self.agent_id, self.model_id,
                self.samples, mode=self.mode, turn_budget=self.turn_budget,
                strategy=self.strategy, conclude=self.conclude,
                run_log=run_log, cancel=self.cancel,
                on_start=self.started_item.emit, on_finish=self.finished_item.emit,
            )
            self.run_done.emit(results, run_log.path)
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        finally:
            run_log.close()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI:GO Auto Test")
        self.resize(1180, 800)

        self.client = None
        self.worker = None
        self.load_errors = []

        report = load_report(SAMPLE_ROOT)
        self.load_errors = report.errors
        self.model = SampleTableModel(report.samples)
        self.proxy = TrackFilter()
        self.proxy.setSourceModel(self.model)

        self._build()
        self._wire()
        self._refresh_counts()
        self.log(f"샘플 {len(report.samples)}개 로드"
                 f"{f' · 실패 {len(report.errors)}개' if report.errors else ''}"
                 f" · math_verify {'사용' if HAVE_MATH_VERIFY else '없음 (근사 채점)'}")

    # ---------- layout ----------

    def _build(self):
        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(10)

        outer.addWidget(self._connection_box())
        outer.addWidget(self._filter_box())

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self._table_box())
        splitter.addWidget(self._detail_box())
        splitter.setSizes([460, 260])
        outer.addWidget(splitter, 1)

        outer.addWidget(self._action_box())
        self.setCentralWidget(central)
        self.statusBar().showMessage("준비됨")

    def _connection_box(self):
        box = QFrame()
        box.setFrameShape(QFrame.StyledPanel)
        grid = QGridLayout(box)
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setHorizontalSpacing(10)

        self.endpoint_edit = QLineEdit(DEFAULT_ENDPOINT)
        self.token_edit = QLineEdit(DEFAULT_TOKEN)
        self.token_edit.setEchoMode(QLineEdit.Password)
        self.connect_button = QPushButton("연결")
        self.health_label = QLabel("연결 안 됨")
        self.health_label.setStyleSheet("color: #8c8c91;")

        self.squad_combo = QComboBox()
        self.squad_combo.setMinimumWidth(280)
        self.agent_combo = QComboBox()
        self.agent_combo.setMinimumWidth(280)
        self.model_label = QLabel("—")
        self.model_label.setStyleSheet("color: #8c8c91;")

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("스쿼드 전체 (discussion room)", MODE_SQUAD)
        self.mode_combo.addItem("단일 에이전트 (스쿼드 테스트 아님)", MODE_AGENT)
        self.strategy_combo = QComboBox()
        for name in DISCUSSION_STRATEGIES:
            self.strategy_combo.addItem(name, name)
        self.strategy_combo.setToolTip(
            "roundRobin 과 brainstorm 은 발언자를 코드로 정한다 (LLM 호출 0).\n"
            "moderated 는 3턴마다 합의 게이트를, autonomous 는 턴마다 참여자 수만큼\n"
            "LLM을 더 부른다 — 토큰이 늘고 발언 순서가 모델 판단에 의존한다.")
        self.turns_spin = QSpinBox()
        self.turns_spin.setRange(1, 100)
        self.turns_spin.setValue(3)
        self.turns_spin.setSuffix(" 턴")
        self.conclude_check = QCheckBox("결론 합성")
        self.conclude_check.setChecked(True)
        self.conclude_check.setToolTip(
            "대화가 끝난 뒤 사회자 역할 에이전트가 대화록을 요약한다.\n"
            "LLM 호출이 한 번 더 붙고, 그 토큰도 집계에 포함된다.")

        grid.addWidget(QLabel("Endpoint"), 0, 0)
        grid.addWidget(self.endpoint_edit, 0, 1)
        grid.addWidget(QLabel("Token"), 0, 2)
        grid.addWidget(self.token_edit, 0, 3)
        grid.addWidget(self.connect_button, 0, 4)
        grid.addWidget(self.health_label, 0, 5)
        grid.addWidget(QLabel("Squad"), 1, 0)
        grid.addWidget(self.squad_combo, 1, 1)
        grid.addWidget(QLabel("Agent"), 1, 2)
        grid.addWidget(self.agent_combo, 1, 3)
        grid.addWidget(self.model_label, 1, 4, 1, 2)

        mode_row = QHBoxLayout()
        mode_row.setContentsMargins(0, 0, 0, 0)
        mode_row.addWidget(QLabel("실행 방식"))
        mode_row.addWidget(self.mode_combo)
        mode_row.addSpacing(12)
        mode_row.addWidget(QLabel("발언 전략"))
        mode_row.addWidget(self.strategy_combo)
        mode_row.addWidget(QLabel("턴 예산"))
        mode_row.addWidget(self.turns_spin)
        mode_row.addWidget(self.conclude_check)
        mode_row.addStretch(1)
        holder = QWidget()
        holder.setLayout(mode_row)
        grid.addWidget(holder, 2, 0, 1, 6)

        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        return box

    def _filter_box(self):
        box = QWidget()
        row = QHBoxLayout(box)
        row.setContentsMargins(0, 0, 0, 0)
        self.track_boxes = {}
        for track in TRACKS:
            check = QCheckBox(track)
            check.setChecked(True)
            self.track_boxes[track] = check
            row.addWidget(check)
        row.addSpacing(16)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("문항 id 검색")
        self.search_edit.setMaximumWidth(240)
        row.addWidget(self.search_edit)
        row.addStretch(1)
        self.select_all_button = QPushButton("보이는 것 전체 선택")
        self.select_none_button = QPushButton("선택 해제")
        row.addWidget(self.select_all_button)
        row.addWidget(self.select_none_button)
        return box

    def _table_box(self):
        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.resizeSection(0, 300)
        for column in (1, 2, 3, 4, 5):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        return self.table

    def _detail_box(self):
        self.tabs = QTabWidget()
        self.prompt_view = QTextEdit(readOnly=True)
        self.output_view = QTextEdit(readOnly=True)
        self.grade_view = QTextEdit(readOnly=True)
        for view in (self.prompt_view, self.output_view, self.grade_view):
            view.setFont(mono_font())
            view.setLineWrapMode(QTextEdit.WidgetWidth)
        self.tabs.addTab(self.prompt_view, "프롬프트")
        self.tabs.addTab(self.output_view, "모델 출력")
        self.tabs.addTab(self.grade_view, "채점 · 로그")
        return self.tabs

    def _action_box(self):
        box = QWidget()
        row = QHBoxLayout(box)
        row.setContentsMargins(0, 0, 0, 0)
        self.check_button = QPushButton("검사")
        self.run_button = QPushButton("실행")
        self.stop_button = QPushButton("중지")
        self.stop_button.setEnabled(False)
        self.run_button.setDefault(True)
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setMaximumWidth(240)
        self.summary_label = QLabel("선택 0개")
        self.summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        row.addWidget(self.check_button)
        row.addWidget(self.run_button)
        row.addWidget(self.stop_button)
        row.addWidget(self.progress)
        row.addSpacing(12)
        row.addWidget(self.summary_label, 1)
        return box

    # ---------- wiring ----------

    def _wire(self):
        self.connect_button.clicked.connect(self.on_connect)
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        self.squad_combo.currentIndexChanged.connect(self.on_squad_changed)
        self.agent_combo.currentIndexChanged.connect(self.on_agent_changed)
        self.search_edit.textChanged.connect(self.proxy.set_needle)
        for track, box in self.track_boxes.items():
            box.toggled.connect(self.on_track_toggled)
        self.select_all_button.clicked.connect(lambda: self.set_visible_checked(True))
        self.select_none_button.clicked.connect(lambda: self.set_visible_checked(False))
        self.model.dataChanged.connect(lambda *_: self._refresh_counts())
        self.table.selectionModel().selectionChanged.connect(self.on_row_selected)
        self.check_button.clicked.connect(self.on_check)
        self.run_button.clicked.connect(self.on_run)
        self.stop_button.clicked.connect(self.on_stop)

    def on_mode_changed(self):
        squad_mode = self.mode_combo.currentData() == MODE_SQUAD
        self.strategy_combo.setEnabled(squad_mode)
        self.turns_spin.setEnabled(squad_mode)
        self.conclude_check.setEnabled(squad_mode)
        self.agent_combo.setEnabled(not squad_mode)
        self._refresh_counts()

    def on_track_toggled(self):
        self.proxy.set_tracks({t for t, b in self.track_boxes.items() if b.isChecked()})
        self._refresh_counts()

    def set_visible_checked(self, checked):
        ids = [self.proxy.index(row, 0).data() for row in range(self.proxy.rowCount())]
        self.model.set_checked(ids, checked)
        self._refresh_counts()

    def selected_samples(self):
        return [s for s in self.model.samples if s.id in self.model.checked]

    def current_sample(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        source = self.proxy.mapToSource(rows[0])
        return self.model.samples[source.row()]

    def on_row_selected(self, *_):
        sample = self.current_sample()
        if sample is None:
            return
        self.prompt_view.setPlainText(sample.prompt)
        result = self.model.results.get(sample.id)
        self.output_view.setPlainText(result.output if result else "(아직 실행 안 함)")
        if result:
            lines = [f"결과      {result.label}",
                     f"outcome   {result.outcome}",
                     f"상세      {result.detail}",
                     f"토큰      {result.prompt_tokens} in / {result.completion_tokens} out",
                     f"시간      {result.seconds:.1f}s",
                     f"방식      {result.mode}"]
            if result.mode == MODE_SQUAD:
                lines.append(f"토론방    {result.discussion_id}  ({result.turns}턴)")
                lines.append("발언 순서 " + " → ".join(s[-7:] for s in result.speakers))
            else:
                lines.append(f"에이전트  {result.agent_id}")
            lines.append(f"모델      {result.model_id}")
            if result.error:
                lines.append(f"오류      {result.error}")
        else:
            lines = [f"정답 규격 {sample.expected}"]
            if not sample.gradable:
                lines.append(f"채점 불가 {sample.ungradable_reason}")
        self.grade_view.setPlainText("\n".join(lines))

    # ---------- connection ----------

    def on_connect(self):
        endpoint = self.endpoint_edit.text().strip()
        token = self.token_edit.text().strip()
        if not endpoint:
            self.warn("Endpoint를 입력해라.")
            return
        client = AigoClient(endpoint, token)
        try:
            health = client.health()
            squads = client.squads()
        except Exception as exc:
            self.client = None
            self.health_label.setText("연결 실패")
            self.health_label.setStyleSheet(f"color: {FAIL_RED.name()};")
            self.log(f"연결 실패 — {type(exc).__name__}: {exc}")
            return

        self.client = client
        status = health.get("status", "?")
        parts = health.get("components", {})
        down = [k for k, v in parts.items() if v is False]
        colour = OK_GREEN if status == "healthy" else FAIL_RED
        self.health_label.setText(status + (f" ({', '.join(down)} down)" if down else ""))
        self.health_label.setStyleSheet(f"color: {colour.name()};")

        self.squad_combo.blockSignals(True)
        self.squad_combo.clear()
        for squad in squads:
            self.squad_combo.addItem(f"{squad.name}  ({squad.agent_count} agents)", squad.id)
        self.squad_combo.blockSignals(False)
        self.log(f"연결됨 — 스쿼드 {len(squads)}개")
        self.on_squad_changed()

    def on_squad_changed(self):
        squad_id = self.squad_combo.currentData()
        self.agent_combo.clear()
        if not (self.client and squad_id):
            return
        try:
            agents = self.client.agents(squad_id)
        except Exception as exc:
            self.log(f"에이전트 목록 실패 — {exc}")
            return
        for agent in agents:
            self.agent_combo.addItem(f"{agent.name}  ({agent.role})", agent)
        self.on_agent_changed()

    def on_agent_changed(self):
        agent = self.agent_combo.currentData()
        self.model_label.setText(f"model  {agent.model_id}" if agent else "—")

    # ---------- check ----------

    def on_check(self):
        selected = self.selected_samples()
        lines = ["=== 검사 ==="]
        ok = True

        for path, problems in self.load_errors:
            ok = False
            lines.append(f"샘플 로드 실패  {path.name}: {'; '.join(problems)}")
        lines.append(f"샘플            {len(self.model.samples)}개 로드, "
                     f"로드 실패 {len(self.load_errors)}개")
        lines.append(f"math_verify     {'사용 가능' if HAVE_MATH_VERIFY else '없음 — 근사 채점, 동치형을 틀렸다고 셀 수 있다'}")

        if self.client is None:
            ok = False
            lines.append("서버            연결 안 됨 — [연결]을 먼저 눌러라")
        else:
            try:
                health = self.client.health()
                down = [k for k, v in health.get("components", {}).items() if v is False]
                lines.append(f"서버            {health.get('status')}"
                             + (f" — {', '.join(down)} 죽음" if down else ""))
                if down:
                    ok = False
                models = self.client.loaded_models()
                lines.append(f"로드된 모델     {', '.join(models) if models else '없음'}")
                agent = self.agent_combo.currentData()
                if agent and models and agent.model_id not in models:
                    ok = False
                    lines.append(f"경고            에이전트 모델 {agent.model_id} 이(가) "
                                 f"로드 목록에 없다")
            except Exception as exc:
                ok = False
                lines.append(f"서버            확인 실패 — {exc}")

        if not self.squad_combo.currentData():
            ok = False
            lines.append("스쿼드          선택 안 됨")
        if not self.agent_combo.currentData():
            ok = False
            lines.append("에이전트        선택 안 됨")

        lines.append(f"선택 문항       {len(selected)}개")
        if not selected:
            ok = False
            lines.append("                하나도 선택 안 됐다")
        ungradable = [s for s in selected if not s.gradable]
        functional = [s for s in selected if s.gradable and functional_livecodebench(s)]
        if ungradable:
            lines.append(f"채점 불가       {len(ungradable)}개 (swebench) — 실행은 되고 "
                         f"토큰은 집계되지만 정답 판정은 안 된다")
        if functional:
            lines.append(f"주의            {len(functional)}개는 livecodebench functional "
                         f"모드다. 로컬 채점기가 stdout으로 비교해서 답이 맞아도 FAIL로 "
                         f"나온다 — 이 항목의 FAIL은 믿지 마라")
        squad_mode = self.mode_combo.currentData() == MODE_SQUAD
        per_item = 28 * self.turns_spin.value() if squad_mode else 12
        est = len(selected) * per_item
        lines.append(f"실행 방식       {'스쿼드 전체 (discussion)' if squad_mode else '단일 에이전트'}"
                     + (f" · {self.strategy_combo.currentData()} · "
                        f"{self.turns_spin.value()}턴" if squad_mode else ""))
        if squad_mode and self.strategy_combo.currentData() in ("moderated", "autonomous"):
            lines.append("주의            이 전략은 발언자 선정에도 LLM을 쓴다. 토큰이 늘고, "
                         "발언 순서가 매번 달라져서 프롬프트 변경 효과와 구분이 안 된다")
        lines.append(f"예상 소요       약 {est // 60}분 {est % 60}초 "
                     f"(문항당 {per_item}초 가정)")
        lines.append("")
        lines.append("통과" if ok else "위 항목을 먼저 해결해라")

        self.grade_view.setPlainText("\n".join(lines))
        self.tabs.setCurrentWidget(self.grade_view)
        self.statusBar().showMessage("검사 통과" if ok else "검사 — 문제 있음")

    # ---------- run ----------

    def on_run(self):
        if self.worker is not None:
            return
        if self.client is None:
            self.warn("먼저 서버에 연결해라.")
            return
        squad_id = self.squad_combo.currentData()
        agent = self.agent_combo.currentData()
        squad_mode = self.mode_combo.currentData() == MODE_SQUAD
        if not squad_id:
            self.warn("스쿼드를 선택해라.")
            return
        if not squad_mode and not agent:
            self.warn("단일 에이전트 방식에서는 에이전트를 선택해야 한다.")
            return
        selected = self.selected_samples()
        if not selected:
            self.warn("실행할 문항을 선택해라.")
            return

        self.model.clear_results()
        self.progress.setRange(0, len(selected))
        self.progress.setValue(0)
        self.progress.setFormat(f"%v / {len(selected)}")
        self.run_button.setEnabled(False)
        self.check_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.statusBar().showMessage(f"{len(selected)}개 실행 중")

        self.worker = RunWorker(
            self.client, squad_id, agent.id if agent else "",
            agent.model_id if agent else "", selected,
            self.mode_combo.currentData(), self.turns_spin.value(),
            self.strategy_combo.currentData(), self.conclude_check.isChecked())
        self.worker.started_item.connect(lambda s: self.model.mark_running(s.id))
        self.worker.finished_item.connect(self.on_item_finished)
        self.worker.run_done.connect(self.on_run_done)
        self.worker.failed.connect(self.on_run_failed)
        self.worker.start()

    def on_item_finished(self, result):
        self.model.apply_result(result)
        self.progress.setValue(self.progress.value() + 1)
        self._refresh_summary()

    def on_run_done(self, results, log_path):
        self._reset_buttons()
        self._refresh_summary()
        self.log(f"실행 끝 — {len(results)}개 · 저장 {log_path}")
        self.statusBar().showMessage(f"끝. 결과 저장: {log_path.name}")

    def on_run_failed(self, message):
        self._reset_buttons()
        self.log(f"실행이 예외로 멈췄다 — {message}")
        self.warn(f"실행 중 예외:\n{message}")

    def on_stop(self):
        if self.worker is None:
            return
        self.worker.cancel.set()
        self.stop_button.setEnabled(False)
        self.statusBar().showMessage(
            f"중지 요청됨 — 진행 중인 문항이 끝나면 멈춘다 (최대 {int(ITEM_TIMEOUT_SECONDS/5)}초)")

    def _reset_buttons(self):
        self.worker = None
        self.run_button.setEnabled(True)
        self.check_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    # ---------- summary ----------

    def _refresh_counts(self):
        checked = len(self.model.checked)
        visible = self.proxy.rowCount()
        self.summary_label.setText(f"선택 {checked}개 · 화면에 {visible}개")

    def _refresh_summary(self):
        results = list(self.model.results.values())
        if not results:
            self._refresh_counts()
            return
        agg = summarize(results)
        accuracy = f"{agg.accuracy:.1%}" if agg.accuracy is not None else "—"
        text = (f"채점 {agg.correct}/{agg.scored} · 정확도 {accuracy}"
                f" · 채점 불가 {agg.ungradable} · 실행 실패 {agg.failed}"
                f" · 토큰 {agg.total_tokens:,} (in {agg.prompt_tokens:,} /"
                f" out {agg.completion_tokens:,}) · {agg.seconds:.1f}s")
        if agg.mixed_conditions:
            text += "  ⚠ 조건이 섞였다 (스쿼드/에이전트/모델)"
        self.summary_label.setText(text)

    # ---------- misc ----------

    def log(self, message):
        self.grade_view.append(message)
        self.statusBar().showMessage(message, 6000)

    def warn(self, message):
        QMessageBox.warning(self, "AI:GO Auto Test", message)

    def closeEvent(self, event):
        if self.worker is not None:
            self.worker.cancel.set()
            self.worker.wait(3000)
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AI:GO Auto Test")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
