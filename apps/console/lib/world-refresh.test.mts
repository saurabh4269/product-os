import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { applyRoomsTryGet } from "./rooms-index-load.ts";
import { mergeAuthRequired, shouldShowHomeConnectOverlay } from "./home-auth-state.ts";
import { shouldWorldPollFetch } from "./world-poll-gate.ts";

describe("shouldWorldPollFetch", () => {
  it("fetches on first paint even when poll is disabled (hidden tab)", () => {
    assert.equal(shouldWorldPollFetch(false, false), true);
  });

  it("skips tick polls while hidden after primed", () => {
    assert.equal(shouldWorldPollFetch(false, true), false);
  });

  it("resumes polls when tab becomes visible", () => {
    assert.equal(shouldWorldPollFetch(true, true), true);
  });
});

describe("applyRoomsTryGet", () => {
  it("clears loading path via authRequired from tryGet", () => {
    const out = applyRoomsTryGet(false, { data: null, authRequired: true });
    assert.equal(out.adminAuthRequired, true);
    assert.deepEqual(out.rooms, []);
  });

  it("keeps prior adminAuthRequired sticky", () => {
    const out = applyRoomsTryGet(true, { data: [], authRequired: false });
    assert.equal(out.adminAuthRequired, true);
  });
});

describe("shouldShowHomeConnectOverlay", () => {
  it("shows overlay before protected world hydrates without a token", () => {
    assert.equal(shouldShowHomeConnectOverlay(false, false, false), true);
  });

  it("shows overlay when API reported authRequired", () => {
    assert.equal(shouldShowHomeConnectOverlay(true, false, true), true);
  });

  it("hides overlay for token holders while world hydrates", () => {
    assert.equal(shouldShowHomeConnectOverlay(false, true, false), false);
  });

  it("hides overlay after hydrate when no auth was required and token present", () => {
    assert.equal(shouldShowHomeConnectOverlay(false, true, true), false);
  });
});

describe("mergeAuthRequired", () => {
  it("merges office and status auth flags", () => {
    assert.equal(mergeAuthRequired(false, false, true), true);
  });
});
