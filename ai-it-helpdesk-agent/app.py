"""
app.py
------
Flask web server exposing a chat UI + JSON API for the AI IT Helpdesk Agent.

Run:
    python app.py
Then open http://127.0.0.1:5000 in your browser.
"""

import uuid

from flask import Flask, jsonify, render_template, request, session

from agent import ITHelpdeskAgent

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-me"  # replace in production / use env var

helpdesk_agent = ITHelpdeskAgent()


@app.route("/")
def index():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True) or {}
    message = (data.get("message") or "").strip()
    session_id = data.get("session_id") or session.get("session_id") or str(uuid.uuid4())
    session["session_id"] = session_id

    if not message:
        return jsonify({"error": "message is required"}), 400

    result = helpdesk_agent.handle_message(session_id, message)
    result["session_id"] = session_id
    return jsonify(result)


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "kb_size": len(helpdesk_agent.kb)})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
