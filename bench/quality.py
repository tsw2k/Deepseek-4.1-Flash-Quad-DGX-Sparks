#!/usr/bin/env python3
"""Measure how far a quantized checkpoint's next-token distribution is from the release's.

  quality.py corpus OUT_DIR
  quality.py collect --base http://10.77.1.11:8000 --corpus-dir DIR --out DIR [--tokens-from REF_DIR]
  quality.py compare REF_DIR TEST_DIR [--out report.json]

corpus   builds three small corpora and a SHA256SUMS. The texts are not kept in this repository
         (Wikipedia and WikiText are CC BY-SA); the hashes in results/ say which texts were used.
           en-wiki.txt  WikiText-2 raw test split (Salesforce/wikitext, datasets-server rows API)
           ru-wiki.txt  paragraphs of the Russian Wikipedia articles in RU_TITLES (REST HTML)
           code.txt     the Python standard library of the node running it, sorted by path
collect  tokenizes each corpus once through the server's /tokenize (or reuses the token ids of a
         previous run with --tokens-from, so reference and test score the same ids), takes
         --windows evenly spaced windows of --len tokens, and asks /v1/completions for
         prompt_logprobs (top --topk) of every position, one request at a time. Resumable.
         Long windows are costly on GB10: the logits of every prompt position are materialized.
compare  per corpus: perplexity of each run over the same tokens, top-1 agreement, and
         KL(ref || test) per position approximated over ref's top-k plus one tail bucket (a
         token missing from test's top-k gets test's lowest listed logprob, an upper bound on
         its probability, so the per-position KL is a lower bound).
"""
import argparse
import hashlib
import html.parser
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

UA = {"User-Agent": "dsv41-quality-eval/1 (https://github.com/tsw2k/Deepseek-4.1-Flash-Quad-DGX-Sparks)"}
CORPORA = ("en-wiki", "ru-wiki", "code")
RU_TITLES = [
    "Россия", "Москва", "Санкт-Петербург", "Пушкин,_Александр_Сергеевич", "Толстой,_Лев_Николаевич",
    "Великая_Отечественная_война", "Математика", "Физика", "Химия", "Биология", "Компьютер",
    "Интернет", "История_России", "Космонавтика", "Гагарин,_Юрий_Алексеевич",
]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S', time.gmtime())}] {msg}", flush=True)


