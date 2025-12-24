#!/bin/bash
# Quick start script for running DHyperNodeTPP on Polymarket data

echo "DHyperNodeTPP - Polymarket Trading Network Prediction"
echo "====================================================="
echo ""
echo "Select dataset:"
echo "  1) Hourly windows (RECOMMENDED - 1,607 events)"
echo "  2) Transaction-based (198k events, slower)"
echo "  3) Daily windows (126 events)"
echo ""
read -p "Choice [1]: " choice
choice=${choice:-1}

case $choice in
    1)
        dataset="polymarket_fed_hourly"
        ;;
    2)
        dataset="polymarket_fed"
        ;;
    3)
        dataset="polymarket_fed_daily"
        ;;
    *)
        echo "Invalid choice, using hourly"
        dataset="polymarket_fed_hourly"
        ;;
esac

echo ""
read -p "Number of epochs [10]: " epochs
epochs=${epochs:-10}

echo ""
echo "Starting training on $dataset for $epochs epochs..."
echo ""

python node_event_hgcn_directed.py \
    --dataset $dataset \
    --type d \
    --epoch $epochs \
    --fileID polymarket_run_$(date +%Y%m%d_%H%M%S) \
    --seed 0 \
    --alpha 0.3

echo ""
echo "Training complete! Check nodeevent_directed/$dataset/ for results."
