"""主窗口：专利申请文件形式审核工具"""
import os
import shutil
from typing import List
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QFileDialog,
    QMessageBox, QProgressBar, QLabel, QGroupBox
)
from PyQt5.QtCore import Qt, QThread, QSettings, QStandardPaths, pyqtSignal
from app.models import DocumentModel, FormIssue
from app.core.doc_parser import parse_docx
from app.core.rule_engine import RuleEngine
from app.core.result_fusion import deduplicate_issues
from app.core.annotator import annotate_document
from app.core.model_review import ModelReviewThread
from app.llm.model_manager import model_manager
from app.ui.widgets import DropZone, ModelSwitch
from app.ui.model_download_dialog import ModelDownloadDialog
from app.utils.path_manager import PathManager


class ReviewWorker(QThread):
    """规则审核工作线程"""
    progress = pyqtSignal(int, str)
    result_ready = pyqtSignal(dict)  # {file_path: List[FormIssue]}

    def __init__(self, models: List[DocumentModel]):
        super().__init__()
        self.models = models

    def run(self):
        engine = RuleEngine()
        all_results = {}
        for idx, doc_model in enumerate(self.models):
            self.progress.emit(
                int(idx / max(len(self.models), 1) * 70),
                f"规则审核: {os.path.basename(doc_model.file_path)}"
            )
            issues = engine.run(doc_model)
            all_results[doc_model.file_path] = issues
        self.result_ready.emit(all_results)


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.file_list: List[str] = []
        self.doc_models: List[DocumentModel] = []
        self.review_results: dict = {}
        self.model_enabled = False
        self.worker: ReviewWorker = None
        self.model_review_thread: ModelReviewThread = None
        self._setup_ui()
        self._refresh_model_status_on_startup()

    def _refresh_model_status_on_startup(self):
        """启动时检测模型本地状态，刷新持久化标签"""
        if model_manager.is_model_downloaded():
            self._set_model_status("已下载 (未启用)", "downloaded")
        else:
            self._set_model_status("未下载", "disabled")

    def _setup_ui(self):
        self.setWindowTitle("专利申请文件形式审核工具")
        self.setMinimumSize(900, 650)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # 拖放区
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self._on_files_dropped)
        layout.addWidget(self.drop_zone)

        # 文件列表
        list_label = QLabel("已选文件 (可点击 [移除] 删除):")
        layout.addWidget(list_label)
        self.file_list_widget = QListWidget()
        self.file_list_widget.setMaximumHeight(110)
        layout.addWidget(self.file_list_widget)

        # 操作按钮
        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("开始审核")
        self.start_btn.clicked.connect(self._on_start_review)
        self.export_btn = QPushButton("导出文档")
        self.export_btn.clicked.connect(self._on_export)
        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self._on_clear)
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.export_btn)
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # 模型开关
        switch_row = QHBoxLayout()
        switch_row.addStretch()
        switch_label = QLabel("模型审核:")
        switch_label.setStyleSheet("font-weight: bold;")
        switch_row.addWidget(switch_label)
        self.model_switch = ModelSwitch(is_on=False)
        self.model_switch.toggled.connect(self._on_model_switch_toggled)
        switch_row.addWidget(self.model_switch)
        switch_row.addStretch()
        switch_container = QWidget()
        switch_container.setLayout(switch_row)
        layout.addWidget(switch_container)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)

        # 模型状态（持久显示在状态栏右侧）
        status_row = QHBoxLayout()
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        self.model_status_label = QLabel("模型状态: 未启用")
        self.model_status_label.setStyleSheet("color: #888; font-size: 12px;")
        status_row.addWidget(self.model_status_label)
        layout.addLayout(status_row)

        # 审核结果区
        result_group = QGroupBox("审核结果")
        result_layout = QVBoxLayout()
        self.result_list = QListWidget()
        result_layout.addWidget(self.result_list)
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

    def _on_files_dropped(self, files: List[str]):
        for f in files:
            if f not in self.file_list and f.lower().endswith(".docx"):
                self.file_list.append(f)
                self.file_list_widget.addItem(os.path.basename(f))

    def _on_model_switch_toggled(self, is_on: bool):
        if is_on:
            # 检测模型是否已下载
            if not model_manager.is_model_downloaded():
                # 弹出下载对话框
                dialog = ModelDownloadDialog(self)
                dialog.start_download()
                if dialog.exec_() == dialog.Accepted:
                    self.model_enabled = True
                    self.status_label.setText("模型下载完成，模型审核已开启")
                    self._set_model_status("已加载", "loaded")
                else:
                    self.model_switch.set_state(False)
                    self.model_enabled = False
                    self._set_model_status("未启用", "disabled")
            else:
                # 已下载，直接加载
                try:
                    self.model_switch.set_busy("加载中...")
                    self._set_model_status("加载中...", "loading")
                    self.status_label.setText("正在加载模型...")
                    from PyQt5.QtWidgets import QApplication
                    QApplication.processEvents()
                    model_manager.load_model()
                    self.model_enabled = True
                    self.model_switch.restore_from_busy()
                    self._set_model_status("已加载 (~2.5GB)", "loaded")
                    self.status_label.setText("模型已加载，模型审核已开启")
                except Exception as e:
                    QMessageBox.warning(self, "模型加载失败", str(e))
                    self.model_switch.set_state(False)
                    self.model_enabled = False
                    self._set_model_status("加载失败", "error")
        else:
            model_manager.unload_model()
            self.model_enabled = False
            self.status_label.setText("模型审核已关闭")
            self._set_model_status("未启用", "disabled")

    def _set_model_status(self, text: str, state: str):
        """更新模型状态标签的文字与颜色
        state: disabled/downloaded/loading/loaded/inferring/error
        """
        color_map = {
            "disabled": "#888",
            "downloaded": "#2196F3",
            "loading": "#FF9800",
            "loaded": "#4CAF50",
            "inferring": "#FF9800",
            "error": "#F44336",
        }
        self.model_status_label.setText(f"模型状态: {text}")
        self.model_status_label.setStyleSheet(
            f"color: {color_map.get(state, '#888')}; font-size: 12px; font-weight: bold;"
        )

    def _on_start_review(self):
        if not self.file_list:
            QMessageBox.warning(self, "提示", "请先拖入 .docx 文件")
            return

        self.start_btn.setEnabled(False)
        self.status_label.setText("正在解析文档...")
        self.progress_bar.setValue(0)
        self.result_list.clear()

        # 解析文档
        try:
            self.doc_models = []
            for f in self.file_list:
                model = parse_docx(f)
                self.doc_models.append(model)
        except Exception as e:
            QMessageBox.warning(self, "解析失败", f"文档解析失败: {e}")
            self.start_btn.setEnabled(True)
            return

        self.status_label.setText("正在执行规则审核...")
        self.worker = ReviewWorker(self.doc_models)
        self.worker.progress.connect(self._on_worker_progress)
        self.worker.result_ready.connect(self._on_worker_result)
        self.worker.start()

    def _on_worker_progress(self, percent: int, status: str):
        self.progress_bar.setValue(percent)
        self.status_label.setText(status)

    def _on_worker_result(self, results: dict):
        self.review_results = results
        self.progress_bar.setValue(70)
        self.status_label.setText("规则审核完成")

        # 如果开启了模型审核，启动模型审核
        if self.model_enabled and self.doc_models:
            self._start_model_review()
        else:
            self._display_results()
            self.progress_bar.setValue(100)
            self.status_label.setText("审核完成")
            self.start_btn.setEnabled(True)

    def _start_model_review(self):
        self.status_label.setText("正在进行模型审核...")
        self.model_switch.set_busy("推理中...")
        self._set_model_status("推理中...", "inferring")
        # 当前实现：仅对第一个文件执行模型审核
        self.model_review_thread = ModelReviewThread(
            self.doc_models[0],
            enable_fluency=True
        )
        self.model_review_thread.progress_signal.connect(
            lambda pct, s: self.progress_bar.setValue(min(70 + pct // 4, 99))
        )
        self.model_review_thread.finished_signal.connect(self._on_model_finished)
        self.model_review_thread.error_signal.connect(self._on_model_error)
        self.model_review_thread.start()

    def _on_model_finished(self, model_issues: List[FormIssue]):
        # 融合结果
        file_path = self.doc_models[0].file_path
        rule_issues = self.review_results.get(file_path, [])
        fused = deduplicate_issues(rule_issues, model_issues)
        self.review_results[file_path] = fused
        self._display_results()
        self.progress_bar.setValue(100)
        self.status_label.setText(f"审核完成（含模型增强，共发现 {len(fused)} 个问题）")
        self.model_switch.restore_from_busy()
        self._set_model_status("已加载 (~2.5GB)", "loaded")
        self.start_btn.setEnabled(True)

    def _on_model_error(self, error_msg: str):
        QMessageBox.warning(self, "模型审核失败", error_msg)
        self.model_switch.restore_from_busy()
        self._set_model_status("已加载 (~2.5GB)", "loaded")
        self._display_results()
        self.start_btn.setEnabled(True)

    def _display_results(self):
        self.result_list.clear()
        total_issues = 0
        for doc_model in self.doc_models:
            issues = self.review_results.get(doc_model.file_path, [])
            for issue in issues:
                source_label = {
                    "rule_engine": "规则",
                    "model_form": "模型-形式",
                    "model_fluency": "模型-通顺"
                }.get(issue.source.value, "未知")
                label = f"[{issue.section.value}] P{issue.range.paragraph_index+1} [{source_label}] {issue.message} ({issue.rule_id})"
                self.result_list.addItem(label)
                total_issues += 1
        if total_issues == 0:
            self.result_list.addItem("未发现问题，文档形式符合要求")

    def _on_export(self):
        if not self.review_results:
            QMessageBox.warning(self, "提示", "请先执行审核")
            return

        # 弹出目录选择对话框，让用户自定义导出位置
        # getExistingDirectory 是 Qt 跨平台 API：
        # - Windows: 调用原生 IFileDialog（资源管理器风格）
        # - macOS: 调用原生 NSOpenPanel
        # - Linux: GTK/Qt 风格
        settings = QSettings("PatentReviewTool", "MainWindow")
        # 用 QStandardPaths 跨平台获取桌面目录
        # Windows: C:\Users\<user>\Desktop
        # macOS:   /Users/<user>/Desktop
        # Linux:   /home/<user>/Desktop
        default_dir = QStandardPaths.writableLocation(QStandardPaths.DesktopLocation)
        if not default_dir or not os.path.isdir(default_dir):
            default_dir = os.path.expanduser("~")

        last_dir = settings.value("last_export_dir", default_dir)
        if not last_dir or not os.path.isdir(last_dir):
            last_dir = default_dir

        output_dir = QFileDialog.getExistingDirectory(
            self, "选择导出目录", last_dir,
            QFileDialog.ShowDirsOnly
        )
        if not output_dir:
            self.status_label.setText("已取消导出")
            return

        # 记住用户选择
        settings.setValue("last_export_dir", output_dir)
        settings.sync()

        try:
            exported_files = []
            for doc_model in self.doc_models:
                issues = self.review_results.get(doc_model.file_path, [])
                basename = os.path.basename(doc_model.file_path)
                output_path = os.path.join(output_dir, f"审核_{basename}")
                annotate_document(doc_model.file_path, output_path, issues)
                exported_files.append(output_path)
            QMessageBox.information(
                self, "导出成功",
                f"已导出 {len(exported_files)} 个文件到:\n{output_dir}\n\n"
                f"（关闭软件时不会被自动清理）"
            )
            self.status_label.setText(f"已导出 {len(exported_files)} 个文件")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", str(e))

    def _on_clear(self):
        self.file_list.clear()
        self.doc_models.clear()
        self.review_results.clear()
        self.file_list_widget.clear()
        self.result_list.clear()
        self.progress_bar.setValue(0)
        self.status_label.setText("就绪")

    def closeEvent(self, event):
        """关闭前检查是否有未导出文档"""
        if self.review_results:
            reply = QMessageBox.question(
                self, "确认退出",
                "您有待审核或未导出的文档。\n"
                "关闭软件后，cache 和 exports 目录会被自动清理。\n"
                "是否先导出文档？",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )
            if reply == QMessageBox.Save:
                self._on_export()
                self._cleanup_on_exit()
                event.accept()
            elif reply == QMessageBox.Discard:
                self._cleanup_on_exit()
                event.accept()
            else:
                event.ignore()
        else:
            self._cleanup_on_exit()
            event.accept()

    def _cleanup_on_exit(self):
        """退出时清理用户测试数据，保留已下载的模型与配置文件
        - 清理：cache/ (临时缓存) + exports/ (审核导出文件)
        - 保留：models/ (2.5GB 模型，避免重复下载) + config.json (安装目录配置)
        """
        cleaned = []
        try:
            for sub in ("cache", "exports"):
                path = PathManager.get_install_dir() + f"/{sub}"
                if os.path.exists(path):
                    shutil.rmtree(path)
                    cleaned.append(sub)
        except Exception:
            pass
        try:
            model_manager.unload_model()
        except Exception:
            pass
        if cleaned:
            print(f"[清理] 已删除: {', '.join(cleaned)}/")
