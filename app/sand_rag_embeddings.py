"""
Optional semantic RAG for SAND using local sentence embeddings.

This module is only used if SAND_RAG_MODE="embeddings".
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict
import pandas as pd

try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
except Exception:  # optional dependency
    np = None
    SentenceTransformer = None


@dataclass
class SandDoc:
    id_img: str
    language: str
    text: str
    meta: Dict


class SandRAGEmbeddings:
    def __init__(self, tsv_path: str | Path, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self.tsv_path = Path(tsv_path)
        self.model_name = model_name
        self.model = SentenceTransformer(model_name) if SentenceTransformer else None
        self.docs: List[SandDoc] = []
        self.embeddings = None

    def load(self) -> "SandRAGEmbeddings":
        if not self.tsv_path.exists():
            return self

        df = pd.read_csv(self.tsv_path, sep="\t")

        for _, row in df.iterrows():
            lang = str(row.get("Language", "")).strip() or "en"
            natural = str(row.get("Natural_text", "")).strip()
            validated = str(row.get("Validated_generated_text", "")).strip()
            text = natural if natural and natural != "nan" else validated

            if not text or text == "nan":
                continue

            self.docs.append(
                SandDoc(
                    id_img=str(row.get("ID_img", "")),
                    language=lang,
                    text=text,
                    meta={},
                )
            )

        return self

    def build(self) -> "SandRAGEmbeddings":
        if not self.docs or not self.model or np is None:
            return self

        texts = [d.text for d in self.docs]
        self.embeddings = self.model.encode(texts, normalize_embeddings=True)
        return self

    def search(self, query: str, lang: Optional[str] = None, k: int = 4) -> List[SandDoc]:
        if not self.docs or self.embeddings is None or not self.model or np is None:
            return []

        candidates = self.docs
        cand_idx = list(range(len(self.docs)))

        if lang in {"ar", "en"}:
            filtered = [(i, d) for i, d in enumerate(self.docs) if d.language == lang]
            if filtered:
                cand_idx = [i for i, _ in filtered]
                candidates = [d for _, d in filtered]

        q_emb = self.model.encode([query], normalize_embeddings=True)[0]
        sub_embs = self.embeddings[cand_idx]
        sims = np.dot(sub_embs, q_emb)

        top = np.argsort(sims)[-k:][::-1]
        return [candidates[i] for i in top]


_sem_singleton: Optional[SandRAGEmbeddings] = None


def get_sand_rag_embeddings() -> SandRAGEmbeddings:
    global _sem_singleton
    if _sem_singleton is not None:
        return _sem_singleton

    rag = SandRAGEmbeddings("data/SAND_texts.tsv").load().build()
    _sem_singleton = rag
    return _sem_singleton