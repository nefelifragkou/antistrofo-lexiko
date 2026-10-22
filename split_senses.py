"""
Βήμα 3: Χωρισμός των λημμάτων του Λεξικού Τριανταφυλλίδη σε σημασίες.

Είσοδος : data/raw/modern-greek-dictionary.parquet  (46.745 λήμματα)
Έξοδος  : data/processed/senses.jsonl   (μία γραμμή ανά σημασία)
          data/processed/excluded.jsonl (λήμματα που εξαιρέθηκαν και γιατί)

Οι κανόνες ακολουθούν το έγγραφο «Κανόνες χωρισμού και ευρήματα δεδομένων»:
  1. καθαρισμός χαρακτήρων (λατινικά γράμματα -> ελληνικά)
  2. αφαίρεση ετυμολογίας (η τελευταία [ ... ])
  3. αφαίρεση κεφαλίδας (μέχρι το πρώτο " : ") - κρατάμε μέρος του λόγου και εναλλακτικούς τύπους
  4. αποκοπή παραγώγων (ΥΠΟΚΟΡ / ΜΕΓΕΘ / ΕΠΙΡΡ)
  5. χωρισμός στην αρίθμηση (I / 1 / α / α 1) με έλεγχο σειράς
  6. απομόνωση ορισμού, συνωνύμων, αντωνύμων, ετικετών
Αποφάσεις: εκτός φράσεις/παροιμίες, εκτός λέξεις γραμματικής/επιφωνήματα/
προθήματα-επιθήματα, «δανεικός» ορισμός για ορισμούς μίας λέξης.
"""
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import parquet_reader  # noqa: E402  (μικρός αναγνώστης parquet χωρίς εξωτερικές βιβλιοθήκες)

# --------------------------------------------------------------------------
# 1. Καθαρισμός χαρακτήρων
# --------------------------------------------------------------------------
LATIN_TO_GREEK = str.maketrans({
    "A": "Α", "B": "Β", "E": "Ε", "H": "Η", "I": "Ι", "K": "Κ", "M": "Μ",
    "N": "Ν", "O": "Ο", "P": "Ρ", "T": "Τ", "X": "Χ", "Y": "Υ", "Z": "Ζ",
    "o": "ο", "v": "ν",
})
GREEK_CHAR = re.compile(r"[Ͱ-Ͽἀ-῿]")
WORD = re.compile(r"\S+")


def fix_mixed_word(match):
    """Μια «λέξη» που έχει ελληνικά γράμματα: τα λατινικά που μοιάζουν γίνονται ελληνικά."""
    w = match.group(0)
    if GREEK_CHAR.search(w) and re.search(r"[A-Za-z]", w):
        return w.translate(LATIN_TO_GREEK)
    return w


def fix_latin(text):
    return WORD.sub(fix_mixed_word, text)


def fix_lemma(lemma):
    """Στο λήμμα, τα κεφαλαία λατινικά είναι πάντα «μεταμφιεσμένα» ελληνικά (Aδάμ, A, α)."""
    out = []
    for tok in lemma.split(" "):
        if re.fullmatch(r"[A-Z]+,?", tok) or GREEK_CHAR.search(tok):
            tok = tok.translate(LATIN_TO_GREEK)
        out.append(tok)
    return " ".join(out)


def strip_accents(s):
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


# --------------------------------------------------------------------------
# 2. Ετυμολογία: η τελευταία [ ... ] του λήμματος (με φωλιασμένες αγκύλες)
# --------------------------------------------------------------------------
def remove_etymology(text):
    t = text.rstrip()
    if not t.endswith("]"):
        return t
    depth = 0
    for i in range(len(t) - 1, -1, -1):
        if t[i] == "]":
            depth += 1
        elif t[i] == "[":
            depth -= 1
            if depth == 0:
                return t[:i].rstrip()
    return t


