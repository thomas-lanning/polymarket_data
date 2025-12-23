# Polymarket Temporal Hypergraphs

This directory contains temporal hypergraph representations of Polymarket trading data, generated from raw OrderFilled events.

## Overview

The hypergraphs capture trading relationships on Polymarket by modeling:
- **Nodes (vertices)**: Individual trader wallet addresses
- **Hyperedges (simplices)**: Groups of traders who bought/sold the same outcome on the same market on the same day
- **Timestamps**: Start of each day (UTC) when the trading activity occurred

## Structure

```
data/hypergraphs/
├── unified/                    # Unified hypergraph across all markets
│   ├── polymarket-unified-node-labels.txt
│   ├── polymarket-unified-nverts.txt
│   ├── polymarket-unified-simplices.txt
│   └── polymarket-unified-times.txt
│
└── by-market/                  # Individual hypergraphs per market
    ├── {market-slug}/
    │   ├── {market-slug}-node-labels.txt
    │   ├── {market-slug}-nverts.txt
    │   ├── {market-slug}-simplices.txt
    │   └── {market-slug}-times.txt
    └── ...
```

## File Format

This dataset follows the standard temporal hypergraph format (same as congress-bills):

### 1. `*-node-labels.txt`
- One trader wallet address per line
- Line number = node ID (1-indexed)
- Format: lowercase Ethereum addresses (e.g., `0x1234...`)

### 2. `*-nverts.txt`
- Number of vertices (traders) in each hyperedge
- One integer per line
- Line number corresponds to hyperedge index

### 3. `*-simplices.txt`
- Contiguous list of node IDs comprising all hyperedges
- One node ID per line
- Node IDs reference line numbers in node-labels.txt
- Total lines = sum of all values in nverts.txt

### 4. `*-times.txt`
- Unix timestamp (seconds) for each hyperedge
- Represents start of day (00:00:00 UTC) when trading occurred
- One timestamp per line
- Same number of lines as nverts.txt

## Hyperedge Definition

Each hyperedge represents a group of traders who:
1. Traded on the **same market** (e.g., "Will China invade Taiwan in 2025?")
2. Traded the **same outcome token** (YES or NO)
3. Were on the **same side** of trades (buyers or sellers)
4. Traded within the **same day** (UTC)

This creates 4 potential hyperedges per market per day:
- Market X, Outcome YES, Buyers, Day N
- Market X, Outcome YES, Sellers, Day N
- Market X, Outcome NO, Buyers, Day N
- Market X, Outcome NO, Sellers, Day N

(Only created if there was actual trading activity in that category)

### Hyperedge Ordering

Hyperedges are sorted by: `(day_start, market, outcome_token_id, side)`

This means for each day with trading activity, the 4 hyperedges appear in this exact order:
1. **YES token, BUY** - All buyers of the YES outcome on that day
2. **YES token, SELL** - All sellers of the YES outcome on that day
3. **NO token, BUY** - All buyers of the NO outcome on that day
4. **NO token, SELL** - All sellers of the NO outcome on that day

The YES token always has a lower token ID than the NO token (lexicographically sorted), and 'BUY' comes before 'SELL' alphabetically. Each of these 4 groups shares the same timestamp (start of that day, 00:00:00 UTC).

### Unified Hypergraph Structure

The unified hypergraph combines all markets but **keeps them separate** - it does NOT merge traders across different markets.

**Sorting order:** `(day_start, market_slug, outcome_token_id, side)`

On any given day, hyperedges are organized in **blocks by market** (alphabetically by market slug). Each market has up to 4 consecutive hyperedges (YES-BUY, YES-SELL, NO-BUY, NO-SELL), and all hyperedges for that day share the same timestamp.

**Example: Sept 18, 2025 with 8 markets trading (32 hyperedges total):**

