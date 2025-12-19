#!/usr/bin/env python3
"""
Witness DePIN Dashboard
Real-time mesh monitoring: node status, ledger chain, attestations, metrics
Runs on localhost:8888
"""

from flask import Flask, render_template_string, request, jsonify
import json
import os
import time
from datetime import datetime
from pathlib import Path
import threading

app = Flask(__name__)

# Mock node data (in production, read from ESP32 via MQTT/HTTP)
NODES_DATA_FILE = Path(os.path.expanduser("~/.witness_nodes.json"))
LEDGER_FILE = Path(os.path.expanduser("~/.witness_ledger.json"))

def init_mock_data():
    """Initialize mock node data for demo."""
    
    nodes = {
        "NodeA": {
            "node_id": "NodeA",
            "status": "online",
            "uptime_hours": 72,
            "packets_received": 1024,
            "packets_validated": 1000,
            "battery_voltage": 4.1,
            "rssi_avg": -68,
            "consensus_rate": 0.98,
            "last_heartbeat": time.time(),
            "ledger_height": 156,
            "neighbors": ["NodeB", "NodeC"]
        },
        "NodeB": {
            "node_id": "NodeB",
            "status": "online",
            "uptime_hours": 65,
            "packets_received": 989,
            "packets_validated": 975,
            "battery_voltage": 3.9,
            "rssi_avg": -72,
            "consensus_rate": 0.96,
            "last_heartbeat": time.time() - 5,
            "ledger_height": 155,
            "neighbors": ["NodeA", "NodeC"]
        },
        "NodeC": {
            "node_id": "NodeC",
            "status": "online",
            "uptime_hours": 48,
            "packets_received": 856,
            "packets_validated": 832,
            "battery_voltage": 4.2,
            "rssi_avg": -78,
            "consensus_rate": 0.97,
            "last_heartbeat": time.time() - 2,
            "ledger_height": 156,
            "neighbors": ["NodeA", "NodeB"]
        }
    }
    
    NODES_DATA_FILE.write_text(json.dumps(nodes, indent=2))
    
    # Mock ledger (chain of receipts)
    ledger = [
        {
            "receipt_id": 156,
            "payload_hash": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
            "attestations": [
                {"node": "A", "rssi": -65, "timestamp": time.time() - 10},
                {"node": "B", "rssi": -72, "timestamp": time.time() - 9},
                {"node": "C", "rssi": -78, "timestamp": time.time() - 8}
            ],
            "consensus": True,
            "chain_hash": "x1y2z3a4b5c6d7e8f9g0h1i2j3k4l5m6",
            "previous_hash": "z9y8x7w6v5u4t3s2r1q0p9o8n7m6l5k4",
            "timestamp": time.time() - 10
        },
        {
            "receipt_id": 155,
            "payload_hash": "b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7",
            "attestations": [
                {"node": "A", "rssi": -67, "timestamp": time.time() - 40},
                {"node": "B", "rssi": -70, "timestamp": time.time() - 39},
            ],
            "consensus": True,
            "chain_hash": "z9y8x7w6v5u4t3s2r1q0p9o8n7m6l5k4",
            "previous_hash": "y8x7w6v5u4t3s2r1q0p9o8n7m6l5k4j3",
            "timestamp": time.time() - 40
        }
    ]
    
    LEDGER_FILE.write_text(json.dumps(ledger, indent=2))

# Initialize on startup
if not NODES_DATA_FILE.exists():
    init_mock_data()

HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Witness DePIN Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Courier New', monospace;
            background: #0a0e27;
            color: #e0e0e0;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #ff6b35;
            padding-bottom: 20px;
        }
        
        h1 {
            color: #ff6b35;
            font-size: 2em;
            margin-bottom: 5px;
        }
        
        .subtitle {
            color: #888;
            font-size: 0.9em;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: #1a1f3a;
            border: 1px solid #444;
            border-radius: 8px;
            padding: 20px;
        }
        
        .card h2 {
            color: #ffa500;
            margin-bottom: 15px;
            font-size: 1.1em;
            border-bottom: 1px solid #333;
            padding-bottom: 10px;
        }
        
        .metric {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #222;
            font-size: 0.9em;
        }
        
        .metric:last-child {
            border-bottom: none;
        }
        
        .label {
            color: #aaa;
        }
        
        .value {
            color: #fff;
            font-weight: bold;
        }
        
        .status-online {
            color: #4ade80;
        }
        
        .status-offline {
            color: #f87171;
        }
        
        .status-warning {
            color: #facc15;
        }
        
        .ledger-section {
            margin-top: 30px;
        }
        
        .ledger-entry {
            background: #1a1f3a;
            border: 1px solid #333;
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 10px;
            font-size: 0.85em;
        }
        
        .receipt-id {
            color: #ff6b35;
            font-weight: bold;
        }
        
        .hash {
            color: #4ade80;
            font-family: monospace;
            word-break: break-all;
            font-size: 0.8em;
        }
        
        .attestation {
            background: #0a0e27;
            border-left: 2px solid #ffa500;
            padding: 10px;
            margin: 8px 0;
            font-size: 0.85em;
        }
        
        .consensus-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 0.8em;
            font-weight: bold;
            margin: 5px 0;
        }
        
        .consensus-yes {
            background: #4ade80;
            color: #000;
        }
        
        .consensus-no {
            background: #f87171;
            color: #fff;
        }
        
        .mesh-viz {
            background: #0a0e27;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 20px;
            text-align: center;
            margin: 20px 0;
        }
        
        .mesh-node {
            display: inline-block;
            width: 80px;
            height: 80px;
            border-radius: 50%;
            border: 2px solid #ffa500;
            background: #1a1f3a;
            margin: 20px;
            padding: 10px;
            text-align: center;
            font-size: 0.9em;
            vertical-align: top;
        }
        
        .mesh-node.online {
            border-color: #4ade80;
            background: rgba(74, 222, 128, 0.1);
        }
        
        .mesh-node.offline {
            border-color: #f87171;
            background: rgba(248, 113, 113, 0.1);
        }
        
        .mesh-node-name {
            color: #fff;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .mesh-node-status {
            font-size: 0.75em;
            color: #aaa;
        }
        
        .refresh-btn {
            background: #ff6b35;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9em;
            float: right;
        }
        
        .refresh-btn:hover {
            background: #ff5520;
        }
        
        .timestamp {
            color: #666;
            font-size: 0.85em;
            margin-top: 10px;
        }
        
        .health-bar {
            background: #0a0e27;
            border: 1px solid #333;
            height: 10px;
            border-radius: 3px;
            overflow: hidden;
            margin: 5px 0;
        }
        
        .health-fill {
            height: 100%;
            background: linear-gradient(90deg, #4ade80, #ffa500, #f87171);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚡🔥 Witness DePIN Dashboard 🔥⚡</h1>
            <div class="subtitle">Physics-Proof Attestation • Tokenless Ledger • Sovereign Mesh</div>
            <button class="refresh-btn" onclick="refreshAll()">🔄 Refresh</button>
        </div>
        
        <div class="mesh-viz">
            <h2 style="color: #ffa500; margin-bottom: 20px;">🌐 Node Mesh Topology</h2>
            <div id="meshContainer"></div>
            <p style="color: #666; font-size: 0.85em; margin-top: 10px;">Connected nodes gossip & validate attestations</p>
        </div>
        
        <div class="grid" id="nodesContainer"></div>
        
        <div class="ledger-section">
            <h2 style="color: #ffa500; margin-bottom: 15px;">📜 Ledger Chain (Most Recent)</h2>
            <div id="ledgerContainer"></div>
        </div>
        
        <div style="text-align: center; margin-top: 30px; color: #666; font-size: 0.85em;">
            <p id="lastUpdate"></p>
            <p>All computation local. All data sovereign. ⚡♾️</p>
        </div>
    </div>
    
    <script>
        async function refreshAll() {
            await Promise.all([
                fetchNodes(),
                fetchLedger()
            ]);
        }
        
        async function fetchNodes() {
            try {
                const res = await fetch('/api/nodes');
                const nodes = await res.json();
                
                // Render mesh topology
                let meshHTML = '';
                for (const [id, node] of Object.entries(nodes)) {
                    const status = node.status === 'online' ? 'online' : 'offline';
                    const battery = (node.battery_voltage / 4.5 * 100).toFixed(0);
                    meshHTML += `
                        <div class="mesh-node ${status}">
                            <div class="mesh-node-name">${node.node_id}</div>
                            <div class="mesh-node-status">
                                🔋 ${battery}%<br>
                                📶 ${node.rssi_avg}dBm
                            </div>
                        </div>
                    `;
                }
                document.getElementById('meshContainer').innerHTML = meshHTML;
                
                // Render node cards
                let cardsHTML = '';
                for (const [id, node] of Object.entries(nodes)) {
                    const healthPercent = Math.round(node.consensus_rate * 100);
                    cardsHTML += `
                        <div class="card">
                            <h2>${node.node_id}</h2>
                            <div class="metric">
                                <span class="label">Status</span>
                                <span class="value status-${node.status === 'online' ? 'online' : 'offline'}">${node.status.toUpperCase()}</span>
                            </div>
                            <div class="metric">
                                <span class="label">Uptime</span>
                                <span class="value">${node.uptime_hours}h</span>
                            </div>
                            <div class="metric">
                                <span class="label">Packets RX</span>
                                <span class="value">${node.packets_received}</span>
                            </div>
                            <div class="metric">
                                <span class="label">Validated</span>
                                <span class="value">${node.packets_validated}</span>
                            </div>
                            <div class="metric">
                                <span class="label">Battery</span>
                                <span class="value">${node.battery_voltage.toFixed(1)}V</span>
                            </div>
                            <div style="margin: 10px 0;">
                                <span class="label">Health</span>
                                <div class="health-bar">
                                    <div class="health-fill" style="width: ${healthPercent}%"></div>
                                </div>
                                <span class="value">${healthPercent}%</span>
                            </div>
                            <div class="metric">
                                <span class="label">RSSI Avg</span>
                                <span class="value">${node.rssi_avg} dBm</span>
                            </div>
                            <div class="metric">
                                <span class="label">Consensus Rate</span>
                                <span class="value">${(node.consensus_rate * 100).toFixed(1)}%</span>
                            </div>
                            <div class="metric">
                                <span class="label">Ledger Height</span>
                                <span class="value">${node.ledger_height}</span>
                            </div>
                            <div class="metric">
                                <span class="label">Neighbors</span>
                                <span class="value">${node.neighbors.join(', ')}</span>
                            </div>
                        </div>
                    `;
                }
                document.getElementById('nodesContainer').innerHTML = cardsHTML;
            } catch (err) {
                console.error('Error fetching nodes:', err);
            }
        }
        
        async function fetchLedger() {
            try {
                const res = await fetch('/api/ledger');
                const ledger = await res.json();
                
                let ledgerHTML = '';
                for (const receipt of ledger.slice(0, 5)) {
                    const timestamp = new Date(receipt.timestamp * 1000).toLocaleString();
                    let attestationsHTML = '';
                    for (const att of receipt.attestations) {
                        attestationsHTML += `
                            <div class="attestation">
                                <strong>${att.node}</strong>: RSSI ${att.rssi} dBm
                            </div>
                        `;
                    }
                    
                    ledgerHTML += `
                        <div class="ledger-entry">
                            <div class="receipt-id">Receipt #${receipt.receipt_id}</div>
                            <div style="margin: 10px 0;">
                                <div class="label">Payload Hash</div>
                                <div class="hash">${receipt.payload_hash}</div>
                            </div>
                            <div style="margin: 10px 0;">
                                <div class="label">Attestations</div>
                                ${attestationsHTML}
                            </div>
                            <div style="margin: 10px 0;">
                                <span class="consensus-badge ${receipt.consensus ? 'consensus-yes' : 'consensus-no'}">
                                    ${receipt.consensus ? '✅ Consensus' : '❌ No Consensus'}
                                </span>
                            </div>
                            <div style="margin: 10px 0;">
                                <div class="label">Chain Hash</div>
                                <div class="hash">${receipt.chain_hash.substring(0, 32)}...</div>
                            </div>
                            <div class="timestamp">${timestamp}</div>
                        </div>
                    `;
                }
                document.getElementById('ledgerContainer').innerHTML = ledgerHTML;
            } catch (err) {
                console.error('Error fetching ledger:', err);
            }
        }
        
        function updateTimestamp() {
            document.getElementById('lastUpdate').textContent = 
                `Last updated: ${new Date().toLocaleTimeString()}`;
        }
        
        // Initial load
        refreshAll();
        updateTimestamp();
        
        // Refresh every 10 seconds
        setInterval(() => {
            refreshAll();
            updateTimestamp();
        }, 10000);
    </script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML)

@app.route("/api/nodes", methods=["GET"])
def get_nodes():
    """Get all node status."""
    try:
        with open(NODES_DATA_FILE) as f:
            return jsonify(json.load(f))
    except:
        return jsonify({}), 500

@app.route("/api/ledger", methods=["GET"])
def get_ledger():
    """Get ledger chain."""
    try:
        with open(LEDGER_FILE) as f:
            return jsonify(json.load(f))
    except:
        return jsonify([]), 500

@app.route("/api/update_node", methods=["POST"])
def update_node():
    """Update node data (for real ESP32 integration)."""
    data = request.json
    
    try:
        with open(NODES_DATA_FILE) as f:
            nodes = json.load(f)
        
        if data.get("node_id") in nodes:
            nodes[data["node_id"]].update(data)
            with open(NODES_DATA_FILE, "w") as f:
                json.dump(nodes, f, indent=2)
            return jsonify({"status": "ok"})
    except:
        pass
    
    return jsonify({"status": "error"}), 500

if __name__ == "__main__":
    print("""
    ⚡ Witness DePIN Dashboard
    🔥 Open http://localhost:8888
    📊 Real-time mesh monitoring
    """)
    app.run(host="0.0.0.0", port=8888, debug=True)
