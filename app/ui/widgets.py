"""自定义 UI 控件：拖放区、模型开关"""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QDragEnterEvent, QDropEvent


class DropZone(QWidget):
    """拖放区域控件 - 接受 .docx 文件拖入"""
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)
        self._setup_ui()

    def _setup_ui(self):
        frame = QFrame(self)
        frame.setObjectName("dropZoneFrame")
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet("""
            QFrame#dropZoneFrame {
                border: 2px dashed #aaa;
                border-radius: 8px;
                background: #f9f9f9;
            }
            QFrame#dropZoneFrame:hover {
                border-color: #4a90e2;
                background: #f0f6ff;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(frame)

        frame_layout = QVBoxLayout(frame)
        self.label = QLabel("拖入 .docx 文件到这里\n（或点击选择文件）", frame)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: #666; font-size: 14px;")
        frame_layout.addWidget(self.label)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path and path.lower().endswith(".docx"):
                files.append(path)
        if files:
            self.files_dropped.emit(files)
            event.acceptProposedAction()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            from PyQt5.QtWidgets import QFileDialog
            files, _ = QFileDialog.getOpenFileNames(
                self, "选择 .docx 文件", "",
                "Word Documents (*.docx)"
            )
            if files:
                self.files_dropped.emit(files)


class ModelSwitch(QWidget):
    """
    模型审核开关控件。
    OFF 状态 → 按钮文本 "开启模型审核"，蓝色
    ON 状态  → 按钮文本 "关闭模型审核"，绿色
    """
    toggled = pyqtSignal(bool)  # True=开启, False=关闭

    def __init__(self, is_on: bool = False, parent=None):
        super().__init__(parent)
        self._is_on = is_on
        self._setup_ui()
        self._update_style()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.btn = QPushButton(self)
        self.btn.setCheckable(True)
        self.btn.setChecked(self._is_on)
        self.btn.setFixedSize(220, 40)
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.clicked.connect(self._on_clicked)
        layout.addStretch()
        layout.addWidget(self.btn)
        layout.addStretch()

    def _on_clicked(self):
        self._is_on = self.btn.isChecked()
        self._update_style()
        self.toggled.emit(self._is_on)

    def _update_style(self):
        if self._is_on:
            self.btn.setText("关闭模型审核")
            self.btn.setStyleSheet(
                "QPushButton { background-color: #4CAF50; color: white; "
                "border: none; padding: 8px 16px; border-radius: 4px; "
                "font-size: 14px; font-weight: bold; }"
                "QPushButton:hover { background-color: #45A049; }"
            )
        else:
            self.btn.setText("开启模型审核")
            self.btn.setStyleSheet(
                "QPushButton { background-color: #2196F3; color: white; "
                "border: none; padding: 8px 16px; border-radius: 4px; "
                "font-size: 14px; font-weight: bold; }"
                "QPushButton:hover { background-color: #1976D2; }"
            )

    def set_state(self, is_on: bool):
        """编程方式设置开关状态"""
        self._is_on = is_on
        self.btn.setChecked(is_on)
        self._update_style()

    def is_on(self) -> bool:
        return self._is_on

    def set_busy(self, text: str):
        """设置中间态（加载中 / 推理中），按钮禁用并显示中性色"""
        self.btn.setEnabled(False)
        self.btn.setText(text)
        self.btn.setStyleSheet(
            "QPushButton { background-color: #9E9E9E; color: white; "
            "border: none; padding: 8px 16px; border-radius: 4px; "
            "font-size: 14px; font-weight: bold; }"
            "QPushButton:disabled { background-color: #9E9E9E; color: #EEE; }"
        )

    def restore_from_busy(self):
        """从中间态恢复到正常 ON/OFF 状态"""
        self.btn.setEnabled(True)
        self._update_style()
