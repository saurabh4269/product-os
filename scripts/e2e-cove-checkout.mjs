#!/usr/bin/env node
/**
 * Cove checkout E2E — mirrors shopper flow against live flags.
 * Usage: node scripts/e2e-cove-checkout.mjs [cove-base-url]
 */
import { chromium } from "playwright";

const COVE = process.argv[2] || "https://cove-5uy6fkd7bq-uc.a.run.app";

async function readFlags(page) {
  const res = await page.request.get(`${COVE}/api/loop/flags`);
  return res.json();
}

async function addProduct(page) {
  await page.goto(`${COVE}/organic-cotton-tshirt`, { waitUntil: "networkidle" });
  const addBtn = page.locator('button:has-text("Add to Cart")').first();
  await addBtn.waitFor({ timeout: 15000 });
  await addBtn.click();
  await page.waitForTimeout(800);
}

async function fillCheckout(page) {
  await page.goto(`${COVE}/checkout`, { waitUntil: "networkidle" });
  await page.fill("#email", "e2e@test.example.com");
  await page.fill("#firstName", "E2E");
  await page.fill("#lastName", "Shopper");
  await page.fill("#line1", "123 Test St");
  await page.fill("#city", "Austin");
  await page.fill("#state", "TX");
  await page.fill("#postalCode", "78701");
  await page.fill("#cardName", "E2E Shopper");
  await page.fill("#cardNumber", "4242 4242 4242 4242");
  await page.fill("#cardExpiry", "12/30");
  await page.fill("#cardCvc", "123");
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const results = [];

  try {
    const flagsBefore = await readFlags(page);
    results.push({
      step: "flags_before",
      sdk: flagsBefore.sdk,
      hung: flagsBefore.hung,
      pay_sdk_4_3: flagsBefore.flags?.pay_sdk_4_3,
    });

    await addProduct(page);
    results.push({ step: "add_to_cart", ok: true });

    await fillCheckout(page);
    const payBtn = page.locator('button[type="submit"]:has-text("Pay now"), button:has-text("Authorizing")').first();
    await payBtn.click();

    if (flagsBefore.hung) {
      await page.waitForSelector("text=Payment authorization timed out", { timeout: 8000 });
      results.push({ step: "checkout_hung", ok: true, path: "timeout+ingest" });
    } else {
      await page.waitForURL(/checkout\/success/, { timeout: 10000 });
      results.push({ step: "checkout_success", ok: true, url: page.url() });
    }

    results.push({ step: "done", ok: true });
    console.log(JSON.stringify({ cove: COVE, results }, null, 2));
  } catch (err) {
    console.error(JSON.stringify({ error: String(err), results }, null, 2));
    process.exit(1);
  } finally {
    await browser.close();
  }
}

main();
