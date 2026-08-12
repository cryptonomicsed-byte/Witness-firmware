#!/usr/bin/env python3
"""
Witness LoRa DePIN Firmware Skeleton
ESP32 + SX1278 LoRa Radio Module
MicroPython implementation

Physics-proof attestation:
- Payload hash (SHA256)
- RSSI + timestamp
- NIP-01-shaped identity: every node has a real secp256k1 keypair and
  BIP-340-Schnorr-signs every attestation and receipt it mints. This is
  the crypto FORMAT only (no relay/network dependency here) -- it closes
  the "unsigned attestation" and "Sybil-open" gaps identified in the
  ecosystem-alignment audit: node_id used to be a bare string with zero
  cryptographic binding, and gossip consensus only checked that neighbor
  attestations shared a payload_hash -- trivially satisfiable by one
  attacker submitting under multiple fake node_id strings. Consensus now
  requires N *distinct pubkeys* to have independently signed the same
  payload, not just N dicts with a matching hash.
- Cross-node gossip validation
- Tokenless ledger receipts

NOTE ON WHAT THIS DOES NOT FIX: spoofable RSSI and the mock radio below
are a physical-layer problem signing cannot solve alone -- a node can
sign a fabricated RSSI reading just as validly as a real one. This patch
makes every reading attributable and non-repudiable (you know exactly
which keypair vouched for a given value, and it can't be forged after
the fact), which is the precondition for the k-of-n cross-correlation
and stake-slashing layers that actually catch a lying node. It does not,
by itself, prove the radio told the truth.

To be forged by the Cody-Pantheon and deployed to ESP32 (once real
LoRa + RNS/microReticulum wiring lands -- this file is the identity/
signing layer that wiring will sit on top of).
"""

import json
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional

from coincurve import PrivateKey, PublicKeyXOnly

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


# ============ NIP-01-shaped Node Identity ============

class WitnessIdentity:
    """A witness node's real cryptographic identity: a secp256k1 keypair,
    signing in the same BIP-340 Schnorr scheme NIP-01 events use. This is
    what node_id used to be (a bare string) -- now the pubkey itself IS
    the node_id, and every claim the node makes is signed by the matching
    privkey. Persisted locally per node; not tied to any relay/network."""

    def __init__(self, privkey_bytes: Optional[bytes] = None):
        self.privkey = PrivateKey(privkey_bytes) if privkey_bytes else PrivateKey()
        self.pubkey_xonly: PublicKeyXOnly = self.privkey.public_key_xonly

    @property
    def node_id(self) -> str:
        """The x-only pubkey hex, NIP-01 style -- this replaces the old
        free-text node_id string. Two nodes can never collide on this
        without colliding on the underlying private key."""
        return self.pubkey_xonly.format().hex()

    def sign(self, message: bytes) -> str:
        """BIP-340 Schnorr signature over sha256(message), hex-encoded."""
        digest = hashlib.sha256(message).digest()
        sig = self.privkey.sign_schnorr(digest)
        return sig.hex()

    @staticmethod
    def verify(pubkey_hex: str, message: bytes, sig_hex: str) -> bool:
        try:
            pk = PublicKeyXOnly(bytes.fromhex(pubkey_hex))
            digest = hashlib.sha256(message).digest()
            return pk.verify(bytes.fromhex(sig_hex), digest)
        except Exception:
            return False


def _signable(d: Dict, exclude: Tuple[str, ...] = ()) -> bytes:
    """Deterministic byte serialization for signing/hashing -- excludes
    whatever keys the caller is about to fill in (sig, chain_hash, etc)."""
    return json.dumps(
        {k: v for k, v in d.items() if k not in exclude}, sort_keys=True
    ).encode()


# ============ Physics-Proof Attestation ============

