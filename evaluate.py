"""Αξιολόγηση: σε πόσες περιγραφές η σωστή λέξη βρίσκεται στις 10 πρώτες."""
import unicodedata


def norm(w):
    w = unicodedata.normalize("NFD", (w or "").strip())
    return "".join(c for c in w if not unicodedata.combining(c)).lower()


def is_target(result, target):
    t = norm(target)
    return norm(result["word"]) == t or t in [norm(a) for a in result.get("alt_forms", [])]


def evaluate(rd, rows, k=10):
    """rows: λίστα από dict με τουλάχιστον «target» και «description»."""
    out = []
    for r in rows:
        res = rd.search(r["description"], k=k)
        rank = next((i + 1 for i, x in enumerate(res) if is_target(x, r["target"])), None)
        out.append(dict(r, rank=rank, found=rank is not None, top10=", ".join(x["word"] for x in res)))
    return out


def summary(results, by=None):
    """Ποσοστά (σωστή 1η, στις 10, MRR), συνολικά ή ανά ομάδα (π.χ. «difficulty»)."""
    groups = {}
    for r in results:
        key = r.get(by, "—") if by else "Σύνολο"
        groups.setdefault(key, []).append(r)
    table = []
    for key, rs in groups.items():
        n = len(rs)
        table.append({
            "Ομάδα": key, "Πλήθος": n,
            "Σωστή 1η": sum(r["rank"] == 1 for r in rs) / n,
            "Σωστή στις 10": sum(r["found"] for r in rs) / n,
            "MRR": sum(1 / r["rank"] for r in rs if r["rank"]) / n,
        })
    return table
