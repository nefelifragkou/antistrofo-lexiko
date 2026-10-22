"""Αντίστροφο Λεξικό — σελίδα αναζήτησης (Streamlit Community Cloud).

Τα δεδομένα (ορισμοί + embeddings) φορτώνονται από ιδιωτικό αποθετήριο δεδομένων στο Hugging Face.
Ρυθμίσεις στα Secrets της εφαρμογής:
    HF_TOKEN  = "hf_..."                         (κλειδί ανάγνωσης από το Hugging Face)
    DATA_REPO = "όνομα-χρήστη/antistrofo-lexiko-data"
"""
import html
import os

import streamlit as st
from huggingface_hub import hf_hub_download, list_repo_files

from encoder import OnnxE5
from search import ReverseDictionary

st.set_page_config(page_title="Αντίστροφο Λεξικό", page_icon="📖", layout="centered")

EXAMPLES = [
    "ο φόβος για κλειστούς χώρους",
    "παιδί που έχασε τους γονείς του",
    "κόσμημα που κρεμάμε στο αυτί",
    "η λύπη που νιώθεις όταν θυμάσαι τον τόπο σου",
]


@st.cache_resource(show_spinner="Φορτώνω το λεξικό και το μοντέλο (την πρώτη φορά θέλει 1–3 λεπτά)…")
def load():
    token = st.secrets.get("HF_TOKEN", os.environ.get("HF_TOKEN"))
    repo = st.secrets.get("DATA_REPO", os.environ.get("DATA_REPO"))
    files = list_repo_files(repo, repo_type="dataset", token=token)
    emb_name = next(f for f in files if f.startswith("embeddings_") and f.endswith(".npy"))
    senses = hf_hub_download(repo, "senses.jsonl.gz", repo_type="dataset", token=token)
    emb = hf_hub_download(repo, emb_name, repo_type="dataset", token=token)
    return ReverseDictionary(senses, emb, OnnxE5())


def card(n, r):
    labels = f"<i style='opacity:.7'>({html.escape(', '.join(r['labels']))})</i> " if r["labels"] else ""
    lemma = f" <span style='opacity:.6;font-size:.9em'>{html.escape(r['lemma'])}</span>" if r["lemma"] != r["word"] else ""
    syn = (f"<div style='opacity:.75;font-size:.92em;margin-top:2px'>Συνώνυμα: {html.escape(', '.join(r['synonyms']))}</div>"
           if r["synonyms"] else "")
    return (f"<div style='border:1px solid rgba(128,128,128,.35);border-radius:10px;padding:8px 14px;margin:8px 0'>"
            f"<span style='opacity:.6'>{n}.</span> <b style='font-size:1.2em'>{html.escape(r['word'])}</b>{lemma}"
            f"<div style='margin-top:3px'>{labels}{html.escape(r['definition'])}</div>{syn}</div>")


st.title("Αντίστροφο Λεξικό")
st.markdown("**Περιγράφω την έννοια, βρίσκω τη λέξη.** Γράψε τι σημαίνει η λέξη που ψάχνεις "
            "και πάρε 10 υποψήφιες λέξεις με τον ορισμό τους.")

rd = load()

if "q" not in st.session_state:
    st.session_state.q = ""
cols = st.columns(len(EXAMPLES))
for c, ex in zip(cols, EXAMPLES):
    if c.button(ex, use_container_width=True):
        st.session_state.q = ex

with st.form("search"):
    q = st.text_input("Περιγραφή", key="q", placeholder="π.χ. ο φόβος για κλειστούς χώρους")
    st.form_submit_button("Βρες τη λέξη", type="primary")

if q.strip():
    results = rd.search(q, k=10)
    st.markdown("".join(card(i, r) for i, r in enumerate(results, 1)), unsafe_allow_html=True)

st.caption("Ορισμοί: Λεξικό της Κοινής Νεοελληνικής, Ινστιτούτο Νεοελληνικών Σπουδών (ΑΠΘ), μέσω glossAPI — "
           "άδεια CC BY-NC-ND 4.0, μη εμπορική χρήση. Αναζήτηση με νόημα: intfloat/multilingual-e5-large. "
           "Εργασία μαθήματος «Σύγχρονες Διαδικτυακές Υπηρεσίες».")
