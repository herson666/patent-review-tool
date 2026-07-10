import sys
from PyQt5.QtWidgets import QApplication
from app.ui.main_window import MainWindow
from app.utils.path_manager import PathManager


def main():
    PathManager.ensure_dirs()
    app = QApplication(sys.argv)
    app.setApplicationName("专利申请文件形式审核工具")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