# --------------------------------------------------------------------------
# 3. Κεφαλίδα
# --------------------------------------------------------------------------
FUNCTION_POS = re.compile(r"(?<![\wͰ-Ͽ])(πρόθ\.|σύνδ\.|επιφ\.|αντων\.|μόριο|άρθρο)")
BODY_PARTICLE = re.compile(r"^(?:[\wͰ-Ͽ]+\s)?μόριο\b")
POS_CODE = re.compile(r"(?:^|\s)(Ο|Ε|Ρ)(?=\d|\s|\(|$|\.)")


def split_header(text):
    if " : " in text:
        head, body = text.split(" : ", 1)
    else:  # σπάνιο: χωρίς άνω-κάτω τελεία
        head, body = text, ""
    return head.strip(), body.strip()


def header_info(head, headword):
    """Μέρος του λόγου (Ο/Ε/Ρ/…) και εναλλακτικοί τύποι (μετά από & ή θηλ.)."""
    after_pron = head.split("]", 1)[1] if "]" in head else head
    pos = None
    m = POS_CODE.search(after_pron)
    if m:
        pos = {"Ο": "ουσιαστικό", "Ε": "επίθετο", "Ρ": "ρήμα"}[m.group(1)]
    elif "επίρρ." in after_pron:
        pos = "επίρρημα"
    elif "αριθμτ." in after_pron:
        pos = "αριθμητικό"
    alt = []
    for m in re.finditer(r"(?:&|θηλ\.)\s*(?:\([^)]*\)\s*)?([Ͱ-Ͽἀ-῿][Ͱ-Ͽἀ-῿\-]+)", head):
        w = m.group(1)
        if not w.startswith("-") and w != headword and w not in alt:
            alt.append(w)
    return pos, alt


def is_function_word(head, body):
    after_pron = head.split("]", 1)[1] if "]" in head else head
    return bool(FUNCTION_POS.search(after_pron) or BODY_PARTICLE.search(body[:40]))


def is_affix(lemma):
    return lemma.startswith("-") or bool(re.match(r"^\S+-(\s\d+)?$", lemma))


# --------------------------------------------------------------------------
# 4. Παράγωγα (υποκοριστικά, μεγεθυντικά, επιρρήματα) στο τέλος του λήμματος
# --------------------------------------------------------------------------
DERIV = re.compile(r"\b(ΥΠΟΚΟΡ|ΜΕΓΕΘ|ΕΠΙΡΡ)\b")


def cut_derivatives(body):
    m = DERIV.search(body)
    if not m:
        return body
    # πηγαίνουμε πίσω ως την προηγούμενη τελεία που κλείνει πρόταση
    prev = body.rfind(". ", 0, m.start())
    return body[: prev + 1] if prev != -1 else body[: m.start()]


# --------------------------------------------------------------------------
# 5. Αρίθμηση σημασιών
# --------------------------------------------------------------------------
ROMANS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]
LETTERS = ["α", "β", "γ", "δ", "ε", "στ", "ζ", "η", "θ", "ι", "ια", "ιβ", "ιγ", "ιδ"]
MARKER = re.compile(
    r"(?:(?<=\s)|^)"
    r"(?P<rom>[IΙ]{1,3}V?|[IΙ]?V[IΙ]{0,3})?"
    r"(?P<num>\d{1,2})?"
    r"(?P<let>στ|ι[α-δ]|[α-θι])?"
    r"(?:\s(?P<sub>\d)\s?)?"
    r"\.(?=\s|$)"
)
PHRASE_LABELS = {"έκφρ.", "γνωμ.", "επιφ. έκφρ.", "απειλή"}
PHRASE_START = re.compile(r"(?:\bΦΡ\b|\bΠΑΡ\b|\(έκφρ\.\)|\(γνωμ\.\)|\(επιφ\. έκφρ\.\)|\(απειλή\))")


def roman_value(s):
    s = s.replace("Ι", "I")
    return ROMANS.index(s) + 1 if s in ROMANS else None


