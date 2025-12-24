#!/usr/bin/env python3
"""
Convert Polymarket trading data to directed temporal hypergraph format.

Creates three files:
- p_k_list_train.txt: Left/head nodes (sellers or makers)
- p_a_list_train.txt: Right/tail nodes (buyers or takers)
- times.txt: Timestamps for each hyperedge

Hypergraph interpretation options:
1. Transaction-based: maker → taker (one hyperedge per transaction)
2. Time-window-based: sellers → buyers (grouped by time window)
"""

import json
from collections import defaultdict
from datetime import datetime
import argparse

def load_polymarket_data(filepath):
    """Load Polymarket fills data."""
    with open(filepath, 'r') as f:
        return json.load(f)

def create_node_mapping(fills):
    """Map wallet addresses to integer node IDs."""
    wallets = set()
    for fill in fills:
        wallets.add(fill['maker'])
        wallets.add(fill['taker'])

    # Sort for deterministic mapping
    wallet_list = sorted(wallets)
    wallet_to_id = {wallet: idx for idx, wallet in enumerate(wallet_list)}

    print(f"Total unique traders (nodes): {len(wallet_to_id)}")
    return wallet_to_id

def transaction_based_hypergraph(fills, wallet_to_id):
    """
    Create hypergraphs where each transaction is a directed hyperedge.
    Direction: maker → taker
    """
    hyperedges = []

    for fill in fills:
        maker_id = wallet_to_id[fill['maker']]
        taker_id = wallet_to_id[fill['taker']]
        timestamp = int(fill['timestamp'])

        # Left nodes (sources): maker
        # Right nodes (targets): taker
        hyperedges.append({
            'left': [maker_id],
            'right': [taker_id],
            'time': timestamp
        })

    return hyperedges

def time_window_based_hypergraph(fills, wallet_to_id, window_seconds=3600):
    """
    Create hypergraphs grouped by time windows.
    Each hyperedge: sellers in window → buyers in window

    window_seconds: Size of time window (default 3600 = 1 hour)
    """
    # Group fills by time window
    windows = defaultdict(lambda: {'sellers': set(), 'buyers': set()})

    for fill in fills:
        maker_id = wallet_to_id[fill['maker']]
        taker_id = wallet_to_id[fill['taker']]
        timestamp = int(fill['timestamp'])

        # Determine time window
        window = (timestamp // window_seconds) * window_seconds

        # Determine who is buying vs selling
        # If makerAssetId == "0", maker has USDC (buying), taker has outcome token (selling)
        # If takerAssetId == "0", taker has USDC (buying), maker has outcome token (selling)

        if fill['makerAssetId'] == "0":
            # Maker buying, taker selling
            windows[window]['buyers'].add(maker_id)
            windows[window]['sellers'].add(taker_id)
        else:
            # Taker buying, maker selling
            windows[window]['buyers'].add(taker_id)
            windows[window]['sellers'].add(maker_id)

    # Convert to hyperedges: sellers → buyers
    hyperedges = []
    for window_time in sorted(windows.keys()):
        sellers = sorted(windows[window_time]['sellers'])
        buyers = sorted(windows[window_time]['buyers'])

        if sellers and buyers:  # Only create hyperedge if both sides exist
            hyperedges.append({
                'left': sellers,
                'right': buyers,
                'time': window_time
            })

    return hyperedges

def write_hypergraph_files(hyperedges, output_dir):
    """Write hypergraph data to files in the required format."""
    import os
    os.makedirs(output_dir, exist_ok=True)

    left_file = os.path.join(output_dir, 'p_k_list_train.txt')
    right_file = os.path.join(output_dir, 'p_a_list_train.txt')
    time_file = os.path.join(output_dir, 'times.txt')

    with open(left_file, 'w') as lf, open(right_file, 'w') as rf, open(time_file, 'w') as tf:
        for idx, edge in enumerate(hyperedges):
            # Write left nodes
            left_nodes = ','.join(map(str, edge['left']))
            lf.write(f"{idx}:{left_nodes}\n")

            # Write right nodes
            right_nodes = ','.join(map(str, edge['right']))
            rf.write(f"{idx}:{right_nodes}\n")

            # Write timestamp
            tf.write(f"{idx}\t{float(edge['time'])}\n")

    print(f"\nWrote {len(hyperedges)} hyperedges to {output_dir}/")
    print(f"  - {left_file}")
    print(f"  - {right_file}")
    print(f"  - {time_file}")

    # Print statistics
    left_sizes = [len(e['left']) for e in hyperedges]
    right_sizes = [len(e['right']) for e in hyperedges]

    print(f"\nLeft nodes (sources) per hyperedge:")
    print(f"  Min: {min(left_sizes)}, Max: {max(left_sizes)}, Avg: {sum(left_sizes)/len(left_sizes):.2f}")
    print(f"Right nodes (targets) per hyperedge:")
    print(f"  Min: {min(right_sizes)}, Max: {max(right_sizes)}, Avg: {sum(right_sizes)/len(right_sizes):.2f}")

def main():
    parser = argparse.ArgumentParser(description='Convert Polymarket data to directed hypergraph format')
    parser.add_argument('input_file', help='Path to Polymarket fills JSON file')
    parser.add_argument('output_dir', help='Directory to write hypergraph files')
    parser.add_argument('--mode', choices=['transaction', 'timewindow'], default='transaction',
                        help='Hypergraph construction mode (default: transaction)')
    parser.add_argument('--window', type=int, default=3600,
                        help='Time window size in seconds for timewindow mode (default: 3600 = 1 hour)')

    args = parser.parse_args()

    print(f"Loading Polymarket data from {args.input_file}...")
    fills = load_polymarket_data(args.input_file)
    print(f"Loaded {len(fills)} fills")

    # Create node mapping
    wallet_to_id = create_node_mapping(fills)

    # Create hypergraph based on mode
    print(f"\nCreating directed hypergraph using '{args.mode}' mode...")
    if args.mode == 'transaction':
        hyperedges = transaction_based_hypergraph(fills, wallet_to_id)
        print(f"  - Each transaction = one hyperedge (maker → taker)")
    else:
        hyperedges = time_window_based_hypergraph(fills, wallet_to_id, args.window)
        print(f"  - Time window = {args.window} seconds")
        print(f"  - Each hyperedge = sellers → buyers in window")

    # Write to files
    write_hypergraph_files(hyperedges, args.output_dir)

    print(f"\n✓ Conversion complete!")
    print(f"\nTo run the model on this data:")
    print(f"  1. Update node_event_hgcn_directed.py to add this dataset")
    print(f"  2. Run: python node_event_hgcn_directed.py --dataset <ID> --type d --epoch 10")

if __name__ == '__main__':
    main()
