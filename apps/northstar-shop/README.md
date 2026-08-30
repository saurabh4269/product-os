# Northstar (dummy company)

The company Product OS is operating. Not the Product OS UI.

**Storefront:** `web/` — home, product, checkout, onboarding, ads landing. Served at `/shop`. After a gate is approved, `/api/company` flags change and the shop pages follow (SDK rollback, copy revert, delivery date).

**Code Agent targets** (no production customer data; merge is denied):

- `pay-sdk-adapter.js` — payment SDK callback
- `onboarding.js` — activation copy
- `checkout.js` — shipping / delivery-date experiment

Ads live in the warehouse (`data/generate.py` → `ads.json`): US-Search-Brand and US-Shopping-Home. Spend stays flat so a conversion drop is not blamed on ads.
