#!/usr/bin/env python3
"""
Utility functions for generating temporal hypergraphs from Polymarket trading data.
"""

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import List, Dict, Set, Tuple


def get_day_start_timestamp(unix_timestamp):
    """Convert Unix timestamp to start of day (UTC) timestamp."""
    dt = datetime.fromtimestamp(int(unix_timestamp), tz=timezone.utc)
    day_start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(day_start.timestamp())


def classify_trade(fill: Dict) -> Dict:
    """
    Classify a fill by buyer, seller, outcome token, and day.

    Args:
        fill: Raw fill record from Goldsky

    Returns:
        dict with keys: buyer, seller, outcome_token, day_start
    """
    maker = fill['maker'].lower()
    taker = fill['taker'].lower()
    maker_asset = fill['makerAssetId']
    taker_asset = fill['takerAssetId']
    timestamp = fill['timestamp']

    # Determine buyer and outcome token
    if maker_asset == "0":
        # Maker has USDC, so maker is buying the outcome token from taker
        buyer = maker
        seller = taker
        outcome_token = taker_asset
    else:
        # Taker has USDC, so taker is buying the outcome token from maker
        buyer = taker
        seller = maker
        outcome_token = maker_asset

    day_start = get_day_start_timestamp(timestamp)

    return {
        'buyer': buyer,
        'seller': seller,
        'outcome_token': outcome_token,
        'day_start': day_start
    }


def build_hypergraph_from_fills(
    fills: List[Dict],
    market_slug: str = None
) -> Tuple[List[Dict], Set[str]]:
    """
    Build hypergraph from fills data for a single market or multiple markets.

    Args:
        fills: List of fill records
        market_slug: Optional market slug (for single market mode)

    Returns:
        Tuple of (hyperedges list, all_traders set)
    """
    # Track hyperedges: (market, outcome_token, day_start, side) -> set of traders
    hyperedge_data = defaultdict(set)
    all_traders = set()

    for fill in fills:
        trade_info = classify_trade(fill)
        buyer = trade_info['buyer']
        seller = trade_info['seller']
        outcome_token = trade_info['outcome_token']
        day_start = trade_info['day_start']

        # Use provided market_slug or extract from fill if available
        market = market_slug or 'market'

        # Add to buyer hyperedge
        buy_key = (market, outcome_token, day_start, 'BUY')
        hyperedge_data[buy_key].add(buyer)
        all_traders.add(buyer)

        # Add to seller hyperedge
        sell_key = (market, outcome_token, day_start, 'SELL')
        hyperedge_data[sell_key].add(seller)
        all_traders.add(seller)

    # Convert to list of hyperedges
    hyperedges = []
    for (market, outcome, day_start, side), traders in hyperedge_data.items():
        hyperedges.append({
            'market': market,
            'outcome': outcome,
            'day_start': day_start,
            'side': side,
            'traders': traders,
        })

    # Sort hyperedges by timestamp, then by market, outcome, side
    hyperedges.sort(key=lambda x: (x['day_start'], x['market'], x['outcome'], x['side']))

    return hyperedges, all_traders


def write_hypergraph_files(
    hyperedges: List[Dict],
    all_traders: Set[str],
    output_dir: str,
    prefix: str
) -> Dict:
    """
    Write hypergraph files in congress-bills format.

    Args:
        hyperedges: List of hyperedge dicts
        all_traders: Set of all trader addresses
        output_dir: Output directory path
        prefix: Filename prefix (e.g., 'polymarket-unified')

    Returns:
        Dictionary with statistics about the generated hypergraph
    """
    os.makedirs(output_dir, exist_ok=True)

    # Create node ID mapping (sorted for consistency)
    traders_list = sorted(all_traders)
    trader_to_id = {trader: idx + 1 for idx, trader in enumerate(traders_list)}

    # Write node labels
    labels_file = os.path.join(output_dir, f'{prefix}-node-labels.txt')
    with open(labels_file, 'w') as f:
        for trader in traders_list:
            f.write(f"{trader}\n")

    # Prepare hyperedge data
    nverts_list = []
    simplices_list = []
    times_list = []

    for edge in hyperedges:
        traders = sorted(edge['traders'])  # Sort for consistency
        nverts = len(traders)

        nverts_list.append(nverts)
        times_list.append(edge['day_start'])

        # Add trader IDs to simplices
        for trader in traders:
            simplices_list.append(trader_to_id[trader])

    # Write nverts
    nverts_file = os.path.join(output_dir, f'{prefix}-nverts.txt')
    with open(nverts_file, 'w') as f:
        for n in nverts_list:
            f.write(f"{n}\n")

    # Write simplices
    simplices_file = os.path.join(output_dir, f'{prefix}-simplices.txt')
    with open(simplices_file, 'w') as f:
        for node_id in simplices_list:
            f.write(f"{node_id}\n")

    # Write times
    times_file = os.path.join(output_dir, f'{prefix}-times.txt')
    with open(times_file, 'w') as f:
        for t in times_list:
            f.write(f"{t}\n")

    # Return statistics
    stats = {
        'nodes': len(traders_list),
        'hyperedges': len(hyperedges),
        'total_vertex_occurrences': sum(nverts_list),
        'output_dir': output_dir,
        'files': {
            'node_labels': labels_file,
            'nverts': nverts_file,
            'simplices': simplices_file,
            'times': times_file
        }
    }

    return stats


