# Quick Start Guide

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

## 2. Run the Model (Easy Mode)

```bash
./run_polymarket.sh
```

This interactive script will guide you through dataset selection and training.

## 3. Run the Model (Command Line)

```bash
# Recommended: Hourly windows
python node_event_hgcn_directed.py --dataset polymarket_fed_hourly --type d --epoch 10

# Or specify all options
python node_event_hgcn_directed.py \
  --dataset polymarket_fed_hourly \
  --type d \
  --epoch 10 \
  --seed 0 \
  --alpha 0.3 \
  --fileID my_experiment
```

## 4. View Results

Training outputs:
- **Logs**: `nodeevent_directed/polymarket_fed_hourly/my_experiment/`
- **Model**: `save_models/best_model_polymarket_fed_hourly_*.pt`

Training prints:
- Loss (lower is better)
- AUC (higher is better, 0.5 = random, 1.0 = perfect)
- MRR (Mean Reciprocal Rank)

## 5. Convert Your Own Data

```bash
python convert_polymarket_to_hypergraph.py \
  /path/to/your/fills.json \
  datasets/my_market_hourly \
  --mode timewindow \
  --window 3600
```

Then run:
```bash
python node_event_hgcn_directed.py --dataset my_market_hourly --type d --epoch 10
```

## Expected Training Time

- **Hourly (1,607 events)**: ~30-60 minutes on CPU
- **Daily (126 events)**: ~5-10 minutes on CPU
- **Transaction (198k events)**: 4-8 hours on CPU

GPU training is significantly faster if available.