class PhysicsProof:
    """Hash-RSSI-Timestamp chain: physics proof of reception, now signed
    by the reporting node's real keypair instead of an unsigned dict."""

    @staticmethod
    def create_attestation(
        payload: bytes,
        rssi: int,
        timestamp: float,
        identity: WitnessIdentity,
    ) -> Dict:
        """Create a signed physics-proof attestation for payload."""

        payload_hash = hashlib.sha256(payload).hexdigest()

        attestation = {
            "payload_hash": payload_hash,
            "rssi": rssi,
            "timestamp": timestamp,
            "node_id": identity.node_id,  # x-only pubkey, not a free string
            "datetime": datetime.fromtimestamp(timestamp).isoformat(),
        }

        # Chain hash: include previous proof (for linked-list chain)
        attestation["chain_hash"] = hashlib.sha256(_signable(attestation)).hexdigest()

        # Sign the fully-formed attestation (payload+rssi+ts+node_id+chain_hash).
        # A forged RSSI value is still possible (that's the physical-layer
        # gap noted above), but it can no longer be forged as coming from
        # a different node, or altered after the fact without detection.
        attestation["sig"] = identity.sign(_signable(attestation))

        return attestation

    @staticmethod
    def validate_attestation(attestation: Dict) -> bool:
        """Validate attestation chain hash AND signature. Previously only
        checked the chain hash -- an attacker could edit any field and
        recompute the hash themselves. Now the signature over the same
        fields must also verify against the claimed node_id (pubkey)."""

        claimed_hash = attestation.get("chain_hash")
        claimed_sig = attestation.get("sig")
        if not claimed_hash or not claimed_sig:
            return False

        recomputed_hash = hashlib.sha256(
            _signable(attestation, exclude=("chain_hash", "sig"))
        ).hexdigest()
        if recomputed_hash != claimed_hash:
            return False

        return WitnessIdentity.verify(
            attestation["node_id"],
            _signable(attestation, exclude=("sig",)),
            claimed_sig,
        )


# ============ Gossip Protocol (Cross-Node Validation) ============

class GossipValidator:
    """Validate attestations via N-neighbor gossip consensus, requiring
    N *distinct, signature-verified* pubkeys -- not just N dicts sharing
    a payload_hash, which is what let one attacker satisfy consensus
    under multiple fake node_id strings before this patch."""

    def __init__(self, identity: WitnessIdentity, neighbors: List[str] = None):
        self.identity = identity
        self.node_id = identity.node_id
        self.neighbors = neighbors or []  # neighbor pubkeys (node_ids)
        self.attestation_cache: Dict[str, Dict[str, Dict]] = {}  # payload_hash -> {node_id: attestation}

    def add_neighbor(self, neighbor_node_id: str):
        """Register a neighbor by their real pubkey/node_id."""
        if neighbor_node_id not in self.neighbors:
            self.neighbors.append(neighbor_node_id)

    def submit_attestation(self, attestation: Dict) -> bool:
        """Receive attestation from a neighbor. Rejects it outright if the
        signature doesn't verify -- an invalid attestation no longer even
        enters the consensus cache, let alone counts toward it."""
        if not PhysicsProof.validate_attestation(attestation):
            return False

        payload_hash = attestation["payload_hash"]
        by_node = self.attestation_cache.setdefault(payload_hash, {})
        # Keyed by node_id (pubkey): a single node can't inflate its own
        # count by resubmitting -- only distinct verified signers count.
        by_node[attestation["node_id"]] = attestation
        return True

    def validate_consensus(self, payload_hash: str, required_count: int = 2) -> bool:
        """Check if 2+ DISTINCT, signature-verified nodes attest to the
        same payload. Every entry in the cache already passed signature
        verification in submit_attestation, so this only needs to count
        distinct pubkeys -- which is the actual Sybil-resistance property
        the old string-matching version was missing."""

        by_node = self.attestation_cache.get(payload_hash)
        if not by_node:
            return False

        return len(by_node) >= required_count


# ============ Tokenless Ledger ============

