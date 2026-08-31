import { api } from "@/lib/api";
import type { PendingApproval } from "@/lib/demo-guide-context";
import { setPipelineHighlight } from "@/lib/pipeline-highlight";

export type PipelineCard = Awaited<ReturnType<typeof api.pipeline>>["cards"][number];

export type DemoPipelineHandlers = {
  setHighlightStage?: (stage: string | null) => void;
  setFleetWorking?: (on: boolean) => void;
  setPendingApproval?: (payload: PendingApproval | null) => void;
};

/** Sync pipeline highlight + return whether the card needs approval. */
export function applyPipelineCard(
  card: PipelineCard,
  demo: DemoPipelineHandlers | null | undefined
): { needsApproval: boolean; actionId?: string } {
  if (card.stage) {
    demo?.setHighlightStage?.(card.stage);
    setPipelineHighlight(card.stage);
  }
  if (card.awaiting_approval && card.pending_action_id) {
    return { needsApproval: true, actionId: card.pending_action_id };
  }
  return { needsApproval: false };
}

export async function pendingApprovalFromCard(
  card: PipelineCard,
  roomId: string
): Promise<PendingApproval> {
  const gates = await api.approvals();
  const act = gates.pending.find((a) => a.id === card.pending_action_id);
  return {
    action_id: card.pending_action_id!,
    room_id: roomId,
    consequence: act?.consequence,
    risk_tier: act?.risk_tier,
    title: card.title,
  };
}

/** Poll pipeline until approval, terminal stage, or timeout — covers slow runs / missed WS. */
export async function pollDemoPipeline(
  roomId: string,
  demo: DemoPipelineHandlers | null | undefined,
  maxMs = 45000
): Promise<void> {
  const deadline = Date.now() + maxMs;
  while (Date.now() < deadline) {
    await new Promise((r) => window.setTimeout(r, 2000));
    try {
      const pipe = await api.pipeline();
      const card = pipe.cards.find((c) => c.room_id === roomId);
      if (!card) continue;
      const { needsApproval, actionId } = applyPipelineCard(card, demo);
      if (needsApproval && actionId) {
        demo?.setPendingApproval?.(await pendingApprovalFromCard(card, roomId));
        demo?.setFleetWorking?.(false);
        return;
      }
      if (card.verified || card.denied || card.stage === "learn") {
        demo?.setFleetWorking?.(false);
        return;
      }
    } catch {
      /* pipeline optional */
    }
  }
  demo?.setFleetWorking?.(false);
}
