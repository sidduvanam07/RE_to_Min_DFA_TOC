"""
Automata Theory Toolchain
=========================
A. Regex  -> NFA  : Thompson's Construction (stack-based, handles precedence & parentheses)
B. NFA    -> DFA  : Subset Construction with correct eps-closure
C. DFA Minimization : Partition-refinement (Hopcroft-style) after removing unreachable states
D. String Testing   : Simulate DFA, output Accepted/Rejected + full transition path
"""

from __future__ import annotations
from collections import defaultdict, deque
from typing import Dict, FrozenSet, List, Optional, Set, Tuple


# ─────────────────────────────────────────────────────────────────
# SHARED STATE COUNTER
# ─────────────────────────────────────────────────────────────────

class StateCounter:
    _count = 0

    @classmethod
    def next(cls) -> int:
        s = cls._count
        cls._count += 1
        return s

    @classmethod
    def reset(cls) -> None:
        cls._count = 0


# ─────────────────────────────────────────────────────────────────
# A.  REGEX → NFA (THOMPSON'S CONSTRUCTION)
# ─────────────────────────────────────────────────────────────────

EPSILON = "eps"


class NFA:
    """Simple NFA represented as an adjacency list."""

    def __init__(self) -> None:
        # transitions[state][symbol] = set of target states
        self.transitions: Dict[int, Dict[str, Set[int]]] = defaultdict(lambda: defaultdict(set))
        self.start: int = -1
        self.accept: int = -1

    def add_transition(self, frm: int, symbol: str, to: int) -> None:
        self.transitions[frm][symbol].add(to)

    def all_states(self) -> Set[int]:
        states: Set[int] = set()
        for src, sym_map in self.transitions.items():
            states.add(src)
            for targets in sym_map.values():
                states |= targets
        states.add(self.start)
        states.add(self.accept)
        return states

    def alphabet(self) -> Set[str]:
        syms: Set[str] = set()
        for sym_map in self.transitions.values():
            syms |= set(sym_map.keys())
        syms.discard(EPSILON)
        return syms


# ── Thompson primitives ──────────────────────────────────────────

def _nfa_symbol(sym: str) -> NFA:
    """NFA that accepts exactly one symbol."""
    nfa = NFA()
    nfa.start = StateCounter.next()
    nfa.accept = StateCounter.next()
    nfa.add_transition(nfa.start, sym, nfa.accept)
    return nfa


def _nfa_epsilon() -> NFA:
    """NFA that accepts the empty string (ε)."""
    return _nfa_symbol(EPSILON)


def _nfa_concat(a: NFA, b: NFA) -> NFA:
    """Concatenation: a followed by b."""
    nfa = NFA()
    nfa.start = a.start
    nfa.accept = b.accept
    # Merge a and b transitions
    _copy_transitions(a, nfa)
    _copy_transitions(b, nfa)
    # ε from a.accept → b.start
    nfa.add_transition(a.accept, EPSILON, b.start)
    return nfa


def _nfa_union(a: NFA, b: NFA) -> NFA:
    """Union (alternation): a | b."""
    nfa = NFA()
    nfa.start = StateCounter.next()
    nfa.accept = StateCounter.next()
    _copy_transitions(a, nfa)
    _copy_transitions(b, nfa)
    nfa.add_transition(nfa.start, EPSILON, a.start)
    nfa.add_transition(nfa.start, EPSILON, b.start)
    nfa.add_transition(a.accept, EPSILON, nfa.accept)
    nfa.add_transition(b.accept, EPSILON, nfa.accept)
    return nfa


def _nfa_kleene(a: NFA) -> NFA:
    """Kleene star: a*."""
    nfa = NFA()
    nfa.start = StateCounter.next()
    nfa.accept = StateCounter.next()
    _copy_transitions(a, nfa)
    nfa.add_transition(nfa.start, EPSILON, a.start)
    nfa.add_transition(nfa.start, EPSILON, nfa.accept)
    nfa.add_transition(a.accept, EPSILON, a.start)
    nfa.add_transition(a.accept, EPSILON, nfa.accept)
    return nfa


def _nfa_plus(a: NFA) -> NFA:
    """One or more: a+ = a·a*"""
    return _nfa_concat(a, _nfa_kleene(_copy_nfa(a)))