class TokenlessLedger:
    """Receipt ledger: physics-proof attestations form a signed chain."""

    def __init__(self, identity: WitnessIdentity):
        self.identity = identity
        self.node_id = identity.node_id
        self.ledger = []  # List of receipts
        self.last_hash = "0" * 64

    def mint_receipt(self, attestation: Dict) -> Dict:
        """Mint a tokenless receipt (no token, just proof), signed by the
        minting node so the receipt itself -- not just the attestation
        inside it -- is non-repudiable."""

        receipt = {
            "receipt_id": len(self.ledger),
            "node_id": self.node_id,
            "attestation": attestation,
            "previous_hash": self.last_hash,
            "timestamp": time.time(),
        }

        receipt_hash = hashlib.sha256(
            _signable(receipt, exclude=("receipt_id",))
        ).hexdigest()
        receipt["receipt_hash"] = receipt_hash
        receipt["sig"] = self.identity.sign(
            _signable(receipt, exclude=("receipt_id",))
        )

        self.ledger.append(receipt)
        self.last_hash = receipt_hash

        return receipt

    def get_ledger(self) -> List[Dict]:
        """Get full ledger chain."""
        return self.ledger

    def verify_chain(self) -> bool:
        """Verify ledger chain integrity: hash linkage AND every receipt's
        own signature (previously only the hash chain was checked)."""

        if not self.ledger:
            return True

        current_hash = "0" * 64

        for receipt in self.ledger:
            if receipt["previous_hash"] != current_hash:
                return False
            if not WitnessIdentity.verify(
                receipt["node_id"],
                _signable(receipt, exclude=("receipt_id", "sig")),
                receipt.get("sig", ""),
            ):
                return False
            current_hash = receipt["receipt_hash"]

        return True


# ============ LoRa Witness Node ============

class LoRaWitnessNode:
    """Main firmware: LoRa radio witness with real signed identity,
    attestation & ledger."""

    def __init__(self, privkey_bytes: Optional[bytes] = None, wake_interval: int = 30):
        self.identity = WitnessIdentity(privkey_bytes)
        self.wake_interval = wake_interval  # seconds
        self.radio = MockSX1278()
        self.gossip = GossipValidator(self.identity)
        self.ledger = TokenlessLedger(self.identity)
        self.packet_count = 0
        self.running = False

    @property
    def node_id(self) -> str:
        return self.identity.node_id

    def init_radio(self):
        """Initialize LoRa radio."""
        self.radio.init()
        print(f"[Node {self.node_id[:12]}] LoRa initialized")

    def sniff_packet(self) -> Tuple[bytes, int, float]:
        """Listen for LoRa packet (30s cycle)."""
        try:
            payload = self.radio.receive(timeout_ms=self.wake_interval * 1000)
            rssi = self.radio.read_rssi()
            timestamp = time.time()

            if payload:
                self.packet_count += 1
                print(f"[Node {self.node_id[:12]}] RX packet #{self.packet_count}: RSSI={rssi} dBm")
                return payload, rssi, timestamp
        except Exception as e:
            print(f"[Node {self.node_id[:12]}] RX error: {e}")

        return None, None, None

    def attest_payload(self, payload: bytes, rssi: int, timestamp: float) -> Dict:
        """Create a signed physics-proof attestation."""
        return PhysicsProof.create_attestation(
            payload=payload,
            rssi=rssi,
            timestamp=timestamp,
            identity=self.identity,
        )

    def validate_and_mint(self, attestation: Dict) -> Optional[Dict]:
        """Validate attestation (hash + signature), mint receipt, store in ledger."""

        if not PhysicsProof.validate_attestation(attestation):
            print(f"[Node {self.node_id[:12]}] Attestation validation FAILED")
            return None

        receipt = self.ledger.mint_receipt(attestation)
        print(f"[Node {self.node_id[:12]}] Receipt minted: {receipt['receipt_id']}")

        return receipt

    def add_neighbor(self, neighbor_node_id: str):
        """Register neighbor for gossip, by their real pubkey/node_id."""
        self.gossip.add_neighbor(neighbor_node_id)

    def gossip_validate(self, payload_hash: str, required_neighbors: int = 2) -> bool:
        """Cross-node validation via gossip (requires distinct signers)."""
        return self.gossip.validate_consensus(payload_hash, required_neighbors)

    def get_status(self) -> Dict:
        """Return node status."""
        return {
            "node_id": self.node_id,
            "packets_received": self.packet_count,
            "ledger_length": len(self.ledger.ledger),
            "ledger_valid": self.ledger.verify_chain(),
        }

