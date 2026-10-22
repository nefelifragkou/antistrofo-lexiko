# Αντίστροφο Λεξικό — «Περιγράφω την Έννοια, Βρίσκω τη Λέξη»

Εργασία μαθήματος **Σύγχρονες Διαδικτυακές Υπηρεσίες** (2026–27), θέμα 11.

Ο χρήστης περιγράφει μια έννοια («ο φόβος για κλειστούς χώρους») και παίρνει **10 υποψήφιες λέξεις
με τον ορισμό τους** από το Λεξικό της Κοινής Νεοελληνικής («κλειστοφοβία»).

- **Εφαρμογή:** ΣΥΝΔΕΣΜΟΣ_STREAMLIT
- **Οδηγός χρήσης:** [USER_GUIDE.md](USER_GUIDE.md)
- **Βασικά prompts προς τον coding agent:** [PROMPTS.md](PROMPTS.md)

## Αποτελέσματα με μια ματιά

30 περιγραφές ελέγχου, γραμμένες χωρίς να δει κανείς τους ορισμούς του λεξικού:

| | Λεξικό (η εφαρμογή) | ChatGPT | Gemini |
| --- | --- | --- | --- |
| Σωστή λέξη στις 10 πρώτες | 15/30 (50%) | 28/30 (93%) | 27/30 (90%) |
| Σωστή λέξη 1η | 6/30 (20%) | 23/30 (77%) | 24/30 (80%) |
| Προτάσεις που υπάρχουν στο λεξικό | 100% | 69% | 82% |

Τα LLM βρίσκουν πιο συχνά τη λέξη· η εφαρμογή δίνει πάντα υπαρκτή λέξη με επίσημο ορισμό.
Αναλυτικά: `evaluation_results.xlsx`.

## Πώς δουλεύει

1. **Εξερεύνηση** 31 λημμάτων με το χέρι → κανόνες για το πώς είναι γραμμένο ένα λήμμα.
2. **Χωρισμός σε σημασίες** (`split_senses.py`): 46.745 λήμματα → 77.039 σημασίες
   (ορισμός, συνώνυμα, αντώνυμα, ετικέτες). Εξαιρούνται προθήματα/επιθήματα, λέξεις γραμματικής,
   επιφωνήματα, φράσεις και παροιμίες. Ορισμοί μίας λέξης παίρνουν «δανεικό» τον ορισμό της λέξης
   στην οποία παραπέμπουν.
3. **Embeddings** (`step4_embeddings.ipynb`, Google Colab): κάθε σημασία γίνεται διάνυσμα «νοήματος».
   Σύγκριση 4 μοντέλων σε 20 περιγραφές-δοκιμής → `intfloat/multilingual-e5-large`
   (80% έναντι 30% για απλή σύγκριση γραμμάτων· `model_comparison.csv`).
4. **Σελίδα αναζήτησης** (`streamlit_app.py`, Streamlit Community Cloud): η περιγραφή γίνεται
   διάνυσμα με το ίδιο μοντέλο (ONNX, quantized) και συγκρίνεται με όλες τις σημασίες.
5. **Αξιολόγηση**: 30 περιγραφές ελέγχου στην εφαρμογή και σε δύο LLM χωρίς πρόσβαση στο λεξικό.

## Αρχεία

