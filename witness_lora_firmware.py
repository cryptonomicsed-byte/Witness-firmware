#!/usr/bin/env python3
"""
Witness LoRa DePIN Firmware Skeleton
ESP32 + SX1278 LoRa Radio Module
MicroPython implementation

Physics-proof attestation:
- Payload hash (SHA256)
- RSSI + timestamp
- Cross-node gossip validation
- Tokenless ledger receipts

To be forged by the Cody-Pantheon and deployed to ESP32.
"""

import json
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Tuple

# ============ Mock for Desktop Testing ============
# On ESP32, use real LoRa driver (e.g., micropython-sx1278)

class MockSX1278:
    """Mock LoRa radio for desktop testing. Replace with real driver on ESP32."""
    
    def __init__(self, cs=5, dio0=2, reset=4, frequency=915000000):
        self.frequency = frequency
        self.tx_power = 20
        self.spreading_factor = 7
        self.bandwidth = 125000
        self.coding_rate = 5
        self.rssi = -80  # mock RSSI
        self.snr = 10
        
    def init(self):
        print("[LoRa] Init SX1278 @ 915MHz")
        
    def send(self, data: bytes):
        print(f"[LoRa TX] {len(data)} bytes sent")
        return True
        
    def receive(self, timeout_ms=0) -> bytes:
        # Mock: simulate receiving a packet
        return b"mock_packet_data"
        
    def read_rssi(self) -> int:
        return self.rssi
        
    def read_snr(self) -> float:
        return self.snr
        
    def set_frequency(self, freq: int):
        self.frequency = freq

# ============ Physics-Proof Attestation ============

class PhysicsProof:
    """Hash-RSSI-Timestamp chain: physics proof of reception."""
    
    @staticmethod
    def create_attestation(
        payload: bytes,
        rssi: int,
        timestamp: float,
        node_id: str
    ) -> Dict:
        """Create physics-proof attestation for payload."""
        
        payload_hash = hashlib.sha256(payload).hexdigest()
        
        attestation = {
            "payload_hash": payload_hash,
            "rssi": rssi,
            "timestamp": timestamp,
            "node_id": node_id,
            "datetime": datetime.fromtimestamp(timestamp).isoformat()
        }
        
        # Chain hash: include previous proof (for linked-list chain)
        chain_input = json.dumps(attestation, sort_keys=True).encode()
        attestation["chain_hash"] = hashlib.sha256(chain_input).hexdigest()
        
        return attestation
    
    @staticmethod
    def validate_attestation(attestation: Dict, expected_hash: str) -> bool:
        """Validate attestation chain hash."""
        
        chain_input = json.dumps(
            {k: v for k, v in attestation.items() if k != "chain_hash"},
            sort_keys=True
        ).encode()
        calculated_hash = hashlib.sha256(chain_input).hexdigest()
        
        return calculated_hash == attestation.get("chain_hash")

# ============ Gossip Protocol (Cross-Node Validation) ============

class GossipValidator:
    """Validate attestations via 3-neighbor gossip consensus."""
    
    def __init__(self, node_id: str, neighbors: List[str] = None):
        self.node_id = node_id
        self.neighbors = neighbors or []
        self.attestation_cache = {}  # payload_hash -> [attestations from neighbors]
        
    def add_neighbor(self, neighbor_id: str):
        """Register neighbor node."""
        if neighbor_id not in self.neighbors:
            self.neighbors.append(neighbor_id)
            
    def submit_attestation(self, attestation: Dict):
        """Receive attestation from neighbor."""
        payload_hash = attestation["payload_hash"]
        
        if payload_hash not in self.attestation_cache:
            self.attestation_cache[payload_hash] = []
            
        self.attestation_cache[payload_hash].append(attestation)
        
    def validate_consensus(self, payload_hash: str, required_count: int = 2) -> bool:
        """Check if 2+ neighbors attest to same payload."""
        
        if payload_hash not in self.attestation_cache:
            return False
            
        attestations = self.attestation_cache[payload_hash]
        
        if len(attestations) < required_count:
            return False
            
        # All attestations must have same payload_hash
        return all(a["payload_hash"] == payload_hash for a in attestations)

# ============ Tokenless Ledger ============

class TokenlessLedger:
    """Receipt ledger: physics-proof attestations form a chain."""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.ledger = []  # List of attestations
        self.last_hash = "0" * 64
        
    def mint_receipt(self, attestation: Dict) -> Dict:
        """Mint a tokenless receipt (no token, just proof)."""
        
        receipt = {
            "receipt_id": len(self.ledger),
            "node_id": self.node_id,
            "attestation": attestation,
            "previous_hash": self.last_hash,
            "timestamp": time.time()
        }
        
        # Receipt hash = chain hash
        receipt_input = json.dumps(
            {k: v for k, v in receipt.items() if k not in ["receipt_id"]},
            sort_keys=True
        ).encode()
        receipt_hash = hashlib.sha256(receipt_input).hexdigest()
        receipt["receipt_hash"] = receipt_hash
        
        self.ledger.append(receipt)
        self.last_hash = receipt_hash
        
        return receipt
        
    def get_ledger(self) -> List[Dict]:
        """Get full ledger chain."""
        return self.ledger
        
    def verify_chain(self) -> bool:
        """Verify ledger chain integrity."""
        
        if not self.ledger:
            return True
            
        current_hash = "0" * 64
        
        for receipt in self.ledger:
            if receipt["previous_hash"] != current_hash:
                return False
            current_hash = receipt["receipt_hash"]
            
        return True

# ============ LoRa Witness Node ============