def find_markers(body):
    """Επιστρέφει τα σημεία αρίθμησης που περνούν τον έλεγχο σειράς."""
    accepted = []
    rom = num = let = sub = None
    in_phrase = False
    last_end = 0
    for m in MARKER.finditer(body):
        g = m.groupdict()
        if not (g["rom"] or g["num"] or g["let"]):
            continue
        if g["sub"] and not g["let"]:
            continue
        # έχουμε μπει σε φράση από το προηγούμενο σημείο;
        if PHRASE_START.search(body, last_end, m.start()):
            in_phrase = True
        r = roman_value(g["rom"]) if g["rom"] else None
        if g["rom"] and r is None:
            continue
        n = int(g["num"]) if g["num"] else None
        l_ = LETTERS.index(g["let"]) if g["let"] else None
        s = int(g["sub"]) if g["sub"] else None
        ok = False
        if r is not None:
            ok = r == (rom or 0) + 1 and (n in (None, 1)) and (l_ in (None, 0)) and (s in (None, 1))
            if ok:
                rom, num, let, sub = r, n, l_, s
        elif n is not None:
            ok = n == (num or 0) + 1 and (l_ in (None, 0)) and (s in (None, 1))
            if ok:
                num, let, sub = n, l_, s
        elif l_ is not None:
            if s is not None and let is not None and l_ == let and s == (sub or 0) + 1:
                ok = True  # γ. … γ 1 . -> γ 2 .
                sub = s
            elif l_ == (let + 1 if let is not None else 0) and (s in (None, 1)):
                # ένα «α.» αμέσως μετά από «φράση:» ανήκει στη φράση (θάλασσα: «τα κάνω ~: α. …»)
                before = re.sub(r"(\s*\([^()]*\))+\s*$", "", body[:m.start()].rstrip())
                ok = not (in_phrase and l_ == 0 and before.endswith(":"))
                if ok:
                    let, sub = l_, s
        if ok:
            in_phrase = False
            accepted.append((m.start(), m.end(), rom, num, let, sub))
            last_end = m.end()
    return accepted


def code_of(rom, num, let, sub):
    c = ""
    if rom:
        c += ROMANS[rom - 1]
    if num:
        c += str(num)
    if let is not None:
        c += LETTERS[let]
    if sub:
        c += str(sub)
    return c


def build_chunks(body):
    """Κόβει το σώμα σε κομμάτια: (κωδικός, βάθος-γονείς, κείμενο)."""
    marks = find_markers(body)
    chunks = []
    preamble = body[: marks[0][0]].strip() if marks else body.strip()
    if preamble:
        chunks.append(("0", (), preamble))
    for i, (st, en, rom, num, let, sub) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(body)
        chunks.append((code_of(rom, num, let, sub), (rom, num, let, sub), body[en:end].strip()))
    return chunks


def parent_codes(path):
    """Οι κωδικοί όλων των «προγόνων» μιας σημασίας (π.χ. II1α -> II, II1)."""
    rom, num, let, sub = path
    out = []
    if rom and (num or let is not None):
        out.append(code_of(rom, None, None, None))
    if num and (let is not None):
        out.append(code_of(rom, num, None, None))
    if let is not None and sub:
        out.append(code_of(rom, num, let, None))
    return out


# --------------------------------------------------------------------------
# 6. Ορισμός, συνώνυμα, αντώνυμα, ετικέτες
# --------------------------------------------------------------------------
LEAD_LABEL = re.compile(r"^\(([^()]*)\)\s*:?\s*")
ABBREV = {
    "κπ.": "κάποιον", "κτ.": "κάτι", "συνήθ.": "συνήθως", "κτλ.": "κτλ.",
    "ενν.": "εννοείται", "ειδικότ.": "ειδικότερα", "κυρ.": "κυρίως",
}


