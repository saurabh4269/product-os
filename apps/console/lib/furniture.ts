import { hashHue } from "@/lib/names";

export type FurnitureKind = "desk" | "chair" | "monitor" | "plant" | "lamp" | "coffee" | "books" | "cabinet";

export type PixelGrid = {
  kind: FurnitureKind;
  grid: string[];
  colors: Record<string, string>;
};

const WOOD = ["#c9b29a", "#b89a7e", "#d4c4b0"] as const;
const METAL = ["#c7c7cc", "#aeaeb2", "#d1d1d6"] as const;
const GLASS = ["#dce3ea", "#c5d0da", "#e8eef3"] as const;
const LEAF = ["#6b7c6e", "#7a8f7c", "#5d6e60"] as const;
const POT = ["#c7c1b3", "#b5a898", "#d8d2c6"] as const;
const LAMP = ["#e8d48b", "#f0e2a8", "#d4c06a"] as const;
const COFFEE = ["#6b3a1f", "#4a2c14"] as const;

function pick<T>(arr: readonly T[], n: number) {
  return arr[n % arr.length];
}

const DESK_A = [
  "................",
  "......oooo......",
  ".....okggko.....",
  ".....okggko.....",
  ".....okkkko.....",
  "..owwwwwwwwwwo..",
  ".owwwwwwwwwwwwo.",
  ".ow..........wo.",
  ".ow..........wo.",
  ".owwwwwwwwwwwwo.",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
];

const DESK_B = [
  "................",
  ".....mmmmmm.....",
  "....mggggggm....",
  "....mggggggm....",
  "....mmmmmmmm....",
  ".owwwwwwwwwwwwo.",
  "owwwwwwwwwwwwwwo",
  "ow............wo",
  "ow............wo",
  "owwwwwwwwwwwwwwo",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
];

const CHAIR = [
  "................",
  "................",
  "................",
  "......ssss......",
  ".....s....s.....",
  ".....ssssss.....",
  "......s..s......",
  "......s..s......",
  ".....ssssss.....",
  "......s..s......",
  "......s..s......",
  "................",
  "................",
  "................",
  "................",
  "................",
];

const MONITOR_ON = [
  "................",
  "...kkkkkkkkkk...",
  "...kggggggggk...",
  "...kg.gggg.gk...",
  "...kggggggggk...",
  "...kggggggggk...",
  "...kkkkkkkkkk...",
  "......kkkk......",
  ".....wwwwww.....",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
];

const MONITOR_OFF = [
  "................",
  "...kkkkkkkkkk...",
  "...k........k...",
  "...k........k...",
  "...k........k...",
  "...k........k...",
  "...kkkkkkkkkk...",
  "......kkkk......",
  ".....wwwwww.....",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
];

const PLANT = [
  "................",
  "......ggg.......",
  ".....ggggg......",
  "....gg.g.gg.....",
  ".....g.s.g......",
  ".......s........",
  "......ppp.......",
  "......ppp.......",
  ".....ppppp......",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
];

const LAMP_GRID = [
  "................",
  "......yyy.......",
  ".....y...y......",
  "......y.y.......",
  ".......k........",
  ".......k........",
  "......kkk.......",
  ".....wwwww......",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
];

const COFFEE_GRID = [
  "................",
  "................",
  "......cc........",
  ".....c..c.ww....",
  ".....c..cww.....",
  ".....cccc.......",
  "......ww........",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
];

const BOOKS = [
  "................",
  "................",
  "....rrr.bbb.....",
  "....rrr.bbb.....",
  "....rrr.bbb.gg..",
  "....rrr.bbb.gg..",
  "...wwwwwwwwwww..",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
];

const CABINET = [
  "................",
  "...mmmmmmmmm....",
  "...m.......m....",
  "...m.kk....m....",
  "...mmmmmmmmm....",
  "...m.......m....",
  "...m.kk....m....",
  "...mmmmmmmmm....",
  "...m.......m....",
  "...mmmmmmmmm....",
  "................",
  "................",
  "................",
  "................",
  "................",
  "................",
];

export type DeskSet = {
  seed: number;
  wood: string;
  items: PixelGrid[];
};

const DISTRICT_EXTRAS: Record<string, FurnitureKind[]> = {
  Incidents: ["cabinet", "coffee"],
  Ideas: ["plant", "lamp"],
  Reviews: ["books", "lamp"],
  Research: ["books", "plant"],
  Ops: ["coffee", "cabinet"],
  Office: ["plant", "coffee"],
};

export function furnitureFor(id: string, district = "Office", working = false): DeskSet {
  const seed = hashHue(id);
  const wood = pick(WOOD, seed);
  const metal = pick(METAL, seed >> 2);
  const glass = pick(GLASS, seed >> 4);
  const leaf = pick(LEAF, seed >> 3);
  const pot = pick(POT, seed >> 5);
  const lamp = pick(LAMP, seed >> 6);
  const coffee = pick(COFFEE, seed >> 1);
  const wide = seed % 3 === 0;

  const items: PixelGrid[] = [
    {
      kind: "desk",
      grid: wide ? DESK_B : DESK_A,
      colors: { o: metal, g: glass, w: wood, k: "#8e8e93", m: metal },
    },
    {
      kind: "chair",
      grid: CHAIR,
      colors: { s: wood },
    },
    {
      kind: "monitor",
      grid: working ? MONITOR_ON : MONITOR_OFF,
      colors: { k: "#3a3a3c", g: working ? "#dce8f4" : "#2c2c2e", w: wood },
    },
  ];

  const extras = DISTRICT_EXTRAS[district] ?? DISTRICT_EXTRAS.Office;
  const extra = extras[seed % extras.length];
  if (extra === "plant") {
    items.push({ kind: "plant", grid: PLANT, colors: { g: leaf, s: "#6b3a1f", p: pot } });
  } else if (extra === "lamp") {
    items.push({ kind: "lamp", grid: LAMP_GRID, colors: { y: lamp, k: "#3a3a3c", w: wood } });
  } else if (extra === "coffee") {
    items.push({ kind: "coffee", grid: COFFEE_GRID, colors: { c: coffee, w: "#f5f5f7" } });
  } else if (extra === "books") {
    items.push({
      kind: "books",
      grid: BOOKS,
      colors: { r: "#8e8e93", b: "#5b7c99", g: leaf, w: wood },
    });
  } else if (extra === "cabinet") {
    items.push({ kind: "cabinet", grid: CABINET, colors: { m: metal, k: "#8e8e93" } });
  }

  if ((seed >> 8) % 5 === 0 && extra !== "coffee") {
    items.push({ kind: "coffee", grid: COFFEE_GRID, colors: { c: coffee, w: "#f5f5f7" } });
  }

  return { seed, wood, items };
}

export function extrasOf(set: DeskSet) {
  return set.items.filter((i) => i.kind !== "desk" && i.kind !== "chair" && i.kind !== "monitor");
}
