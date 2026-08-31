import { shortName } from "@/lib/names";

const ASKS: Record<string, string> = {
  analytics: "can you pull the numbers?",
  logs: "can you check the logs?",
  deploy: "what shipped around then?",
  deployment: "what shipped around then?",
  database: "anything weird in the db?",
  customer: "what are customers saying?",
  code: "can you look at the code?",
  security: "is this allowed?",
  learning: "can you check the metric after?",
  risk: "how risky is this?",
  product: "want to draft a proposal?",
  feedback: "can you call them back?",
  coordination: "can you book a review?",
};

/** Bare handoff tokens become a short group-chat ask. */
export function narrateHandoff(_from: string, to: string, summary: string): string {
  const s = (summary || "").trim();
  const name = shortName(to).split(" ")[0] || shortName(to);
  if (s && (/\s/.test(s) || s.length > 28)) {
    if (s.toLowerCase().includes(name.toLowerCase())) return s.replace(/[—–]/g, ". ");
    const lower = s[0].toLowerCase() + s.slice(1);
    return `${name}, ${lower}`.replace(/[—–]/g, ". ");
  }
  const key = (s || to.replace(/_agent$/, "")).toLowerCase().replace(/\s+/g, "_");
  const ask = ASKS[key] || "can you take a look?";
  return `${name}, ${ask}`;
}
