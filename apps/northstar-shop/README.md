# northstar-shop (sample product)

Tiny commerce surface the Code Agent patches. Not the Product OS UI.

Files the agent is allowed to touch:

- `pay-sdk-adapter.js` — payment SDK callback (Safari / Android fixtures)
- `onboarding.js` — activation copy (non-checkout fixture)
- `checkout.js` — shipping / delivery-date experiment

No production customer data lives here. PRs stay in this tree. Merge and deploy are denied by the gateway.