# Συντομογραφίες του λεξικού (βγήκαν από τα δεδομένα: λέξεις με τελεία που σχεδόν πάντα
# ακολουθούνται από πεζό γράμμα). Μια τελεία μετά από αυτές ΔΕΝ κλείνει πρόταση.
ABBREVIATIONS = set("""
αρχ ελνστ κτ κπ γαλλ συνήθ σημδ μτφρδ λόγ μσν θηλ αγγλ απαρέμφ μππ αόρ λατ ουσ ουδ αποβ ιταλ
υποκορ ανομ επίδρ άτ παθ νλατ διάκρ διεθ πληθ προσαρμ απόδ επιθ γεν συνίζ δημοτ ενεστ συνοπτ
αναλ τουρκ αρσ υστλατ πρτ συμπροφ παρετυμ φρ αλλ βεν απλοπ αραβ αριθμτ μετακ μεε μσνλατ έκφρ
αφηρ μπε συγγ ίδ παλ προφ σύγκρ υποχωρ αντων εξέλ ισπαν μτφ ιδ πρβ γλ σπάν ηχηροπ σύνδ μετάθ
κυρ σύντμ αορ επέκτ νεοελλ συνθ επιρρ ημιφ ρωσ αντ προστ συγκ μτχ συμφυρ ονομ σλαβ συν περσ δηλ
μετουσ ορθογρ αποηχηροπ μεταρ ελλην συγκρ διαλεκτ υπερθ ρηματ νεότ άνθρ ισχυροπ λαϊκότρ μορφολ
διαφ διάσπ ετυμ όμ παράλλ προχωρ δοτ σύνθ σπανιότ αρνητ πργ σανσκρ σύμπτ πορτογαλ σημιτ κτητ αλβ
προσ παλαιότ περιλ σχ βουλγ τελ μειωτ ανάλ αραμ ειρ εξομάλ ανατολ κλητ αναδιπλ μετον υπ ιαπων
ενν ειδικότ βλ κτλ πρόσ ερωτ οικ ιατρ νομ στρατ ναυτ βοτ ζωολ φυσ χημ μαθ μουσ αρχιτ θρησκ
εκκλ γραμμ γλωσσ οικον πολιτ τεχν φιλοσ ψυχολ λογοτ αθλ ειρων υβρ συναισθ παιδ σημ ως
""".split())


def leading_labels(t):
    labels = []
    while True:
        m = LEAD_LABEL.match(t)
        if not m or len(m.group(1)) > 80:
            break
        labels.append(m.group(1).strip())
        t = t[m.end():]
    return labels, t


def first_sentence_end(t):
    """Τέλος ορισμού: πρώτο «:», «||», «·», ή τελεία που ακολουθείται από κεφαλαίο/τέλος."""
    best = len(t)
    for sym in (":", "||", "·", ";"):
        i = t.find(sym)
        if i != -1:
            best = min(best, i)
    for m in re.finditer(r"\.(?=\s|$)", t):
        i = m.start()
        if i >= best:
            break
        before = re.search(r"(\S+)$", t[:i])
        tok = before.group(1) if before else ""
        after = t[m.end():].lstrip()
        if re.fullmatch(r"[Α-ΩA-Z]", tok):          # «Π.» Διαθήκη
            continue
        if tok.lstrip("(") in ABBREVIATIONS:     # «συνήθ.» κ.λπ.
            continue
        return i
    return best


