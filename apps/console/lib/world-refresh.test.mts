import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { applyRoomsTryGet } from "./rooms-index-load.ts";
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
