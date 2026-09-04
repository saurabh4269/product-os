import asyncio
import os
import subprocess
from pathlib import Path
from playwright.async_api import async_playwright

ADMIN_TOKEN = ""
token_path = Path("/tmp/.loop_admin")
if token_path.exists():
    ADMIN_TOKEN = token_path.read_text().strip()

async def smooth_scroll(page, target_y, duration=2.5, steps=25):
    """Smooth human-like scrolling."""
    current_y = await page.evaluate("window.scrollY")
    distance = target_y - current_y
    for i in range(steps):
        # Ease out quad
        t = (i + 1) / steps
        ease = t * (2 - t)
        y = current_y + distance * ease
        await page.evaluate(f"window.scrollTo({{ top: {y}, behavior: 'instant' }})")
        await asyncio.sleep(duration / steps)

async def run_walkthrough():
    print("Launching Chromium on DISPLAY=:1 at 1920x1080...")
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

        # Tab 1: Product OS Campus
        page_os = await context.new_page()
        # Seed admin token before navigation
        await page_os.add_init_script(f"""
            sessionStorage.setItem('loop_admin_token', '{ADMIN_TOKEN}');
            localStorage.setItem('loop-sidebar', '1');
        """)

        # Tab 2: Cove Storefront
        page_cove = await context.new_page()

        # Tab 3: GitHub PR #17 on Cove
        page_gh = await context.new_page()

        # Bring Tab 1 to front
        await page_os.bring_to_front()

        # ========================================================
        # BEAT 1 & 2: CAMPUS & LIVE RECEIPTS (0s - 32s)
        # ========================================================
        print("[Beat 1-2] Navigating to Campus...")
        await page_os.goto("http://127.0.0.1:3000/", wait_until="networkidle")
        await asyncio.sleep(4)

        # Hover campus elements gently
        await page_os.mouse.move(960, 360, steps=20)
        await asyncio.sleep(2)
        await page_os.mouse.move(750, 420, steps=20)
        await asyncio.sleep(2)

        # Scroll down smoothly to Live Work & Tools in focus
        print("Scrolling down to live work & receipts...")
        await smooth_scroll(page_os, 580, duration=3.0)
        await asyncio.sleep(4)

        # Hover over agent handoff strip
        await page_os.mouse.move(500, 480, steps=15)
        await asyncio.sleep(2)
        await page_os.mouse.move(1200, 480, steps=20)
        await asyncio.sleep(3)

        # Scroll slightly further to reveal proof cards
        await smooth_scroll(page_os, 880, duration=2.5)
        await asyncio.sleep(4)

        # ========================================================
        # BEAT 3: CONNECT DESK (32s - 54s)
        # ========================================================
        print("[Beat 3] Navigating to /connect...")
        await page_os.goto("http://127.0.0.1:3000/connect", wait_until="networkidle")
        await asyncio.sleep(3)

        # Showcase Cove integration and OAuth
        await page_os.mouse.move(960, 420, steps=20)
        await asyncio.sleep(3)
        await smooth_scroll(page_os, 450, duration=2.5)
        await asyncio.sleep(3)
        await smooth_scroll(page_os, 850, duration=2.5)
        await asyncio.sleep(4)

        # ========================================================
        # BEAT 4: COVE TENANT STOREFRONT (54s - 78s)
        # ========================================================
        print("[Beat 4] Switching to Cove Storefront Tab...")
        await page_cove.bring_to_front()
        await page_cove.goto("https://cove-5uy6fkd7bq-uc.a.run.app/", wait_until="networkidle")
        await asyncio.sleep(4)

        # Browse products
        await smooth_scroll(page_cove, 450, duration=2.5)
        await asyncio.sleep(3)
        await page_cove.mouse.move(600, 500, steps=20)
        await asyncio.sleep(2)
        await smooth_scroll(page_cove, 900, duration=2.5)
        await asyncio.sleep(4)
        await smooth_scroll(page_cove, 0, duration=2.0)
        await asyncio.sleep(2)

        # ========================================================
        # BEAT 5 & 6: INCIDENT ROOM & SPECIALISTS (78s - 120s)
        # ========================================================
        print("[Beat 5-6] Switching back to Product OS -> Hang Room...")
        await page_os.bring_to_front()
        await page_os.goto("http://127.0.0.1:3000/rooms/room_f627763ea9", wait_until="networkidle")
        await asyncio.sleep(4)

        # Look at the room header & tags
        await page_os.mouse.move(400, 150, steps=15)
        await asyncio.sleep(3)

        # Scroll down through initial signal & specialist handoffs
        print("Scrolling through room messages...")
        await smooth_scroll(page_os, 400, duration=3.0)
        await asyncio.sleep(4)
        await smooth_scroll(page_os, 850, duration=3.0)
        await asyncio.sleep(4)

        # ========================================================
        # BEAT 7 & 8: CUSTOMER VOICE & PROOFS (120s - 158s)
        # ========================================================
        print("[Beat 7-8] Customer Voice & Evidence Proofs...")
        await smooth_scroll(page_os, 1400, duration=3.0)
        await asyncio.sleep(5)

        # Hover on structured customer voice evidence
        await page_os.mouse.move(680, 520, steps=15)
        await asyncio.sleep(3)

        # Scroll down to proof embed cards & coordination messages
        await smooth_scroll(page_os, 2100, duration=3.0)
        await asyncio.sleep(4)
        await page_os.mouse.move(800, 600, steps=15)
        await asyncio.sleep(3)

        # Scroll to pending action / risk assessment
        await smooth_scroll(page_os, 2800, duration=3.0)
        await asyncio.sleep(4)

        # ========================================================
        # BEAT 9 & 10: GITHUB PR #17 TAB (158s - 176s)
        # ========================================================
        print("[Beat 9-10] Switching to GitHub PR #17 Tab...")
        await page_gh.bring_to_front()
        await page_gh.goto("https://github.com/saurabh4269/cove/pull/17", wait_until="networkidle")
        await asyncio.sleep(3)

        # Show PR description and title
        await smooth_scroll(page_gh, 350, duration=2.5)
        await asyncio.sleep(3)

        # Show changed files tab if available or scroll down diff
        await page_gh.goto("https://github.com/saurabh4269/cove/pull/17/files", wait_until="networkidle")
        await asyncio.sleep(3)
        await smooth_scroll(page_gh, 400, duration=2.5)
        await asyncio.sleep(4)

        # ========================================================
        # BEAT 11: APPROVALS & GOVERNANCE (176s - 192s)
        # ========================================================
        print("[Beat 11] Navigating to Approvals page...")
        await page_os.bring_to_front()
        await page_os.goto("http://127.0.0.1:3000/approvals", wait_until="networkidle")
        await asyncio.sleep(3)

        await page_os.mouse.move(700, 350, steps=15)
        await asyncio.sleep(3)
        await smooth_scroll(page_os, 400, duration=2.0)
        await asyncio.sleep(3)

        # ========================================================
        # BEAT 12: RETURN TO CAMPUS (192s - 208s)
        # ========================================================
        print("[Beat 12] Returning to Campus Hero...")
        await page_os.goto("http://127.0.0.1:3000/", wait_until="networkidle")
        await asyncio.sleep(3)
        await page_os.mouse.move(960, 400, steps=20)
        await asyncio.sleep(5)

        print("Walkthrough completed successfully!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_walkthrough())
