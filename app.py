#!/usr/bin/env python3
"""
Flask web application for fetching and transforming Polymarket data.
"""

from flask import Flask, render_template, request, jsonify
import os
from polymarket_processor import PolymarketProcessor

app = Flask(__name__)

# Configuration
RAW_DATA_DIR = 'data/raw'


@app.route('/')
def index():
    """Serve the main HTML interface."""
    return render_template('index.html')


@app.route('/api/process', methods=['POST'])
def process_market():
    """
    Process a single market: fetch raw fills and generate hypergraphs.

    Expected JSON body:
    {
        "market_url": "https://polymarket.com/event/..."
    }
    """
    try:
        data = request.json
        market_url = data.get('market_url', '').strip()

        if not market_url:
            return jsonify({'success': False, 'error': 'Market URL is required'}), 400

        processor = PolymarketProcessor(RAW_DATA_DIR)
        result = processor.process_market(market_url)

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/process-batch', methods=['POST'])
def process_batch():
    """
    Process multiple markets in batch.

    Expected JSON body:
    {
        "markets": [
            {"url": "..."},
            {"url": "..."}
        ]
    }
    """
    try:
        data = request.json
        markets = data.get('markets', [])

        if not markets:
            return jsonify({'success': False, 'error': 'No markets provided'}), 400

        processor = PolymarketProcessor(RAW_DATA_DIR)
        results = []

        for market_data in markets:
            market_url = market_data.get('url', '').strip()

            if not market_url:
                results.append({
                    'url': market_url,
                    'success': False,
                    'error': 'Empty URL'
                })
                continue

            try:
                result = processor.process_market(market_url)
                results.append({
                    'url': market_url,
                    'success': True,
                    'data': result
                })
            except Exception as e:
                results.append({
                    'url': market_url,
                    'success': False,
                    'error': str(e)
                })

        return jsonify({
            'success': True,
            'results': results
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/fetch-event', methods=['POST'])
def fetch_event():
    """
    Fetch event metadata and return list of markets with volume info.

    Expected JSON body:
    {
        "event_url": "https://polymarket.com/events/republican-presidential-nominee-2028"
    }

    Response:
    {
        "success": true,
        "event": {
            "slug": "republican-presidential-nominee-2028",
            "title": "Republican Presidential Nominee 2028",
            "description": "...",
            "total_markets": 128
        },
        "markets": [
            {
                "slug": "will-donald-trump-win-...",
                "question": "Will Donald Trump win...",
                "groupItemTitle": "Donald Trump",
                "volume": "1322638.121053",
                "liquidity": "168927.04814",
                "lastTradePrice": "0.044"
            },
            ...
        ]
    }
    """
    try:
        data = request.json
        event_url = data.get('event_url', '').strip()

        if not event_url:
            return jsonify({'success': False, 'error': 'Event URL is required'}), 400

        processor = PolymarketProcessor(RAW_DATA_DIR)

        # Parse event slug
        event_slug = processor.parse_event_slug(event_url)

        # Fetch event data
        event_data = processor.fetch_event_metadata(event_slug)

        # Extract markets with volume info
        markets = processor.get_event_markets(event_data)

        # Build response
        event_info = {
            'slug': event_slug,
            'title': event_data.get('title', ''),
            'description': event_data.get('description', ''),
            'total_markets': len(markets)
        }

        return jsonify({
            'success': True,
            'event': event_info,
            'markets': markets
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/process-event', methods=['POST'])
def process_event():
    """
    Process selected markets from an event.

    Expected JSON body:
    {
        "event_slug": "republican-presidential-nominee-2028",
        "market_slugs": ["market-slug-1", "market-slug-2", ...]
    }

    Response:
    {
        "success": true,
        "results": [
            {
                "slug": "market-slug-1",
                "success": true,
                "data": {...}
            },
            {
                "slug": "market-slug-2",
                "success": false,
                "error": "No fills found"
            }
        ]
    }
    """
    try:
        data = request.json
        event_slug = data.get('event_slug', '').strip()
        market_slugs = data.get('market_slugs', [])

        if not event_slug:
            return jsonify({'success': False, 'error': 'Event slug is required'}), 400

        if not market_slugs:
            return jsonify({'success': False, 'error': 'No market slugs provided'}), 400

        processor = PolymarketProcessor(RAW_DATA_DIR)
        results = []

        # Process each market
        for market_slug in market_slugs:
            try:
                result = processor.process_market(market_slug)
                results.append({
                    'slug': market_slug,
                    'success': True,
                    'data': result
                })
            except Exception as e:
                results.append({
                    'slug': market_slug,
                    'success': False,
                    'error': str(e)
                })

        return jsonify({
            'success': True,
            'results': results
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    # Ensure raw data directory exists
    os.makedirs(RAW_DATA_DIR, exist_ok=True)

    print("="*60)
    print("Polymarket Data Fetcher - Web Interface")
    print("="*60)
    print(f"Raw data directory: {RAW_DATA_DIR}")
    print("\nStarting server at http://localhost:8080")
    print("="*60)

    app.run(debug=True, host='0.0.0.0', port=8080)
