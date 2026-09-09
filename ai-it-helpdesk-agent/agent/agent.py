"""
agent.py
--------
ITHelpdeskAgent: the orchestrator that ties together

    RAG    - retrieves relevant knowledge-base articles for the user's issue
    Tools  - runs simulated diagnostics / ticket actions when needed
    Memory - keeps per-session conversation + escalation state

The agent works fully offline out of the box (rule/template based
response synthesis). If an ANTHROPIC_API_KEY environment variable is
present and the `anthropic` package is installed, it will additionally
use Claude to turn the retrieved context + tool results into a more
natural free-form reply -- but nothing in the project *requires* an API
key to run or be graded.
"""

import os
import re

from .knowledge_base import load_knowledge_base, build_document_text
from .rag import TfidfRetriever
from .memory import ConversationMemory
from . import tools as tool_module

RETRIEVAL_CONFIDENCE_THRESHOLD = 0.08
ESCALATION_THRESHOLD = 2  # unresolved turns before offering to escalate

# Very small, transparent intent -> tool trigger rules. Kept simple and
# explainable on purpose -- this is a teaching project, not a black box.
_TOOL_TRIGGERS = [
    (re.compile(r"\b(check|run|test)\b.*\b(network|internet|connection|wifi|wi-fi)\b", re.I), "run_network_diagnostic"),
    (re.compile(r"\b(slow|freez|hang|lag|high cpu|not responding)\b", re.I), "get_system_diagnostics"),
    (re.compile(r"\bprint(er)?\b.*\b(spooler|queue|stuck)\b", re.I), "restart_service:Print Spooler"),
    (re.compile(r"\b(similar|past|previous)\b.*\bticket", re.I), "search_ticket_history"),
    (re.compile(r"\b(status of|is)\b.*\bservice\b", re.I), "check_service_status:helpdesk-agent-service"),
]

_NEGATIVE_FEEDBACK_RE = re.compile(
    r"\b(still (not|isn'?t|doesn'?t)|didn'?t work|not working|no luck|same (issue|problem)|"
    r"nothing changed|still broken|still fail(ing|ed)?)\b",
    re.I,
)

_GREETING_RE = re.compile(r"^\s*(hi|hello|hey|good (morning|afternoon|evening))\b", re.I)


