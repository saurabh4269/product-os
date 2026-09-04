import asyncio
import os
import subprocess
from pathlib import Path
from playwright.async_api import async_playwright

ADMIN_TOKEN = ""
token_path = Path("/tmp/.loop_admin")
if token_path.exists():
    ADMIN_TOKEN = token_path.read_text().strip()

async def smooth_scroll_window(page, target_y, duration=3.0, steps=30):
    """Smooth window scrolling with continuous subtle mouse movements."""
    current_y = await page.evaluate("window.scrollY")
    distance = target_y - current_y
    for i in range(steps):
        t = (i + 1) / steps
        ease = t * (2 - t)
        y = current_y + distance * ease
        await page.evaluate(f"window.scrollTo({{ top: {y}, behavior: 'instant' }})")
        await page.mouse.move(960 + (i % 6) * 5, 540 + (i % 4) * 4)
        await asyncio.sleep(duration / steps)

async def smooth_scroll_chat(page, target_y, duration=3.5, steps=35):
    """Smooth scroll within the incident room .chat-scroll container."""
    current_y = await page.evaluate("""() => {
        const el = document.querySelector('.chat-scroll');
        return el ? el.scrollTop : window.scrollY;
    }""")
    distance = target_y - current_y
    for i in range(steps):
        t = (i + 1) / steps
        ease = t * (2 - t)
        y = current_y + distance * ease
        await page.evaluate(f"""() => {{
            const el = document.querySelector('.chat-scroll');
            if (el) {{
                el.scrollTop = {y};
            }} else {{
                window.scrollTo(0, {y});
            }}
        }}""")
        await page.mouse.move(700 + (i % 5) * 6, 400 + (i % 4) * 5)
        await asyncio.sleep(duration / steps)

async def active_pause(page, seconds, center_x=960, center_y=540):
    """Keep screen alive with natural human cursor drift while narrator speaks."""
    steps = int(seconds * 5)
    for i in range(steps):
        dx = (i % 7 - 3) * 6
        dy = (i % 5 - 2) * 5
        await page.mouse.move(center_x + dx, center_y + dy)
        await asyncio.sleep(0.2)