def _nfa_optional(a: NFA) -> NFA:
    """Zero or one: a? = a | ε"""
    nfa = NFA()
    nfa.start = StateCounter.next()
    nfa.accept = StateCounter.next()
    _copy_transitions(a, nfa)
    nfa.add_transition(nfa.start, EPSILON, a.start)
    nfa.add_transition(nfa.start, EPSILON, nfa.accept)   # skip
    nfa.add_transition(a.accept, EPSILON, nfa.accept)
    return nfa


def _copy_transitions(src: NFA, dst: NFA) -> None:
    for state, sym_map in src.transitions.items():
        for sym, targets in sym_map.items():
            for t in targets:
                dst.add_transition(state, sym, t)


def _copy_nfa(src: NFA) -> NFA:
    """Return a fresh NFA with fresh state numbers, structurally identical."""
    # Build a mapping old→new states
    old_states = src.all_states()
    mapping: Dict[int, int] = {s: StateCounter.next() for s in old_states}
    nfa = NFA()
    nfa.start = mapping[src.start]
    nfa.accept = mapping[src.accept]
    for state, sym_map in src.transitions.items():
        for sym, targets in sym_map.items():
            for t in targets:
                nfa.add_transition(mapping[state], sym, mapping[t])
    return nfa


# ── Operator precedence and stack-based parser ───────────────────

def _add_explicit_concat(regex: str) -> str:
    """
    Insert an explicit concatenation operator '·' between tokens where
    concatenation is implied.
    """
    output: List[str] = []
    i = 0
    while i < len(regex):
        c = regex[i]
        output.append(c)
        if i + 1 < len(regex):
            nxt = regex[i + 1]
            # After these tokens, concatenation may follow
            if c not in ('(', '|') and nxt not in (')', '|', '*', '+', '?'):
                output.append('·')
        i += 1
    return ''.join(output)


PRECEDENCE = {'|': 1, '·': 2, '*': 3, '+': 3, '?': 3}
UNARY_OPS = {'*', '+', '?'}
BINARY_OPS = {'|', '·'}


def _to_postfix(regex: str) -> List[str]:
    """Shunting-yard algorithm → postfix (RPN) list of tokens."""
    output: List[str] = []
    op_stack: List[str] = []

    for token in regex:
        if token == '(':
            op_stack.append(token)
        elif token == ')':
            while op_stack and op_stack[-1] != '(':
                output.append(op_stack.pop())
            if not op_stack:
                raise ValueError("Mismatched parentheses in regex")
            op_stack.pop()  # pop '('
        elif token in PRECEDENCE:
            while (op_stack and op_stack[-1] != '(' and
                   op_stack[-1] in PRECEDENCE and
                   PRECEDENCE[op_stack[-1]] >= PRECEDENCE[token]):
                output.append(op_stack.pop())
            op_stack.append(token)
        else:
            # Literal character
            output.append(token)

    while op_stack:
        top = op_stack.pop()
        if top in ('(', ')'):
            raise ValueError("Mismatched parentheses in regex")
        output.append(top)

    return output


def regex_to_nfa(regex: str) -> NFA:
    """
    Convert a regular expression string to an NFA using Thompson's construction.

    Supported syntax:
        a·b  or  ab   → concatenation
        a|b          → union / alternation
        a*           → Kleene star (zero or more)
        a+           → one or more
        a?           → zero or one
        (a|b)*       → grouping
    """
    StateCounter.reset()

    if not regex:
        return _nfa_epsilon()

    augmented = _add_explicit_concat(regex)
    postfix = _to_postfix(augmented)

    stack: List[NFA] = []

    for token in postfix:
        if token == '·':
            if len(stack) < 2:
                raise ValueError("Invalid regex: not enough operands for '·'")
            b = stack.pop()
            a = stack.pop()
            stack.append(_nfa_concat(a, b))
        elif token == '|':
            if len(stack) < 2:
                raise ValueError("Invalid regex: not enough operands for '|'")
            b = stack.pop()
            a = stack.pop()
            stack.append(_nfa_union(a, b))
        elif token == '*':
            if not stack:
                raise ValueError("Invalid regex: '*' has no operand")
            a = stack.pop()
            stack.append(_nfa_kleene(a))
        elif token == '+':
            if not stack:
                raise ValueError("Invalid regex: '+' has no operand")
            a = stack.pop()
            stack.append(_nfa_plus(a))
        elif token == '?':
            if not stack:
                raise ValueError("Invalid regex: '?' has no operand")
            a = stack.pop()
            stack.append(_nfa_optional(a))
        else:
            stack.append(_nfa_symbol(token))

    if len(stack) != 1:
        raise ValueError("Invalid regex expression")

    return stack[0]


