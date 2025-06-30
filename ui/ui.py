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
    """
    Cleans and formats a raw YAML string by removing code fences and adjusting indentation.

    This function performs the following operations:
    1. Strips leading and trailing whitespace from the input string.
    2. Removes opening and closing code fences if present.
    3. If the text starts with 'technology_stack:', it adjusts the indentation of the lines
       by removing leading spaces from each line after the first.

    Args:
        raw (str): The raw YAML string to be cleaned.

    Returns:
        str: The cleaned and formatted YAML string.
    """

    txt = raw.strip()

    txt = re.sub(r"^```[^\n]*\n", "", txt)  # opening fence
    txt = re.sub(r"\n```$", "", txt)  # closing fence

    if txt.startswith("technology_stack:"):
        txt = "\n".join(
            line[2:] if line.startswith("  ") else line for line in txt.splitlines()[1:]
        )

    return txt.strip()


class ModifyDialog(QDialog):
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

        # ------------ Input ------------
        self.in_edit = QTextEdit()
        self.in_edit.setPlaceholderText("Beschreibe dein Projekt …")

        self.ask_btn = QPushButton("Tech-Stack vorschlagen")
        self.ask_btn.clicked.connect(self.on_suggest)

        # ------------ Output ------------
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Komponente", "Details"])

        self.question_lbl = QLabel("")

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

        # --- Tab 1: Project ---
        tab1 = QWidget()
        lyt1 = QVBoxLayout(tab1)
        lyt1.addWidget(QLabel("Projekt anlegen & Tech-Stack"))
        lyt1.addWidget(self.in_edit)
        lyt1.addWidget(self.ask_btn)
        lyt1.addWidget(self.tree)
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

        self.setCentralWidget(tabs)

        # ---------- State ----------
        self.yaml_raw = ""
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

        # YAML → fill Tree
        self.populate_tree(yaml_part)

        # Btn & questions activate
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
            return  # break

        changes_txt = dlg.changes()
        if not changes_txt:
            QMessageBox.warning(
                self, "Keine Änderungen", "Du hast keine Änderungen eingegeben."
            )
            return

        # --- call KI ---
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

        for sp in self.sprint_plan:
            # sprint name
            name = sp.get("name", "Sprint")
            goal = sp.get("goal", "")
            sprint_id = create_sprint(jira, board_id, name, days=14)
            log_lines.append(f"🏃 {name} (ID {sprint_id}) angelegt")

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

        # tree and stories clear
        self.tree.clear()
        self.stories = []
        self.sprint_plan = []

        # LLM call
        try:
            plan = decompose_project(self.in_edit.toPlainText(), self.yaml_raw)
            if isinstance(plan, dict):
                self.stories = plan.get("epics", [])
                self.sprint_plan = plan.get("sprints", [])
            else:
                # Fallback
                self.stories = plan
        except Exception as exc:
            QMessageBox.critical(self, "LLM-Fehler", str(exc))
            self.gen_btn.setEnabled(True)
            return

        # fill tree
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

        # activate btn for push
        self.push_btn.setEnabled(True)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
