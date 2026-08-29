/** Sample payment adapter. Code Agent opens PRs against this file. */
export const PAY_SDK_VERSION = "4.3.0";
export const ANDROID_SDK_VERSION = "3.8.0";

export function onPspSuccess(callback) {
  // Fixture bug: some WebKit / Android builds drop the callback.
  if (typeof callback === "function") {
    callback({ ok: true, version: PAY_SDK_VERSION });
  }
}

export function shouldHoldCallback(ua) {
  return /Safari/.test(ua) && PAY_SDK_VERSION.startsWith("4.3");
}
