# Regular Expression to Minimization of DFA

# Automata Theory Toolchain

A web-based visualizer and simulator for Automata Theory. This toolchain allows you to define a regular expression and witness its transformation step-by-step through the classic automata theory pipeline.

## Features

- **Regex to NFA:** Converts a regular expression to a Nondeterministic Finite Automaton using **Thompson's Construction**.
- **NFA to DFA:** Converts the NFA to a Deterministic Finite Automaton using **Subset Construction**.
- **DFA Minimization:** Optimizes the DFA using **Partition Refinement (Hopcroft's algorithm)**.
- **Interactive Visualization:** Graphically renders the generated NFA, DFA, and Minimized DFA using Cytoscape.js.

## String Simulation

The **Simulation** feature is the core interactive component of this toolchain. It allows you to test custom input strings against your defined regular expression to see if they are **Accepted** or **Rejected** by the generated automaton.

**How the Simulation Engine Works:**
1. **DFA Traversal:** The string is processed character by character through the **Minimized DFA**.
2. **Transition Tracking:** Every state transition is recorded to build a complete execution path.
3. **Verdict Generation:** If the simulation ends on an **Accept State**, the string is classified as valid for the language. If it ends on a non-accepting state or encounters a missing transition, it is rejected.
4. **Visual Feedback:** The user interface displays the exact path taken through the graph (e.g., `q0 --[a]--> q1 --[b]--> q2`), making it easy to debug *why* a string was accepted or rejected. 

This step-by-step traceability makes it an invaluable educational tool for understanding how abstract mathematical machines process strings in real-time.

## Deployment

This application is ready to be deployed on platforms like Render. It uses `gunicorn` as the WSGI HTTP server in production.
