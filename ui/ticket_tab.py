# ticket_tab.py
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QComboBox,
    QTextEdit,
    QPushButton,
    QMessageBox,
)
from PySide6.QtCore import Slot, QEvent
from jira_client import get_jira, ensure_board, add_issue_to_sprint, create_story


class TicketTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.current_sprint_id = None
        self._projects_loaded = False

    def showEvent(self, event: QEvent):
        super().showEvent(event)
        # Beim ersten Anzeigen des Tabs Projekte laden
        if not self._projects_loaded:
            self.load_projects()

    def _setup_ui(self):
        l = QVBoxLayout(self)  # noqa: E741

        # Dropdown, um ein Projekt auszuwählen
        l.addWidget(QLabel("Jira-Projekt auswählen:"))
        self.project_cb = QComboBox()
        l.addWidget(self.project_cb)

        # Button, um die aktuellen Sprints zu laden
        self.load_btn = QPushButton("Sprints laden")
        self.load_btn.clicked.connect(self.load_sprints)
        l.addWidget(self.load_btn)

        # Dropdown, um den aktiven Sprint auszuwählen
        l.addWidget(QLabel("Sprint auswählen:"))
        self.sprint_cb = QComboBox()
        l.addWidget(self.sprint_cb)

        # Freitext für AI-Ticketbeschreibung
        l.addWidget(QLabel("Ticket-Inhalt (AI-Prompt):"))
        self.prompt_te = QTextEdit()
        l.addWidget(self.prompt_te, stretch=1)

        # Erstellen-Button
        self.create_btn = QPushButton("Ticket erstellen")
        self.create_btn.clicked.connect(self.on_create_ticket)
        l.addWidget(self.create_btn)

    def load_projects(self):
        """
        Lädt alle Jira-Projekte einmalig in das Dropdown.
        """
        try:
            jira = get_jira()
        except Exception:
            QMessageBox.warning(
                self,
                "Jira-Einstellungen fehlen",
                "Bitte in den Einstellungen Jira-URL, Email und Token speichern.",
            )
            return

        # Nur einmal laden
        if self._projects_loaded:
            return

        for project in jira.projects():
            self.project_cb.addItem(f"{project.key} – {project.name}", project.key)
        self._projects_loaded = True

    def load_sprints(self):
        """Sprints des ausgewählten Projekts laden."""
        try:
            jira = get_jira()
        except Exception:
            QMessageBox.warning(
                self,
                "Jira-Einstellungen fehlen",
                "Bitte in den Einstellungen Jira-URL, Email und Token speichern.",
            )
            return

        self.load_projects()

        project_key = self.project_cb.currentData()
        if not project_key:
            QMessageBox.warning(self, "Fehler", "Bitte zuerst ein Projekt auswählen.")
            return

        project_key = self.project_cb.currentData()
        board = ensure_board(jira, project_key)
        sprints = jira.sprints(board)
        self.sprint_cb.clear()
        for s in sprints:
            if s.state in ("active", "future"):
                self.sprint_cb.addItem(f"{s.name} [{s.state}]", s.id)

    @Slot()
    def on_create_ticket(self):
        project_key = self.project_cb.currentData()
        sprint_id = self.sprint_cb.currentData()
        prompt = self.prompt_te.toPlainText().strip()
        if not all([project_key, sprint_id, prompt]):
            QMessageBox.warning(
                self, "Fehler", "Projekt, Sprint und Prompt müssen ausgewählt sein."
            )
            return

        from ai import generate_ticket_content

        result = generate_ticket_content(prompt)
        # Erwarte entweder ein einzelnes Ticket oder eine Liste von Tickets
        tickets = result if isinstance(result, list) else [result]

        try:
            jira = get_jira()
        except Exception:
            QMessageBox.warning(
                self,
                "Jira-Einstellungen fehlen",
                "Bitte in den Einstellungen Jira-URL, Email und Token speichern.",
            )
            return

        created_keys = []
        for ticket in tickets:
            # Für jede Ticket-Definition eine Story anlegen
            story_key = create_story(
                jira,
                project_key,
                None,
                {
                    "summary": ticket.get("summary", ""),
                    "acceptance_criteria": ticket.get("acceptance_criteria", []),
                    "points": ticket.get("points", 1),
                    "tasks": ticket.get("tasks", []),
                },
            )
            add_issue_to_sprint(jira, sprint_id, story_key)
            created_keys.append(story_key)

        QMessageBox.information(
            self, "Erfolg", f"Tickets angelegt: {', '.join(created_keys)} im Sprint."
        )
        self.prompt_te.clear()
