import { AgentView } from "@/components/agent-view";

export function generateStaticParams() {
  return [{ id: "_" }];
}

export default function AgentPage() {
  return <AgentView />;
}
