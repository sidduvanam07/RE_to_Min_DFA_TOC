"""app.py – Flask web server for Automata Toolchain."""

from flask import Flask, request, jsonify, render_template
from p1 import regex_to_nfa, nfa_to_dfa, minimize_dfa, test_string, NFA, DFA

app = Flask(__name__)

# ── Serializers ────────────────────────────────────────────────────

def serialize_nfa(nfa):
    transitions = []
    for state in sorted(nfa.transitions):
        for sym, targets in sorted(nfa.transitions[state].items()):
            for t in sorted(targets):
                transitions.append({"from": f"q{state}", "symbol": sym, "to": f"q{t}"})
    return {
        "label": "NFA — Thompson's Construction",
        "states": [f"q{s}" for s in sorted(nfa.all_states())],
        "start": f"q{nfa.start}",
        "accept": [f"q{nfa.accept}"],
        "alphabet": sorted(nfa.alphabet()),
        "transitions": transitions,
    }

def serialize_dfa(dfa, label):
    transitions = []
    for state in sorted(dfa.states):
        for sym in sorted(dfa.alphabet):
            if sym in dfa.transitions.get(state, {}):
                transitions.append({"from": state, "symbol": sym, "to": dfa.transitions[state][sym]})
    return {
        "label": label,
        "states": sorted(dfa.states),
        "start": dfa.start,
        "accept": sorted(dfa.accept_states),
        "alphabet": sorted(dfa.alphabet),
        "transitions": transitions,
    }

# ── Routes ─────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/run", methods=["POST"])
def api_run():
    body = request.get_json(force=True)
    regex = (body.get("regex") or "").strip()
    inputs = body.get("inputs") or []
    if not regex:
        return jsonify({"error": "regex is required"}), 400
    try:
        nfa = regex_to_nfa(regex)
        dfa = nfa_to_dfa(nfa)
        min_dfa = minimize_dfa(dfa)
        results = []
        for s in inputs:
            accepted, path = test_string(min_dfa, s)
            results.append({
                "input": s, "accepted": accepted,
                "path": [{"from": f, "symbol": sym, "to": t} for f, sym, t in path],
            })
        return jsonify({
            "error": None,
            "nfa": serialize_nfa(nfa),
            "dfa": serialize_dfa(dfa, "DFA — Subset Construction"),
            "min_dfa": serialize_dfa(min_dfa, "Minimized DFA — Partition Refinement"),
            "results": results,
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400

# ── Entry ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("  Automata Toolchain  |  http://127.0.0.1:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)
