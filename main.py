from PySide6.QtWidgets import QApplication
from ui.ui import MainWindow
import sys
import dotenv

dotenv.load_dotenv()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
