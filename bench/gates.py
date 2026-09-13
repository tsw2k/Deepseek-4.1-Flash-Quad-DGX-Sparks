#!/usr/bin/env python3
"""Correctness gates. Run after every boot, before any benchmark: a fast number from a
model that emits garbage is worthless, and on this stack garbage does not crash anything
(a wrong vLLM tree under the patches boots cleanly and repeats one token; a hole in an
Engram slice reads as zeros).

usage: gates.py --base http://10.77.1.11:8000/v1 [--model deepseek-v4.1-flash] [--out gates.json]

Stdlib only. Exit 1 if any gate fails.

  identity     /v1/models serves the name, a short answer comes back
  count        count 1..100 at temperature 0, exact (DSpark accepts near the maximum here)
  greedy       the same prompt twice at temperature 0 gives identical text
  garble       30 generations, 6 in flight, temperatures 0 / 0.7 / 1.0 (Tech2Wild/Kai's gate)
  prefill      recall a fact placed at the end of ~100 to ~4000-token prompts; MiaAI saw
               garbage for prefills over 64 tokens with expandable_segments on SGLang, and
               this stack runs expandable_segments:True
  prefill_x4   the same recall, four different prompts prefilled at once
  json         response_format json_object parses
  tool         a tool call with the right function and arguments
  vision       name the colors of three generated stripes, left to right
  thinking     thinking on per request returns reasoning and a correct answer
"""
import argparse
import base64
import json
import re
import struct
import sys
import time
import urllib.request
import zlib
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

ap = argparse.ArgumentParser()
ap.add_argument("--base", required=True)
ap.add_argument("--model", default="deepseek-v4.1-flash")
ap.add_argument("--out")
args = ap.parse_args()
BASE = args.base.rstrip("/")
M = args.model