# ─────────────────────────────────────────────────────────────────
# B.  NFA → DFA (SUBSET CONSTRUCTION)
# ─────────────────────────────────────────────────────────────────

class DFA:
    """DFA with named states (strings like 'q0', 'q1', …)."""

    def __init__(self) -> None:
        self.states: List[str] = []
        self.alphabet: Set[str] = set()
        self.transitions: Dict[str, Dict[str, str]] = {}  # state → {symbol → state}
        self.start: str = ""
        self.accept_states: Set[str] = set()
        # Map from DFA state name → frozenset of NFA states (for debugging)
        self.state_map: Dict[str, FrozenSet[int]] = {}

    def add_state(self, name: str, nfa_states: FrozenSet[int]) -> None:
        self.states.append(name)
        self.transitions[name] = {}
        self.state_map[name] = nfa_states

    def add_transition(self, frm: str, sym: str, to: str) -> None:
        self.transitions[frm][sym] = to


def _epsilon_closure(nfa: NFA, states: Set[int]) -> FrozenSet[int]:
    """Return the eps-closure of a set of NFA states."""
    closure: Set[int] = set(states)
    worklist = deque(states)
    while worklist:
        s = worklist.popleft()
        for t in nfa.transitions[s].get(EPSILON, set()):
            if t not in closure:
                closure.add(t)
                worklist.append(t)
    return frozenset(closure)


def _move(nfa: NFA, states: FrozenSet[int], symbol: str) -> Set[int]:
    """Return the set of NFA states reachable from `states` on `symbol`."""
    result: Set[int] = set()
    for s in states:
        result |= nfa.transitions[s].get(symbol, set())
    return result


def nfa_to_dfa(nfa: NFA) -> DFA:
    """Subset (powerset) construction NFA -> DFA."""
    dfa = DFA()
    dfa.alphabet = nfa.alphabet()

    start_closure = _epsilon_closure(nfa, {nfa.start})
    state_id: Dict[FrozenSet[int], str] = {}
    counter = 0

    def get_name(fs: FrozenSet[int]) -> str:
        nonlocal counter
        if fs not in state_id:
            name = f"q{counter}"
            counter += 1
            state_id[fs] = name
            dfa.add_state(name, fs)
            if nfa.accept in fs:
                dfa.accept_states.add(name)
        return state_id[fs]

    dfa.start = get_name(start_closure)
    worklist: deque[FrozenSet[int]] = deque([start_closure])

    while worklist:
        current_fs = worklist.popleft()
        current_name = state_id[current_fs]

        for sym in sorted(dfa.alphabet):
            moved = _move(nfa, current_fs, sym)
            if not moved:
                continue
            target_fs = _epsilon_closure(nfa, moved)
            is_new = target_fs not in state_id
            target_name = get_name(target_fs)
            dfa.add_transition(current_name, sym, target_name)
            if is_new:
                worklist.append(target_fs)

    return dfa


# ─────────────────────────────────────────────────────────────────
# C.  DFA MINIMIZATION (PARTITION REFINEMENT)
# ─────────────────────────────────────────────────────────────────

def _reachable_states(dfa: DFA) -> Set[str]:
    """BFS/DFS to find all states reachable from start."""
    visited: Set[str] = set()
    queue = deque([dfa.start])
    while queue:
        s = queue.popleft()
        if s in visited:
            continue
        visited.add(s)
        for sym, t in dfa.transitions.get(s, {}).items():
            if t not in visited:
                queue.append(t)
    return visited


