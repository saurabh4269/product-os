#!/usr/bin/env python3
"""Generate narration audio segments using Microsoft Edge TTS (natural neural voices)."""

import asyncio
import os
import subprocess
from pathlib import Path
import edge_tts

OUT_DIR = Path("/workspace/apps/demo/out/narration")
OUT_DIR.mkdir(parents=True, exist_ok=True)

VOICE = "en-US-BrianMultilingualNeural"  # Approachable, Casual, Sincere

# Timed sections for the walkthrough
SEGMENTS = [
    (
        "01_intro",
        "Hey everyone, welcome to Product OS. Today I want to walk you through how our autonomous product team actually works in practice, from live customer signals all the way to verified fixes and shipped code."
    ),
    (
        "02_campus",
        "Here on our campus overview, our autonomous agents are continuously watching telemetry. We can see live receipts streaming in from BigQuery, Google Analytics 4, error logs, and recent deployments. You see the active handoffs between the Incident Commander, Analytics, and the Investigator."
    ),
    (
        "03_connect",
        "Over in Connect, this is where we plug in our tenant product. Here you can see Cove, our demo ecommerce tenant, wired with its Cloud Run service and GitHub repository. We also have Google Workspace OAuth connected for Gmail drafts and Calendar incident holds, plus our telemetry datasets."
    ),
    (
        "04_cove_storefront",
        "Let's switch over to the actual Cove storefront. This is the real customer-facing app our agents are monitoring. When customers experience payment hangs or drop-offs during checkout, those signals instantly flow into Product OS."
    ),
    (
        "05_room_entry",
        "Back in Product OS, let's open up this active incident room for the OTP verification hang. Notice the Type A bug classification with a high risk tier because it directly impacts customer checkout and authentication."
    ),
    (
        "06_specialist_handoffs",
        "Inside the room, the Incident Commander immediately fanned out to specialist agents in parallel. Analytics queried BigQuery and confirmed an eighteen percent drop in conversion. The Logs agent identified errors clustered around payment timeouts right after a recent SDK release."
    ),
    (
        "07_customer_voice",
        "Next, our Customer Voice agent gathered structured diagnostic evidence directly from affected customer sessions. Notice this isn't just a survey transcript; it's structured telemetry capturing ninety-four percent purchase intent, the exact friction point, and whether the customer is willing to retry."
    ),
    (
        "08_proof_cards",
        "Here are the live glass-box proof cards. BigQuery queries with real SQL, deployment timestamps, and coordination messages. The agent drafted a customer follow-up in Gmail and placed a Calendar hold for the engineering team."
    ),
    (
        "09_github_pr",
        "Because this involves authentication and payment flags, the Risk agent marked this as High, requiring human sign-off. Product OS prepared Pull Request seventeen on the Cove repository, modifying flags dot json to rollback the faulty payment SDK."
    ),
    (
        "10_github_tab",
        "Here is the actual pull request live on GitHub in the Cove repo. You can see the exact diff: flipping the pay SDK flag back so shoppers aren't left hanging. Product OS never merges PRs automatically; human engineers remain in complete control."
    ),
    (
        "11_approvals",
        "In the Approvals console, we see our strict governance gates: policy enforcement, exfiltration guards, and Model Armor scans. Every proposed change requires explicit authorization."
    ),
    (
        "12_outcomes_campus",
        "Once verified, the Learning agent captures the outcome into organizational memory so similar regressions never repeat. That's the full Product OS loop: observe, diagnose, coordinate across tools, gate with human approval, and ship with confidence. Thanks for watching."
    )
]

async def generate():
    concat_list = []
    for name, text in SEGMENTS:
        mp3_path = OUT_DIR / f"{name}.mp3"
        print(f"Generating {name}...")
        communicate = edge_tts.Communicate(text, VOICE, rate="+3%", pitch="+0Hz")
        await communicate.save(str(mp3_path))
        concat_list.append(mp3_path)
    
    # Also combine into one master audio track with natural pauses
    print("Combining segments into master voiceover...")
    filter_complex = ""
    inputs = []
    for i, path in enumerate(concat_list):
        inputs.extend(["-i", str(path)])
    
    # We will build a timed master audio or let ffmpeg concat with 1.5s silent gaps
    # Create silent mp3
    silence_file = OUT_DIR / "silence.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
        "-t", "1.5", "-q:a", "9", "-acodec", "libmp3lame", str(silence_file)
    ], check=True, capture_output=True)

    concat_manifest = OUT_DIR / "concat.txt"
    with open(concat_manifest, "w") as f:
        for p in concat_list:
            f.write(f"file '{p.name}'\n")
            f.write(f"file 'silence.mp3'\n")
    
    master_path = OUT_DIR / "voiceover_master.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_manifest),
        "-c", "copy", str(master_path)
    ], check=True)
    
    # Check duration
    res = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(master_path)
    ], capture_output=True, text=True, check=True)
    
    print(f"Master voiceover ready: {master_path} ({float(res.stdout.strip()):.1f}s)")

if __name__ == "__main__":
    asyncio.run(generate())