| Αρχείο | Τι κάνει / τι περιέχει |
| --- | --- |
| **Εφαρμογή** | |
| `streamlit_app.py` | Η σελίδα: αναζήτηση και κομμάτι «Αξιολόγηση» |
| `search.py` | Περιγραφή → 10 λέξεις (μία φορά κάθε λέξη, με την πιο κοντινή σημασία της) |
| `encoder.py` | Το μοντέλο e5-large σε μορφή ONNX (χωρά στη δωρεάν μνήμη του Streamlit) |
| `evaluate.py` | Μέτρηση: σωστή λέξη 1η / στις 10, ανά ομάδα |
| `requirements.txt` | Βιβλιοθήκες της εφαρμογής |
| **Επεξεργασία δεδομένων** | |
| `parquet_reader.py` | Μικρός αναγνώστης parquet χωρίς εξωτερικές βιβλιοθήκες |
| `split_senses.py` | Χωρισμός λημμάτων σε σημασίες (βήμα 3) |
| `review_workbook.py` | Excel για χειροκίνητο έλεγχο του χωρισμού |
| **Embeddings** | |
| `build_notebook.py` → `step4_embeddings.ipynb` | Notebook για Colab: embeddings και σύγκριση μοντέλων |
| `dev_queries.json` | Οι 20 περιγραφές-δοκιμής (μόνο για την επιλογή μοντέλου) |
| `model_comparison.csv`, `dev_queries_results.csv`, `chosen_model.json` | Αποτελέσματα σύγκρισης μοντέλων |
| **Αξιολόγηση** | |
| `eval_template.py` | Excel για τη συγγραφή των 30 περιγραφών ελέγχου |
| `eval_queries.csv` | Οι 30 περιγραφές ελέγχου (λέξη, περιγραφή, είδος, δυσκολία, ίδια ρίζα) |
| `llm_prompt.txt` | Το prompt που δόθηκε στα LLM |
| `eval_results_dictionary.csv` | Αποτελέσματα της εφαρμογής |
| `llm_answers_chatgpt.txt`, `llm_answers_gemini.txt` | Απαντήσεις των LLM (22/10/2026) |
| `score_llm.py` | Βαθμολόγηση των LLM με τους ίδιους κανόνες |
| `results_workbook.py` → `evaluation_results.xlsx` | Σύνοψη και αποτελέσματα ανά περιγραφή |
| **Τεκμηρίωση** | |
| `USER_GUIDE.md` | Οδηγός χρήσης |
| `PROMPTS.md` | Τα βασικά prompts προς τον coding agent, με τη σειρά |

## Δεδομένα και άδεια

- Πηγή: [glossAPI/modern-greek-dictionary](https://huggingface.co/datasets/glossAPI/modern-greek-dictionary)
  ([Mozilla Data Collective](https://mozilladatacollective.com/datasets/cmo1sklpo00d0mk07taoepe1a)) —
  Λεξικό της Κοινής Νεοελληνικής, Ινστιτούτο Νεοελληνικών Σπουδών (ΑΠΘ).
- Άδεια: **CC BY-NC-ND 4.0** (μόνο μη εμπορική χρήση). Γι' αυτό τα δεδομένα του λεξικού **δεν**
  βρίσκονται σε αυτό το αποθετήριο: η εφαρμογή φορτώνει τις σημασίες και τα embeddings από ιδιωτικό
  αποθετήριο δεδομένων στο Hugging Face.

## Αναπαραγωγή

```bash
# 1. Χωρισμός σε σημασίες (θέλει το αρχείο του λεξικού στο data/raw/)
python3 split_senses.py                 # → data/processed/senses.jsonl

# 2. Embeddings: άνοιγμα του step4_embeddings.ipynb στο Google Colab (GPU T4), «Run all»,
#    ανέβασμα του senses.jsonl.gz όταν ζητηθεί.

# 3. Εφαρμογή (τοπικά)
pip install -r requirements.txt
HF_TOKEN=hf_... DATA_REPO=χρήστης/antistrofo-lexiko-data streamlit run streamlit_app.py

# 4. Αξιολόγηση: eval_queries.csv στο κομμάτι «Αξιολόγηση» της σελίδας → eval_results_dictionary.csv,
#    llm_prompt.txt σε ChatGPT/Gemini → llm_answers_*.txt, και μετά:
python3 score_llm.py && python3 results_workbook.py evaluation_results.xlsx
```

Στο Streamlit Community Cloud τα `HF_TOKEN` και `DATA_REPO` μπαίνουν στα **Secrets** της εφαρμογής.

## Υλοποίηση

Ο κώδικας γράφτηκε με coding agent (Claude), όπως επιτρέπει η εκφώνηση· οι αποφάσεις περιεχομένου
και ο έλεγχος ποιότητας έγιναν χειροκίνητα. Βλ. [PROMPTS.md](PROMPTS.md).