def generate_market_hypergraph(
    raw_fills_path: str,
    market_slug: str,
    output_dir: str = None
) -> Dict:
    """
    Generate hypergraph for a single market from raw fills JSON file.

    Args:
        raw_fills_path: Path to raw fills JSON file
        market_slug: Market slug
        output_dir: Optional custom output directory. Defaults to data/hypergraphs/by-market/{slug}

    Returns:
        Dictionary with hypergraph statistics
    """
    # Load fills
    with open(raw_fills_path, 'r') as f:
        fills = json.load(f)

    if not fills:
        raise ValueError(f"No fills found in {raw_fills_path}")

    # Build hypergraph
    hyperedges, all_traders = build_hypergraph_from_fills(fills, market_slug)

    # Determine output directory
    if output_dir is None:
        output_dir = f"data/hypergraphs/by-market/{market_slug}"

    # Write files
    stats = write_hypergraph_files(hyperedges, all_traders, output_dir, market_slug)

    print(f"Generated hypergraph for {market_slug}:")
    print(f"  - {stats['nodes']} nodes")
    print(f"  - {stats['hyperedges']} hyperedges")
    print(f"  - {stats['total_vertex_occurrences']} total vertex occurrences")

    return stats


def generate_unified_hypergraph(
    raw_dir: str = 'data/raw',
    output_dir: str = 'data/hypergraphs/unified'
) -> Dict:
    """
    Generate unified hypergraph from all markets in raw directory.

    Args:
        raw_dir: Directory containing raw fills JSON files
        output_dir: Output directory for unified hypergraph

    Returns:
        Dictionary with hypergraph statistics
    """
    # Load all fills from all markets
    fills_by_market = {}

    for filename in os.listdir(raw_dir):
        if filename.startswith('fills_') and filename.endswith('.json'):
            market_slug = filename[6:-5]  # Remove 'fills_' prefix and '.json' suffix
            filepath = os.path.join(raw_dir, filename)

            with open(filepath, 'r') as f:
                fills = json.load(f)
                fills_by_market[market_slug] = fills

    if not fills_by_market:
        raise ValueError(f"No fills files found in {raw_dir}")

    # Build unified hypergraph
    hyperedge_data = defaultdict(set)
    all_traders = set()

    for market_slug, fills in fills_by_market.items():
        for fill in fills:
            trade_info = classify_trade(fill)
            buyer = trade_info['buyer']
            seller = trade_info['seller']
            outcome_token = trade_info['outcome_token']
            day_start = trade_info['day_start']

            # Add to buyer hyperedge
            buy_key = (market_slug, outcome_token, day_start, 'BUY')
            hyperedge_data[buy_key].add(buyer)
            all_traders.add(buyer)

            # Add to seller hyperedge
            sell_key = (market_slug, outcome_token, day_start, 'SELL')
            hyperedge_data[sell_key].add(seller)
            all_traders.add(seller)

    # Convert to list of hyperedges
    hyperedges = []
    for (market, outcome, day_start, side), traders in hyperedge_data.items():
        hyperedges.append({
            'market': market,
            'outcome': outcome,
            'day_start': day_start,
            'side': side,
            'traders': traders,
        })

    # Sort by timestamp, market, outcome, side
    hyperedges.sort(key=lambda x: (x['day_start'], x['market'], x['outcome'], x['side']))

    # Write files
    stats = write_hypergraph_files(hyperedges, all_traders, output_dir, 'polymarket-unified')

    print(f"Generated unified hypergraph:")
    print(f"  - {stats['nodes']} nodes")
    print(f"  - {stats['hyperedges']} hyperedges")
    print(f"  - {stats['total_vertex_occurrences']} total vertex occurrences")
    print(f"  - {len(fills_by_market)} markets")

    stats['markets_count'] = len(fills_by_market)
    return stats
