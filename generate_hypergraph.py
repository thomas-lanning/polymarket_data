#!/usr/bin/env python3
"""
Generate temporal hypergraphs from Polymarket trading data.

Hypergraph Structure:
- Nodes: Individual trader wallet addresses
- Hyperedges: Groups of traders who bought/sold the same outcome on the same market on the same day
- Timestamps: Start of each day (UTC)

Output Format (congress-bills style):
- node-labels.txt: List of trader addresses
- nverts.txt: Number of vertices in each hyperedge
- simplices.txt: Contiguous list of node IDs for all hyperedges
- times.txt: Timestamp for each hyperedge (day start in Unix seconds)
"""

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def load_raw_fills(raw_dir):
    """Load all raw fills JSON files from the specified directory."""
    fills_by_market = {}

    for filename in os.listdir(raw_dir):
        if filename.startswith('fills_') and filename.endswith('.json'):
            market_slug = filename[6:-5]  # Remove 'fills_' prefix and '.json' suffix
            filepath = os.path.join(raw_dir, filename)

            with open(filepath, 'r') as f:
                fills = json.load(f)
                fills_by_market[market_slug] = fills
                print(f"Loaded {len(fills)} fills for market: {market_slug}")

    return fills_by_market


def get_day_start_timestamp(unix_timestamp):
    """Convert Unix timestamp to start of day (UTC) timestamp."""
    dt = datetime.fromtimestamp(int(unix_timestamp), tz=timezone.utc)
    day_start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(day_start.timestamp())


def classify_trade(fill):
    """
    Classify a fill by buyer, seller, outcome token, and day.

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


def build_hypergraph(fills_by_market):
    """
    Build hypergraph from fills data.

    Returns:
        dict with:
        - hyperedges: list of (market, outcome, day, side, traders_set, timestamp)
        - all_traders: set of all unique trader addresses
    """
    # Track hyperedges: (market, outcome_token, day_start, side) -> set of traders
    hyperedge_data = defaultdict(set)
    all_traders = set()

    for market_slug, fills in fills_by_market.items():
        print(f"\nProcessing {market_slug}...")

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

    # Sort hyperedges by timestamp, then by market, outcome, side
    hyperedges.sort(key=lambda x: (x['day_start'], x['market'], x['outcome'], x['side']))

    print(f"\nTotal hyperedges: {len(hyperedges)}")
    print(f"Total unique traders: {len(all_traders)}")

    return hyperedges, all_traders


def write_hypergraph_files(hyperedges, all_traders, output_dir, prefix):
    """
    Write hypergraph files in congress-bills format.

    Args:
        hyperedges: list of hyperedge dicts
        all_traders: set of all trader addresses
        output_dir: output directory path
        prefix: filename prefix (e.g., 'polymarket-unified')
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

    print(f"\nWrote hypergraph to {output_dir}:")
    print(f"  - {len(traders_list)} nodes")
    print(f"  - {len(hyperedges)} hyperedges")
    print(f"  - {sum(nverts_list)} total vertex occurrences")

    # Verify integrity
    assert len(nverts_list) == len(times_list), "nverts and times must have same length"
    assert sum(nverts_list) == len(simplices_list), "sum of nverts must equal simplices length"


def build_per_market_hypergraph(market_slug, fills):
    """Build hypergraph for a single market."""
    hyperedge_data = defaultdict(set)
    all_traders = set()

    for fill in fills:
        trade_info = classify_trade(fill)
        buyer = trade_info['buyer']
        seller = trade_info['seller']
        outcome_token = trade_info['outcome_token']
        day_start = trade_info['day_start']

        # Add to buyer hyperedge
        buy_key = (outcome_token, day_start, 'BUY')
        hyperedge_data[buy_key].add(buyer)
        all_traders.add(buyer)

        # Add to seller hyperedge
        sell_key = (outcome_token, day_start, 'SELL')
        hyperedge_data[sell_key].add(seller)
        all_traders.add(seller)

    # Convert to list of hyperedges
    hyperedges = []
    for (outcome, day_start, side), traders in hyperedge_data.items():
        hyperedges.append({
            'outcome': outcome,
            'day_start': day_start,
            'side': side,
            'traders': traders,
        })

    # Sort by timestamp, outcome, side
    hyperedges.sort(key=lambda x: (x['day_start'], x['outcome'], x['side']))

    return hyperedges, all_traders


def main():
    # Configuration
    raw_dir = 'data/raw'
    unified_output_dir = 'data/hypergraphs/unified'
    by_market_output_dir = 'data/hypergraphs/by-market'

    print("="*60)
    print("Polymarket Temporal Hypergraph Generator")
    print("="*60)

    # Load all raw fills
    print("\n[1/3] Loading raw fills...")
    fills_by_market = load_raw_fills(raw_dir)

    if not fills_by_market:
        print("ERROR: No fills files found in", raw_dir)
        return

    # Build unified hypergraph
    print("\n[2/3] Building unified hypergraph...")
    unified_hyperedges, unified_traders = build_hypergraph(fills_by_market)
    write_hypergraph_files(
        unified_hyperedges,
        unified_traders,
        unified_output_dir,
        'polymarket-unified'
    )

    # Build per-market hypergraphs
    print("\n[3/3] Building per-market hypergraphs...")
    for market_slug, fills in fills_by_market.items():
        print(f"\nProcessing {market_slug}...")
        market_hyperedges, market_traders = build_per_market_hypergraph(market_slug, fills)

        market_output_dir = os.path.join(by_market_output_dir, market_slug)
        write_hypergraph_files(
            market_hyperedges,
            market_traders,
            market_output_dir,
            market_slug
        )

    print("\n" + "="*60)
    print("Hypergraph generation complete!")
    print("="*60)
    print(f"\nOutput locations:")
    print(f"  Unified: {unified_output_dir}/")
    print(f"  Per-market: {by_market_output_dir}/*/")


if __name__ == '__main__':
    main()
