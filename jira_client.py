from jira import JIRA
import os
from datetime import datetime, timedelta, timezone
from jira.exceptions import JIRAError


def is_team_managed(jira: JIRA, project_key: str) -> bool:
    """Is the given project a team-managed project?

    Args:
        jira (JIRA): the JIRA instance to use
        project_key (str): the key of the project to check

    Returns:
        bool: True if the project is team-managed, False otherwise
    """

    proj = jira.project(project_key)
    return getattr(proj, "isSimplified", False) or getattr(proj, "simplified", False)


EPIC_NAME_ID = "customfield_10011"
EPIC_LINK_ID = "customfield_10014"


def get_jira():
    """Returns a JIRA instance created from environment variables.

    The JIRA instance is created by passing the values of the
    JIRA_URL, JIRA_EMAIL, and JIRA_TOKEN environment variables to the
    JIRA constructor.

    If any of the environment variables are not set, a ValueError is
    raised.

    Returns:
        JIRA: The JIRA instance created from the environment variables.
    """
    url = os.getenv("JIRA_URL")
    email = os.getenv("JIRA_EMAIL")
    token = os.getenv("JIRA_TOKEN")

    if not all([url, email, token]):
        raise ValueError("JIRA_URL / JIRA_EMAIL / JIRA_TOKEN fehlen!")

    return JIRA(server=url, basic_auth=(email, token))


def create_issue(summary, description, project_key, issue_type="Task"):
    """
    Creates a Jira issue with the specified details.

    Args:
        summary (str): The summary or title of the issue.
        description (str): A detailed description of the issue.
        project_key (str): The key of the project where the issue will be created.
        issue_type (str, optional): The type of the issue to create. Defaults to "Task".

    Returns:
        Issue: The created Jira issue object.

    Raises:
        JIRAError: If there is an error during the creation of the issue.
    """

    jira = get_jira()
    issue_dict = {
        "project": {"key": project_key},
        "summary": summary,
        "description": description,
        "issuetype": {"name": issue_type},
    }
    return jira.create_issue(fields=issue_dict)


def create_epic(jira, project_key: str, epic_name: str) -> str:
    """
    Creates a Jira epic issue under a given project, along with its name field if the project is not team-managed.

    Args:
        jira: An instance of the JIRA client.
        project_key (str): The key of the project in which the epic is to be created.
        epic_name (str): The name of the epic issue to be created.

    Returns:
        str: The key of the created epic issue.

    Raises:
        JIRAError: If there is an error during the creation of the epic.
    """
    fields = {
        "project": {"key": project_key},
        "summary": epic_name,
        "issuetype": {"name": "Epic"},
    }
    if not is_team_managed(jira, project_key):
        fields[EPIC_NAME_ID] = epic_name

    try:
        issue = jira.create_issue(fields=fields)
    except JIRAError as e:
        msg = str(e)
        # epic name issue, try without again
        if EPIC_NAME_ID in msg:
            fields.pop(EPIC_NAME_ID, None)
            issue = jira.create_issue(fields=fields)
        else:
            raise
    return issue.key


def create_story(jira, project_key: str, epic_key: str, story: dict) -> str:
    """
    Creates a Jira story issue under a given project and epic, along with its sub-tasks.

    Args:
        jira: An instance of the JIRA client.
        project_key (str): The key of the project in which the story is to be created.
        epic_key (str): The key of the epic under which the story is to be created.
        story (dict): A dictionary containing the story details, including summary,
                      acceptance criteria, and tasks.

    Returns:
        str: The key of the created story issue.

    Raises:
        JIRAError: If there is an error during the creation of the story or sub-tasks.

    Note:
        If the project is not team-managed, the epic link field will be added to the story.
        If there is an issue with the epic link field during creation, it will attempt
        to create the story without this field.
    """

    fields = {
        "project": {"key": project_key},
        "summary": story["summary"],
        "description": "\n".join(f"* {a}" for a in story["acceptance_criteria"]),
        "issuetype": {"name": "Story"},
    }
    if not is_team_managed(jira, project_key):
        fields[EPIC_LINK_ID] = epic_key

    try:
        issue = jira.create_issue(fields=fields)
    except JIRAError as e:
        msg = str(e)
        # Epic link issus, try again
        if EPIC_LINK_ID in msg:
            fields.pop(EPIC_LINK_ID, None)
            issue = jira.create_issue(fields=fields)
        else:
            raise

    for t in story.get("tasks", []):
        jira.create_issue(
            fields={
                "project": {"key": project_key},
                "summary": t,
                "issuetype": {"name": "Sub-task"},
                "parent": {"key": issue.key},
            }
        )
    return issue.key


def ensure_board(jira, project_key: str) -> int:
    """Exist Srcumboard?"""
    boards = jira.boards(projectKeyOrID=project_key, type="scrum")
    if boards:
        return boards[0].id
    return jira.create_board(
        name=f"{project_key} Board", project_key=project_key, preset="scrum"
    ).id


def create_sprint(jira, board_id: int, name: str, days: int = 14) -> int:
    """
    Creates a Jira sprint under a specified board with a given name and duration.

    Args:
        jira: An instance of the JIRA client.
        board_id (int): The ID of the board where the sprint is to be created.
        name (str): The name of the sprint.
        days (int, optional): The duration of the sprint in days. Defaults to 14.

    Returns:
        int: The ID of the created sprint.

    Raises:
        JIRAError: If there is an error during the creation of the sprint.
    """

    now = datetime.now(timezone.utc)
    start_ts = now.strftime("%Y-%m-%dT%H:%M:%S.000+0000")
    end_ts = (now + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.000+0000")

    sprint = jira.create_sprint(
        name,
        board_id,
        startDate=start_ts,
        endDate=end_ts,
    )
    return getattr(sprint, "id", None) or sprint.raw["id"]


def add_issue_to_sprint(jira, sprint_id: int, issue_key: str):
    # jira.add_issues_to_sprint uses /rest/agile/1.0/sprint/{id}/issue
    """
    Adds an issue to a sprint in Jira.

    Args:
        jira: An instance of the JIRA client.
        sprint_id (int): The ID of the sprint to add the issue to.
        issue_key (str): The key of the issue to add to the sprint.

    Raises:
        JIRAError: If there is an error during the addition of the issue to the sprint.
    """
    jira.add_issues_to_sprint(sprint_id, [issue_key])


def create_jira_project(name: str, key: str | None = None) -> str:
    """
    Creates a new Jira project with the specified name and optional key.

    Args:
        name (str): The name of the project to be created.
        key (str, optional): The unique project key. If not provided, an automatic key will be generated.

    Returns:
        str: The key of the created project.

    Raises:
        RuntimeError: If the project could not be created.
    """

    jira = get_jira()
    me = jira.myself()
    account_id = me["accountId"]
    if not key:
        key = "".join(c for c in name.upper() if c.isalpha())[:4]  # Auto-Key

    body = {
        "key": key,
        "name": name,
        "projectTypeKey": "software",
        "projectTemplateKey": "com.pyxis.greenhopper.jira:gh-scrum-template",
        "leadAccountId": account_id,
    }

    res = jira._session.post(
        jira._get_url("project"),
        json=body,
        headers={"Content-Type": "application/json"},
    )
    if res.status_code not in (200, 201):
        raise RuntimeError(f"Projekt konnte nicht angelegt werden: {res.text}")

    return res.json()["key"]
