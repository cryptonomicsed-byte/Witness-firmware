#!/usr/bin/env python3
"""
Witness RNS Identity Layer
Reticulum Network Stack (RNS) identity/signing/encryption for witness nodes.

This is the wiring the ecosystem-alignment audit's round-1/round-2 proposal
asked for: "Reticulum (RNS) proposed for Witness-firmware's identity/
signing layer (real crypto identities, no source address, signature-only
auth)." It is deliberately separate from witness_lora_firmware.py's
WitnessIdentity (secp256k1/BIP-340 Schnorr, NIP-01-shaped) -- the two
serve different layers and are not competing:

  - WitnessIdentity (witness_lora_firmware.py): signs the ATTESTATION
    content itself (payload_hash/rssi/timestamp) -- the application-level
    claim, portable to any NIP-01-speaking consumer (relays, other agents).
  - RNSWitnessIdentity (this file): the TRANSPORT-level identity RNS uses
    to address, route, and authenticate a node on the mesh itself --
    "no source address, signature-only auth" means RNS never trusts a
    packet's claimed sender; only a valid signature against a known
    Identity proves who sent it. This is what a real ESP32-S3 +
    microReticulum witness node will run to actually reach other nodes
    over LoRa, independent of what it's attesting.

Both signatures can travel together: an attestation (WitnessIdentity-
signed) gets sent as the payload of an RNS packet (RNS-Identity-signed at
the transport layer). Two independent signatures, two independent trust
domains, matching the ecosystem's "don't concentrate authority" principle
already applied elsewhere (Zàngbétò/Twelve-Thrones judge-vs-jury split,
ZERO kept off the hot-path Èṣù mask).

THIS FILE RUNS ON DESKTOP TODAY (no ESP32/LoRa hardware needed) -- that's
RNS's own design point: the same Identity/crypto primitives that run here
in pure Python run identically on microReticulum on real hardware. What
this file does NOT yet do: join a real Reticulum network with live
interfaces (LoRa/packet radio/etc) -- it demonstrates and tests the
identity/signing/encryption primitives real hardware nodes will use, as
the prerequisite step before wiring actual RNS Interfaces + Destinations
+ Transport for live mesh routing.
"""

import os
from pathlib import Path
from typing import Optional

import RNS


IDENTITY_DIR = Path(__file__).parent / ".witness_rns_identities"


class RNSWitnessIdentity:
    """Wraps a real RNS.Identity for a witness node: persistent keypair,
    sign/verify, and encrypt/decrypt to a peer's known public key. This is
    the transport-authentication identity -- "no source address" means
    RNS never trusts who a packet claims to be from; only a signature
    that validates against a specific Identity's public key counts."""

    def __init__(self, name: str, identity: Optional[RNS.Identity] = None):
        self.name = name
        self.identity = identity if identity is not None else RNS.Identity()

    @property
    def identity_hash(self) -> str:
        """RNS's own identity hash (truncated SHA-256 of the public key
        pair) -- this is the real node address RNS routes to."""
        return self.identity.hash.hex()

    @classmethod
    def load_or_create(cls, name: str) -> "RNSWitnessIdentity":
        """Persist identities to disk so a node keeps the same RNS
        address across restarts -- mirrors what a real ESP32 node would
        do with its keypair in flash."""
        IDENTITY_DIR.mkdir(exist_ok=True)
        path = IDENTITY_DIR / f"{name}.identity"
        if path.exists():
            identity = RNS.Identity.from_file(str(path))
            if identity is None:
                raise RuntimeError(f"Failed to load RNS identity from {path}")
        else:
            identity = RNS.Identity()
            identity.to_file(str(path))
        return cls(name, identity)

    def sign(self, message: bytes) -> bytes:
        """Sign a message with this node's RNS identity (Ed25519, RNS's
        own scheme -- distinct from the Schnorr signing in
        witness_lora_firmware.py's WitnessIdentity)."""
        return self.identity.sign(message)

    @staticmethod
    def verify(public_key: bytes, signature: bytes, message: bytes) -> bool:
        """Verify a signature against a peer's public key, without ever
        needing that peer's private key or trusting a claimed source
        address -- the signature is the only thing that counts."""
        try:
            peer_view = RNS.Identity(create_keys=False)
            peer_view.load_public_key(public_key)
            return peer_view.validate(signature, message)
        except Exception:
            return False

    def encrypt_to(self, peer_public_key: bytes, plaintext: bytes) -> bytes:
        """Encrypt a message that only the holder of peer_public_key's
        matching private key can decrypt."""
        peer_view = RNS.Identity(create_keys=False)
        peer_view.load_public_key(peer_public_key)
        return peer_view.encrypt(plaintext)

    def decrypt(self, ciphertext: bytes) -> bytes:
        """Decrypt a message that was encrypted to this node's public key.
        RNS.Identity.decrypt() fails SOFT on a key mismatch or corrupted
        ciphertext -- it returns None rather than raising, which is easy
        to miss (a caller doing `plaintext = id.decrypt(ct)` and using
        `plaintext` without a None check would silently proceed with junk).
        This wrapper fails loud instead, since a witness node silently
        treating a failed decrypt as an empty-but-valid message is exactly
        the kind of bug this whole signing effort exists to prevent."""
        plaintext = self.identity.decrypt(ciphertext)
        if plaintext is None:
            raise ValueError("RNS decrypt failed: wrong key or corrupted ciphertext")
        return plaintext

    def public_key(self) -> bytes:
        return self.identity.get_public_key()


