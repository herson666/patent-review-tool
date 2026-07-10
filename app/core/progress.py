"""审核进度信号管理（跨线程推送 GUI 更新）"""
from PyQt5.QtCore import QObject, pyqtSignal


class ProgressSignal(QObject):
    """审核进度信号"""
    progress_updated = pyqtSignal(int, str)   # (percent, status_text)
    stage_changed = pyqtSignal(str)            # 阶段名称变更
    log_message = pyqtSignal(str)              # 日志信息

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


def emit_progress(percent: int, status: str = ""):
    """触发进度更新信号"""
    ProgressSignal.get_instance().progress_updated.emit(percent, status)


def emit_stage(stage_name: str):
    """触发阶段变更信号"""
    ProgressSignal.get_instance().stage_changed.emit(stage_name)


def emit_log(message: str):
    """触发日志信号"""
    ProgressSignal.get_instance().log_message.emit(message)