def minimize_dfa(dfa: DFA) -> DFA:
    """
    Hopcroft / partition-refinement DFA minimisation.
    1. Remove unreachable states.
    2. Initial partition: accepting vs non-accepting.
    3. Iteratively refine partitions.
    4. Build the minimised DFA.
    """
    # ── Step 1: remove unreachable states ───────────────────────
    reachable = _reachable_states(dfa)
    live_accept = dfa.accept_states & reachable
    live_non_accept = reachable - live_accept

    if not live_non_accept and not live_accept:
        raise ValueError("DFA has no reachable states")

    # ── Step 2: initial partition ────────────────────────────────
    partitions: List[FrozenSet[str]] = []
    if live_accept:
        partitions.append(frozenset(live_accept))
    if live_non_accept:
        partitions.append(frozenset(live_non_accept))

    # Map state → partition index
    def state_to_part(state: str) -> int:
        for i, p in enumerate(partitions):
            if state in p:
                return i
        return -1  # dead/unreachable

    # ── Step 3: refinement ───────────────────────────────────────
    changed = True
    while changed:
        changed = False
        new_partitions: List[FrozenSet[str]] = []
        for group in partitions:
            # Split group by distinguishability signature
            sig: Dict[str, Tuple] = {}
            for s in group:
                key = tuple(
                    state_to_part(dfa.transitions[s][sym]) if sym in dfa.transitions.get(s, {}) else -1
                    for sym in sorted(dfa.alphabet)
                )
                sig[s] = key

            # Group states with identical signatures
            buckets: Dict[Tuple, List[str]] = defaultdict(list)
            for s, k in sig.items():
                buckets[k].append(s)

            if len(buckets) > 1:
                changed = True
            for bucket in buckets.values():
                new_partitions.append(frozenset(bucket))

        partitions = new_partitions

    # ── Step 4: build minimised DFA ─────────────────────────────
    min_dfa = DFA()
    min_dfa.alphabet = dfa.alphabet.copy()

    # Name each partition group
    group_name: Dict[FrozenSet[str], str] = {}
    for i, p in enumerate(partitions):
        group_name[p] = f"q{i}"

    def group_of(state: str) -> Optional[str]:
        for p, name in group_name.items():
            if state in p:
                return name
        return None

    for p, name in group_name.items():
        # Pick any representative
        rep = next(iter(p))
        min_dfa.add_state(name, frozenset())
        if rep in dfa.accept_states:
            min_dfa.accept_states.add(name)

    # Start state
    min_dfa.start = group_of(dfa.start)  # type: ignore

    # Transitions
    for p, name in group_name.items():
        rep = next(iter(p))
        for sym in sorted(dfa.alphabet):
            if sym in dfa.transitions.get(rep, {}):
                target = dfa.transitions[rep][sym]
                if target in reachable:
                    min_dfa.add_transition(name, sym, group_of(target))  # type: ignore

    return min_dfa


# ─────────────────────────────────────────────────────────────────
# D.  STRING TESTING (DFA SIMULATION)
# ─────────────────────────────────────────────────────────────────

def test_string(dfa: DFA, input_string: str) -> Tuple[bool, List[Tuple[str, str, str]]]:
    """
    Simulate the DFA on `input_string`.

    Returns:
        accepted : bool
        path     : list of (current_state, symbol, next_state)
    """
    current = dfa.start
    path: List[Tuple[str, str, str]] = []

    for ch in input_string:
        if ch not in dfa.alphabet:
            # Symbol not in alphabet -> immediate reject
            return False, path
        if ch in dfa.transitions.get(current, {}):
            nxt = dfa.transitions[current][ch]
            path.append((current, ch, nxt))
            current = nxt
        else:
            # No transition → stuck (dead/reject)
            return False, path

    accepted = current in dfa.accept_states
    return accepted, path


# ─────────────────────────────────────────────────────────────────
# PRETTY-PRINT HELPERS
# ─────────────────────────────────────────────────────────────────

def print_nfa(nfa: NFA) -> None:
    print("\n" + "=" * 50)
    print("  NFA  (Thompson's Construction)")
    print("=" * 50)
    print(f"  Start state : q{nfa.start}")
    print(f"  Accept state: q{nfa.accept}")
    print("  Transitions:")
    for state in sorted(nfa.transitions):
        for sym, targets in sorted(nfa.transitions[state].items()):
            for t in sorted(targets):
                print(f"    q{state} --[{sym}]--> q{t}")
    print()