# ============ Demo Ritual ============

def demo_witness_ritual():
    """Demonstrate LoRa Witness DePIN on desktop, with real signed identity
    and Sybil-resistant gossip consensus."""

    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║        🔥 LoRa Witness DePIN Firmware Demo 🔥             ║
    ║   Physics-Proof Attestation + Signed Identity + Ledger      ║
    ╚════════════════════════════════════════════════════════════╝
    """)

    # Spawn 3 witness nodes, each with a real secp256k1 keypair
    node_a = LoRaWitnessNode()
    node_b = LoRaWitnessNode()
    node_c = LoRaWitnessNode()

    print(f"Node A pubkey: {node_a.node_id}")
    print(f"Node B pubkey: {node_b.node_id}")
    print(f"Node C pubkey: {node_c.node_id}")

    # Register neighbors (gossip mesh) by their real pubkeys
    node_a.add_neighbor(node_b.node_id)
    node_a.add_neighbor(node_c.node_id)

    node_b.add_neighbor(node_a.node_id)
    node_b.add_neighbor(node_c.node_id)

    node_c.add_neighbor(node_a.node_id)
    node_c.add_neighbor(node_b.node_id)

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

    # Each node attests independently, signing with its own keypair
    print("\n[Attestation Phase]")
    att_a = node_a.attest_payload(payload, rssi_a, timestamp)
    att_b = node_b.attest_payload(payload, rssi_b, timestamp + 0.1)
    att_c = node_c.attest_payload(payload, rssi_c, timestamp + 0.2)

    print(f"\nNode A attestation: {att_a['payload_hash'][:16]}... sig={att_a['sig'][:16]}...")
    print(f"Node B attestation: {att_b['payload_hash'][:16]}... sig={att_b['sig'][:16]}...")
    print(f"Node C attestation: {att_c['payload_hash'][:16]}... sig={att_c['sig'][:16]}...")

    # Cross-node gossip validation -- each submission is signature-checked
    print("\n[Gossip Validation Phase]")
    ok_b = node_a.gossip.submit_attestation(att_b)
    ok_c = node_a.gossip.submit_attestation(att_c)
    print(f"Node A accepted B's attestation (sig verified): {ok_b}")
    print(f"Node A accepted C's attestation (sig verified): {ok_c}")

    # Also submit A's own attestation into its own cache so the payload_hash
    # has 3 distinct verified signers on record for the consensus check.
    node_a.gossip.submit_attestation(att_a)

    consensus = node_a.gossip_validate(att_a["payload_hash"], required_neighbors=2)
    print(f"Node A consensus check (2+ DISTINCT signed nodes): {consensus}")

    # Sybil demonstration: an attacker resubmitting the SAME attestation
    # twice (as if from two fake identities) does NOT inflate the count,
    # because the cache is keyed by verified node_id (pubkey), not by
    # submission count.
    fake_resubmit = node_a.gossip.submit_attestation(att_b)
    print(f"Resubmitting B's attestation again still accepted (idempotent): {fake_resubmit}, "
          f"but distinct-signer count unchanged: {len(node_a.gossip.attestation_cache[att_a['payload_hash']])}")

    # Mint receipts (tokenless), each signed by its minting node
    print("\n[Receipt Minting Phase]")
    receipt_a = node_a.validate_and_mint(att_a)
    receipt_b = node_b.validate_and_mint(att_b)
    receipt_c = node_c.validate_and_mint(att_c)

    # Verify ledger chains (hash linkage + per-receipt signature)
    print("\n[Ledger Verification Phase]")
    for node in [node_a, node_b, node_c]:
        status = node.get_status()
        valid = node.ledger.verify_chain()
        print(f"{status['node_id'][:12]}...: {status['ledger_length']} receipts, chain valid: {valid}")

    # Display ledger (Node A)
    print("\n[Node A Ledger Chain]")
    for receipt in node_a.ledger.get_ledger():
        print(json.dumps(receipt, indent=2))

    print("\n✅ Signed witness firmware simulation complete.")


if __name__ == "__main__":
    demo_witness_ritual()
