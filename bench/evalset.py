#!/usr/bin/env python3
"""Answer accuracy on fixed public question sets: is a checkpoint better or worse at the job.

The quality probe (quality.py) asks whether the serving stack reproduces a reference
distribution; it cannot rank two different checkpoints, whose distributions legitimately
differ. This scores answers instead, the same questions in the same order every run:

  gsm8k     grade-school math (openai/gsm8k, test), exact match on the final number
  mmlupro   multiple choice over 14 subjects (TIGER-Lab/MMLU-Pro, test), exact match on the letter

  evalset.py fetch DIR [--gsm8k 250] [--mmlupro 280]      once: evenly spaced rows, cached as JSON
                                                          (needs pyarrow; see cmd_fetch)
  evalset.py run DIR --base http://10.77.1.11:8000 --out FILE [--concurrency 4]

Temperature 0, thinking off (the serving default), one answer per question. Besides accuracy
it records completion tokens per answer: 1017 claims shorter outputs.
"""
import argparse, json, os, re, statistics as st, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

PARQUET = {
    "gsm8k": ("openai/gsm8k main test",
              "https://huggingface.co/datasets/openai/gsm8k/resolve/main/main/test-00000-of-00001.parquet"),
    "mmlupro": ("TIGER-Lab/MMLU-Pro test",
                "https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro/resolve/main/data/test-00000-of-00001.parquet"),
}


def cmd_fetch(a):
    """Download each test split as parquet (a few MB) and keep n rows as n/10 evenly spaced
    blocks of 10 consecutive rows. Needs pyarrow (a venv: python3 -m venv .venv && .venv/bin/pip
    install pyarrow); `run` needs nothing beyond the standard library."""
    import pyarrow.parquet as pq
    os.makedirs(a.dir, exist_ok=True)
    for name, n in (("gsm8k", a.gsm8k), ("mmlupro", a.mmlupro)):
        label, url = PARQUET[name]
        path = os.path.join(a.dir, f"{name}-test.parquet")
        if not os.path.exists(path):
            urllib.request.urlretrieve(url, path)
        rows = pq.read_table(path).to_pylist()
        offsets = [blk * len(rows) // (n // 10) + k for blk in range(n // 10) for k in range(10)]
        keep = ("question", "answer", "options", "category")
        sel = [{k: v for k, v in rows[o].items() if k in keep} for o in offsets]
        json.dump({"dataset": label, "offsets": offsets, "rows": sel}, open(os.path.join(a.dir, f"{name}.json"), "w"))
        print(f"{name}: {len(sel)} of {len(rows)} rows")


def chat(base, model, prompt, max_tokens):
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens,
            "temperature": 0, "chat_template_kwargs": {"thinking": False}}
    req = urllib.request.Request(base + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        res = json.load(r)
    msg = res["choices"][0]["message"]
    return (msg.get("content") or ""), res["usage"]["completion_tokens"], res["choices"][0]["finish_reason"], time.time() - t0


def last_number(text):
    m = re.findall(r"-?\d[\d,]*\.?\d*", text.replace("$", ""))
    return m[-1].replace(",", "").rstrip(".") if m else None


def norm_num(s):
    try:
        v = float(s)
        return str(int(v)) if v == int(v) else str(v)
    except (TypeError, ValueError):
        return None


def items(dir_):
    g = json.load(open(os.path.join(dir_, "gsm8k.json")))["rows"]
    for i, r in enumerate(g):
        yield ("gsm8k", i, r["question"] + "\n\nSolve the problem. End your answer with a line of the form "
               "'Answer: <number>'.", r["answer"].split("####")[-1].strip(), 1024)
    m = json.load(open(os.path.join(dir_, "mmlupro.json")))["rows"]
    for i, r in enumerate(m):
        letters = "ABCDEFGHIJ"[:len(r["options"])]
        opts = "\n".join(f"{l}. {o}" for l, o in zip(letters, r["options"]))
        yield ("mmlupro", i, f"{r['question']}\n\n{opts}\n\nThink briefly, then end your answer with a line of the "
               "form 'Answer: <letter>'.", r["answer"], 1024)


def grade(kind, text, gold):
    tail = re.findall(r"Answer:\s*\**\s*([^\n*]+)", text)
    pick = tail[-1].strip() if tail else ""
    if kind == "gsm8k":
        got = norm_num(last_number(pick) or last_number(text))
        return got, got is not None and got == norm_num(gold.replace(",", ""))
    m = re.match(r"\(?([A-J])\b", pick)
    got = m.group(1) if m else None
    return got, got == gold


def cmd_run(a):
    todo = list(items(a.dir))

    def one(it):
        kind, i, prompt, gold, mt = it
        try:
            text, ct, fin, dt = chat(a.base, a.model, prompt, mt)
        except Exception as e:  # noqa: BLE001
            return {"set": kind, "i": i, "error": str(e)}
        got, ok = grade(kind, text, gold)
        return {"set": kind, "i": i, "gold": gold, "got": got, "ok": ok, "tokens": ct, "finish": fin, "s": round(dt, 2)}

    t0 = time.time()
    with ThreadPoolExecutor(a.concurrency) as ex:
        res = list(ex.map(one, todo))
    summary = {}
    for kind in ("gsm8k", "mmlupro"):
        r = [x for x in res if x["set"] == kind]
        ok = [x for x in r if x.get("ok")]
        toks = [x["tokens"] for x in r if "tokens" in x]
        summary[kind] = {"n": len(r), "correct": len(ok), "accuracy": round(len(ok) / len(r), 4) if r else None,
                         "errors": sum(1 for x in r if "error" in x),
                         "truncated": sum(1 for x in r if x.get("finish") == "length"),
                         "tokens_median": st.median(toks) if toks else None,
                         "tokens_mean": round(st.mean(toks), 1) if toks else None}
    out = {"base": a.base, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0),
           "concurrency": a.concurrency, "summary": summary, "results": res}
    json.dump(out, open(a.out, "w"), indent=1)
    for k, v in summary.items():
        print(f"{k}: {v['correct']}/{v['n']} = {v['accuracy']}, tokens median {v['tokens_median']}, "
              f"truncated {v['truncated']}, errors {v['errors']}")


ap = argparse.ArgumentParser()
sub = ap.add_subparsers(dest="cmd", required=True)
f = sub.add_parser("fetch"); f.add_argument("dir"); f.add_argument("--gsm8k", type=int, default=250)
f.add_argument("--mmlupro", type=int, default=280)
r = sub.add_parser("run"); r.add_argument("dir"); r.add_argument("--base", required=True)
r.add_argument("--model", default="deepseek-v4.1-flash"); r.add_argument("--out", required=True)
r.add_argument("--concurrency", type=int, default=4)
a = ap.parse_args()
{"fetch": cmd_fetch, "run": cmd_run}[a.cmd](a)
