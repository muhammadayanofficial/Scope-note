# ScopeNote

ScopeNote turns messy client messages into a structured project brief. It is a small Flask app for freelancers and small teams who want clearer requirements before estimating a job.

## What it does

- Converts a raw client message into goals, requirements, and suggested deliverables.
- Lists the questions to clarify before quoting or starting work.
- Flags possible project risks and offers scope boundaries to confirm with the client.
- Drafts a client-facing summary for confirmation.
- Saves each analysis in a local SQLite database.
- Exports a saved brief as a Markdown file.
- Uses Gemini for richer analysis when an API key is configured. Without one, it uses a clearly labeled local rules-based fallback.

The local fallback does not call an AI model. Treat its generated items as a starting point for review, not as an authoritative statement of what a client has agreed to.

## Requirements

- Python 3.10 or newer
- pip
- Optional: a Gemini API key from Google AI Studio for AI-powered analysis

## Windows setup

Open this folder in VS Code. In the VS Code terminal, run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks virtual-environment activation, use Command Prompt and run:

```bat
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

Create your local environment file by copying `.env.example` and naming the copy `.env`.

Generate a secret key by running:

```powershell
py -c "import secrets; print(secrets.token_hex(32))"
```

Copy the generated random text after `SECRET_KEY=` in `.env`. Do not publish this key or commit `.env` to Git.

### Enable Gemini (optional)

Open `.env` and put your Gemini API key after `GEMINI_API_KEY=`. Keep the key private. The default model is `gemini-3.8-flash`; you can change `GEMINI_MODEL` if needed. If the API request fails, ScopeNote falls back to local rules-based analysis and displays a warning.

## Run the app

```powershell
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

Your analyses are stored in `instance/scopenote.sqlite3` on this computer. The database is created automatically the first time the app starts.

## Main files

```text
ScopeNote/
├── app.py
├── database.py
├── scope_engine.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── instance/                 # Created automatically; local database is not committed
├── templates/
│   ├── index.html
│   └── history.html
└── static/
    ├── css/style.css
    └── js/app.js
```

## Test endpoint

With the server running, open [http://127.0.0.1:5000/health](http://127.0.0.1:5000/health). It should return a small JSON status response.

## Important limitations

- This is a local portfolio prototype, not a hosted multi-user service.
- Do not paste confidential client information unless you are comfortable storing it on this computer. When Gemini is enabled, the client message is sent to Google's Gemini API for analysis.
- The output is a draft. Confirm scope, price, timelines, ownership, approvals, and exclusions with the client before relying on it.
- The local fallback uses heuristics; it is not equivalent to LLM analysis.
- `FLASK_DEBUG=true` is for local development only. Do not deploy with debug mode enabled.
