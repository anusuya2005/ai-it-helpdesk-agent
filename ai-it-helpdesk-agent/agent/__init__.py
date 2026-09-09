"""
AI IT Helpdesk Agent
=====================
An agentic AI system that diagnoses common IT issues and recommends
troubleshooting steps using Retrieval-Augmented Generation (RAG),
Tool Calling, and Memory.

Modules:
    knowledge_base  - loads and exposes the IT issue knowledge base
    rag             - lightweight TF-IDF based retriever (zero heavy deps)
    tools           - simulated IT support tools the agent can call
    memory          - per-session conversation + issue-state memory
    agent           - the orchestrating agent (Agent + RAG + Tools + Memory)
"""

from .agent import ITHelpdeskAgent

__all__ = ["ITHelpdeskAgent"]
__version__ = "1.0.0"