def post(body, timeout=900):
    req = urllib.request.Request(BASE + "/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def chat(content, max_tokens=200, temperature=0.0, **extra):
    body = {"model": M, "messages": [{"role": "user", "content": content}], "max_tokens": max_tokens,
            "temperature": temperature, "chat_template_kwargs": {"thinking": False}}
    body.update(extra)
    return post(body)


def text(r):
    return r["choices"][0]["message"].get("content") or ""


def garbled(t):
    if not t or not t.strip():
        return "EMPTY"
    cjk = len(re.findall(r"[一-鿿]", t))
    if cjk > len(t) * 0.10:
        return f"CJK {cjk}"
    words = re.findall(r"\S+", t)
    if len(words) > 12:
        top = Counter(words).most_common(1)[0]
        if top[1] > len(words) * 0.4:
            return f"REPEAT {top[0]!r}x{top[1]}"
    if re.search(r"(.{12,}?)\1{3,}", t):
        return "LOOPFRAG"
    return None


FILLER = ("amber basin cedar delta ember fjord garnet harbor iris juniper kestrel lumen meadow nimbus "
          "orchid pylon quartz raven sierra tundra umber vessel willow xenon yarrow zephyr").split()


def recall_prompt(words, code):
    body = " ".join(FILLER[(i * 7 + words) % len(FILLER)] for i in range(words))
    return (f"{body}\n\nThe access code is {code}. Reply with the access code only.")


def png_stripes(colors, w=90, h=30):
    rows = b""
    for _ in range(h):
        row = b"\x00"
        for x in range(w):
            row += bytes(colors[x * len(colors) // w])
        rows += row

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    return raw + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


results = {}


def gate(name):
    def wrap(fn):
        t = time.time()
        try:
            ok, detail = fn()
        except Exception as e:  # noqa: BLE001
            ok, detail = False, f"{type(e).__name__}: {e}"
        results[name] = {"pass": ok, "detail": detail, "seconds": round(time.time() - t, 1)}
        print(f"{'PASS' if ok else 'FAIL'} {name:11s} {time.time() - t:6.1f}s  {str(detail)[:150]}", flush=True)
        return fn
    return wrap


@gate("identity")
def _():
    with urllib.request.urlopen(BASE + "/models", timeout=30) as r:
        ids = [m["id"] for m in json.load(r)["data"]]
    t = text(chat("Say hello in one short sentence.", 40))
    return M in ids and not garbled(t) and len(t.strip()) > 0, f"models={ids} reply={t.strip()!r}"


@gate("count")
def _():
    t = text(chat("Count from 1 to 100, separated by spaces. Output only the numbers.", 400))
    nums = [int(x) for x in re.findall(r"\d+", t)]
    return nums == list(range(1, 101)), f"{len(nums)} numbers, tail {t.strip()[-40:]!r}"


@gate("greedy")
def _():
    p = "Explain in about 80 words why the sky is blue."
    a, b = text(chat(p, 160)), text(chat(p, 160))
    return a == b and not garbled(a), f"identical={a == b} len={len(a)}"


@gate("garble")
def _():
    prompts = [
        ("json", "Return only a JSON object with keys name (string), count (integer), tags (array of 3 strings). No prose.", 120),
        ("extract", 'Extract to JSON: "Meet Ana at 3pm Tuesday at Cafe Rio for 45 minutes." Keys: who, time, day, place, duration_min.', 120),
        ("code", "Write a Python one-liner that reverses a string s. Only the code.", 60),
    ]
    jobs = [(temp, p, mt) for temp in (0.0, 0.7, 1.0) for _, p, mt in prompts for _ in range(4 if temp else 2)]
    with ThreadPoolExecutor(max_workers=6) as ex:
        outs = list(ex.map(lambda j: text(chat(j[1], j[2], j[0])), jobs))
    bad = [(j[0], g) for j, t in zip(jobs, outs) if (g := garbled(t))]
    return len(bad) <= len(jobs) * 0.1, f"{len(jobs) - len(bad)}/{len(jobs)} clean {bad[:3]}"


@gate("prefill")
def _():
    fails = []
    for words, code in ((70, "4417"), (350, "90210"), (1500, "31337"), (3000, "77301")):
        r = chat(recall_prompt(words, code), 16)
        got = text(r)
        if code not in got:
            fails.append((r["usage"]["prompt_tokens"], got.strip()[:30]))
    return not fails, f"failures {fails}" if fails else "4 lengths recalled"


@gate("prefill_x4")
def _():
    cases = [(900 + i * 300, str(58000 + i * 111)) for i in range(4)]
    with ThreadPoolExecutor(max_workers=4) as ex:
        outs = list(ex.map(lambda c: text(chat(recall_prompt(*c), 16)), cases))
    fails = [(c[1], o.strip()[:30]) for c, o in zip(cases, outs) if c[1] not in o]
    return not fails, f"failures {fails}" if fails else "4 concurrent prefills recalled"


@gate("json")
def _():
    t = text(chat("Describe a fictional city as JSON with keys name, population (integer), districts (array of 3 strings).",
                  200, response_format={"type": "json_object"}))
    obj = json.loads(t)
    return isinstance(obj.get("population"), int) and len(obj.get("districts", [])) == 3, t.strip()[:120]


@gate("tool")
def _():
    tools = [{"type": "function", "function": {
        "name": "get_weather", "description": "Get the current weather for a city",
        "parameters": {"type": "object", "properties": {"city": {"type": "string"},
                                                        "unit": {"type": "string", "enum": ["c", "f"]}},
                       "required": ["city"]}}}]
    r = chat("What is the weather in Paris in celsius?", 200, tools=tools, tool_choice="auto")
    calls = r["choices"][0]["message"].get("tool_calls") or []
    if not calls:
        return False, f"no tool call: {text(r)[:100]!r}"
    fn = calls[0]["function"]
    a = json.loads(fn["arguments"])
    return fn["name"] == "get_weather" and "paris" in a.get("city", "").lower(), f"{fn['name']} {a}"


@gate("vision")
def _():
    img = base64.b64encode(png_stripes([(255, 0, 0), (0, 255, 0), (0, 0, 255)])).decode()
    content = [{"type": "text", "text": "The image has three vertical stripes. Name their colors left to right, comma separated, nothing else."},
               {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}}]
    t = text(chat(content, 30)).lower()
    pos = [t.find(c) for c in ("red", "green", "blue")]
    return all(p >= 0 for p in pos) and pos == sorted(pos), repr(t.strip())


@gate("thinking")
def _():
    r = post({"model": M, "messages": [{"role": "user", "content": "What is 17 * 23? Answer with the number."}],
              "max_tokens": 1500, "temperature": 0, "chat_template_kwargs": {"thinking": True}})
    msg = r["choices"][0]["message"]
    reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
    return "391" in (msg.get("content") or "") and len(reasoning) > 0, \
        f"reasoning={len(reasoning)} chars, answer={(msg.get('content') or '').strip()[:40]!r}"


passed = sum(1 for v in results.values() if v["pass"])
print(f"{passed}/{len(results)} gates passed")
if args.out:
    json.dump({"base": BASE, "model": M, "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "gates": results}, open(args.out, "w"), indent=1)
sys.exit(0 if passed == len(results) else 1)
