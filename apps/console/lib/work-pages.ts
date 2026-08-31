import type { OfficeDesk, Room, RoomDetail } from "@/lib/api";

export type WorkPage = {
  id: string;
  kicker: string;
  title: string;
  body: string;
  people?: string[];
};

export function kindLabel(kind: string) {
  if (kind === "incident") return "Incident";
  if (kind === "opportunity") return "Idea";
  if (kind === "review") return "Review";
  if (kind === "research") return "Research";
  if (kind === "ops") return "Ops";
  return kind;
}

export function loopNote(loop?: string | null) {
  if (loop === "type_a") return " · fix";
  if (loop === "type_b") return " · improve";
  return "";
}

export function pagesFromRoom(room: Room, desks: OfficeDesk[] = [], detail?: RoomDetail | null): WorkPage[] {
  const inside = desks.filter((d) => d.room_id === room.id);
  const pages: WorkPage[] = [
    {
      id: `${room.id}-cover`,
      kicker: `${kindLabel(room.kind)}${loopNote(room.loop_type)}`,
      title: room.title,
      body: room.topic || room.preview || "The room is open.",
      people: inside.length ? inside.map((d) => d.id) : room.members.filter((m) => m !== "system"),
    },
  ];

  if (inside.length) {
    const working = inside.filter((d) => d.status !== "idle");
    pages.push({
      id: `${room.id}-who`,
      kicker: "Inside",
      title: working.length ? `${working.length} working right now` : `${inside.length} people here`,
      body: (working[0]?.doing || inside[0]?.doing || "The room is quiet.").slice(0, 220),
      people: inside.map((d) => d.id),
    });
  }

  const preview = room.preview && room.preview !== room.topic ? room.preview : null;
  if (preview) {
    pages.push({
      id: `${room.id}-latest`,
      kicker: "Latest",
      title: "The last thing said",
      body: preview,
    });
  }

  const bundle = detail?.bundle;
  if (bundle?.evidence?.[0]) {
    pages.push({
      id: `${room.id}-evidence`,
      kicker: "Evidence",
      title: bundle.evidence[0].source_type.replace(/_/g, " "),
      body: bundle.evidence[0].claim,
    });
  }
  if (bundle?.hypotheses?.[0]) {
    pages.push({
      id: `${room.id}-hyp`,
      kicker: "Working theory",
      title: bundle.hypotheses[0].classification.replace(/_/g, " "),
      body: bundle.hypotheses[0].statement,
    });
  }
  const action = bundle?.actions?.[0];
  if (action && ["proposed", "awaiting_approval"].includes(action.status)) {
    pages.push({
      id: `${room.id}-gate`,
      kicker: `Needs a look · ${action.risk_tier}`,
      title: "This change is waiting on you",
      body: action.consequence,
    });
  }

  const lastHuman = detail?.messages?.filter((m) => m.author !== "system").slice(-1)[0];
  if (lastHuman && lastHuman.text !== preview) {
    pages.push({
      id: `${room.id}-chat`,
      kicker: "In the room",
      title: lastHuman.author.replace(/_agent$/, "").replace(/_/g, " "),
      body: lastHuman.text,
    });
  }

  pages.push({
    id: `${room.id}-open`,
    kicker: "Go deeper",
    title: "Open",
    body: "The full thread, handoffs, and anything waiting on you.",
    people: room.members.filter((m) => m !== "system").slice(0, 6),
  });

  return pages;
}

export function pagesFromDistrict(
  district: string,
  rooms: Room[],
  desks: OfficeDesk[]
): WorkPage[] {
  const here = desks.filter((d) => d.district === district);
  const roomIds = new Set(here.map((d) => d.room_id).filter(Boolean) as string[]);
  const listed = rooms.filter((r) => roomIds.has(r.id));
  const pages: WorkPage[] = [
    {
      id: `${district}-cover`,
      kicker: "Building",
      title: district,
      body: here.length
        ? `${here.filter((d) => d.status !== "idle").length} people at work in this building.`
        : "Quiet for the moment.",
      people: here.map((d) => d.id),
    },
  ];
  for (const room of listed.slice(0, 4)) {
    pages.push({
      id: room.id,
      kicker: kindLabel(room.kind),
      title: room.title,
      body: room.preview ?? room.topic,
      people: room.members.filter((m) => m !== "system").slice(0, 4),
    });
  }
  return pages;
}
