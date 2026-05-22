# 🏢 MCP Entreprises France

**A Model Context Protocol (MCP) server for Claude Desktop** that provides real-time access to official French business data from 3 free public APIs — no subscription required (optional Pappers token for enhanced data).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![MCP SDK](https://img.shields.io/badge/MCP_SDK-1.27.1-teal)](https://github.com/modelcontextprotocol/python-sdk)
[![APIs](https://img.shields.io/badge/APIs-data.gouv.fr%20%7C%20BODACC%20%7C%20Pappers-green)](https://recherche-entreprises.api.gouv.fr)

---

## 📡 Data Sources

| API | Auth | Data provided |
|---|---|---|
| [Recherche Entreprises](https://recherche-entreprises.api.gouv.fr) | None (free, open) | Identity, status, NAF, address, headcount, directors |
| [BODACC / DILA](https://bodacc-datadila.opendatasoft.com) | None (free, open) | Official legal announcements |
| [Pappers API v2](https://www.pappers.fr/api) | Free token required | Balance sheets, beneficial owners, health score, legal acts |

---

## 🛠️ Tools (6 available)

| Tool | Description | Auth required |
|---|---|---|
| `entreprise_search` | Search by name, SIREN, SIRET, keyword, NAF, département | None |
| `entreprise_fiche_complete` | Full company profile — enriched with Pappers if token present | Pappers (optional) |
| `entreprise_finances` | Multi-year balance sheet history (CA, net result, equity, debt) | Pappers |
| `entreprise_bodacc` | Official BODACC legal announcements (creations, modifications, insolvency) | None |
| `entreprise_dirigeants` | Directors + beneficial owners (UBO) | Pappers (for UBO) |
| `entreprise_verifier` | Validate a SIREN or SIRET — status, address, activity | None |

---

## 🚀 Quick Install (Windows)

### Option 1 — Automatic (PowerShell)

```powershell
# 1. Clone or download the repo
git clone https://github.com/Clv47500/mcp-entreprises-france.git
cd mcp-entreprises-france

# 2. Run the installer (auto-detects Python, installs deps, registers in Claude Desktop)
.\install.ps1
```

### Option 2 — Manual

**Step 1 — Copy the server**
```powershell
# Create the MCP servers directory
New-Item -ItemType Directory -Force -Path "$env:APPDATA\Claude\mcp-servers\entreprises-france"

# Copy files
Copy-Item server.py "$env:APPDATA\Claude\mcp-servers\entreprises-france\"
Copy-Item requirements.txt "$env:APPDATA\Claude\mcp-servers\entreprises-france\"
```

**Step 2 — Install Python dependencies**
```powershell
python -m pip install mcp[cli] httpx pydantic
```

**Step 3 — Register in Claude Desktop**

Edit `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "entreprises-france": {
      "command": "C:\\Users\\[YOUR_USER]\\AppData\\Local\\Programs\\Python\\Python313\\python.exe",
      "args": [
        "C:\\Users\\[YOUR_USER]\\AppData\\Roaming\\Claude\\mcp-servers\\entreprises-france\\server.py"
      ]
    }
  }
}
```

> **Important:** Always use the **absolute path** to `python.exe`. If multiple Python versions are installed, the wrong interpreter will cause `ModuleNotFoundError`.

**Step 4 — Restart Claude Desktop**

The 6 tools appear under **Developer → Local MCPs** (not in Extensions — this is normal for manually configured MCPs).

---

## 🔑 Pappers API Token (optional but recommended)

Without a token, `entreprise_search`, `entreprise_bodacc`, and `entreprise_verifier` work fully. `entreprise_fiche_complete` returns partial data. `entreprise_finances` and UBO data from `entreprise_dirigeants` require a token.

**Get your free token:**
1. Go to [pappers.fr/api](https://www.pappers.fr/api)
2. Register (free, 2 min)
3. Copy your API token

**Configure the token** — two options:

Option A — `config.json` file (recommended):
```bash
cp config.json.example config.json
# Edit config.json and replace YOUR_PAPPERS_TOKEN_HERE with your actual token
```

Option B — Environment variable:
```powershell
$env:PAPPERS_API_TOKEN = "your_token_here"
```

---

## 💬 Usage Examples

Once installed, use natural language in Claude Desktop (Cowork mode):

```
"Search for all accounting firms (NAF 6920Z) in département 13"
→ entreprise_search

"Give me the full profile of SIREN 380129866"
→ entreprise_fiche_complete (enhanced with Pappers if token configured)

"Show the last 5 years of financial data for this company"
→ entreprise_finances

"Are there any insolvency proceedings published in BODACC for this SIREN?"
→ entreprise_bodacc

"Who are the current directors and beneficial owners?"
→ entreprise_dirigeants

"Is SIRET 38012986600034 valid and active?"
→ entreprise_verifier
```

---

## 🔧 Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'mcp'` | MCP SDK not installed | `python -m pip install mcp` |
| `ModuleNotFoundError: No module named 'pydantic'` | Pydantic not installed | `python -m pip install pydantic` |
| `Erreur Pappers : Token invalide` | Wrong or missing token | Check `config.json` or `PAPPERS_API_TOKEN` env var |
| Server not visible in Claude | Config JSON error | Validate JSON at [jsonlint.com](https://jsonlint.com) |
| Server in "Local MCPs" not "Extensions" | Normal behaviour | Manually configured MCPs appear under Developer → Local MCPs |

**Quick repair command:**
```powershell
python -m pip install "mcp[cli]" httpx pydantic
```

---

## 📁 Repository Structure

```
mcp-entreprises-france/
├── README.md                        # This file (EN + FR)
├── LICENSE                          # MIT License
├── .gitignore                       # config.json excluded!
├── server.py                        # MCP server (FastMCP + 6 tools)
├── requirements.txt                 # Python dependencies
├── install.ps1                      # Windows auto-installer (PowerShell)
├── config.json.example              # Token config template (copy → config.json)
└── CHANGELOG.md                     # Version history
```

---

## 📄 License

MIT — see [LICENSE](LICENSE)

Created by **Christian Levannier** ([@Clv47500](https://github.com/Clv47500))

---

---

# 🏢 MCP Entreprises France — Documentation française

**Serveur MCP pour Claude Desktop** donnant accès en temps réel aux données officielles des entreprises françaises depuis 3 APIs publiques gratuites.

## Sources de données

- **API Recherche Entreprises** (data.gouv.fr) — sans clé, données de base
- **BODACC / DILA** — sans clé, annonces légales officielles
- **Pappers API v2** — token gratuit requis, données enrichies (bilans, score santé, UBO)

## Installation rapide

```powershell
git clone https://github.com/Clv47500/mcp-entreprises-france.git
cd mcp-entreprises-france
.\install.ps1
```

Le script installe les dépendances Python et enregistre automatiquement le serveur dans `claude_desktop_config.json`.

## Token Pappers (recommandé)

```bash
cp config.json.example config.json
# Remplacer YOUR_PAPPERS_TOKEN_HERE par votre token (inscription gratuite sur pappers.fr/api)
```

## Les 6 outils

| Outil | Description | Token requis |
|---|---|---|
| `entreprise_search` | Recherche multi-critères (nom, SIREN, NAF, département…) | Non |
| `entreprise_fiche_complete` | Fiche complète enrichie | Optionnel |
| `entreprise_finances` | Historique bilans multi-années | Oui |
| `entreprise_bodacc` | Annonces légales BODACC | Non |
| `entreprise_dirigeants` | Dirigeants + bénéficiaires effectifs | Oui (pour UBO) |
| `entreprise_verifier` | Validation SIREN/SIRET | Non |

## Dépannage rapide

```powershell
python -m pip install "mcp[cli]" httpx pydantic
```

Redémarrer Claude Desktop après installation. Le serveur apparaît dans **Développeur → MCPs locaux**.