def clean_text(t, headword):
    t = re.sub(r"\[[^\]]*\]", "", t)          # προφορά μέσα στο κείμενο, π.χ. [álfa]
    t = t.replace("*", "")
    t = re.sub(r"(?<!\S)~(?!\S)", headword, t)
    t = t.replace("~", headword)
    for k, v in ABBREV.items():
        t = re.sub(r"(?<![\wͰ-Ͽ])" + re.escape(k), v, t)
    t = re.sub(r"(?<![\w\u0370-\u03ff])κπ(?![\w\u0370-\u03ff])", "κάποιον", t)
    t = re.sub(r"(?<![\w\u0370-\u03ff])κτ(?![\w\u0370-\u03ff])", "κάτι", t)
    # αριθμός ομόγραφου μετά από λέξη: «θόρυβο 2,» -> «θόρυβο,»
    t = re.sub(r"([\u0370-\u03ff\u1f00-\u1fff]{3,}) \d(?=\s*[,.;:)]|\s*$)", r"\1", t)
    t = re.sub(r"(?<![\w\u0370-\u03ff])μππ\.?(?![\w\u0370-\u03ff])", "μετοχή παθητικού παρακειμένου", t)
    t = re.sub(r"\s+([,.;:·)])", r"\1", t)
    t = re.sub(r"\(\s+", "(", t)
    t = re.sub(r"\s{2,}", " ", t)
    return t.strip(" ,.;:·")


def parse_segment(seg, headword):
    """Από ένα κομμάτι κειμένου βγάζει (ετικέτες, ορισμό, συνώνυμα, αντώνυμα, πλαίσιο)."""
    labels, t = leading_labels(seg.strip())
    frame = None
    if t.startswith("~"):  # πλαίσιο σύνταξης, π.χ. «~ κπ.:» ή «~ πίσω από κπ., ορισμός»
        m = re.match(r"~[^:,]*[:,]\s*", t)
        if m:
            frame = t[: m.end()].strip(" :,")
            t = t[m.end():]
            more, t = leading_labels(t)
            labels += more
    # φράσεις/παροιμίες: ό,τι ακολουθεί κόβεται
    pm = PHRASE_START.search(t)
    if pm:
        t = t[: pm.start()]
        # «…, συνήθ. στη ΦΡ …» -> σβήνουμε το «συνήθ. στη» που έμεινε μετέωρο
        t = re.sub(r"[,;]?\s*(?:(?:συνήθ\.|συνήθως|κυρίως|κυρ\.|ιδίως|ιδ\.|μόνο|μόνο\s+ως)\s*)?(?:στη|στην|στις|στο|στα|στον|σε|και)?\s*$", "", t)
    # αντώνυμα
    antonyms = []
    am = re.search(r"\bANT\b\s*", t)
    if am:
        rest = t[am.end():]
        stop = re.search(r"[:.;]|\|\|", rest)
        antonyms = [clean_text(a, headword) for a in (rest[: stop.start()] if stop else rest).split(",")]
        antonyms = [a for a in antonyms if a]
        t = t[: am.start()]
    end = first_sentence_end(t)
    definition = t[:end]
    if definition[:1].isupper() or definition[:1] == "«":
        # ο «ορισμός» είναι παράδειγμα· κρατάμε την εξήγηση μετά το κόμμα, αν υπάρχει
        m = re.match(r"(.+?),\s+([a-zα-ωά-ώ(].*)$", definition)
        definition = f"{m.group(2)} ({m.group(1)})" if m else ""
    synonyms = []
    if end < len(t) and t[end] == "·":
        rest = t[end + 1:]
        stop = re.search(r"[:;]|\.(?=\s|$)|\|\||\(πρβ", rest)
        syn_txt = rest[: stop.start()] if stop else rest
        syn_txt = re.sub(r"\([^)]*\)", "", syn_txt)
        if not re.search(r"\b(ΣΥΝ|βλ\.)", syn_txt):
            synonyms = [clean_text(s, headword) for s in syn_txt.split(",")]
            synonyms = [s for s in synonyms if s and len(s.split()) <= 4]
    definition = clean_text(definition, headword)
    # «…, το σκυλί» στο τέλος του ορισμού = συνώνυμο
    m = re.search(r",\s+(?:ο|η|το|οι|τα)\s+([\u0370-\u03ff\u1f00-\u1fff]+)$", definition)
    if m and len(definition.split()) >= 6:
        synonyms = [m.group(1)] + synonyms
        definition = definition[: m.start()]
    return labels, definition, synonyms, antonyms, frame


