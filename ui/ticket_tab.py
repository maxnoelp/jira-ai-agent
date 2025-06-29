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
from PySide6.QtCore import Slot
from jira_client import get_jira, ensure_board, add_issue_to_sprint, create_story


class TicketTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.current_sprint_id = None

    def _setup_ui(self):
        l = QVBoxLayout(self)

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

        # initial füllen
        self._load_projects()

    def _load_projects(self):
        jira = get_jira()
        projects = jira.projects()
        for p in projects:
            self.project_cb.addItem(f"{p.key} – {p.name}", p.key)

    @Slot()
    def load_sprints(self):
        # Board holen & aktuelle Sprints befüllen
        project_key = self.project_cb.currentData()
        jira = get_jira()
        board = ensure_board(jira, project_key)
        # hier verwenden wir das Agile-API-List-Sprints
        sprints = jira.sprints(board)  # returns list of Sprint objects
        self.sprint_cb.clear()
        for s in sprints:
            # nur offene/future Sprints anzeigen
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

        # AI-Aufruf: z.B. ai.generate_ticket_content(prompt)
        from ai import (
            generate_ticket_content,
        )  # Du müsstest diese neue Funktion implementieren

        ticket = generate_ticket_content(prompt)

        # Ticket in Jira anlegen (Story unter dem aktuellen Sprint)
        jira = get_jira()
        # wir legen eine Story ohne Epic an, nur einen Task
        story_key = create_story(
            jira,
            project_key,
            None,
            {
                "summary": ticket["summary"],
                "acceptance_criteria": ticket.get("acceptance_criteria", []),
                "points": ticket.get("points", 1),
                "tasks": ticket.get("tasks", []),
            },
        )
        add_issue_to_sprint(jira, sprint_id, story_key)

        QMessageBox.information(
            self, "Erfolg", f"Ticket {story_key} im Sprint angelegt."
        )
        self.prompt_te.clear()