class ITHelpdeskAgent:
    def __init__(self, kb_path: str = None):
        self.kb = load_knowledge_base(kb_path) if kb_path else load_knowledge_base()
        documents = [build_document_text(entry) for entry in self.kb]
        doc_ids = [entry["id"] for entry in self.kb]
        self.retriever = TfidfRetriever(documents, doc_ids)
        self._kb_by_id = {entry["id"]: entry for entry in self.kb}

        # Optional LLM enhancement -- purely additive, never required.
        self._llm_client = None
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            try:
                import anthropic  # type: ignore

                self._llm_client = anthropic.Anthropic(api_key=api_key)
            except ImportError:
                self._llm_client = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def handle_message(self, session_id: str, user_message: str) -> dict:
        memory = ConversationMemory(session_id)
        memory.add_message("user", user_message)

        if _GREETING_RE.match(user_message.strip()):
            reply = (
                "Hi, I'm your AI IT Helpdesk Assistant. Describe the issue "
                "you're facing (e.g. \"my wifi keeps disconnecting\" or "
                "\"printer won't print\") and I'll help you troubleshoot it."
            )
            memory.add_message("assistant", reply)
            return {
                "response": reply,
                "category": None,
                "sources": [],
                "tools_used": [],
                "escalated": False,
            }

        # 1. Escalation / frustration check FIRST -- a message like "still not
        #    working" carries no useful retrieval signal of its own, so we
        #    must not run RAG on it (that previously caused nonsense matches
        #    like "Keyboard not working"). Instead we lean on the category
        #    already stored in memory from the prior turn.
        escalated = False
        ticket_info = None
        if _NEGATIVE_FEEDBACK_RE.search(user_message):
            streak = memory.mark_unresolved()
            last_category = memory.get_last_category() or "General"
            if streak >= ESCALATION_THRESHOLD:
                summary = f"User reports unresolved issue in category '{last_category}': {user_message}"
                result = tool_module.create_ticket(summary, last_category)
                ticket_info = result["ticket"]
                escalated = True
            else:
                reply = (
                    "Sorry that didn't fix it. Could you tell me exactly what "
                    "happens now (any error message, or at which step it "
                    "fails)? If the next attempt still doesn't work, I'll "
                    "escalate this to a human technician for you."
                )
                memory.add_message("assistant", reply, {"category": last_category})
                return {
                    "response": reply,
                    "category": last_category,
                    "sources": [],
                    "tools_used": [],
                    "escalated": False,
                }
        else:
            memory.reset_unresolved()

        # 2. RAG retrieval (skipped once we've already decided to escalate,
        #    since the triggering message itself carries no retrieval signal)
        retrieved_entries = []
        category = memory.get_last_category()
        if not escalated:
            retrieved = self.retriever.query(user_message, top_k=3)
            top_id, top_score, _ = retrieved[0] if retrieved else (None, 0.0, "")
            retrieved_entries = [
                (self._kb_by_id[doc_id], score) for doc_id, score, _ in retrieved if score > 0
            ]
            category = self._kb_by_id[top_id]["category"] if top_id and top_score > 0 else None
            if category:
                memory.set_last_category(category)

        # 3. Tool calling (skip extra tools if we're already escalating)
        tools_used = []
        if not escalated:
            tools_used = self._maybe_call_tools(user_message)

        # 4. Low-confidence retrieval -> ask a clarifying question instead of guessing
        if not escalated and (not retrieved_entries or top_score < RETRIEVAL_CONFIDENCE_THRESHOLD):
            reply = (
                "I couldn't confidently match that to a known issue yet. "
                "Could you share a bit more detail -- for example, any error "
                "message you see, and whether this started after a recent "
                "update or change?"
            )
            memory.add_message("assistant", reply, {"category": category, "tools_used": tools_used})
            return {
                "response": reply,
                "category": category,
                "sources": [],
                "tools_used": tools_used,
                "escalated": False,
            }

        # 5. Compose the final reply
        if escalated:
            reply = self._compose_escalation_reply(ticket_info)
        else:
            reply = self._compose_reply(user_message, retrieved_entries, tools_used, memory)

        memory.add_message(
            "assistant",
            reply,
            {"category": category, "sources": [e["id"] for e, _ in retrieved_entries], "tools_used": tools_used},
        )

        return {
            "response": reply,
            "category": category,
            "sources": [{"id": e["id"], "title": e["title"], "score": round(s, 3)} for e, s in retrieved_entries],
            "tools_used": tools_used,
            "escalated": escalated,
        }

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _maybe_call_tools(self, user_message: str) -> list:
        results = []
        for pattern, action in _TOOL_TRIGGERS:
            if pattern.search(user_message):
                if ":" in action:
                    tool_name, arg = action.split(":", 1)
                    fn = tool_module.TOOL_REGISTRY[tool_name]
                    results.append(fn(arg))
                else:
                    fn = tool_module.TOOL_REGISTRY[action]
                    if action == "search_ticket_history":
                        results.append(fn(user_message))
                    else:
                        results.append(fn())
        return results

    def _compose_reply(self, user_message: str, retrieved_entries, tools_used, memory) -> str:
        # Try LLM-enhanced synthesis first, fall back to a clear template.
        if self._llm_client is not None:
            llm_reply = self._compose_with_llm(user_message, retrieved_entries, tools_used, memory)
            if llm_reply:
                return llm_reply
        return self._compose_template_reply(retrieved_entries, tools_used)

    def _compose_template_reply(self, retrieved_entries, tools_used) -> str:
        best_entry, best_score = retrieved_entries[0]
        lines = [
            f"This looks like it's related to **{best_entry['title']}** ({best_entry['category']}). "
            f"Here's what I'd try, in order:"
        ]
        for i, step in enumerate(best_entry["solution"], start=1):
            lines.append(f"{i}. {step}")

        if tools_used:
            lines.append("")
            lines.append("I also ran a quick automated check for you:")
            for result in tools_used:
                lines.append(f"- {self._describe_tool_result(result)}")

        if len(retrieved_entries) > 1:
            others = ", ".join(e["title"] for e, _ in retrieved_entries[1:])
            lines.append("")
            lines.append(f"If that's not quite it, this could also be related to: {others}.")

        lines.append("")
        lines.append("Let me know if that resolves it, or tell me if it's still not working.")
        return "\n".join(lines)

    @staticmethod
    def _describe_tool_result(result: dict) -> str:
        tool = result.get("tool")
        if tool == "run_network_diagnostic":
            return (
                f"Network diagnostic: {result['status']} "
                f"(latency {result['avg_latency_ms']}ms, packet loss {result['packet_loss_percent']}%)."
            )
        if tool == "get_system_diagnostics":
            return (
                f"System check: CPU {result['cpu_usage_percent']}%, "
                f"RAM {result['ram_usage_percent']}%, free disk {result['disk_free_gb']}GB."
            )
        if tool == "restart_service":
            return result["message"]
        if tool == "check_service_status":
            return f"Service '{result['service']}' is currently {result['status']}."
        if tool == "search_ticket_history":
            if result["matches"]:
                match_strs = [f"{m['id']} ({m['issue']} -> {m['resolution']})" for m in result["matches"]]
                return "Similar past tickets found: " + "; ".join(match_strs)
            return "No closely matching past tickets found."
        return f"{tool} completed."

    @staticmethod
    def _compose_escalation_reply(ticket_info: dict) -> str:
        return (
            "I'm sorry the suggested steps haven't resolved this. I've escalated "
            f"the issue to a human technician -- your ticket ID is **{ticket_info['id']}** "
            f"(category: {ticket_info['category']}). They'll follow up with you shortly. "
            "Is there anything else I can help with in the meantime?"
        )

    def _compose_with_llm(self, user_message, retrieved_entries, tools_used, memory) -> str:
        try:
            context_snippets = []
            for entry, score in retrieved_entries:
                steps = "; ".join(entry["solution"])
                context_snippets.append(f"[{entry['id']}] {entry['title']} ({entry['category']}): {steps}")

            tool_snippets = [self._describe_tool_result(r) for r in tools_used]
            history = memory.recent_history(6)
            history_text = "\n".join(f"{m['role']}: {m['content']}" for m in history)

            system_prompt = (
                "You are an AI IT Helpdesk Assistant. Use ONLY the provided knowledge-base "
                "context and tool results to give a concise, friendly, numbered troubleshooting "
                "reply. Do not invent steps that aren't grounded in the context. Keep it under "
                "150 words."
            )
            user_prompt = (
                f"Conversation so far:\n{history_text}\n\n"
                f"Retrieved knowledge base context:\n" + "\n".join(context_snippets) + "\n\n"
                f"Tool results:\n" + ("\n".join(tool_snippets) if tool_snippets else "none") + "\n\n"
                f"User's latest message: {user_message}"
            )

            response = self._llm_client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=400,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text_blocks = [b.text for b in response.content if getattr(b, "type", None) == "text"]
            return "\n".join(text_blocks).strip() or None
        except Exception:
            # Any LLM/network failure silently falls back to the template reply
            return None
