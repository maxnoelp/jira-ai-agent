# ui.py
from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QMessageBox,
    QTreeWidget,
    QTreeWidgetItem,
    QDialog,
    QDialogButtonBox,
    QPlainTextEdit,
    QTabWidget,
)
import yaml
import re

from ai import suggest_stack, revise_stack, decompose_project
from dialogs.project_dialog import ProjectDialog
from jira_client import create_jira_project
from ui.ticket_tab import TicketTab
from ui.settings_tab import SettingsTab


def clean_yaml(raw: str) -> str:
    """Entfernt ```-Fences und evtl. Root-Key."""
    txt = raw.strip()

    # 1) Code-Fences entfernen
    txt = re.sub(r"^```[^\n]*\n", "", txt)  # opening fence
    txt = re.sub(r"\n```$", "", txt)  # closing fence

    # 2) Root-Key 'technology_stack:' entfernen
    if txt.startswith("technology_stack:"):
        txt = "\n".join(
            line[2:] if line.startswith("  ") else line  # Einrückung kürzen
            for line in txt.splitlines()[1:]
        )

    return txt.strip()


class ModifyDialog(QDialog):
    """Einfacher Modal-Dialog für Stack-Änderungen"""

    def __init__(self, question: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Stack anpassen")
        self.setMinimumWidth(500)

        vbox = QVBoxLayout(self)
        vbox.addWidget(QLabel(question))

        self.edit = QPlainTextEdit()
        self.edit.setPlaceholderText("Schreibe hier deine Änderungs-Wünsche …")
        vbox.addWidget(self.edit)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        vbox.addWidget(btns)

    def changes(self) -> str:
        return self.edit.toPlainText().strip()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Prinz-Code Agent")
        self.resize(1100, 640)

        # ------------ Eingabe ------------
        self.in_edit = QTextEdit()
        self.in_edit.setPlaceholderText("Beschreibe dein Projekt …")

        self.ask_btn = QPushButton("Tech-Stack vorschlagen")
        self.ask_btn.clicked.connect(self.on_suggest)

        # ------------ Ausgabe ------------
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Komponente", "Details"])

        self.question_lbl = QLabel("")  # zeigt „FRAGE: …“

        self.ok_btn = QPushButton("Tech-Stack bestätigen")
        self.mod_btn = QPushButton("Anpassen")

        # Buttons anfangs deaktivieren
        for b in (self.ok_btn, self.mod_btn):
            b.setEnabled(False)

        self.ok_btn.clicked.connect(self.on_confirm)
        self.mod_btn.clicked.connect(self.on_modify)

        self.gen_btn = QPushButton("User-Stories generieren")
        self.push_btn = QPushButton("Stories an Jira senden")

        for b in (self.gen_btn, self.push_btn):
            b.setEnabled(False)  # anfangs deaktiviert

        self.gen_btn.clicked.connect(self.on_generate_stories)
        self.push_btn.clicked.connect(self.on_push_to_jira)

        # ------------ Layout ------------
        tabs = QTabWidget()

        # --- Tab 1: Projekt anlegen & Stack vorschlagen ---
        tab1 = QWidget()
        lyt1 = QVBoxLayout(tab1)
        lyt1.addWidget(QLabel("Projekt anlegen & Tech-Stack"))
        lyt1.addWidget(self.in_edit)
        lyt1.addWidget(self.ask_btn)
        lyt1.addWidget(self.tree)  # ggf. nur die Stack-Ansicht
        lyt1.addWidget(self.question_lbl)
        lyt1.addWidget(self.ok_btn)
        lyt1.addWidget(self.mod_btn)
        lyt1.addWidget(QLabel("User-Stories & Jira"))
        lyt1.addWidget(self.gen_btn)
        lyt1.addWidget(self.push_btn)
        tabs.addTab(tab1, "Projekt")

        # --- Tab 2: Stories & Jira-Push ---
        self.ticket_tab = TicketTab()
        tabs.addTab(self.ticket_tab, "Tickets")

        # --- Tab 3: Settings ---
        tab3 = SettingsTab()
        tabs.addTab(tab3, "Einstellungen")

        # Setze das Tab-Widget als zentrales Widget
        self.setCentralWidget(tabs)

        # ---------- State ----------
        self.yaml_raw = ""  # aktuell angezeigter YAML-Text
        self.stories = []

    # ---------- Slots ----------
    @Slot()
    def on_suggest(self) -> None:
        desc = self.in_edit.toPlainText().strip()
        if not desc:
            QMessageBox.warning(self, "Fehler", "Bitte Projektbeschreibung eingeben.")
            return

        self.ask_btn.setEnabled(False)
        self.question_lbl.setText("⏳ LLM wird gefragt …")
        QApplication.processEvents()

        try:
            yaml_part, question = suggest_stack(desc)
            self.yaml_raw = yaml_part
        except Exception as exc:
            QMessageBox.critical(self, "LLM-Fehler", str(exc))
            self.ask_btn.setEnabled(True)
            self.question_lbl.clear()
            return

        # YAML → Tree füllen
        self.populate_tree(yaml_part)

        # Frage & Buttons aktivieren
        self.question_lbl.setText(question)
        for b in (self.ok_btn, self.mod_btn):
            b.setEnabled(True)
        self.ask_btn.setEnabled(True)

    def populate_tree(self, yaml_text: str) -> None:
        self.tree.clear()
        yaml_text = clean_yaml(yaml_text)
        try:
            data = yaml.safe_load(yaml_text)
        except yaml.YAMLError as err:
            self.tree.setHeaderLabel("⚠️ Ungültiges YAML")
            return

        for section, content in data.items():
            sec_item = QTreeWidgetItem([section])
            self.tree.addTopLevelItem(sec_item)
            if isinstance(content, dict):
                for k, v in content.items():
                    QTreeWidgetItem(sec_item, [k, str(v)])
            sec_item.setExpanded(True)
        self.tree.resizeColumnToContents(0)

    @Slot()
    def on_confirm(self) -> None:
        dlg = ProjectDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        proj_name, proj_key = dlg.values()
        try:
            self.project_key = create_jira_project(proj_name, proj_key)
        except Exception as exc:
            QMessageBox.critical(self, "Jira-Fehler", str(exc))
            return

        self.gen_btn.setEnabled(True)

    @Slot()
    def on_modify(self) -> None:
        dlg = ModifyDialog(self.question_lbl.text(), self)
        if dlg.exec() != QDialog.Accepted:
            return  # abgebrochen

        changes_txt = dlg.changes()
        if not changes_txt:
            QMessageBox.warning(
                self, "Keine Änderungen", "Du hast keine Änderungen eingegeben."
            )
            return

        # --- KI aufrufen ---
        self.ok_btn.setEnabled(False)
        self.mod_btn.setEnabled(False)
        self.question_lbl.setText("⏳ Änderungen werden geprüft …")
        QApplication.processEvents()

        try:
            new_yaml, new_q = revise_stack(self.yaml_raw, changes_txt)
            self.yaml_raw = new_yaml
            self.populate_tree(new_yaml)
            self.question_lbl.setText(new_q)
        except Exception as exc:
            QMessageBox.critical(self, "LLM-Fehler", str(exc))
        finally:
            self.ok_btn.setEnabled(True)
            self.mod_btn.setEnabled(True)

    @Slot()
    @Slot()
    def on_push_to_jira(self) -> None:
        from jira_client import (
            get_jira,
            ensure_board,
            create_sprint,
            create_epic,
            create_story,
            add_issue_to_sprint,
        )

        if not self.stories:
            QMessageBox.warning(
                self, "Keine Stories", "Bitte erst User-Stories generieren."
            )
            return

        jira = get_jira()
        project_key = self.project_key
        board_id = ensure_board(jira, project_key)

        log_lines = []

        # für jeden Sprint aus dem Plan
        for sp in self.sprint_plan:
            # sprint_name und optional goal aus dem Plan
            name = sp.get("name", "Sprint")
            goal = sp.get("goal", "")
            # Hier kannst du goal verwenden, wenn du willst
            sprint_id = create_sprint(jira, board_id, name, days=14)
            log_lines.append(f"🏃 {name} (ID {sprint_id}) angelegt")

            # alle Epics, die in diesem Sprint gelistet sind
            for epic in self.stories:
                if epic["epic"] in sp.get("epics", []):
                    epic_key = create_epic(jira, project_key, epic["epic"])
                    log_lines.append(f"  ✔ Epic {epic_key} für {epic['epic']}")
                    for story in epic["stories"]:
                        story_key = create_story(jira, project_key, epic_key, story)
                        add_issue_to_sprint(jira, sprint_id, story_key)
                        log_lines.append(f"     ↳ Story {story_key}")

        QMessageBox.information(
            self,
            "Fertig",
            "Alles angelegt 🎉\n\n" + "\n".join(log_lines),
        )
        self.push_btn.setEnabled(False)

    @Slot()
    def on_generate_stories(self):
        # UI-Status
        self.gen_btn.setEnabled(False)
        self.push_btn.setEnabled(False)
        self.question_lbl.setText("⏳ Stories werden erstellt …")
        QApplication.processEvents()

        # Baum & State zurücksetzen
        self.tree.clear()
        self.stories = []
        self.sprint_plan = []

        # LLM-Aufruf
        try:
            plan = decompose_project(self.in_edit.toPlainText(), self.yaml_raw)
            # plan ist jetzt ein dict mit "epics" und "sprints"
            if isinstance(plan, dict):
                self.stories = plan.get("epics", [])
                self.sprint_plan = plan.get("sprints", [])
            else:
                # Fallback: reine Liste von Epics
                self.stories = plan
        except Exception as exc:
            QMessageBox.critical(self, "LLM-Fehler", str(exc))
            self.gen_btn.setEnabled(True)
            return

        # Tree neu befüllen (Epics & ihre Stories)
        for epic in self.stories:
            epic_item = QTreeWidgetItem([f"[EPIC] {epic['epic']}"])
            self.tree.addTopLevelItem(epic_item)
            for st in epic["stories"]:
                story_item = QTreeWidgetItem(
                    epic_item, [f"{st['summary']}  (SP: {st['points']})"]
                )
                for t in st.get("tasks", []):
                    QTreeWidgetItem(story_item, [f"• {t}"])
        self.tree.expandAll()

        # Button für Push freigeben
        self.push_btn.setEnabled(True)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
