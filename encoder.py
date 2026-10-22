"""Το μοντέλο e5-large σε «ελαφριά» μορφή (ONNX, quantized) — χωρά στη δωρεάν μνήμη του Streamlit.

Κάνει ό,τι και το SentenceTransformer του Colab: tokenizer -> μοντέλο -> μέσος όρος (mean pooling)
-> κανονικοποίηση, ώστε οι ερωτήσεις να συγκρίνονται με τα embeddings των ορισμών.
"""
import numpy as np
import onnxruntime as ort
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer

ONNX_REPO = "Xenova/multilingual-e5-large"


class OnnxE5:
    def __init__(self, repo=ONNX_REPO, onnx_file="onnx/model_quantized.onnx", max_len=256):
        tok_path = hf_hub_download(repo, "tokenizer.json")
        model_path = hf_hub_download(repo, onnx_file)
        self.tokenizer = Tokenizer.from_file(tok_path)
        self.tokenizer.enable_truncation(max_length=max_len)
        self.tokenizer.enable_padding(pad_id=1, pad_token="<pad>")
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 2
        self.session = ort.InferenceSession(model_path, opts, providers=["CPUExecutionProvider"])
        self.input_names = {i.name for i in self.session.get_inputs()}

    def encode(self, texts, normalize_embeddings=True):
        enc = self.tokenizer.encode_batch(list(texts))
        ids = np.array([e.ids for e in enc], dtype=np.int64)
        mask = np.array([e.attention_mask for e in enc], dtype=np.int64)
        feeds = {"input_ids": ids, "attention_mask": mask}
        if "token_type_ids" in self.input_names:
            feeds["token_type_ids"] = np.zeros_like(ids)
        hidden = self.session.run(None, feeds)[0]          # (πλήθος, λέξεις, 1024)
        m = mask[..., None].astype(np.float32)
        vec = (hidden * m).sum(axis=1) / np.clip(m.sum(axis=1), 1e-9, None)
        if normalize_embeddings:
            vec = vec / np.linalg.norm(vec, axis=1, keepdims=True)
        return vec.astype(np.float32)
