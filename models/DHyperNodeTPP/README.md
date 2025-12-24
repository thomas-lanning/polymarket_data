# DHyperNodeTPP - Directed Temporal Hypergraph Neural Network

Temporal point process model for predicting hyperedge formation in directed hypergraphs. Applied to Polymarket trading data to forecast trader participation patterns.

## Model

**DHyperNodeTPP** (Directed Hypergraph Node Temporal Point Process) learns to:
- Predict when traders will participate in future trades
- Forecast which groups of traders will interact
- Model temporal dynamics of buyer-seller networks

Based on the AAAI 2025 paper on temporal hypergraph neural networks.

## Polymarket Data

Three hypergraph representations of the market "Fed decreases interest rates by 50 bps after December 2025 meeting":

| Dataset | Hyperedges | Nodes | Description |
|---------|------------|-------|-------------|
| `polymarket_fed` | 198,413 | 26,270 | Transaction-based: maker → taker |
| `polymarket_fed_hourly` | 1,607 | 26,270 | Hourly windows: sellers → buyers (RECOMMENDED) |
| `polymarket_fed_daily` | 126 | 26,270 | Daily windows: sellers → buyers |

**Hypergraph Structure:**
- **Nodes**: Trader wallet addresses (mapped to integers)
- **Directed Hyperedges**: Sellers → Buyers in each time window
- **Timestamps**: Unix timestamps for each hyperedge

## Installation

```bash
pip install -r requirements.txt
```

Requires Python 3.12+, PyTorch 2.2.0, torch-scatter, torch-sparse.

## Usage

### Run Model on Polymarket Data

```bash
# Hourly data (recommended - 1,607 events)
python node_event_hgcn_directed.py \
  --dataset polymarket_fed_hourly \
  --type d \
  --epoch 10 \
  --fileID polymarket_hourly_run

# Transaction data (198k events, slower)
python node_event_hgcn_directed.py \
  --dataset polymarket_fed \
  --type d \
  --epoch 10 \
  --fileID polymarket_txn_run

# Daily data (126 events, may underfit)
python node_event_hgcn_directed.py \
  --dataset polymarket_fed_daily \
  --type d \
  --epoch 10 \
  --fileID polymarket_daily_run
```

### Key Arguments

- `--dataset`: Dataset name (polymarket_fed, polymarket_fed_hourly, polymarket_fed_daily)
- `--type d`: Directed hypergraph model
- `--epoch`: Number of training epochs (default: 10)
- `--alpha`: Connectivity model hyperparameter (default: 0.3)
- `--seed`: Random seed (default: 0)
- `--neg_e`: Number of negative samples (default: 20)

### Convert Your Own Polymarket Data

```bash
python convert_polymarket_to_hypergraph.py \
  path/to/fills.json \
  datasets/my_market \
  --mode timewindow \
  --window 3600
```

Modes:
- `transaction`: Each fill = one hyperedge (maker → taker)
- `timewindow`: Group by time, create sellers → buyers hyperedges

Then add your dataset to `node_event_hgcn_directed.py` (see line 53).

## Outputs

Training creates:
- `nodeevent_directed/{dataset}/{fileID}/`: Logs and metrics
- `save_models/`: Model checkpoints (best model based on validation AUC)

Metrics tracked:
- **AUC**: Area under ROC curve for hyperedge prediction
- **MRR**: Mean reciprocal rank for node ranking
- **Loss**: Combined time prediction + size prediction + connectivity loss

## Files

```
DHyperNodeTPP/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── convert_polymarket_to_hypergraph.py # Data conversion script
├── node_event_hgcn_directed.py        # Main training script
├── datasets/                          # Polymarket hypergraph data
│   ├── polymarket_fed/
│   ├── polymarket_fed_hourly/
│   └── polymarket_fed_daily/
├── DataLoader/                        # Data loading utilities
├── Models/                            # Neural network models
├── Modules/                           # Model components
└── Utils/                             # Helper functions
```

## Example Results (Enron Benchmark)

Training on Enron email network (14,990 hyperedges, 147 nodes):
- Epoch 1: Loss=13.90, AUC=0.48
- Epoch 9: Loss=5.97, AUC=0.73 (+52% improvement)

Similar improvements expected on Polymarket trading networks.
