import sys
import os

_DLL_HANDLES = []


def _prepare_qt_dll_paths():
    if os.name != "nt" or not hasattr(os, "add_dll_directory"):
        return

    try:
        import PySide6
        import shiboken6
    except ImportError:
        return

    for package in (PySide6, shiboken6):
        package_dir = os.path.dirname(package.__file__)
        if os.path.isdir(package_dir):
            _DLL_HANDLES.append(os.add_dll_directory(package_dir))


def main():
    _prepare_qt_dll_paths()

    from PySide6.QtWidgets import QApplication

    from .main_window import MainWindow

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