def sub_uses(chunk_text, headword):
    """Τα κομμάτια μετά από «||» που είναι νέες χρήσεις με δικό τους ορισμό."""
    out = []
    parts = chunk_text.split("||")[1:]
    for p in parts:
        labels, t = leading_labels(p.strip())
        if not t or t.startswith(":") or t.startswith("~") or t[0].isupper() or t[0] in "«*[":
            continue
        if PHRASE_START.match(t):
            continue
        lab2, definition, syn, ant, frame = parse_segment(t, headword)
        if PHRASE_LABELS & set(labels + lab2):
            continue
        if len(definition.split()) >= 3:
            out.append((labels + lab2, definition, syn, ant))
    return out


# --------------------------------------------------------------------------
# Κύρια διαδικασία
# --------------------------------------------------------------------------
def process_entry(row):
    lemma_raw = row["lemma"]
    lemma = fix_lemma(lemma_raw)
    headword = lemma.split(" ")[0].rstrip(",")
    homograph = None
    m = re.match(r"^\S+\s(\d+)\b", lemma)
    if m:
        homograph = int(m.group(1))
    text = fix_latin(row["entry_text"])
    text = remove_etymology(text)
    head, body = split_header(text)

    if is_affix(lemma):
        return None, "πρόθημα/επίθημα"
    if is_function_word(head, body):
        return None, "λέξη γραμματικής/επιφώνημα"

    pos, alt = header_info(head, headword)
    body = cut_derivatives(body)
    chunks = build_chunks(body)
    has_children = set()
    for code, path, _ in chunks:
        if path:
            for pc in parent_codes(path):
                has_children.add(pc)

    labels_by_code = {}
    short_def_by_code = {}
    senses = []
    for code, path, chunk in chunks:
        labels, definition, syn, ant, frame = parse_segment(chunk, headword)
        labels_by_code[code] = labels
        inherited = []
        if path:
            for pc in parent_codes(path):
                inherited += labels_by_code.get(pc, [])
        all_labels = inherited + labels
        is_parent = code in has_children or (code == "0" and len(chunks) > 1)
        if is_parent and 1 <= len(definition.split()) < 3:
            short_def_by_code[code] = definition
        if path and definition:
            prefix = [short_def_by_code[pc] for pc in parent_codes(path) if pc in short_def_by_code]
            if prefix:
                definition = " — ".join(prefix + [definition])
        if PHRASE_LABELS & set(all_labels):
            continue
        # γονείς/εισαγωγή κρατιούνται μόνο αν έχουν ουσιαστικό δικό τους ορισμό
        if is_parent and len(definition.split()) < 3:
            pass
        elif definition:
            senses.append(dict(code=("1" if code == "0" and len(chunks) == 1 else code), labels=all_labels, definition=definition,
                               synonyms=syn, antonyms=ant, frame=frame, kind="σημασία"))
        for lab, d, s, a in sub_uses(chunk, headword):
            senses.append(dict(code=("1" if code == "0" and len(chunks) == 1 else code) + "+", labels=all_labels + lab, definition=d,
                               synonyms=s, antonyms=a, frame=None, kind="ειδικότερη χρήση"))
    base = dict(lemma=lemma, headword=headword, homograph=homograph, alt_forms=alt, pos=pos,
                source_url=row["source_url"])
    return [dict(base, **s) for s in senses], None


TOKEN = re.compile(r"[\u0370-\u03ff\u1f00-\u1fff]+")


def build_vocab(rows):
    vocab = Counter()
    for r in rows:
        vocab.update(w.lower() for w in TOKEN.findall(fix_latin(r["entry_text"])))
    return vocab


