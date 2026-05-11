"""FAISS index over the product catalog, used for vibe-to-item retrieval."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from vibecheck.rec.encoder import FashionBertEncoder, l2_normalize

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PRODUCTS_PATH = REPO_ROOT / "reddit" / "example-fashion-dataset.json"
DEFAULT_PRECOMPUTED_EMBEDDINGS = REPO_ROOT / "reddit" / "FINAL-EMBEDDINGS.csv"
DEFAULT_CACHE_PATH = REPO_ROOT / "data" / "processed" / "product_embeddings.npy"


@dataclass
class Product:
    """A single product catalog entry (currently sourced from Depop)."""

    id: str
    name: str
    description: str
    category: str
    brand: str
    gender: str
    price: str
    product_link: str
    image_link: str

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "Product":
        """Build a Product from a raw row of example-fashion-dataset.json."""
        return cls(
            id=str(raw.get("ID", "")),
            name=str(raw.get("name", "")),
            description=str(raw.get("description", "")),
            category=str(raw.get("category", "")),
            brand=str(raw.get("brand", "")),
            gender=str(raw.get("gender", "")),
            price=str(raw.get("price", "")),
            product_link=str(raw.get("prodLink", "")),
            image_link=str(raw.get("prodImgLink", "")),
        )

    def encode_text(self) -> str:
        """Return the text used to compute this product's embedding."""
        parts = [self.name, self.description, self.category, self.gender]
        return " ".join(p for p in parts if p)

    def to_dict(self, score: float | None = None) -> dict[str, Any]:
        """Return a JSON-safe representation, optionally with a similarity score."""
        out: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "brand": self.brand,
            "gender": self.gender,
            "price": self.price,
            "image_url": self.image_link,
            "product_url": self.product_link,
        }
        if score is not None:
            out["score"] = round(float(score), 4)
        return out


@dataclass
class ProductIndex:
    """In-memory FAISS index over product embeddings."""

    products: list[Product]
    embeddings: np.ndarray
    _index: Any = field(default=None, init=False, repr=False)

    @property
    def index(self):
        """Return the lazily-built FAISS IndexFlatIP."""
        if self._index is None:
            import faiss

            self._index = faiss.IndexFlatIP(self.embeddings.shape[1])
            self._index.add(self.embeddings)
        return self._index

    def search(self, query_vec: np.ndarray, k: int = 10) -> list[tuple[float, int, Product]]:
        """Return (score, idx, product) triples for the k most similar products.

        ``idx`` is the product's row in ``self.products`` and ``self.embeddings``,
        which downstream selection logic uses to look up embeddings without
        re-encoding.
        """
        if query_vec.ndim == 1:
            query_vec = query_vec[None, :]
        if k <= 0 or len(self.products) == 0:
            return []
        scores, idxs = self.index.search(query_vec.astype(np.float32), k)
        results: list[tuple[float, int, Product]] = []
        for score, idx in zip(scores[0], idxs[0]):
            if 0 <= idx < len(self.products):
                results.append((float(score), int(idx), self.products[idx]))
        return results


def load_product_index(
    *,
    encoder: FashionBertEncoder | None = None,
    products_path: Path | str = DEFAULT_PRODUCTS_PATH,
    precomputed_embeddings: Path | str | None = DEFAULT_PRECOMPUTED_EMBEDDINGS,
    cache_path: Path | str | None = DEFAULT_CACHE_PATH,
    rebuild: bool = False,
) -> ProductIndex:
    """Load (or build + cache) the product FAISS index.

    Resolution order for embeddings:

    1. ``cache_path`` if it exists and matches the catalog size.
    2. ``precomputed_embeddings`` (Julia's ``FINAL-EMBEDDINGS.csv``) aligned to
       product IDs. Only the products that have a precomputed embedding are
       kept; one product in the example dataset has no precomputed vector.
    3. Encode every product on the fly with ``encoder``.
    """
    products_path = Path(products_path)
    cache_path = Path(cache_path) if cache_path else None
    precomputed_path = Path(precomputed_embeddings) if precomputed_embeddings else None

    products = _load_products(products_path)
    if not products:
        raise FileNotFoundError(
            f"No products found at {products_path}. "
            "Make sure reddit/example-fashion-dataset.json is in the repo."
        )

    embeddings: np.ndarray | None = None

    if cache_path and cache_path.exists() and not rebuild:
        cached = np.load(cache_path)
        if cached.shape[0] == len(products):
            embeddings = cached.astype(np.float32)

    if embeddings is None and precomputed_path and precomputed_path.exists() and not rebuild:
        aligned = _load_precomputed_embeddings(precomputed_path, products)
        if aligned is not None:
            embeddings, products = aligned
            if cache_path:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                np.save(cache_path, embeddings)

    if embeddings is None:
        encoder = encoder or FashionBertEncoder()
        embeddings = encoder.encode([p.encode_text() for p in products], show_progress=True)
        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            np.save(cache_path, embeddings)

    embeddings = l2_normalize(embeddings)
    return ProductIndex(products=products, embeddings=embeddings)


def _load_products(path: Path) -> list[Product]:
    """Load the product catalog JSON into typed Product records."""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, list):
        return []
    return [Product.from_raw(item) for item in raw if isinstance(item, dict)]


def _load_precomputed_embeddings(
    path: Path, products: list[Product]
) -> tuple[np.ndarray, list[Product]] | None:
    """Read FINAL-EMBEDDINGS.csv and align it to the product catalog by ID."""
    id_to_product = {p.id: p for p in products}
    aligned_products: list[Product] = []
    rows: list[np.ndarray] = []

    with path.open("r", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        next(reader, None)  # header: id,dim0,dim1,...,dimN
        for row in reader:
            if not row:
                continue
            row_id = row[0].strip()
            product = id_to_product.get(row_id)
            if product is None:
                continue
            try:
                vec = np.array([float(x) for x in row[1:]], dtype=np.float32)
            except ValueError:
                continue
            aligned_products.append(product)
            rows.append(vec)

    if not rows:
        return None
    return np.stack(rows, axis=0), aligned_products
