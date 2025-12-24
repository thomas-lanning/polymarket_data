# Polymarket Model Repository

This directory contains machine learning models for analyzing Polymarket trading data.

## DHyperNodeTPP

**Location**: `DHyperNodeTPP/`

**What it does**: Predicts future trader participation in prediction markets using temporal hypergraph neural networks. Models the dynamic network of buyers and sellers to forecast when and which traders will interact.

**Key capabilities**:
- Temporal point process modeling of trading events
- Hypergraph structure captures many-to-many trader interactions
- Learns patterns in buyer-seller networks over time

**Dataset**: Fed interest rate market (198k fills, 26k traders)
- Hourly aggregation: 1,607 hyperedges (recommended)
- Transaction-level: 198,413 hyperedges
- Daily aggregation: 126 hyperedges

**Quick start**:
```bash
cd DHyperNodeTPP
./run_polymarket.sh
```

See `DHyperNodeTPP/README.md` for full documentation.

---

## Future Models

Additional models can be added here for:
- Price prediction
- Volume forecasting  
- Market maker analysis
- etc.
