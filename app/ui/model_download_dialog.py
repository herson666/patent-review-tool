"""模型下载进度对话框"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from app.llm.model_manager import model_manager


class DownloadThread(QThread):
    """模型下载线程"""
    progress = pyqtSignal(int, float)  # percent, speed_mbps
    finished = pyqtSignal(bool, str)   # success, error_msg

    def __init__(self):
        super().__init__()
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            def cancel_flag():
                return self._cancelled

            model_manager.download_model(
                progress_callback=lambda pct, spd: self.progress.emit(pct, spd),
                cancel_flag=cancel_flag
            )
            if self._cancelled:
                self.finished.emit(False, "已取消下载")
            else:
                self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))


class ModelDownloadDialog(QDialog):
    """模型下载进度对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.download_thread = None
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("正在下载模型")
        self.setFixedSize(480, 280)
        self.setModal(True)
        layout = QVBoxLayout(self)

        self.title_label = QLabel("正在下载 Qwen3-4B-Instruct-Q4_K_M.gguf")
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.title_label)

        self.size_label = QLabel("预计大小: 约 2.5 GB")
        layout.addWidget(self.size_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("已下载: 0.0 GB / 2.5 GB")
        layout.addWidget(self.status_label)

        self.speed_label = QLabel("速度: -- MB/s")
        layout.addWidget(self.speed_label)

        self.remain_label = QLabel("预计剩余: 计算中...")
        layout.addWidget(self.remain_label)

        self.cancel_btn = QPushButton("取消下载")
        self.cancel_btn.clicked.connect(self._on_cancel)
        layout.addWidget(self.cancel_btn)

    def start_download(self):
        self.download_thread = DownloadThread()
        self.download_thread.progress.connect(self._on_progress)
        self.download_thread.finished.connect(self._on_finished)
        self.download_thread.start()

    def _on_progress(self, percent: int, speed_mbps: float):
        self.progress_bar.setValue(percent)
        downloaded_gb = percent / 100 * 2.5
        self.status_label.setText(f"已下载: {downloaded_gb:.1f} GB / 2.5 GB")
        self.speed_label.setText(f"速度: {speed_mbps:.1f} MB/s")
        if speed_mbps > 0:
            remaining_gb = (100 - percent) / 100 * 2.5
            remaining_sec = int(remaining_gb * 1024 / speed_mbps)
            mins, secs = remaining_sec // 60, remaining_sec % 60
            self.remain_label.setText(f"预计剩余: {mins} 分 {secs} 秒")

    def _on_finished(self, success: bool, error_msg: str):
        if success:
            self.accept()
        else:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "下载失败", f"模型下载失败: {error_msg}")
            self.reject()

    def _on_cancel(self):
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.cancel()
            self.download_thread.quit()
            self.download_thread.wait(3000)
        self.reject()

    def closeEvent(self, event):
        """关闭对话框时取消下载"""
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.cancel()
            self.download_thread.quit()
            self.download_thread.wait(3000)
        super().closeEvent(event)