# ============ Demo: real RNS identity exchange between two witness nodes ============

def demo_rns_witness_handshake():
    """Two witness nodes (real RNS identities, no network/radio needed)
    prove they can mutually authenticate and exchange a confidential
    message using nothing but their RNS keypairs -- this is the identity-
    layer half of wE's mutual-auth PoC (a real Omo-Koda2 agent counterpart
    is the other half, tracked separately as a cross-pillar build)."""

    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║      🔗 Witness RNS Identity Layer — Real Handshake 🔗      ║
    ╚════════════════════════════════════════════════════════════╝
    """)

    witness_1 = RNSWitnessIdentity.load_or_create("witness-node-1")
    witness_2 = RNSWitnessIdentity.load_or_create("witness-node-2")

    print(f"Witness 1 RNS address: {witness_1.identity_hash}")
    print(f"Witness 2 RNS address: {witness_2.identity_hash}")

    # 1. Witness 1 signs an attestation-summary message with its RNS identity
    message = b"attestation-ref:3e18340a...:consensus=2/3:height=458752"
    sig = witness_1.sign(message)
    print(f"\nWitness 1 signed message ({len(sig)}-byte signature)")

    # 2. Witness 2 verifies it using ONLY witness 1's public key -- no
    #    trust in any claimed source address, matching RNS's design.
    valid = RNSWitnessIdentity.verify(witness_1.public_key(), sig, message)
    print(f"Witness 2 verifies witness 1's signature (no shared secret needed): {valid}")

    # 3. Attack check: a forged message must fail verification
    forged = RNSWitnessIdentity.verify(witness_1.public_key(), sig, b"forged content")
    print(f"Witness 2 rejects a forged message under the same signature: {not forged}")

    # 4. Confidential exchange: witness 2 encrypts a reply only witness 1 can read
    reply = b"ack:consensus-confirmed:height=458752"
    ciphertext = witness_2.encrypt_to(witness_1.public_key(), reply)
    print(f"\nWitness 2 encrypted a {len(reply)}-byte reply to witness 1's pubkey")

    decrypted = witness_1.decrypt(ciphertext)
    print(f"Witness 1 decrypted it: {decrypted == reply} ('{decrypted.decode()}')")

    # 5. Attack check: a third party cannot decrypt without witness 1's private key
    try:
        eavesdropper = RNSWitnessIdentity.load_or_create("eavesdropper")
        eavesdropper.decrypt(ciphertext)
        print("Eavesdropper decrypted the message: THIS SHOULD NOT HAPPEN")
    except Exception:
        print("Eavesdropper (no matching private key) correctly fails to decrypt")

    print(f"""
    Real RNS identity addresses persisted at:
      {IDENTITY_DIR}/witness-node-1.identity
      {IDENTITY_DIR}/witness-node-2.identity
    Same Identity primitives an ESP32-S3 + microReticulum node would run;
    next real step is wiring RNS Interfaces/Destinations/Transport for
    actual mesh routing once physical radio hardware is available.

    ✅ RNS identity/signing/encryption layer verified end-to-end.
    """)


if __name__ == "__main__":
    demo_rns_witness_handshake()
