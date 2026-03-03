#!/usr/bin/env python3
"""
SeatEngine API Tool - Flask web interface for SeatEngine API testing.
Serves a simple UI to query venue data and events via SeatEngine API and display pretty-printed JSON responses.
"""

import json
import asyncio
import sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify

from laughtrack.core.clients.seatengine.client import SeatEngineClient
from laughtrack.core.entities.club.model import Club

# Add the src directory to the Python path (go up two levels from web/seatengine_api_tool)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


# Configure Flask to use templates colocated with the app
app = Flask(__name__, template_folder='template')

@app.route('/')
def index():
    """Serve the main SeatEngine API tool UI page."""
    return render_template('seatengine_api_tool.html')

def create_dummy_club(venue_id: str) -> Club:
    """Create a minimal Club object for SeatEngine API requests."""
    return Club(
        id=int(venue_id),
        name=f"Venue {venue_id}",
        address="Unknown Address",
        website="https://example.com",
        scraping_url="https://example.com",
        popularity=0,
        zip_code="00000",
        phone_number="000-000-0000",
        visible=True,
        timezone="America/New_York",
        seatengine_id=venue_id  # This is the key field for SeatEngine
    )

async def fetch_venue_from_seatengine(venue_id: str):
    """Fetch venue data from SeatEngine API."""
    try:
        # Create a dummy club with the venue_id as seatengine_id
        club = create_dummy_club(venue_id)
        
        # Create SeatEngine client
        client = SeatEngineClient(club)
        
        # Fetch venue details
        venue_data = await client.fetch_venue_details(venue_id)
        
        return venue_data
    except Exception as e:
        print(f"Error fetching venue {venue_id}: {e}")
        return None

@app.route('/api/venue/<venue_id>')
def get_venue(venue_id):
    """API endpoint to get venue data by ID from SeatEngine."""
    try:
        # Run the async function in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            venue_data = loop.run_until_complete(fetch_venue_from_seatengine(venue_id))
            
            if venue_data:
                return jsonify({
                    'success': True,
                    'source': 'seatengine_api',
                    'venue_id': venue_id,
                    'data': venue_data
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'Venue ID {venue_id} not found or API error'
                }), 404
        finally:
            loop.close()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

async def fetch_events_from_seatengine(venue_id: str):
    """Fetch events data from SeatEngine API."""
    try:
        # Create a dummy club with the venue_id as seatengine_id
        club = create_dummy_club(venue_id)
        
        # Create SeatEngine client
        client = SeatEngineClient(club)
        
        # Fetch events
        events_data = await client.fetch_events(venue_id)
        
        return events_data
    except Exception as e:
        print(f"Error fetching events for venue {venue_id}: {e}")
        return None

@app.route('/api/venue/<venue_id>/events')
def get_venue_events(venue_id):
    """API endpoint to get venue events by ID from SeatEngine."""
    try:
        # Run the async function in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            events_data = loop.run_until_complete(fetch_events_from_seatengine(venue_id))
            
            if events_data is not None:
                return jsonify({
                    'success': True,
                    'source': 'seatengine_api',
                    'venue_id': venue_id,
                    'event_count': len(events_data),
                    'data': events_data
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'No events found for venue ID {venue_id}'
                }), 404
        finally:
            loop.close()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/api/stats')
def get_stats():
    """Get statistics about the SeatEngine API."""
    return jsonify({
        'api_source': 'SeatEngine Live API',
        'description': 'Making live requests to SeatEngine API',
        'note': 'Enter any venue ID to query SeatEngine directly'
    })

if __name__ == '__main__':
    print("🎭 SeatEngine API Tool")
    print("📡 Making live API requests to SeatEngine")
    print("📍 Open your browser to: http://localhost:9247")
    print("🛑 Press Ctrl+C to stop the server")
    print("-" * 50)
    app.run(debug=True, host='0.0.0.0', port=9247)
