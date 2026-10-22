"""Φτιάχνει το notebook του βήματος 4 (embeddings) για το Google Colab."""
import json
from pathlib import Path

DEV_QUERIES = [
    ("ο φόβος για κλειστούς χώρους", "κλειστοφοβία"),
    ("όταν δεν μπορείς να κοιμηθείς το βράδυ", "αϋπνία"),
    ("η λύπη που νιώθεις όταν θυμάσαι το παρελθόν ή τον τόπο σου", "νοσταλγία"),
    ("αυτός που σβήνει τις φωτιές", "πυροσβέστης"),
    ("κόσμημα που κρεμάμε στο αυτί", "σκουλαρίκι"),
    ("παιδί που έχασε τους γονείς του", "ορφανός"),
    ("ζώο που ζει και στη στεριά και στο νερό", "αμφίβιος"),
    ("κάποιος που ταξιδεύει κρυφά χωρίς εισιτήριο", "λαθρεπιβάτης"),
    ("συσκευή της κουζίνας που κρατά τα τρόφιμα κρύα", "ψυγείο"),
    ("άνθρωπος που δεν τρώει κρέας", "χορτοφάγος"),
    ("λέξη που φτιάχνεται από τα αρχικά γράμματα άλλων λέξεων", "ακρωνύμιο"),
    ("κάνει τον θαρραλέο αλλά στην πραγματικότητα φοβάται", "θρασύδειλος"),
    ("πολύ άσχημη μυρωδιά", "δυσωδία"),
    ("φάρμακο που σκοτώνει τα αγριόχορτα", "ζιζανιοκτόνο"),
    ("αυτός που γράφει με το αριστερό χέρι", "αριστερόχειρας"),
    ("άνθρωπος που ζει στα σύννεφα και αγνοεί την πραγματικότητα", "αιθεροβάμων"),
    ("αυτός που βρίσκει σπίτια για αγορά και παίρνει προμήθεια", "μεσίτης"),
    ("όποιος λέει συνέχεια ψέματα", "ψεύτης"),
    ("πανί που σε κατεβάζει με ασφάλεια όταν πηδάς από αεροπλάνο", "αλεξίπτωτο"),
    ("η ώρα που αρχίζει να βγαίνει ο ήλιος", "ξημέρωμα"),
]

cells = []


def md(text):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(True)})


def code(text):
    cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
                  "source": text.strip("\n").splitlines(True)})


md("""
# Αντίστροφο Λεξικό — Βήμα 4: «αριθμοί νοήματος» (embeddings)

Αυτό το notebook:
1. φορτώνει τις **77.039 σημασίες** του λεξικού (αρχείο `senses.jsonl.gz` από το βήμα 3),
2. τις μετατρέπει σε embeddings με **4 διαφορετικά μοντέλα**,
3. δοκιμάζει κάθε μοντέλο σε **20 περιγραφές-δοκιμής** (π.χ. «ο φόβος για κλειστούς χώρους» → κλειστοφοβία),
4. κρατά το καλύτερο και σου δίνει το αρχείο για κατέβασμα.

### Πώς το τρέχεις
1. Πάνω αριστερά: **Runtime → Change runtime type → T4 GPU → Save**.
2. **Runtime → Run all**.
3. Όταν εμφανιστεί κουμπί «Choose files», διάλεξε το `senses.jsonl.gz`.
4. Περίμενε (περίπου 15–25 λεπτά συνολικά). Στο τέλος κατεβαίνει αυτόματα το `step4_results.zip`.

Οι 20 περιγραφές εδώ χρησιμεύουν **μόνο για να διαλέξουμε μοντέλο**. Η επίσημη αξιολόγηση
θα γίνει με τις 30 δικές σου περιγραφές (βήμα 6), με διαφορετικές λέξεις.
""")

code("""
# 1. Έλεγχος κάρτας γραφικών και εγκατάσταση βιβλιοθηκών
import subprocess, sys
try:
    import torch
    print("GPU:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "ΔΕΝ ΒΡΕΘΗΚΕ — άλλαξε Runtime σε T4 GPU")
except ImportError:
    print("Δεν υπάρχει torch")
try:
    import sentence_transformers
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "sentence-transformers"], check=True)
""")

