"""Vibe-to-product recommendation: encoder, indexes, query expansion, retrieval."""

from vibecheck.rec.encoder import FashionBertEncoder
from vibecheck.rec.expansion import expand_query
from vibecheck.rec.playlists import Track, build_search_queries, recommend_tracks
from vibecheck.rec.products import Product, ProductIndex, load_product_index
from vibecheck.rec.recommend import (
    RecommendationConfig,
    build_query_string,
    recommend_items,
)
from vibecheck.rec.select import SelectionConfig, SelectionResult, select_items
from vibecheck.rec.spotify_client import SpotifyAPIError, SpotifyClient
from vibecheck.rec.text_index import RedditTextIndex, load_reddit_index

__all__ = [
    "FashionBertEncoder",
    "Product",
    "ProductIndex",
    "RecommendationConfig",
    "RedditTextIndex",
    "SelectionConfig",
    "SelectionResult",
    "SpotifyAPIError",
    "SpotifyClient",
    "Track",
    "build_query_string",
    "build_search_queries",
    "expand_query",
    "load_product_index",
    "load_reddit_index",
    "recommend_items",
    "recommend_tracks",
    "select_items",
]