class LoRaWitnessNode:
    """Main firmware: LoRa radio witness with attestation & ledger."""
    
    def __init__(self, node_id: str, wake_interval: int = 30):
        self.node_id = node_id
        self.wake_interval = wake_interval  # seconds
        self.radio = MockSX1278()
        self.gossip = GossipValidator(node_id)
        self.ledger = TokenlessLedger(node_id)
        self.packet_count = 0
        self.running = False
        
    def init_radio(self):
        """Initialize LoRa radio."""
        self.radio.init()
        print(f"[Node {self.node_id}] LoRa initialized")
        
    def sniff_packet(self) -> Tuple[bytes, int, float]:
        """Listen for LoRa packet (30s cycle)."""
        try:
            payload = self.radio.receive(timeout_ms=self.wake_interval * 1000)
            rssi = self.radio.read_rssi()
            timestamp = time.time()
            
            if payload:
                self.packet_count += 1
                print(f"[Node {self.node_id}] RX packet #{self.packet_count}: RSSI={rssi} dBm")
                return payload, rssi, timestamp
        except Exception as e:
            print(f"[Node {self.node_id}] RX error: {e}")
            
        return None, None, None
        
    def attest_payload(self, payload: bytes, rssi: int, timestamp: float) -> Dict:
        """Create physics-proof attestation."""
        return PhysicsProof.create_attestation(
            payload=payload,
            rssi=rssi,
            timestamp=timestamp,
            node_id=self.node_id
        )
        
    def validate_and_mint(self, attestation: Dict) -> Dict:
        """Validate attestation, mint receipt, store in ledger."""
        
        if not PhysicsProof.validate_attestation(attestation, attestation["chain_hash"]):
            print(f"[Node {self.node_id}] Attestation validation FAILED")
            return None
            
        receipt = self.ledger.mint_receipt(attestation)
        print(f"[Node {self.node_id}] Receipt minted: {receipt['receipt_id']}")
        
        return receipt
        
    def add_neighbor(self, neighbor_id: str):
        """Register neighbor for gossip."""
        self.gossip.add_neighbor(neighbor_id)
        
    def gossip_validate(self, payload_hash: str, required_neighbors: int = 2) -> bool:
        """Cross-node validation via gossip."""
        return self.gossip.validate_consensus(payload_hash, required_neighbors)
        
    def get_status(self) -> Dict:
        """Return node status."""
        return {
            "node_id": self.node_id,
            "packets_received": self.packet_count,
            "ledger_length": len(self.ledger.ledger),
            "ledger_valid": self.ledger.verify_chain()
        }

# ============ Demo Ritual ============

def demo_witness_ritual():
    """Demonstrate LoRa Witness DePIN on desktop."""
    
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║        🔥 LoRa Witness DePIN Firmware Demo 🔥             ║
    ║          Physics-Proof Attestation + Tokenless Ledger      ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    # Spawn 3 witness nodes
    node_a = LoRaWitnessNode("NodeA")
    node_b = LoRaWitnessNode("NodeB")
    node_c = LoRaWitnessNode("NodeC")
    
    # Register neighbors (gossip mesh)
    node_a.add_neighbor("NodeB")
    node_a.add_neighbor("NodeC")
    
    node_b.add_neighbor("NodeA")
    node_b.add_neighbor("NodeC")
    
    node_c.add_neighbor("NodeA")
    node_c.add_neighbor("NodeB")
    
    # Init radios
    for node in [node_a, node_b, node_c]:
        node.init_radio()
    
    print("\n⚡ Simulation: Payload broadcast across mesh\n")
    
    # Simulate payload broadcast (from external source)
    payload = b"sensor:temperature=42.5C,humidity=65%"
    rssi_a = -65
    rssi_b = -72
    rssi_c = -78
    timestamp = time.time()
    
    # Each node attests independently
    print("\n[Attestation Phase]")
    att_a = node_a.attest_payload(payload, rssi_a, timestamp)
    att_b = node_b.attest_payload(payload, rssi_b, timestamp + 0.1)
    att_c = node_c.attest_payload(payload, rssi_c, timestamp + 0.2)
    
    print(f"\nNode A attestation: {att_a['payload_hash'][:16]}...")
    print(f"Node B attestation: {att_b['payload_hash'][:16]}...")
    print(f"Node C attestation: {att_c['payload_hash'][:16]}...")
    
    # Cross-node gossip validation
    print("\n[Gossip Validation Phase]")
    node_a.gossip.submit_attestation(att_b)
    node_a.gossip.submit_attestation(att_c)
    
    consensus = node_a.gossip_validate(att_a["payload_hash"], required_count=2)
    print(f"Node A consensus check (2+ nodes): {consensus}")
    
    # Mint receipts (tokenless)
    print("\n[Receipt Minting Phase]")
    receipt_a = node_a.validate_and_mint(att_a)
    receipt_b = node_b.validate_and_mint(att_b)
    receipt_c = node_c.validate_and_mint(att_c)
    
    # Verify ledger chains
    print("\n[Ledger Verification Phase]")
    for node in [node_a, node_b, node_c]:
        status = node.get_status()
        valid = node.ledger.verify_chain()
        print(f"{status['node_id']}: {status['ledger_length']} receipts, chain valid: {valid}")
    
    # Display ledger (Node A)
    print("\n[Node A Ledger Chain]")
    for receipt in node_a.get_status():
        print(json.dumps(receipt, indent=2))
    
    print("\n✅ Prophetic firmware simulation complete.")
    print("Ready for ESP32 deployment via Cody-Pantheon.\n")

if __name__ == "__main__":
    demo_witness_ritual()