def get(url, data=None, timeout=600):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None,
                                 headers={**UA, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


class Paragraphs(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth, self.skip, self.buf, self.out = 0, 0, [], []

    def handle_starttag(self, tag, attrs):
        if tag == "p":
            self.depth += 1
        elif self.depth and tag in ("sup", "style", "script"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag == "p" and self.depth:
            self.depth -= 1
            text = " ".join("".join(self.buf).split())
            if len(text) > 80:
                self.out.append(text)
            self.buf = []
        elif self.skip and tag in ("sup", "style", "script"):
            self.skip -= 1

    def handle_data(self, data):
        if self.depth and not self.skip:
            self.buf.append(data)


def build_corpus(out):
    os.makedirs(out, exist_ok=True)
    rows, off = [], 0
    while True:
        q = urllib.parse.urlencode({"dataset": "Salesforce/wikitext", "config": "wikitext-2-raw-v1",
                                    "split": "test", "offset": off, "length": 100})
        page = json.loads(get(f"https://datasets-server.huggingface.co/rows?{q}"))
        rows += [r["row"]["text"] for r in page["rows"]]
        off += 100
        if off >= page["num_rows_total"]:
            break
    open(f"{out}/en-wiki.txt", "w").write("".join(rows))
    parts = []
    for t in RU_TITLES:
        p = Paragraphs()
        p.feed(get(f"https://ru.wikipedia.org/api/rest_v1/page/html/{urllib.parse.quote(t)}").decode())
        parts.append(t.replace("_", " ") + "\n\n" + "\n\n".join(p.out))
    open(f"{out}/ru-wiki.txt", "w").write("\n\n".join(parts))
    lib = os.path.dirname(os.__file__)
    files = []
    for root, dirs, names in os.walk(lib):
        dirs[:] = sorted(d for d in dirs if d not in ("test", "tests", "idlelib", "site-packages", "dist-packages", "__pycache__"))
        files += [os.path.join(root, n) for n in sorted(names) if n.endswith(".py")]
    with open(f"{out}/code.txt", "w") as f:
        for p in sorted(files):
            f.write(f"# file: {os.path.relpath(p, lib)}\n{open(p, errors='replace').read()}\n")
    with open(f"{out}/SHA256SUMS", "w") as f:
        for c in CORPORA:
            data = open(f"{out}/{c}.txt", "rb").read()
            f.write(f"{hashlib.sha256(data).hexdigest()}  {c}.txt\n")
            log(f"{c}.txt: {len(data) / 1e6:.2f} MB")
    log(f"sources: WikiText-2 raw test, ru.wikipedia.org REST HTML ({len(RU_TITLES)} articles), Python {sys.version.split()[0]} stdlib")


def collect(a):
    os.makedirs(a.out, exist_ok=True)
    meta = {"base": a.base, "model": a.model, "windows": a.windows, "len": a.len, "topk": a.topk,
            "server_models": json.loads(get(f"{a.base}/v1/models")), "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    json.dump(meta, open(f"{a.out}/meta.json", "w"), indent=1)
    for c in CORPORA:
        tok_path = f"{a.out}/{c}.tokens.json"
        if not os.path.exists(tok_path):
            if a.tokens_from:
                ids = json.load(open(f"{a.tokens_from}/{c}.tokens.json"))
            else:
                text = open(f"{a.corpus_dir}/{c}.txt").read()
                ids = json.loads(get(f"{a.base}/tokenize", {"model": a.model, "prompt": text, "add_special_tokens": False}))["tokens"]
            json.dump(ids, open(tok_path, "w"))
        ids = json.load(open(tok_path))
        span = a.len - 1  # one BOS per window
        if len(ids) < span * a.windows:
            sys.exit(f"{c}: {len(ids)} tokens, need {span * a.windows} for {a.windows} windows of {a.len}")
        step = (len(ids) - span) // max(a.windows - 1, 1)
        out_path = f"{a.out}/{c}.jsonl"
        done = sum(1 for _ in open(out_path)) if os.path.exists(out_path) else 0
        log(f"{c}: {len(ids)} tokens, windows {done}/{a.windows} done")
        t0 = time.time()
        with open(out_path, "a") as f:
            for w in range(done, a.windows):
                prompt = [a.bos] + ids[w * step: w * step + span]
                r = json.loads(get(f"{a.base}/v1/completions", {
                    "model": a.model, "prompt": prompt, "max_tokens": 1, "temperature": 0,
                    "prompt_logprobs": a.topk}))
                pl = r["choices"][0]["prompt_logprobs"]
                pos = []
                for i in range(1, len(prompt)):
                    d = pl[i]
                    actual = d[str(prompt[i])]["logprob"]
                    top = sorted(((int(k), v["logprob"]) for k, v in d.items() if v.get("rank", 99) <= a.topk), key=lambda x: -x[1])[:a.topk]
                    pos.append([prompt[i], actual, top])
                f.write(json.dumps({"window": w, "start": w * step, "pos": pos}) + "\n")
                f.flush()
        log(f"{c}: {a.windows - done} windows in {time.time() - t0:.0f} s")
    meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    json.dump(meta, open(f"{a.out}/meta.json", "w"), indent=1)


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))]


def compare(a):
    report = {"ref": a.ref, "test": a.test, "corpora": {}}
    for c in CORPORA:
        ref = [json.loads(l) for l in open(f"{a.ref}/{c}.jsonl")]
        test = {r["window"]: r for r in map(json.loads, open(f"{a.test}/{c}.jsonl"))}
        nll_r = nll_t = 0.0
        n = agree = 0
        kls = []
        for rw in ref:
            tw = test.get(rw["window"])
            if tw is None:
                continue
            for (tok, lr, top_r), (tok2, lt, top_t) in zip(rw["pos"], tw["pos"]):
                if tok != tok2:
                    sys.exit(f"{c} window {rw['window']}: token ids differ; collect the test with --tokens-from")
                n += 1
                nll_r -= lr
                nll_t -= lt
                agree += top_r[0][0] == top_t[0][0]
                tmap = dict(top_t)
                floor = min(tmap.values())
                kl = mass_r = mass_t = 0.0
                for t, lp in top_r:
                    q = tmap.get(t, floor)
                    kl += math.exp(lp) * (lp - q)
                    mass_r += math.exp(lp)
                    mass_t += math.exp(q)
                tail_r, tail_t = max(1 - mass_r, 1e-12), max(1 - mass_t, 1e-12)
                kls.append(max(kl + tail_r * math.log(tail_r / tail_t), 0.0))
        report["corpora"][c] = {
            "positions": n, "ppl_ref": math.exp(nll_r / n), "ppl_test": math.exp(nll_t / n),
            "ppl_ratio": math.exp((nll_t - nll_r) / n), "top1_agreement": agree / n,
            "kl_mean": sum(kls) / n, "kl_p50": pct(kls, 0.5), "kl_p90": pct(kls, 0.9), "kl_p99": pct(kls, 0.99),
        }
    print(f"{'corpus':8} {'positions':>9} {'ppl ref':>8} {'ppl test':>8} {'ratio':>6} {'top1':>6} {'KL mean':>8} {'p90':>7} {'p99':>7}")
    for c, r in report["corpora"].items():
        print(f"{c:8} {r['positions']:9d} {r['ppl_ref']:8.3f} {r['ppl_test']:8.3f} {r['ppl_ratio']:6.3f} "
              f"{r['top1_agreement']:6.3f} {r['kl_mean']:8.4f} {r['kl_p90']:7.4f} {r['kl_p99']:7.4f}")
    if a.out:
        json.dump(report, open(a.out, "w"), indent=1)


ap = argparse.ArgumentParser()
sub = ap.add_subparsers(dest="cmd", required=True)
s = sub.add_parser("corpus")
s.add_argument("out")
s = sub.add_parser("collect")
s.add_argument("--base", default="http://10.77.1.11:8000")
s.add_argument("--model", default="deepseek-v4.1-flash")
s.add_argument("--corpus-dir")
s.add_argument("--tokens-from")
s.add_argument("--out", required=True)
s.add_argument("--windows", type=int, default=40)
s.add_argument("--len", type=int, default=1024)
s.add_argument("--topk", type=int, default=20)
s.add_argument("--bos", type=int, default=0)
s = sub.add_parser("compare")
s.add_argument("ref")
s.add_argument("test")
s.add_argument("--out")
a = ap.parse_args()
if a.cmd == "corpus":
    build_corpus(a.out)
elif a.cmd == "collect":
    if not (a.corpus_dir or a.tokens_from):
        sys.exit("collect needs --corpus-dir or --tokens-from")
    collect(a)
else:
    compare(a)
