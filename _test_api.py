import urllib.request, json

payload = json.dumps({"regex": "(a|b)*abb", "inputs": ["abb", "ab", "babb", ""]}).encode()
req = urllib.request.Request(
    "http://127.0.0.1:5000/api/run",
    data=payload,
    headers={"Content-Type": "application/json"}
)
resp = urllib.request.urlopen(req)
body = json.loads(resp.read())

print("NFA states  :", body["nfa"]["states"])
print("NFA accept  :", body["nfa"]["accept"])
print("DFA accept  :", body["dfa"]["accept"])
print("MinDFA accept:", body["min_dfa"]["accept"])
print("\nString Test Results:")
for r in body["results"]:
    verdict = "ACCEPTED" if r["accepted"] else "REJECTED"
    steps = " -> ".join(f"{s['from']}--[{s['symbol']}]-->{s['to']}" for s in r["path"])
    print(f"  {r['input']!r:12s}  {verdict:8s}  path: {steps or '(none)'}")
