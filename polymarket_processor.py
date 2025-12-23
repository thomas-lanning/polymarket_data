#!/usr/bin/env python3
"""
Module for fetching Polymarket data from Gamma API and Goldsky subgraph.
"""

import json
import os
import re
import time
import requests
from typing import List, Dict, Tuple
from hypergraph_utils import generate_market_hypergraph, generate_unified_hypergraph


class PolymarketProcessor:
    """Handles fetching Polymarket market data from Gamma API and Goldsky subgraph."""

    GAMMA_BASE = "https://gamma-api.polymarket.com"
    GOLDSKY_ORDERBOOK = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn"

    FILLS_QUERY_TEMPLATE = """
    query Fills($tokenIds: [String!]!, $first: Int!, $skip: Int!) {
      orderFilledEvents(
        where: { SIDE_in: $tokenIds }
        orderBy: timestamp
        orderDirection: asc
        first: $first
        skip: $skip
      ) {
        id
        timestamp
        transactionHash
        orderHash
        maker
        taker
        makerAssetId
        takerAssetId
        makerAmountFilled
        takerAmountFilled
        fee
      }
    }
    """

    def __init__(self, raw_data_dir: str):
        """
        Initialize the processor.

        Args:
            raw_data_dir: Directory for raw fills JSON files (e.g., 'data/raw')
        """
        self.raw_data_dir = raw_data_dir

    @staticmethod
    def _ensure_list(x):
        """Gamma sometimes returns arrays as JSON strings. Normalize to Python list."""
        if x is None:
            return []
        if isinstance(x, list):
            return x
        if isinstance(x, str):
            s = x.strip()
            if s.startswith("[") and s.endswith("]"):
                return json.loads(s)
            return [x]
        return [x]

    @staticmethod
    def parse_market_slug(text: str) -> str:
        """
        Parse market slug from URL or slug string.

        Args:
            text: Market slug or full URL

        Returns:
            Market slug string
        """
        text = text.strip()
        if "polymarket.com" in text:
            # Take the last non-empty path segment
            parts = [p for p in re.split(r"[/?#]", text) if p]
            return parts[-1]
        return text

    @staticmethod
    def parse_event_slug(text: str) -> str:
        """
        Parse event slug from URL or slug string.

        Args:
            text: Event slug or full URL (e.g., "https://polymarket.com/events/republican-presidential-nominee-2028")

        Returns:
            Event slug string
        """
        text = text.strip()
        if "polymarket.com" in text:
            # Look for /events/ in the URL and extract the slug after it
            if "/events/" in text:
                parts = text.split("/events/")
                if len(parts) > 1:
                    # Get everything after /events/, remove query params and fragments
                    slug_part = parts[1].split("?")[0].split("#")[0]
                    # Remove trailing slashes
                    return slug_part.rstrip("/")
            # Fallback: take the last non-empty path segment
            parts = [p for p in re.split(r"[/?#]", text) if p]
            return parts[-1]
        return text

    def fetch_market_metadata(self, slug: str) -> Dict:
        """
        Fetch market metadata from Gamma API.

        Args:
            slug: Market slug

        Returns:
            Market metadata dictionary
        """
        url = f"{self.GAMMA_BASE}/markets/slug/{slug}"
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        return r.json()

    def fetch_event_metadata(self, event_slug: str) -> Dict:
        """
        Fetch event metadata from Gamma API events endpoint.

        Args:
            event_slug: Event slug

        Returns:
            Event metadata dictionary with 'markets' array
        """
        url = f"{self.GAMMA_BASE}/events/slug/{event_slug}"
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        return r.json()

    def get_event_markets(self, event_data: Dict) -> List[Dict]:
        """
        Extract and format markets list from event data with volume info.

        Args:
            event_data: Event metadata from Gamma API

        Returns:
            List of market dictionaries sorted by volume descending
        """
        markets = event_data.get("markets", [])

        formatted_markets = []
        for market in markets:
            # Normalize clobTokenIds from JSON string to list
            clob_token_ids = self._ensure_list(market.get("clobTokenIds"))

            formatted_market = {
                "slug": market.get("slug", ""),
                "question": market.get("question", ""),
                "conditionId": market.get("conditionId", ""),
                "clobTokenIds": clob_token_ids,
                "groupItemTitle": market.get("groupItemTitle", ""),
                "volume": str(market.get("volume", 0)),
                "liquidity": str(market.get("liquidity", 0)),
                "lastTradePrice": str(market.get("lastTradePrice", ""))
            }
            formatted_markets.append(formatted_market)

        # Sort by volume descending
        formatted_markets.sort(key=lambda m: float(m["volume"]), reverse=True)

        return formatted_markets

    def extract_market_ids(self, market_obj: Dict) -> Tuple[str, List[str], List[str]]:
        """
        Extract condition ID, token IDs, and outcomes from market object.

        Args:
            market_obj: Market metadata from Gamma API

        Returns:
            Tuple of (condition_id, token_ids, outcomes)
        """
        condition_id = market_obj.get("conditionId")
        token_ids = [str(x) for x in self._ensure_list(market_obj.get("clobTokenIds"))]
        outcomes = [str(x) for x in self._ensure_list(market_obj.get("outcomes"))]

        if len(token_ids) != 2:
            raise ValueError(f"Expected 2 clobTokenIds; got {len(token_ids)}. token_ids={token_ids[:5]}")

        if len(outcomes) != 2:
            outcomes = outcomes or ["Yes", "No"]

        return condition_id, token_ids, outcomes

    def gql_post(self, query: str, variables: Dict) -> Dict:
        """
        Execute GraphQL query against Goldsky endpoint.

        Args:
            query: GraphQL query string
            variables: Query variables

        Returns:
            Response data dictionary
        """
        r = requests.post(
            self.GOLDSKY_ORDERBOOK,
            json={"query": query, "variables": variables},
            timeout=60
        )
        r.raise_for_status()
        data = r.json()
        if "errors" in data:
            raise RuntimeError(data["errors"])
        return data["data"]

    def fetch_side(self, token_ids: List[str], side_field: str, page_size: int = 1000) -> List[Dict]:
        """
        Fetch fills for one side (maker or taker).

        Args:
            token_ids: List of token IDs to query
            side_field: Either "makerAssetId" or "takerAssetId"
            page_size: Number of records per page

        Returns:
            List of fill records
        """
        query = self.FILLS_QUERY_TEMPLATE.replace("SIDE_in", f"{side_field}_in")
        all_rows = []
        skip = 0

        print(f"  Fetching {side_field}...")

        while True:
            data = self.gql_post(query, {"tokenIds": token_ids, "first": page_size, "skip": skip})
            rows = data["orderFilledEvents"]
            all_rows.extend(rows)
            print(f"    Fetched {len(all_rows)} records...")

            if len(rows) < page_size:
                break

            skip += page_size
            time.sleep(0.1)  # Small delay to avoid rate limiting

        return all_rows

    def fetch_all_fills(self, token_ids: List[str], page_size: int = 1000) -> List[Dict]:
        """
        Fetch all fills for given token IDs (both maker and taker side).

        Args:
            token_ids: List of token IDs
            page_size: Number of records per page

        Returns:
            Deduplicated and sorted list of fills
        """
        print("Fetching fills from Goldsky...")

        # Fetch both sides
        maker_side = self.fetch_side(token_ids, "makerAssetId", page_size)
        taker_side = self.fetch_side(token_ids, "takerAssetId", page_size)

        # Deduplicate by ID
        by_id = {}
        for row in maker_side + taker_side:
            by_id[row["id"]] = row

        fills = list(by_id.values())
        fills.sort(key=lambda x: int(x["timestamp"]))

        print(f"Total unique fills: {len(fills)}")
        return fills

    def process_market(self, market_url: str) -> Dict:
        """
        Complete pipeline: fetch raw fills and generate hypergraphs for a Polymarket market.

        Args:
            market_url: Market URL or slug

        Returns:
            Dictionary with processing results and statistics
        """
        print("="*60)
        print(f"Processing market: {market_url}")
        print("="*60)

        # Parse slug
        slug = self.parse_market_slug(market_url)
        print(f"Market slug: {slug}")

        # Fetch metadata
        print("\nFetching market metadata from Gamma API...")
        market_data = self.fetch_market_metadata(slug)
        condition_id, token_ids, outcomes = self.extract_market_ids(market_data)

        print(f"Condition ID: {condition_id}")
        print(f"Token IDs: {token_ids}")
        print(f"Outcomes: {outcomes}")

        # Fetch fills
        fills = self.fetch_all_fills(token_ids)

        if not fills:
            raise ValueError("No fills found for this market")

        # Save raw fills
        raw_fills_path = os.path.join(self.raw_data_dir, f"fills_{slug}.json")
        os.makedirs(self.raw_data_dir, exist_ok=True)
        with open(raw_fills_path, 'w') as f:
            json.dump(fills, f, indent=2)
        print(f"\nSaved raw fills to: {raw_fills_path}")

        # Calculate basic statistics from raw fills
        market_title = market_data.get('question', slug.replace('-', ' ').title())
        unique_traders = set()
        for fill in fills:
            unique_traders.add(fill['maker'].lower())
            unique_traders.add(fill['taker'].lower())

        timestamps = [int(fill['timestamp']) for fill in fills]
        min_ts = min(timestamps)
        max_ts = max(timestamps)

        print("\n" + "="*60)
        print("FETCH COMPLETE")
        print("="*60)
        print(f"Market: {slug}")
        print(f"Total fills: {len(fills)}")
        print(f"Unique traders: {len(unique_traders)}")
        print(f"Date range: {min_ts} to {max_ts}")
        print(f"Raw fills saved to: {raw_fills_path}")
        print("="*60)

        # Generate hypergraph for this market
        print("\nGenerating temporal hypergraph...")
        try:
            hypergraph_stats = generate_market_hypergraph(raw_fills_path, slug)
            print("Hypergraph generation complete!")
        except Exception as e:
            print(f"Warning: Hypergraph generation failed: {e}")
            hypergraph_stats = None

        # Regenerate unified hypergraph with all markets
        print("\nRegenerating unified hypergraph...")
        try:
            unified_stats = generate_unified_hypergraph()
            print("Unified hypergraph generation complete!")
        except Exception as e:
            print(f"Warning: Unified hypergraph generation failed: {e}")
            unified_stats = None

        return {
            'market_slug': slug,
            'market_title': market_title,
            'condition_id': condition_id,
            'total_fills': len(fills),
            'unique_traders': len(unique_traders),
            'timestamp_range': {
                'start': min_ts,
                'end': max_ts
            },
            'raw_fills_path': raw_fills_path,
            'hypergraph': hypergraph_stats,
            'unified_hypergraph': unified_stats
        }
