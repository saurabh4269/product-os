function apiBase() {
  const h = location.hostname;
  const p = location.port;
  if ((h === "127.0.0.1" || h === "localhost") && p && p !== "8080") return "http://127.0.0.1:8080";
  return "";
}

export async function loadCompany() {
  const res = await fetch(`${apiBase()}/api/company`, { cache: "no-store" });
  if (!res.ok) throw new Error("company " + res.status);
  return res.json();
}

export function paySdk(flags) {
  return flags?.pay_sdk_4_3 === "off" ? "4.2.1" : "4.3.0";
}

export function activationCta(flags) {
  return flags?.onboarding_copy_exp_b === "off" ? "Create your account" : "Continue with workspace";
}

export function showDeliveryDate(flags) {
  const v = flags?.show_delivery_date_earlier;
  return Boolean(v) && v !== "off";
}
