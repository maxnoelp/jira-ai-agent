import os
import json
from jira import JIRA
from dotenv import load_dotenv

load_dotenv()

jira = JIRA(
    server=os.getenv("JIRA_URL"),
    basic_auth=(os.getenv("JIRA_EMAIL"), os.getenv("JIRA_TOKEN")),
)

for f in jira.fields():
    if "epic" in f["name"].lower():  # filtert alles mit „epic“
        print(f"{f['name']:25s}  →  {f['id']}")
