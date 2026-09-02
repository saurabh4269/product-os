import { MIcon } from "./icon";

/** Connective tissue between signal → understand → fix cards (reference HTML). */
export function FlowConnector() {
  return (
    <div className="relative z-0 -my-2 flex justify-center">
      <div className="h-8 border-l border-dashed border-secondary" />
      <div className="absolute top-1/2 -translate-y-1/2 rounded-full border border-secondary bg-surface p-0.5 text-secondary">
        <MIcon name="arrow_downward" className="text-[14px]" />
      </div>
    </div>
  );
}
