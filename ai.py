# ai.py   (openai ≥ 1.0)
import os
import json
import traceback
from openai import OpenAI
from PySide6.QtCore import QSettings

# settings = QSettings("PrinzCodeAgent")
# openai_key = settings.value("openai/key", type=str)

# if not openai_key:
#     raise RuntimeError("OpenAI API-Key fehlt! Bitte in den Einstellungen setzen.")

# client = OpenAI(api_key=openai_key)

SYSTEM_PROMPT = """
You are a senior solution architect.

• If the user's product idea is in German, answer in German; else English.
• DO NOT wrap the YAML in code fences (```).
• DO NOT add any root key like 'technology_stack:'.

Return TWO blocks:
1) pure YAML with the keys frontend, backend, database, authentication, media
2) exactly ONE follow-up line that starts with FRAGE: (DE) or QUESTION: (EN)
"""


def _get_openai_client() -> str:
    settings = QSettings("PrinzCodeAgent")
    openai_key = settings.value("openai/key", type=str)
    if not openai_key:
        raise RuntimeError("OpenAI API-Key fehlt! Bitte in den Einstellungen setzen.")
    return OpenAI(api_key=openai_key)


def suggest_stack(project_desc: str) -> tuple[str, str]:
    client = _get_openai_client()
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": project_desc},
        ],
        temperature=0.3,
    )
    answer = resp.choices[0].message.content.strip()

    # YAML + Frage/Question trennen
    splitter = "\nFRAGE:" if "\nFRAGE:" in answer else "\nQUESTION:"
    yaml_part, question = answer.split(splitter, 1)
    return yaml_part.strip(), splitter.strip() + question.strip()


REVISION_PROMPT = """
You are a senior solution architect.

The current agreed tech stack is:

$STACK

The user suggests these modifications (keep the same language as the user's suggestion):

$CHANGES

Return TWO blocks:

1) PURE YAML with the same top-level keys (frontend, backend, database, authentication, media) – no root key.
2) Exactly ONE follow-up line:
     – If German: begin with 'FRAGE:' and ask politely whether further changes are desired.
     – If English: begin with 'QUESTION:' and ask politely whether further changes are desired.
"""


def revise_stack(current_yaml: str, user_changes: str) -> tuple[str, str]:
    client = _get_openai_client()
    """Returns (new_yaml, new_question)"""
    prompt = REVISION_PROMPT.replace("$STACK", current_yaml).replace(
        "$CHANGES", user_changes
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
        ],
        temperature=0.3,
    )
    answer = resp.choices[0].message.content.strip()
    splitter = "\nFRAGE:" if "\nFRAGE:" in answer else "\nQUESTION:"
    yaml_part, question = answer.split(splitter, 1)
    return yaml_part.strip(), splitter.strip() + question.strip()


DECOMP_PROMPT = """
You are a senior agile product owner.
Given the confirmed tech stack and the product description, do two things:

1) Create a JSON array of epics with their stories (as before).
2) Plan these epics into 3–5 sequential sprints.  
   - Sprint 1: basics & foundation  
   - Sprint 2: technical setup & integrations  
   - Sprint 3+: UI, polishing, etc.  
   Each sprint gets a name, a goal, and a list of epic names.

Output ONLY valid JSON matching this schema, no markdown, no commentary:

{
  "epics": [
    {
      "epic": "string",
      "stories": [
        {
          "summary": "string",
          "points": 5,
          "tasks": ["string", ...],
          "acceptance_criteria": ["string", ...]
        }
      ]
    }
  ],
  "sprints": [
    {
      "name": "Sprint 1",
      "goal": "string",
      "epics": ["Flotten-Dashboard", "Nutzer- & Rollenverwaltung"]
    },
    {
      "name": "Sprint 2",
      "goal": "string",
      "epics": [ ... ]
    }
  ]
}
"""


def decompose_project(description: str, stack_yaml: str) -> dict:
    client = _get_openai_client()
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": DECOMP_PROMPT},
            {
                "role": "user",
                "content": f"DESC:\n{description}\n\nSTACK:\n{stack_yaml}",
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        timeout=60,
    )
    raw = resp.choices[0].message.content.strip()
    print("⮕ LLM-Raw-JSON:\n", raw)
    return json.loads(raw)


TICKET_PROMPT = """
You are a senior agile product owner and ticket writer.
Given a user prompt describing a desired ticket, output a JSON object with the following keys:
- "summary": a short, clear title for the ticket
- "points": an integer estimate (1-13)
- "tasks": an array of step-by-step tasks needed to complete the ticket
- "acceptance_criteria": an array of acceptance criteria strings

Output ONLY valid JSON matching this schema, no markdown, no commentary.
"""


def generate_ticket_content(prompt: str) -> list[dict]:
    client = _get_openai_client()
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": TICKET_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            timeout=30,
        )
        raw = resp.choices[0].message.content.strip()
        print("⮕ Ticket-LLM-Raw-JSON:\n", raw)
        parsed = json.loads(raw)

        # Extrahiere die Ticket-Liste
        if isinstance(parsed, dict):
            # wenn der LLM unter "tickets" ausgeliefert hat
            if "tickets" in parsed and isinstance(parsed["tickets"], list):
                return parsed["tickets"]
            # einzelnes Ticket
            return [parsed]
        elif isinstance(parsed, list):
            return parsed

        raise RuntimeError(f"Unerwartetes Format von LLM: {type(parsed)}")

    except Exception as e:
        err = traceback.format_exc()
        raise RuntimeError(f"generate_ticket_content fehlgeschlagen: {e}\n{err}")
