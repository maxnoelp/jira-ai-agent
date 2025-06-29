from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox


class ProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Neues Jira-Projekt anlegen")
        v = QVBoxLayout(self)
        v.addWidget(QLabel("Projektname"))
        self.name_edit = QLineEdit()
        v.addWidget(self.name_edit)

        v.addWidget(QLabel("Projekt-Key (2-10 Großbuchstaben)"))
        self.key_edit = QLineEdit()
        v.addWidget(self.key_edit)

        btn = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn.accepted.connect(self.accept)
        btn.rejected.connect(self.reject)
        v.addWidget(btn)

    def values(self):
        return self.name_edit.text().strip(), self.key_edit.text().strip().upper()
