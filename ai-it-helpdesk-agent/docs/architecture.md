# Architecture

## Overview

The AI IT Helpdesk Agent follows the classic **Agent + RAG + Tools + Memory**
pattern used across the course's five use cases:

```
                       ┌─────────────────────────────┐
                       │        User Message          │
                       └───────────────┬───────────────┘
                                       │
                                       ▼
                       ┌─────────────────────────────┐
                       │   ITHelpdeskAgent (agent.py) │
                       │   - intent / category check  │
                       │   - escalation detection     │
                       └───────────────┬───────────────┘
                     ┌─────────────────┼─────────────────┐
                     ▼                 ▼                 ▼
            ┌────────────────┐ ┌──────────────┐ ┌──────────────────┐
            │   RAG (rag.py) │ │ Tools         │ │ Memory            │
            │  TF-IDF cosine │ │ (tools.py)    │ │ (memory.py)       │
            │  similarity    │ │ - diagnostics │ │ - chat history    │
            │  over KB       │ │ - restart svc │ │ - last category   │
            │  articles      │ │ - ticket ops  │ │ - unresolved count│
            └────────┬───────┘ └──────┬───────┘ └─────────┬─────────┘
                     └─────────────────┼─────────────────┘
                                       ▼
                       ┌─────────────────────────────┐
                       │     Response Composer        │
                       │  (rule-based template, or    │
                       │  optional Claude LLM call)    │
                       └───────────────┬───────────────┘
                                       ▼
                       ┌─────────────────────────────┐
                       │   Reply + sources + tools    │
                       │   used + escalation status   │
                       └─────────────────────────────┘
```

## Components

### 1. Retrieval-Augmented Generation (`agent/rag.py`)
A dependency-free TF-IDF vectorizer + cosine similarity search over
`data/knowledge_base.json` (27 IT-issue articles across Network,
Hardware, Software, Account, Email, Security, Performance, and OS
categories). Each article has a title, category, keyword list, and a
step-by-step solution. No vector database or embedding API is required,
which keeps the project runnable anywhere with zero setup friction.

### 2. Tool Calling (`agent/tools.py`)
The agent can decide, based on lightweight regex triggers on the user's
message, to call one or more simulated IT tools:

| Tool | Purpose |
|---|---|
| `run_network_diagnostic` | Simulated ping/latency/packet-loss check |
| `get_system_diagnostics` | Simulated CPU/RAM/disk snapshot |
| `check_service_status` | Simulated service up/down check |
| `restart_service` | Simulated service restart (e.g. print spooler) |
| `search_ticket_history` | Keyword search over sample past tickets |
| `create_ticket` | Persists a real escalation ticket to `data/tickets.json` |

These are simulations so the project runs safely offline with no real
system access or credentials, while still demonstrating genuine
tool-selection and tool-use reasoning.

### 3. Memory (`agent/memory.py`)
Each conversation is identified by a `session_id` and persisted to
`data/sessions/<id>.json`. Memory tracks:
- full message history (role, content, timestamp, metadata)
- the last identified issue category (used to keep escalation tickets
  on-topic even when the triggering message, e.g. "still not working",
  has no retrieval signal of its own)
- an "unresolved streak" counter used to trigger escalation to a human
  technician after repeated failed attempts

### 4. Response Composition (`agent/agent.py`)
By default, replies are assembled from the retrieved knowledge-base
steps and any tool results using a clear, deterministic template -- this
makes the agent's reasoning fully explainable and gradable without
needing an API key.

If an `ANTHROPIC_API_KEY` environment variable is set **and** the
`anthropic` package is installed, the agent will instead ask Claude to
turn the same retrieved context + tool results into a more natural
free-form reply (still grounded only in that context). If the LLM call
fails or is unavailable for any reason, it transparently falls back to
the template composer -- the app never breaks.

## Design decisions

- **Zero mandatory external dependencies** beyond Flask: the RAG
  retriever, tools, and memory are all pure Python + stdlib, so grading
  or demoing the project never requires API keys, internet access, or
  paid services.
- **Escalation is a first-class flow**, not an afterthought: the agent
  detects frustration/failure language, tracks it in memory, and after
  a configurable threshold automatically creates a ticket via the
  `create_ticket` tool -- mirroring how a real support agent would hand
  off to a human.
- **Low-confidence retrieval asks a clarifying question** rather than
  guessing a wrong KB article, which is a basic but important RAG
  safety behavior.
