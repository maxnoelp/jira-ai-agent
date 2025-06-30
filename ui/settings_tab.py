from PySide6.QtCore import QSettings, Slot
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QFormLayout,
)


class SettingsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("PrinzCodeAgent")
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        self.jira_url = QLineEdit()
        self.jira_email = QLineEdit()
        self.jira_token = QLineEdit()
        self.openai_key = QLineEdit()
        save_btn = QPushButton("Speichern")
        save_btn.clicked.connect(self._save_settings)

        form = QFormLayout(self)
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(24)
        form.setContentsMargins(24, 24, 24, 24)

        form.addRow("Jira-URL:", self.jira_url)
        form.addRow("Jira-Email:", self.jira_email)
        form.addRow("Jira-Token:", self.jira_token)
        form.addRow("OpenAI API-Key:", self.openai_key)
        form.addRow(QLabel(), save_btn)

    def _load_settings(self):
        self.jira_url.setText(self.settings.value("jira/url", ""))
        self.jira_email.setText(self.settings.value("jira/email", ""))
        self.jira_token.setText(self.settings.value("jira/token", ""))
        self.openai_key.setText(self.settings.value("openai/key", ""))

    @Slot()
    def _save_settings(self):
        self.settings.setValue("jira/url", self.jira_url.text())
        self.settings.setValue("jira/email", self.jira_email.text())
        self.settings.setValue("jira/token", self.jira_token.text())
        self.settings.setValue("openai/key", self.openai_key.text())
        self.settings.sync()
        QMessageBox.information(
            self, "Gespeichert", "Jira-Einstellungen wurden gespeichert."
        )