```
All 32 hyperedges have timestamp: 1726617600 (Sept 18, 2025 00:00:00 UTC)

Hyperedges 0-3:   fed-decreases-interest-rates-by-25-bps
  → YES-BUY (3 traders), YES-SELL (3 traders), NO-BUY (6 traders), NO-SELL (2 traders)

Hyperedges 4-7:   fed-decreases-interest-rates-by-50-bps
  → YES-BUY (10 traders), YES-SELL (7 traders), NO-BUY (9 traders), NO-SELL (9 traders)

Hyperedges 8-11:  fed-increases-interest-rates-by-25-bps
  → YES-BUY (4 traders), YES-SELL (5 traders), NO-BUY (4 traders), NO-SELL (2 traders)

... (continues for all 8 markets)
```

**Key points:**
- Each market maintains separate hyperedges (not merged)
- A trader who trades on multiple markets appears in multiple hyperedges
- Markets are sorted alphabetically by slug
- Maximum hyperedges per day = (number of active markets) × 4
- The node-labels.txt contains all unique traders across ALL markets

## Statistics

### Unified Hypergraph
- **Nodes**: 96,114 unique traders
- **Hyperedges**: 6,110 trading groups
- **Total vertex occurrences**: 481,926
- **Markets**: 11 markets
- **Average hyperedge size**: 78.87 traders
- **Trading days**: 329 unique dates

### Per-Market Examples

**will-china-invade-taiwan-in-2025:**
- Nodes: 13,173 traders
- Hyperedges: 1,316 groups
- Vertex occurrences: 44,287

**will-jd-vance-win-the-2028-republican-presidential-nomination:**
- Nodes: 8,919 traders
- Hyperedges: 640 groups
- Vertex occurrences: 39,103

**will-gavin-newsom-win-the-2028-democratic-presidential-nomination-568:**
- Nodes: 10,650 traders
- Hyperedges: 634 groups
- Vertex occurrences: 45,331

## Data Integrity

The dataset follows these invariants:
- `len(nverts) == len(times)` - Each hyperedge has one timestamp
- `sum(nverts) == len(simplices)` - Sum of hyperedge sizes equals total node occurrences
- All node IDs in simplices are valid (1 to len(node-labels))

## Example

Consider this simplified example:

**nverts.txt:**
```
3
2
```

**simplices.txt:**
```
1
2
3
2
4
```

**times.txt:**
```
1738108800
1738195200
```

This represents:
- **Hyperedge 1** (timestamp 1738108800 = 2025-01-29): Traders {1, 2, 3} bought YES tokens
- **Hyperedge 2** (timestamp 1738195200 = 2025-01-30): Traders {2, 4} sold YES tokens

Note: Trader 2 appears in both hyperedges (bought on Jan 29, sold on Jan 30).

**Real data example from China-Taiwan market (Jan 29, 2025):**
- Hyperedge 1: 75 traders bought YES (timestamp 1738108800)
- Hyperedge 2: 116 traders sold YES (timestamp 1738108800)
- Hyperedge 3: 134 traders bought NO (timestamp 1738108800)
- Hyperedge 4: 68 traders sold NO (timestamp 1738108800)

All 4 hyperedges share the same timestamp because they occurred on the same day.

## Use Cases

This hypergraph structure enables analysis of:
1. **Co-trading patterns**: Which traders consistently trade together?
2. **Cross-market behavior**: Do the same traders participate across multiple markets?
3. **Temporal dynamics**: How do trading communities evolve over time?
4. **Directional clustering**: Do buyers and sellers form distinct groups?
5. **Market segmentation**: Which markets attract overlapping vs. distinct trader communities?

## Generation

Generated using `generate_hypergraph.py` from raw Polymarket fills data.

To regenerate:
```bash
python3 generate_hypergraph.py
```

## Related Files

- Raw fills data: `data/raw/fills_*.json`
- Generation script: `generate_hypergraph.py`
- Reference example: `congress-bills[EXAMPLE]/`
