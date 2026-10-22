"""Ο «πυρήνας» της αναζήτησης: περιγραφή -> 10 υποψήφιες λέξεις με τον ορισμό τους."""
import gzip
import json
import numpy as np

QUERY_PREFIX = "query: "  # τα μοντέλα e5 θέλουν «query:» μπροστά από την ερώτηση


class ReverseDictionary:
    def __init__(self, senses_path, embeddings_path, model):
        self.senses = [json.loads(l) for l in gzip.open(senses_path, "rt", encoding="utf-8")]
        emb = np.load(embeddings_path)
        if emb.shape[0] != len(self.senses):
            raise ValueError(f"Τα embeddings ({emb.shape[0]}) δεν ταιριάζουν με τις σημασίες ({len(self.senses)})")
        self.emb = emb.astype(np.float32)
        self.model = model

    def search(self, description, k=10):
        description = (description or "").strip()
        if not description:
            return []
        q = self.model.encode([QUERY_PREFIX + description], normalize_embeddings=True)[0].astype(np.float32)
        scores = self.emb @ q
        top = np.argpartition(-scores, min(len(scores) - 1, 400))[:400]
        top = top[np.argsort(-scores[top])]
        results, seen = [], set()
        for i in top:
            s = self.senses[i]
            if s["lemma"] in seen:  # μία φορά κάθε λέξη, με την πιο κοντινή σημασία της
                continue
            seen.add(s["lemma"])
            results.append(dict(word=s["headword"], lemma=s["lemma"], code=s["code"], labels=s["labels"],
                                definition=s["definition"], synonyms=s["synonyms"], score=float(scores[i])))
            if len(results) == k:
                break
        return results
