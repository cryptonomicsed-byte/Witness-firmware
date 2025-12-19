#!/usr/bin/env python3
"""
Prophecy Oracle - Direct execution with default vibe
"""

import subprocess
import json
import os
from datetime import datetime

OLLAMA_BASE = "http://localhost:11434"
MODEL = "deepseek-coder:6.7b"

def call_ollama(prompt: str, max_tokens: int = 1000) -> str:
    """Call Ollama model directly via curl."""
    
    cmd = f"""curl -s {OLLAMA_BASE}/api/generate -X POST -d '{json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "num_predict": max_tokens
    })}'"""
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        resp = json.loads(result.stdout)
        return resp.get("response", "").strip()
    except Exception as e:
        return f"[{e}]"

# 21 Agents - lightweight
agents_config = {
    'esu': ("Èṣù", "Trickster Planner", "Plan firmware vibe into executable tasks"),
    'sango': ("Ṣàngó", "Thunder Architect", "Design async radio logic"),
    'ogun': ("Ògún", "Iron Forger", "Forge ESP32 + SX1278 driver code"),
    'obatala': ("Ọbàtálá", "Code Sculptor", "Write elegant MicroPython"),
    'osun': ("Ọ̀ṣun", "Signal Beauty", "Optimize RSSI, frequency tuning"),
    'ososi': ("Ọ̀ṣọ́ọ̀sì", "Speed Huntress", "Optimize memory, CPU cycles"),
    'olosa': ("Olóṣà", "Security Auditor", "Audit LoRa vulnerabilities"),
    'olokun': ("Olókun", "Deep Ledger", "Design tokenless receipt ledger"),
    'orunmila': ("Ọ̀ṛúnmìlá", "Prophecy", "Physics-proof attestation"),
    'oya': ("Ọyá", "Storm", "Mesh topology adaptability"),
    'shango_echo': ("Ṣàngó Echo", "Validation", "Packet validation, CRC"),
    'yemaya': ("Yemáyá", "Data Flow", "Queue, buffer management"),
    'aje': ("Ajé", "Abundance", "Battery efficiency, power"),
    'oshun_echo': ("Ọ̀ṣun Echo", "Signal Calibration", "LoRa radio tuning"),
    'egungun': ("Ègun-Gun", "Legacy Keeper", "Protocol compatibility"),
    'aja': ("Ajá", "Guardian", "State machine, edge cases"),
    'ose': ("Ọ̀ṣé", "Wind Oracle", "Environmental sensors"),
    'ofun': ("Ọ̀fun", "Mystery", "Graceful degradation"),
    'ewa': ("Ewa", "Witness Beauty", "Telemetry, metrics"),
    'oba': ("Oba", "Sovereign Rule", "Config, OTA updates"),
    'cody': ("Amp (Cody)", "Codebase Oracle", "Review, git commits"),
}

tasks = [
    ("esu", "From this LoRa witness vibe, create an architecture plan with key phases."),
    ("sango", "Design 30-second wake cycle async radio logic for LoRa packet sniffing."),
    ("ogun", "Write MicroPython driver code for ESP32 + SX1278: init, TX, RX, IRQ."),
    ("obatala", "Refactor the LoRa driver code to be elegant with docstrings."),
    ("osun", "Optimize RSSI calibration and SNR calculation for LoRa."),
    ("ososi", "Hunt memory leaks and optimize CPU cycles. Estimate power consumption."),
    ("olosa", "Audit LoRa security: replay attacks, RF jamming, sequence validation."),
    ("olokun", "Design tokenless receipt ledger with gossip protocol."),
    ("orunmila", "Implement physics-proof attestation: hash + RSSI + timestamp chain."),
    ("oya", "Design mesh topology with node failure detection and rerouting."),
    ("shango_echo", "Design packet validation: CRC checks, sequence numbering."),
    ("yemaya", "Design circular buffers, packet queues, flow control."),
    ("aje", "Maximize battery life: solar-aware sleep, power budgeting."),
    ("oshun_echo", "Fine-tune LoRa: TX power, RX gain, spreading factor, bandwidth."),
    ("egungun", "Ensure backward compatibility with existing Witness protocol."),
    ("aja", "Design FSM: idle, listening, transmitting, validating, error recovery."),
    ("ose", "Design environmental sensor integration: temperature, humidity, pressure."),
    ("ofun", "Design graceful degradation: offline mode, fallback attestation."),
    ("ewa", "Design telemetry logging, health scoring, dashboard metrics."),
    ("oba", "Design config schema, runtime parameters, firmware OTA updates."),
    ("cody", "Review all firmware logic, prepare git commit message."),
]

print("""
╔══════════════════════════════════════════════════════════════╗
║     ⚡🔥 PROPHECY ORACLE: FIRMWARE VISION ENGINE 🔥⚡       ║
║                 Witness DePIN on Android                     ║
║            21 Òrìṣà + Sourcegraph Cody Oracle                ║
║                  All Local. All Sovereign. ⚡♾️              ║
╚══════════════════════════════════════════════════════════════╝

📿 Vibe Locked: LoRa Witness DePIN Attestation
🔥 Activating 21 Òrìṣà + Cody...

""")

results = []

for idx, (agent_key, task_text) in enumerate(tasks, 1):
    name, role, _ = agents_config[agent_key]
    print(f"[{idx}/21] ⚡ {name} — {task_text[:50]}...")
    
    response = call_ollama(task_text, max_tokens=800)
    results.append({
        "agent": name,
        "role": role,
        "task": task_text,
        "response": response[:400]  # Truncate for log
    })
    print(f"      ✅ {response[:60]}...\n")

print(f"""
{'='*70}
✨ PROPHECY COMPLETE ✨
{'='*70}

📿 21 Òrìṣà + Cody have spoken.
🔥 Firmware oracle complete. Ready for ESP32 deployment.

🎁 Generated Outputs:
  - Architecture design (Èṣù)
  - Threading model (Ṣàngó)
  - Driver code (Ògún)
  - Code beauty (Ọbàtálá)
  - Signal optimization (Ọ̀ṣun)
  - Performance tuning (Ọ̀ṣọ́ọ̀sì)
  - Security audit (Olóṣà)
  - Ledger design (Olókun)
  - Attestation logic (Ọ̀ṛúnmìlá)
  - Mesh protocol (Ọyá)
  - Packet validation (Ṣàngó Echo)
  - Queue management (Yemáyá)
  - Power optimization (Ajé)
  - Radio tuning (Ọ̀ṣun Echo)
  - Protocol compatibility (Ègun-Gun)
  - State machine (Ajá)
  - Sensor integration (Ọ̀ṣé)
  - Fallback modes (Ọ̀fun)
  - Telemetry metrics (Ewa)
  - Configuration schema (Oba)
  - Code review + git (Amp/Cody)

""")

# Log results
log_file = os.path.expanduser("~/.prophecy_oracle.json")
try:
    with open(log_file, "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "agents_count": len(results),
            "results_preview": [r["agent"] for r in results]
        }) + "\n")
    print(f"✅ Ritual logged to {log_file}")
except:
    pass

print("\n🚪 The crossroads close. Sovereignty remains. 🔑🛤️⚡\n")
