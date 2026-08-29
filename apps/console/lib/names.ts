export function shortName(id: string) {
  if (id === "you") return "You";
  if (id === "system") return "System";
  return id
    .replace(/_agent$/, "")
    .replace(/^customer_/, "")
    .replace(/^product_intelligence$/, "intel")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function hashHue(id: string) {
  let n = 0;
  for (let i = 0; i < id.length; i++) n = (n * 31 + id.charCodeAt(i)) >>> 0;
  return n;
}
