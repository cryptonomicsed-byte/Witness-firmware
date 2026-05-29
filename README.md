# Witness DePIN Firmware 📿⚡

A sovereign, local-first LoRa Witness Decentralized Physical Infrastructure Network (DePIN) implementation. Designed for ESP32 + SX1278 hardware, featuring a unique "Prophetic Pantheon" agent orchestration system for firmware development and auditing.

## 🌟 Core Features

- **Physics-Proof Attestation**: A robust mechanism using Payload Hash + RSSI + Timestamps to create verifiable evidence of signal reception.
- **Prophetic Pantheon Orchestration**: 21 Òrìṣà agents + Cody (Sourcegraph) collaborate to design, forge, and audit firmware logic entirely on local hardware (e.g., Termux/Android) using Ollama.
- **Mesh Gossip Protocol**: Cross-node validation and decentralized ledger synchronization without reliance on centralized tokens.
- **Real-time Dashboard**: Flask-based monitoring for node status, attestation chains, and mesh health metrics.
- **Sovereign & Local-First**: Built to run entirely on the edge, avoiding "cloud exile" and ensuring maximum privacy and autonomy.

## 📂 Project Structure

- `witness_lora_firmware.py`: The core MicroPython firmware implementation for ESP32 + SX1278.
- `witness_dashboard.py`: Real-time mesh monitoring and ledger visualization dashboard.
- `prophecy_oracle.py` & `run_prophecy.py`: Lightweight agent orchestration engines for firmware tasks.
- `cody_prophetic_pantheon.py`: Comprehensive CrewAI-based orchestration for the full 21 Òrìṣà pantheon.
- `PROPHECY_SUMMARY.md`: Generated output detailing the collective wisdom and code for the DePIN ecosystem.

## 🚀 Getting Started

### Prerequisites

- **Hardware**: ESP32 with SX1278 LoRa module (or compatible).
- **Firmware**: MicroPython installed on ESP32.
- **Local LLM**: [Ollama](https://ollama.com/) running with `deepseek-coder:6.7b` for the Prophetic Oracle.

### Running the Dashboard

```bash
python3 witness_dashboard.py
```
Visit `http://localhost:8888` to view the mesh status.

### Igniting the Prophecy

To generate or audit firmware logic using the pantheon:

```bash
python3 run_prophecy.py
```

## 🛡️ Security & Integrity

The system employs a hash-linked chain for attestations, ensuring that every piece of data is tied to the physical reality of the RF environment (RSSI/SNR) and verified by neighboring nodes through a gossip-based consensus mechanism.

---
*Built with ⚡ and ♾️ by the Witness Collective.*
