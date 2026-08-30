# northstar-shop (fixture patch targets)

Tiny in-repo files the Code Agent is allowed to touch in engine fixtures. This is **not** a product, not a storefront, and not hosted by Product OS.

- `pay-sdk-adapter.js` — payment SDK callback (Safari / Android fixtures)
- `onboarding.js` — activation copy (non-checkout fixture)
- `checkout.js` — shipping / delivery-date experiment

No production customer data. No `web/` storefront in this repo. Merge and deploy stay denied until a real tenant repo is connected.