def print_dfa(dfa: DFA, title: str = "DFA") -> None:
    print("\n" + "=" * 50)
    print(f"  {title}")
    print("=" * 50)
    print(f"  Start state  : {dfa.start}")
    print(f"  Accept states: {sorted(dfa.accept_states)}")
    print("  Transitions:")
    for state in sorted(dfa.states):
        for sym in sorted(dfa.alphabet):
            if sym in dfa.transitions.get(state, {}):
                t = dfa.transitions[state][sym]
                mark = " [*]" if state in dfa.accept_states else ""
                print(f"    {state}{mark} --[{sym}]--> {t}")
    print()


def print_test_result(input_string: str, accepted: bool,
                       path: List[Tuple[str, str, str]]) -> None:
    print("\n" + "-" * 50)
    print(f"  String Testing : \"{input_string}\"")
    print("-" * 50)
    if path:
        print("  Transition path:")
        for frm, sym, to in path:
            print(f"    {frm} --[{sym}]--> {to}")
    else:
        if input_string == "":
            print("  (empty string - no transitions taken)")
        else:
            print("  (no valid transitions from start)")
    verdict = "[ACCEPTED]" if accepted else "[REJECTED]"
    print(f"\n  Result: {verdict}")
    print("-" * 50)


# ─────────────────────────────────────────────────────────────────
# MAIN  – interactive demo
# ─────────────────────────────────────────────────────────────────

def run_pipeline(regex: str, test_inputs: List[str],
                 verbose_nfa: bool = True) -> None:
    """
    End-to-end pipeline:
        regex  ->  NFA  ->  DFA  ->  Minimized DFA  ->  string tests
    """
    print("\n" + "#" * 50)
    print(f"  Regex: {regex}")
    print("#" * 50)

    # A. Regex -> NFA
    nfa = regex_to_nfa(regex)
    if verbose_nfa:
        print_nfa(nfa)

    # B. NFA -> DFA
    dfa = nfa_to_dfa(nfa)
    print_dfa(dfa, "DFA  (Subset Construction)")

    # C. DFA Minimization
    min_dfa = minimize_dfa(dfa)
    print_dfa(min_dfa, "Minimized DFA  (Partition Refinement)")

    # D. String testing
    print("\n  ── String Testing ──")
    for s in test_inputs:
        accepted, path = test_string(min_dfa, s)
        print_test_result(s, accepted, path)


# ─────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  AUTOMATA THEORY TOOLCHAIN")
    print("  Regex -> NFA -> DFA -> Minimized DFA -> String Testing")
    print("=" * 60)

    mode = input("\n  Run [1] Demo examples  or  [2] Custom input? (1/2): ").strip()

    if mode == "1":
        # ── Example 1: (a|b)*abb ────────────────────────────────
        run_pipeline(
            regex="(a|b)*abb",
            test_inputs=["abb", "aabb", "babb", "ab", "bb", "ababb", ""],
        )

        # ── Example 2: a(b|c)* ──────────────────────────────────
        run_pipeline(
            regex="a(b|c)*",
            test_inputs=["a", "ab", "ac", "abc", "abcc", "b", ""],
        )

        # ── Example 3: (ab)+ ────────────────────────────────────
        run_pipeline(
            regex="(ab)+",
            test_inputs=["ab", "abab", "ababab", "a", "b", ""],
        )

    else:
        # ── Custom interactive mode ──────────────────────────────
        regex = input("\n  Enter regular expression: ").strip()
        if not regex:
            print("  [!] Empty regex — exiting.")
        else:
            nfa = regex_to_nfa(regex)
            print_nfa(nfa)

            dfa = nfa_to_dfa(nfa)
            print_dfa(dfa, "DFA  (Subset Construction)")

            min_dfa = minimize_dfa(dfa)
            print_dfa(min_dfa, "Minimized DFA  (Partition Refinement)")

            print("\n  Enter strings to test (blank line to stop):")
            while True:
                s = input("    Input string: ")
                if s == "":
                    break
                accepted, path = test_string(min_dfa, s)
                print_test_result(s, accepted, path)

    print("\n  Done.")