code("""
# 2. Ανέβασμα του αρχείου senses.jsonl.gz
import os
if not os.path.exists("senses.jsonl.gz"):
    from google.colab import files
    files.upload()
print("Αρχείο:", os.path.getsize("senses.jsonl.gz") // 1024, "KB")
""")

code("""
# 3. Φόρτωση σημασιών και κείμενα για embedding
import gzip, json, unicodedata
senses = [json.loads(l) for l in gzip.open("senses.jsonl.gz", "rt", encoding="utf-8")]
print("Σημασίες:", len(senses))

def passage_text(s, with_word=True):
    parts = []
    if with_word:
        parts.append(s["headword"] + ":")
    if s["labels"]:
        parts.append("(" + ", ".join(s["labels"]) + ")")
    parts.append(s["definition"])
    if s["synonyms"]:
        parts.append("Συνώνυμα: " + ", ".join(s["synonyms"]) + ".")
    return " ".join(parts)

def norm(w):
    w = unicodedata.normalize("NFD", w)
    return "".join(c for c in w if not unicodedata.combining(c)).lower()

print(passage_text(senses[0]))
""")

code("DEV_QUERIES = " + json.dumps(DEV_QUERIES, ensure_ascii=False, indent=1) + """
print(len(DEV_QUERIES), "περιγραφές-δοκιμής")
""")

code("""
# 4. Αναζήτηση και μετρήσεις
import numpy as np, time

def top_words(query_vec, emb, k=10):
    scores = emb @ query_vec
    order = np.argsort(-scores)
    seen, out = set(), []
    for i in order:
        lem = senses[i]["lemma"]
        if lem in seen:
            continue
        seen.add(lem)
        out.append((senses[i], float(scores[i])))
        if len(out) == k:
            break
    return out

def is_target(s, target):
    t = norm(target)
    return norm(s["headword"]) == t or t in [norm(a) for a in s.get("alt_forms", [])]

def evaluate(model, emb, q_prefix):
    qv = model.encode([q_prefix + q for q, _ in DEV_QUERIES], normalize_embeddings=True)
    rows = []
    for (q, target), v in zip(DEV_QUERIES, qv):
        res = top_words(v, emb)
        rank = next((i + 1 for i, (s, _) in enumerate(res) if is_target(s, target)), None)
        rows.append(dict(query=q, target=target, rank=rank, top3=[s["headword"] for s, _ in res[:3]]))
    hit1 = sum(r["rank"] == 1 for r in rows) / len(rows)
    hit10 = sum(r["rank"] is not None for r in rows) / len(rows)
    mrr = sum(1 / r["rank"] for r in rows if r["rank"]) / len(rows)
    return dict(hit1=hit1, hit10=hit10, mrr=mrr), rows
""")

