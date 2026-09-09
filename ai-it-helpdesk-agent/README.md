# 🛠️ AI IT Helpdesk Agent

An **agentic AI system** that diagnoses common IT issues and recommends
troubleshooting steps using **RAG (Retrieval-Augmented Generation)**,
**Tool Calling**, and **Memory**.

> Built as the Day 1 use-case project for the **TNSDC – IBM Agentic AI
> Internship**, based on Use Case #4: *AI IT Helpdesk Agent — diagnoses
> common technical issues and recommends troubleshooting steps using a
> knowledge base.* Key agent capabilities: **Agent + RAG + Tools**.

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Flask](https://img.shields.io/badge/flask-3.x-black)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen)

---

## ✨ Features

- **RAG-based diagnosis** — a 27-article IT knowledge base (network,
  hardware, software, account, email, security, performance, OS issues)
  retrieved with a dependency-free TF-IDF + cosine-similarity engine.
- **Tool calling** — the agent decides when to run simulated diagnostics
  (network check, system resource check, service restart, ticket-history
  search) and folds the results into its answer.
- **Memory** — per-session conversation history, last-known issue
  category, and an "unresolved streak" counter.
- **Automatic escalation** — if the user reports the same issue is still
  unresolved, the agent creates a real support ticket (persisted to
  `data/tickets.json`) instead of looping forever.
- **Clarifying questions** — low-confidence retrieval triggers a
  follow-up question instead of a wrong guess.
- **Two interfaces** — a chat **web UI** (Flask) and a **CLI** for quick
  terminal demos.
- **Zero mandatory API keys** — works fully offline out of the box.
  Optionally plug in `ANTHROPIC_API_KEY` for LLM-enhanced natural-language
  responses (falls back gracefully if not set).
- **Unit tested** — retrieval, intent detection, and the full escalation
  flow are covered under `tests/`.

---

## 🧠 How it works (Agent + RAG + Tools + Memory)

```
User message
   │
   ▼
Escalation / frustration check ──► (repeated failure) ──► create_ticket tool
   │ (else)
   ▼
RAG retrieval over knowledge_base.json (TF-IDF cosine similarity)
   │
   ▼
Tool triggers (network diagnostic / system check / service restart / ticket search)
   │
   ▼
Response composer (template, or optional Claude LLM call)
   │
   ▼
Reply + sources + tools used + escalation status  ──►  saved to session memory
```

See [`docs/architecture.md`](docs/architecture.md) for the full breakdown.

---

## 📁 Project structure

```
ai-it-helpdesk-agent/
├── app.py                  # Flask web app (chat UI + JSON API)
├── cli.py                  # Terminal chat interface
├── requirements.txt
├── LICENSE
├── agent/
│   ├── agent.py             # Orchestrator: Agent + RAG + Tools + Memory
│   ├── rag.py                # Pure-Python TF-IDF retriever
│   ├── tools.py               # Simulated IT support tools
│   ├── memory.py              # Per-session conversation memory
│   └── knowledge_base.py      # KB loader
├── data/
│   └── knowledge_base.json   # 27 IT-issue articles (source of truth for RAG)
├── templates/index.html      # Chat UI markup
├── static/style.css          # Chat UI styling
├── static/script.js          # Chat UI logic (fetch → /api/chat)
├── tests/test_agent.py       # Unit tests
└── docs/architecture.md      # Architecture deep-dive
```

---

## 🚀 Getting started

### 1. Clone & install

```bash
git clone https://github.com/<your-username>/ai-it-helpdesk-agent.git
cd ai-it-helpdesk-agent
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run the web app

```bash
python app.py
```

Open **http://127.0.0.1:5000** and start chatting, e.g.:
- "my wifi keeps disconnecting"
- "printer won't print"
- "I forgot my password"
- "outlook is not syncing"

### 3. Or run the CLI

```bash
python cli.py
```

### 4. (Optional) Enable LLM-enhanced replies

```bash
export ANTHROPIC_API_KEY=your_key_here   # Windows: set ANTHROPIC_API_KEY=...
pip install anthropic
python app.py
```

Without this, the agent still works perfectly using its built-in
template-based response composer.

### 5. Run the tests

```bash
python -m unittest discover -s tests -v
```

---

## 💬 Example conversation

```
You: my wifi keeps disconnecting

Assistant: This looks like it's related to Wi-Fi not connecting (Network).
Here's what I'd try, in order:
1. Toggle Wi-Fi off and on from the network settings panel.
2. Forget the network and reconnect using the correct password.
3. Restart the router/access point and wait 60 seconds before reconnecting.
4. Update the wireless network adapter driver.
5. Run the built-in network troubleshooter.

Let me know if that resolves it, or tell me if it's still not working.

You: still not working
Assistant: Sorry that didn't fix it. Could you tell me exactly what happens
now (any error message, or at which step it fails)? If the next attempt
still doesn't work, I'll escalate this to a human technician for you.

You: still not working
Assistant: I'm sorry the suggested steps haven't resolved this. I've
escalated the issue to a human technician -- your ticket ID is TCK-9287
(category: Network). They'll follow up with you shortly.
```

---

## 🧩 Extending the project

- **Bigger knowledge base**: add more entries to
  `data/knowledge_base.json` — no code changes needed, the retriever
  picks them up automatically.
- **Real tools**: swap the simulated functions in `agent/tools.py` for
  real integrations (e.g. a real ticketing API, an actual ping/ICMP
  library, Active Directory password reset).
- **Vector DB**: swap `agent/rag.py`'s TF-IDF retriever for FAISS/Chroma
  without changing the agent's calling code — it's isolated behind a
  simple `.query(text, top_k)` interface.
- **Persistent, multi-user memory**: replace the per-session JSON files
  in `agent/memory.py` with a real database.

---

## 📚 About this project

This repository implements **Use Case #4 — AI IT Helpdesk Agent** from the
TNSDC × IBM *Agentic AI* internship's Day 1 use-case selection, where each
student picks one use case and develops it into a full project across the
program. The required agent capabilities for this use case — **Agent +
RAG + Tools** — are all implemented, with **Memory** added on top to
support multi-turn troubleshooting and automatic escalation.

## 📄 License

Released under the [MIT License](LICENSE).
