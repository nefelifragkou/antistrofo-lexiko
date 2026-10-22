"""Βήμα 7: βαθμολόγηση των απαντήσεων των LLM και σύγκριση με το λεξικό.

Είσοδος : eval_results_dictionary.csv  (από το κομμάτι «Αξιολόγηση» της σελίδας)
          llm_answers_chatgpt.txt, llm_answers_gemini.txt (μία γραμμή «N. λέξη, λέξη, …» ανά περιγραφή)
          data/processed/senses.jsonl   (για τους εναλλακτικούς τύπους και το «υπάρχει στο λεξικό;»)
Έξοδος  : comparison.json (το διαβάζει το results_workbook.py)

Κανόνας ταύτισης (ίδιος για όλα τα συστήματα): χωρίς τόνους και κεφαλαία· δεκτοί οι εναλλακτικοί
τύποι του λεξικού (τριγυρίζω / τριγυρνώ) και το -άω/-ώ των ρημάτων (ξενυχτάω = ξενυχτώ).
"""
import csv
import json
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root))
from evaluate import norm  # noqa: E402

SYSTEMS = {"llm": "llm_answers_chatgpt.txt", "gem": "llm_answers_gemini.txt"}


def same(w, t):
    w, t = norm(w), norm(t)
    return w == t or (w.endswith("αω") and w[:-2] + "ω" == t) or (t.endswith("αω") and t[:-2] + "ω" == w)


def read_answers(path):
    out = {}
    for line in open(path, encoding="utf-8"):
        m = re.match(r"\s*(\d+)\.\s*(.+)", line)
        if m:
            out[int(m.group(1))] = [w.strip() for w in m.group(2).split(",") if w.strip()][:10]
    return out


def main():
    senses = [json.loads(l) for l in open(root / "data/processed/senses.jsonl", encoding="utf-8")]
    vocab = {norm(s["headword"]) for s in senses} | {norm(a) for s in senses for a in s["alt_forms"]}
    alt = {}
    for s in senses:
        alt.setdefault(norm(s["headword"]), set()).update(norm(a) for a in s["alt_forms"])
    dict_rows = list(csv.DictReader(open(root / "eval_results_dictionary.csv", encoding="utf-8-sig")))
    answers = {k: read_answers(root / f) for k, f in SYSTEMS.items()}

    rows = []
    for d in dict_rows:
        i, target = int(d["id"]), d["target"]
        row = dict(id=i, target=target, difficulty=d["difficulty"], pos=d["pos"], same_root=d["same_root"],
                   dict_rank=int(float(d["rank"])) if d["rank"] else None)
        for key, ans in answers.items():
            words = ans[i]
            ok = lambda w: same(w, target) or norm(w) in alt.get(norm(target), set())  # noqa: E731
            row[f"{key}_rank"] = next((k + 1 for k, w in enumerate(words) if ok(w)), None)
            row[f"{key}_valid"] = sum(1 for w in words if norm(w) in vocab)
            row[f"{key}_top10"] = ", ".join(words)
        rows.append(row)
    json.dump(rows, open(root / "comparison.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for key in ("dict", "llm", "gem"):
        print(key, "1η:", sum(r[f"{key}_rank"] == 1 for r in rows), "στις 10:", sum(r[f"{key}_rank"] is not None for r in rows))


if __name__ == "__main__":
    main()