def join_broken_words(text, vocab):
    """«σύνο λο» -> «σύνολο»: ενώνει δύο διαδοχικά κομμάτια όταν η ενωμένη λέξη υπάρχει
    στο λεξικό και τουλάχιστον ένα από τα κομμάτια σπάνια εμφανίζεται μόνο του."""
    parts = text.split(" ")
    out = []
    i = 0
    while i < len(parts):
        cur = parts[i]
        if i + 1 < len(parts):
            nxt = parts[i + 1]
            ma = re.search(r"([\u0370-\u03ff\u1f00-\u1fff]+)$", cur)
            mb = re.match(r"^([\u0370-\u03ff\u1f00-\u1fff]+)", nxt)
            if ma and mb:
                a, b = ma.group(1), mb.group(1)
                w = (a + b).lower()
                fa, fb = vocab[a.lower()], vocab[b.lower()]
                if (vocab[w] >= 2 and (fa <= 3 or fb <= 3)) or (vocab[w] >= 10 and vocab[w] >= 5 * max(fa, fb)):
                    parts[i + 1] = cur + nxt
                    i += 1
                    continue
        out.append(cur)
        i += 1
    return " ".join(out)


def borrow_definitions(senses):
    """Ορισμός μίας λέξης -> δανειζόμαστε τον (πρώτο) ορισμό της λέξης στην οποία παραπέμπει."""
    index = defaultdict(list)
    for s in senses:
        index[strip_accents(s["headword"])].append(s)

    def real_definition(word, depth=0):
        cands = index.get(strip_accents(word), [])
        for c in cands:
            if len(c["definition"].split()) >= 2:
                return c
        if depth < 2:
            for c in cands:
                if len(c["definition"].split()) == 1 and strip_accents(c["definition"]) != strip_accents(word):
                    r = real_definition(c["definition"], depth + 1)
                    if r:
                        return r
        return None

    borrowed = 0
    for s in senses:
        d = re.sub(r"^(ο|η|το|οι|τα)\s+", "", s["definition"])
        if len(d.split()) == 1 and len(d) > 2:
            target = real_definition(d)
            if target and target is not s:
                s["borrowed_from"] = target["headword"]
                s["definition"] = f"{d}: {target['definition']}"
                borrowed += 1
    return borrowed


def main(parquet_path, out_dir):
    cols = parquet_reader.read(parquet_path)
    rows = [dict(zip(cols.keys(), r)) for r in zip(*cols.values())]
    senses, excluded = [], []
    for row in rows:
        result, reason = process_entry(row)
        if result is None:
            excluded.append(dict(lemma=fix_lemma(row["lemma"]), reason=reason))
            continue
        if not result:
            excluded.append(dict(lemma=fix_lemma(row["lemma"]), reason="χωρίς ορισμό μετά τον χωρισμό"))
            continue
        senses.extend(result)
    vocab = build_vocab(rows)
    joined = 0
    for sn in senses:
        new = join_broken_words(sn["definition"], vocab)
        if new != sn["definition"]:
            joined += 1
            sn["definition"] = new
        sn["synonyms"] = [join_broken_words(x, vocab) for x in sn["synonyms"]]
    borrowed = borrow_definitions(senses)
    for i, s in enumerate(senses):
        s["id"] = i
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "senses.jsonl", "w", encoding="utf-8") as f:
        for s in senses:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    with open(out_dir / "excluded.jsonl", "w", encoding="utf-8") as f:
        for e in excluded:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    stats = dict(
        entries=len(rows),
        senses=len(senses),
        lemmas_with_senses=len({s["lemma"] for s in senses}),
        excluded=dict(Counter(e["reason"] for e in excluded)),
        borrowed_definitions=borrowed,
        sub_uses=sum(1 for s in senses if s["kind"] == "ειδικότερη χρήση"),
        joined_broken_words=joined,
    )
    with open(out_dir / "stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    main(root / "data/raw/modern-greek-dictionary.parquet", root / "data/processed")