code("""
# 5. Σύγκριση μοντέλων (αυτό το κελί παίρνει τον περισσότερο χρόνο)
from sentence_transformers import SentenceTransformer
import torch, gc

MODELS = [
    # (όνομα, πρόθεμα ερώτησης, πρόθεμα ορισμού)
    ("intfloat/multilingual-e5-small", "query: ", "passage: "),
    ("intfloat/multilingual-e5-base",  "query: ", "passage: "),
    ("intfloat/multilingual-e5-large", "query: ", "passage: "),
    ("BAAI/bge-m3",                    "",        ""),
]
device = "cuda" if torch.cuda.is_available() else "cpu"
results, details, embeddings = {}, {}, {}

def run(name, qp, pp, with_word=True):
    t0 = time.time()
    model = SentenceTransformer(name, device=device)
    model.max_seq_length = 256
    texts = [pp + passage_text(s, with_word) for s in senses]
    emb = model.encode(texts, batch_size=128, normalize_embeddings=True, show_progress_bar=True,
                       convert_to_numpy=True).astype(np.float32)
    metrics, rows = evaluate(model, emb, qp)
    metrics["λεπτά"] = round((time.time() - t0) / 60, 1)
    metrics["διαστάσεις"] = emb.shape[1]
    key = name + ("" if with_word else "  (χωρίς λήμμα)")
    results[key], details[key] = metrics, rows
    embeddings[key] = emb.astype(np.float16)
    print(key, metrics)
    del model; gc.collect(); torch.cuda.empty_cache()

# Σημείο αναφοράς: απλή σύγκριση γραμμάτων (χωρίς «νόημα»), για να φανεί τι προσθέτουν τα embeddings
from sklearn.feature_extraction.text import TfidfVectorizer
class LetterBaseline:
    def __init__(self, texts):
        self.v = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, sublinear_tf=True)
        self.m = self.v.fit_transform(texts)
    def encode(self, qs, normalize_embeddings=True):
        return self.v.transform(qs)
def run_baseline():
    t0 = time.time()
    base = LetterBaseline([passage_text(s) for s in senses])
    rows = []
    for q, target in DEV_QUERIES:
        scores = (base.m @ base.encode([q]).T).toarray().ravel()
        order = np.argsort(-scores); seen, res = set(), []
        for i in order:
            if senses[i]["lemma"] in seen: continue
            seen.add(senses[i]["lemma"]); res.append(senses[i])
            if len(res) == 10: break
        rank = next((k + 1 for k, s in enumerate(res) if is_target(s, target)), None)
        rows.append(dict(query=q, target=target, rank=rank, top3=[s["headword"] for s in res[:3]]))
    m = dict(hit1=sum(r["rank"] == 1 for r in rows) / len(rows), hit10=sum(r["rank"] is not None for r in rows) / len(rows),
             mrr=sum(1 / r["rank"] for r in rows if r["rank"]) / len(rows), λεπτά=round((time.time() - t0) / 60, 1), διαστάσεις=0)
    results["Σημείο αναφοράς: σύγκριση γραμμάτων"], details["Σημείο αναφοράς: σύγκριση γραμμάτων"] = m, rows
    print("Σύγκριση γραμμάτων", m)
run_baseline()

for name, qp, pp in MODELS:
    run(name, qp, pp)
# έλεγχος: βοηθά να γράφουμε τη λέξη μπροστά από τον ορισμό;
run("intfloat/multilingual-e5-base", "query: ", "passage: ", with_word=False)
""")

code("""
# 6. Πίνακας αποτελεσμάτων
import pandas as pd
table = pd.DataFrame(results).T[["hit1", "hit10", "mrr", "λεπτά", "διαστάσεις"]]
table.columns = ["Σωστή λέξη 1η", "Σωστή λέξη στις 10", "MRR", "Λεπτά", "Διαστάσεις"]
display(table.style.format({"Σωστή λέξη 1η": "{:.0%}", "Σωστή λέξη στις 10": "{:.0%}", "MRR": "{:.2f}"}))
best = max([k for k in embeddings], key=lambda k: (results[k]["hit10"], results[k]["mrr"]))
print("Καλύτερο:", best)
display(pd.DataFrame(details[best])[["query", "target", "rank", "top3"]])
""")

code("""
# 7. Αποθήκευση και κατέβασμα
import zipfile
safe = best.replace("/", "__").replace("  (χωρίς λήμμα)", "__no-headword")
np.save(f"embeddings_{safe}.npy", embeddings[best])
pd.DataFrame(results).T.to_csv("model_comparison.csv")
all_rows = [dict(model=m, **r) for m, rows in details.items() for r in rows]
pd.DataFrame(all_rows).to_csv("dev_queries_results.csv", index=False)
with open("chosen_model.json", "w") as f:
    json.dump(dict(model=best, rows=len(senses)), f, ensure_ascii=False)
with zipfile.ZipFile("step4_results.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for fn in [f"embeddings_{safe}.npy", "model_comparison.csv", "dev_queries_results.csv", "chosen_model.json"]:
        z.write(fn)
print("Μέγεθος zip:", os.path.getsize("step4_results.zip") // (1024 * 1024), "MB")
try:
    from google.colab import files
    files.download("step4_results.zip")
except ImportError:
    pass
""")

md("""
### Τέλος
Στείλε μου στη συνομιλία τα δύο μικρά αρχεία από το zip: `model_comparison.csv` και
`dev_queries_results.csv`. Το `.npy` (τα embeddings, ~100–160 MB) κράτησέ το στον υπολογιστή σου·
θα το χρειαστούμε στο βήμα 5 (σελίδα αναζήτησης).
""")

nb = {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"provenance": []},
      "kernelspec": {"display_name": "Python 3", "name": "python3"}, "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 0}
out = Path(__file__).parent / "step4_embeddings.ipynb"
out.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
json.dump(DEV_QUERIES, open(Path(__file__).parent / "dev_queries.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ok", out)
