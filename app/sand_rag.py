"""
SAND RAG (TF-IDF) for Suwwah.

Provides lightweight retrieval over the Saudi Arabia Self-Narrative Dataset (SAND).
Includes a small mock fallback so the system stays functional if the TSV is missing.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class SandDoc:
    id_img: str
    language: str
    text: str
    meta: Dict


class SandRAG:
    def __init__(self, tsv_path: str | Path):
        self.tsv_path = Path(tsv_path)
        self.docs: List[SandDoc] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.matrix = None

    def load(self) -> "SandRAG":
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
                    meta={
                        "error_type": row.get("Error_type", ""),
                        "gender_label": row.get("Gender_label", ""),
                        "image_activity": row.get("Image_activity", ""),
                        "image_object": row.get("Image_object", ""),
                        "image_context": row.get("Image_context", ""),
                    },
                )
            )

        return self

    def build(self) -> "SandRAG":
        if not self.docs:
            return self

        corpus = [d.text for d in self.docs]
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            max_features=5000,
            ngram_range=(1, 2),
        )
        self.matrix = self.vectorizer.fit_transform(corpus)
        return self

    def search(self, query: str, lang: Optional[str] = None, k: int = 4) -> List[SandDoc]:
        if not self.docs or self.vectorizer is None or self.matrix is None:
            return []

        candidates = self.docs
        if lang in {"ar", "en"}:
            filtered = [d for d in self.docs if d.language == lang]
            if filtered:
                candidates = filtered

        subset_texts = [d.text for d in candidates]
        subset_matrix = self.vectorizer.transform(subset_texts)

        q_vec = self.vectorizer.transform([query])
        sims = cosine_similarity(q_vec, subset_matrix).flatten()

        top_idx = sims.argsort()[-k:][::-1]
        return [candidates[i] for i in top_idx]


def get_mock_sand_rag() -> SandRAG:
    rag = SandRAG("data/SAND_texts.tsv")
    rag.docs = [
        SandDoc(
            id_img="mock_ar_1",
            language="ar",
            text="تجارب سياحية تجمع بين الثقافة والطبيعة والضيافة السعودية في مناطق متعددة.",
            meta={}
        ),
        SandDoc(
            id_img="mock_ar_2",
            language="ar",
            text="التراث والتاريخ والأسواق التقليدية من أبرز عناصر التجربة السياحية المحلية.",
            meta={}
        ),
        SandDoc(
            id_img="mock_en_1",
            language="en",
            text="Saudi tourism highlights culture, nature, and authentic local hospitality across regions.",
            meta={}
        ),
        SandDoc(
            id_img="mock_en_2",
            language="en",
            text="Heritage sites, traditional markets, and family-friendly experiences remain key themes.",
            meta={}
        ),
    ]
    rag.build()
    return rag


_sand_rag_singleton: Optional[SandRAG] = None


def get_sand_rag(use_mock_if_missing: bool = True) -> SandRAG:
    global _sand_rag_singleton
    if _sand_rag_singleton is not None:
        return _sand_rag_singleton

    rag = SandRAG("data/SAND_texts.tsv").load()

    if not rag.docs and use_mock_if_missing:
        _sand_rag_singleton = get_mock_sand_rag()
        return _sand_rag_singleton

    _sand_rag_singleton = rag.build()
    return _sand_rag_singleton