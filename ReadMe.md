## Test Prompt

```text
PROJEKT: B2B-Plattform „GreenFleet“

Ziel
- KMU sollen ihre Firmenfahrzeuge (E-Autos, Plug-in-Hybride, Fahrräder) inkl. Lade-/Service-Historie verwalten können.
- CO₂-Bilanz jedes Fahrzeugs wird automatisch berechnet und als Report exportierbar gemacht.

Hauptfunktionen
1. Flotten-Dashboard mit Live-Status (Kilometerstand, Ladestand, nächste Wartung).
2. Nutzer- & Rollenverwaltung (Fuhrparkleitung, Fahrer, Buchhaltung).
3. Elektronisches Fahrtenbuch (automatischer Trip-Import via GPS-Connector-API).
4. Lade-Management: Backend-Schnittstelle zu Wallbox-Anbietern (EnBW, Wallbe, easee).
5. CO₂-Report: jährlicher PDF-Download & CSV-Export je Fahrzeug und gesamt.
6. Benachrichtigungen: E-Mail / In-App bei Wartungs-/HU-Terminen und niedriger Batterieladung.
7. Zahlungsmodul: Abo-Gestaffelung (Basic, Pro, Enterprise) via Stripe.
8. Mehrsprachigkeit: Deutsch / Englisch / Französisch (i18n-Framework).

Nicht-Funktionen
- Keine Routenplanung, keine In-App-Navigation.
- Kein eigenes Ersatzteil-Shop-Modul.

Nicht-funktionale Anforderungen
- SaaS-Cloud-Deployment (AWS) mit 99.5 % Uptime-SLA.
- DSGVO-konforme Datenspeicherung (Region: EU-Central-1).
- Responsive UI (Desktop, Tablet, Mobile).

Offene Punkte
- BI-/Analytics-Stack noch offen (Metabase oder Looker?).
- Wunsch nach On-Premise-Option für Enterprise-Kunden, aber nicht Teil des MVP.

```
## Install

- make a virutal Enviorment
- create .env file
    ```text
    JIRA_URL=
    JIRA_EMAIL=
    JIRA_TOKEN=
    OPENAI_API_KEY=
    ```
- run `pip install requirements.txt`
- run `python main.py`

## Function

- can create TechStack and make all Sprints and tickets from ai
- can make a unique Ticket from ai