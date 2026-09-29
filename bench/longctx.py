#!/usr/bin/env python3
"""Long-context, single-stream timings: the shape of the traffic this cluster actually serves.

The proxy log (results/2026-09-29-traffic-profile) shows one agent at a time with a 100-190K-token
context and short answers. What its user waits for is time to first token, cold (a prefix-cache miss
pays the whole prefill) and warm (the next turn reuses the cached prefix), and decode with that
context behind it. The fixed-prompt benchmark (bench/tony/) measures neither: its prompts are short
and its levels go to six streams.

Per repetition, one request at a time:
  cold  a user turn of --tokens tokens of code, with a tag at the front unique within the run
  warm  the same conversation one turn later: that turn, the answer to it, and a new user turn of
        --append tokens; everything up to the new turn is in the prefix cache
Both ask for exactly --answer tokens (ignore_eos), so decode is measured over the same length. The
engine's prefix-cache counters are read around every request: a "cold" request that hit the cache
(a run without a relaunch in front of it) is reported, not averaged in silently.

The text is the code corpus of bench/quality.py (its SHA-256 is recorded), so the prompt is the same
across boots. Temperature 0, thinking off, as in bench/tony/.

usage: longctx.py --base http://10.77.1.11:8000 --out longctx.json
       [--corpus /home/mtxc/dsv41-quality/corpus/code.txt] [--tokens 150000] [--append 2000]
       [--answer 256] [--reps 2]
"""
import argparse, hashlib, json, re, statistics as st, time, urllib.request

VERSION = "v1"


def post(url, body, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def cache_counters(base):
    """Prefix-cache queries and hits, in tokens, summed over engines; None if not exported."""
    with urllib.request.urlopen(base + "/metrics", timeout=10) as r:
        text = r.read().decode()
    out = {}
    for name in ("prefix_cache_queries", "prefix_cache_hits"):
        vals = re.findall(rf"^vllm:{name}(?:_total)?(?:{{[^}}]*}})? ([0-9.e+]+)$", text, re.M)
        out[name] = sum(float(v) for v in vals) if vals else None
    return out


def cut(base, model, text, tokens):
    """The longest line-aligned prefix of text that tokenizes to at most `tokens` tokens."""
    def count(t):
        return post(base + "/tokenize", {"model": model, "prompt": t, "add_special_tokens": False})["count"]
    n = min(len(text), tokens * 4)
    for _ in range(6):
        c = count(text[:n])
        if abs(c - tokens) <= tokens * 0.002:
            break
        n = int(n * tokens / c)
    n = text.rfind("\n", 0, n) + 1 or n
    return text[:n]


def stream(base, model, messages, answer, timeout=1800):
    body = {"model": model, "messages": messages, "max_tokens": answer, "min_tokens": answer, "ignore_eos": True,
            "temperature": 0, "stream": True, "stream_options": {"include_usage": True},
            "chat_template_kwargs": {"thinking": False}}
    req = urllib.request.Request(base + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time(); ttft = None; usage = None; parts = []
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for raw in r:
            line = raw.decode("utf-8", "ignore").strip()
            if not line.startswith("data:") or line[5:].strip() == "[DONE]":
                continue
            ev = json.loads(line[5:])
            if ev.get("usage"):
                usage = ev["usage"]
            for ch in ev.get("choices") or []:
                piece = (ch.get("delta") or {}).get("content") or ""
                if piece:
                    ttft = ttft if ttft is not None else time.time() - t0
                    parts.append(piece)
    total = time.time() - t0
    ct = (usage or {}).get("completion_tokens", 0); pt = (usage or {}).get("prompt_tokens", 0)
    return {"prompt_tokens": pt, "completion_tokens": ct, "ttft_s": ttft, "total_s": total,
            "decode_tok_s": (ct - 1) / (total - ttft) if ttft is not None and ct > 1 and total > ttft else None,
            "text": "".join(parts)}


def measured(base, model, messages, answer):
    c0 = cache_counters(base)
    r = stream(base, model, messages, answer)
    c1 = cache_counters(base)
    if None not in c0.values() and None not in c1.values():
        r["cache_queried_tokens"] = int(c1["prefix_cache_queries"] - c0["prefix_cache_queries"])
        r["cache_hit_tokens"] = int(c1["prefix_cache_hits"] - c0["prefix_cache_hits"])
    new = r["prompt_tokens"] - r.get("cache_hit_tokens", 0)
    r["prefill_tok_s"] = new / r["ttft_s"] if r["ttft_s"] else None
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="engine root, without /v1")
    ap.add_argument("--model", default="deepseek-v4.1-flash")
    ap.add_argument("--corpus", default="/home/mtxc/dsv41-quality/corpus/code.txt")
    ap.add_argument("--tokens", type=int, default=150000)
    ap.add_argument("--append", type=int, default=2000)
    ap.add_argument("--answer", type=int, default=256)
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    raw = open(a.corpus, "rb").read()
    text = raw.decode("utf-8", "ignore")
    body = cut(a.base, a.model, text, a.tokens)
    extra = cut(a.base, a.model, text[len(body):], a.append)
    ask = "\n\nWhat does the last function in the code above do? Answer in a few sentences."
    ask2 = "\n\nThe code above was appended to the file. What changed, and does it interact with the earlier code?"

    reps = []
    for i in range(a.reps):
        tag = f"[longctx {VERSION} r{i}]\n"
        turn1 = [{"role": "user", "content": tag + body + ask}]
        cold = measured(a.base, a.model, turn1, a.answer)
        turn2 = turn1 + [{"role": "assistant", "content": cold["text"]}, {"role": "user", "content": extra + ask2}]
        warm = measured(a.base, a.model, turn2, a.answer)
        for name, r in (("cold", cold), ("warm", warm)):
            r.pop("text")
            print(f"r{i} {name}: prompt {r['prompt_tokens']} cached {r.get('cache_hit_tokens', '?')} "
                  f"ttft {r['ttft_s']:.2f}s prefill {r['prefill_tok_s'] or 0:.0f} tok/s "
                  f"decode {r['decode_tok_s'] or 0:.1f} tok/s", flush=True)
        reps.append({"cold": cold, "warm": warm})

    def med(kind, key):
        v = [r[kind][key] for r in reps if r[kind].get(key) is not None]
        return round(st.median(v), 2) if v else None
    dirty = [i for i, r in enumerate(reps) if r["cold"].get("cache_hit_tokens", 0) > r["cold"]["prompt_tokens"] * 0.05]
    summary = {k: med(*k.split(".")) for k in
               ("cold.ttft_s", "cold.prefill_tok_s", "cold.decode_tok_s", "warm.ttft_s", "warm.decode_tok_s")}
    json.dump({"version": VERSION, "corpus": a.corpus, "corpus_sha256": hashlib.sha256(raw).hexdigest(),
               "tokens": a.tokens, "append": a.append, "answer": a.answer, "summary": summary,
               "cold_runs_that_hit_the_cache": dirty, "reps": reps,
               "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, open(a.out, "w"), indent=1)
    print("summary: " + " ".join(f"{k} {v}" for k, v in summary.items()))
    if dirty:
        print(f"WARNING: cold repetitions {dirty} found the prompt in the prefix cache: relaunch before measuring")


if __name__ == "__main__":
    main()
