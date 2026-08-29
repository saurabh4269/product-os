---
name: safari-payment-sdk
description: Investigate Safari checkout regressions after payment SDK upgrades.
version: 1
---

# Safari payment SDK playbook

1. Query daily `events_YYYYMMDD` for purchase / begin_checkout by browser. Do not use intraday tables as evidence.
2. Confirm a logs independence group: 3DS or challenge-frame errors on WebKit.
3. Confirm a deploy independence group: payment SDK version change within the onset window.
4. Do not emit a hypothesis unless all three groups exist.
5. Payment authorization surfaces are HIGH. Do not execute without a recorded approval.
6. After rollback, measure the originating Safari conversion metric before closing.