async def run_walkthrough():
    print("Launching Chromium single-page walkthrough on DISPLAY=:1...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--no-sandbox",
                "--start-maximized",
                "--disable-infobars",
                "--disable-dev-shm-usage",
                "--window-size=1920,1080",
                "--window-position=0,0",
            ],
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
        )

        page = await context.new_page()
        # Seed admin token & sidebar state
        await page.add_init_script(f"""
            sessionStorage.setItem('loop_admin_token', '{ADMIN_TOKEN}');
            localStorage.setItem('loop_admin_token', '{ADMIN_TOKEN}');
            localStorage.setItem('loop_admin_token_remember', '1');
            localStorage.setItem('loop-sidebar', '1');
            sessionStorage.setItem('loop-welcome-dismissed', '1');
            sessionStorage.setItem('loop-brief-dismissed', '1');
        """)

        # ========================================================
        # SEGMENT 01 (0s - 12s): INTRO ON CAMPUS
        # ========================================================
        print("[01] Intro on Campus...")
        await page.goto("http://127.0.0.1:3000/", wait_until="load", timeout=15000)
        await active_pause(page, 10.0, 960, 360)

        # ========================================================
        # SEGMENT 02 (12s - 32s): CAMPUS RECEIPT STRIP & HANDOFFS
        # ========================================================
        print("[02] Campus Live Receipts & Handoffs...")
        await smooth_scroll_window(page, 580, duration=3.5)
        await active_pause(page, 6.0, 600, 480)
        await smooth_scroll_window(page, 880, duration=3.0)
        await active_pause(page, 6.0, 1100, 520)

        # ========================================================
        # SEGMENT 03 (32s - 50s): CONNECT DESK (TENANT & OAUTH)
        # ========================================================
        print("[03] Connect Desk...")
        await page.goto("http://127.0.0.1:3000/connect", wait_until="load", timeout=15000)
        await active_pause(page, 5.0, 960, 420)
        await smooth_scroll_window(page, 450, duration=3.0)
        await active_pause(page, 4.0, 700, 500)
        await smooth_scroll_window(page, 850, duration=3.0)
        await active_pause(page, 4.0, 700, 600)

        # ========================================================
        # SEGMENT 04 (50s - 66s): COVE TENANT STOREFRONT
        # ========================================================
        print("[04] Cove Storefront...")
        await page.goto("https://cove-5uy6fkd7bq-uc.a.run.app/", wait_until="load", timeout=15000)
        await active_pause(page, 3.5, 960, 350)
        await smooth_scroll_window(page, 450, duration=2.5)
        await active_pause(page, 3.5, 600, 500)
        await smooth_scroll_window(page, 850, duration=2.5)
        await active_pause(page, 3.0, 800, 500)
        await smooth_scroll_window(page, 0, duration=2.0)

        # ========================================================
        # SEGMENT 05 (66s - 80s): INCIDENT ROOM ENTRY
        # ========================================================
        print("[05] Incident Room Entry...")
        await page.goto("http://127.0.0.1:3000/rooms/room_f627763ea9", wait_until="load", timeout=15000)
        await active_pause(page, 12.0, 400, 200)

        # ========================================================
        # SEGMENT 06 (80s - 98s): PARALLEL SPECIALIST HANDOFFS
        # ========================================================
        print("[06] Specialist Handoffs...")
        await smooth_scroll_chat(page, 450, duration=3.0)
        await active_pause(page, 5.0, 500, 350)
        await smooth_scroll_chat(page, 950, duration=3.0)
        await active_pause(page, 6.0, 500, 450)

        # ========================================================
        # SEGMENT 07 (98s - 118s): CUSTOMER VOICE DIAGNOSTIC JSON
        # ========================================================
        print("[07] Customer Voice Diagnostic Evidence...")
        await smooth_scroll_chat(page, 1550, duration=3.0)
        await active_pause(page, 14.0, 680, 520)

        # ========================================================
        # SEGMENT 08 (118s - 134s): PROOF CARDS & COORDINATION
        # ========================================================
        print("[08] Proof Embed Cards & Coordination...")
        await smooth_scroll_chat(page, 2200, duration=3.0)
        await active_pause(page, 12.0, 800, 550)

        # ========================================================
        # SEGMENT 09 (134s - 151s): HIGH RISK & PR PREPARATION
        # ========================================================
        print("[09] High Risk & PR Preparation...")
        await smooth_scroll_chat(page, 2850, duration=3.0)
        await active_pause(page, 13.0, 700, 600)

        # ========================================================
        # SEGMENT 10 (151s - 169s): GITHUB PR #17 DIFF
        # ========================================================
        print("[10] GitHub PR #17 Diff...")
        await page.goto("https://github.com/saurabh4269/cove/pull/17", wait_until="load", timeout=15000)
        await active_pause(page, 4.0, 500, 300)
        await smooth_scroll_window(page, 350, duration=2.5)
        await active_pause(page, 3.0, 600, 400)
        try:
            await page.goto("https://github.com/saurabh4269/cove/pull/17/files", wait_until="load", timeout=15000)
            await active_pause(page, 3.0, 500, 300)
            await smooth_scroll_window(page, 350, duration=2.5)
            await active_pause(page, 3.0, 600, 450)
        except Exception:
            await active_pause(page, 6.0, 600, 400)

        # ========================================================
        # SEGMENT 11 (169s - 185s): WORKFLOWS ORCHESTRATION PIPELINE
        # ========================================================
        print("[11] Workflows Orchestration Pipeline...")
        await page.goto("http://127.0.0.1:3000/workflows", wait_until="load", timeout=15000)
        await active_pause(page, 5.0, 700, 350)
        await smooth_scroll_window(page, 450, duration=2.5)
        await active_pause(page, 7.0, 600, 500)

        # ========================================================
        # SEGMENT 12 (185s - 206s): RETURN TO CAMPUS HERO & CLOSE
        # ========================================================
        print("[12] Return to Campus Hero...")
        await page.goto("http://127.0.0.1:3000/", wait_until="load", timeout=15000)
        await active_pause(page, 17.0, 960, 400)

        print("Single-page walkthrough perfectly timed and completed!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_walkthrough())
