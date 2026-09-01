#!/usr/bin/env python3
"""Product OS architecture — excalidraw-skill, no library merges (avoids label overflow)."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "architecture-full.excalidraw"


@dataclass
class Box:
    id: str
    x: float
    y: float
    w: float
    h: float
    stroke: str
    bg: str
    seed: int
    label: str
    sub: str | None = None
    arrows: list[str] = field(default_factory=list)

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


def _el(
    id_: str,
    type_: str,
    x: float,
    y: float,
    w: float,
    h: float,
    seed: int,
    **kw,
) -> dict:
    stroke = kw.get("stroke", "#475569")
    el: dict = {
        "id": id_,
        "type": type_,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "angle": 0,
        "strokeColor": stroke if type_ != "text" else kw.get("color", "#1e293b"),
        "backgroundColor": kw.get("bg", "transparent"),
        "fillStyle": "solid",
        "strokeWidth": 2 if type_ != "text" else 1,
        "strokeStyle": kw.get("stroke_style", "solid"),
        "roughness": 0,
        "opacity": kw.get("opacity", 100),
        "seed": seed,
        "updated": 1,
        "boundElements": kw.get("bound"),
        "groupIds": [],
    }
    if kw.get("roundness"):
        el["roundness"] = kw["roundness"]
    if type_ == "text":
        el["text"] = kw.get("text", "")
        el["fontSize"] = kw.get("font_size", 16)
        el["fontFamily"] = 2
        el["textAlign"] = kw.get("align", "left")
        el["verticalAlign"] = kw.get("valign", "top")
        el["containerId"] = kw.get("container_id")
    if type_ == "arrow":
        el["backgroundColor"] = "transparent"
        el["points"] = kw.get("points", [[0, 0], [100, 0]])
        el["startArrowhead"] = None
        el["endArrowhead"] = "arrow"
        if kw.get("start"):
            el["startBinding"] = {"elementId": kw["start"], "gap": 8, "focus": 0}
        if kw.get("end"):
            el["endBinding"] = {"elementId": kw["end"], "gap": 8, "focus": 0}
    return el


class Scene:
    def __init__(self) -> None:
        self.elements: list[dict] = []
        self.boxes: dict[str, Box] = {}

    def box(self, b: Box) -> None:
        self.boxes[b.id] = b
        bound: list[dict] | None = [{"id": f"{b.id}_t", "type": "text"}]
        if b.arrows:
            bound.extend({"id": a, "type": "arrow"} for a in b.arrows)
        text = b.label if not b.sub else f"{b.label}\n{b.sub}"
        self.elements.append(
            _el(
                b.id,
                "rectangle",
                b.x,
                b.y,
                b.w,
                b.h,
                b.seed,
                stroke=b.stroke,
                bg=b.bg,
                bound=bound,
                roundness={"type": 3},
            )
        )
        self.elements.append(
            _el(
                f"{b.id}_t",
                "text",
                b.x + 6,
                b.y + (8 if b.sub else 14),
                b.w - 12,
                b.h - 10,
                b.seed + 1,
                text=text,
                font_size=17 if b.sub else 18,
                container_id=b.id,
                align="center",
                valign="middle",
            )
        )

    def text(self, id_: str, x: float, y: float, w: float, text: str, seed: int, size=14, color="#64748b") -> None:
        self.elements.append(_el(id_, "text", x, y, w, size + 6, seed, text=text, font_size=size, color=color))

    def zone(self, id_: str, x: float, y: float, w: float, h: float, seed: int) -> None:
        self.elements.append(
            _el(
                id_,
                "rectangle",
                x,
                y,
                w,
                h,
                seed,
                stroke="#94a3b8",
                bg="#f8fafc",
                opacity=35,
                stroke_style="dashed",
                bound=None,
                roundness={"type": 3},
            )
        )

    def arrow(
        self,
        id_: str,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        seed: int,
        *,
        start: str | None = None,
        end: str | None = None,
        points: list[list[float]] | None = None,
        dashed: bool = False,
    ) -> None:
        if start and start in self.boxes:
            self.boxes[start].arrows.append(id_)
        if end and end in self.boxes:
            self.boxes[end].arrows.append(id_)
        pts = points or [[0, 0], [x2 - x1, y2 - y1]]
        self.elements.append(
            _el(
                id_,
                "arrow",
                x1,
                y1,
                abs(pts[-1][0]),
                abs(pts[-1][1]),
                seed,
                points=pts,
                stroke_style="dashed" if dashed else "solid",
                bound=None,
                start=start,
                end=end,
            )
        )

    def hlink(self, id_: str, a: Box, b: Box, seed: int, y: float | None = None) -> None:
        yy = y if y is not None else a.cy
        self.arrow(id_, a.right, yy, b.x, yy, seed, start=a.id, end=b.id)

    def vlink(self, id_: str, top: Box, bottom: Box, seed: int) -> None:
        self.arrow(id_, top.cx, top.bottom, bottom.cx, bottom.y, seed, start=top.id, end=bottom.id)

    def dump(self) -> dict:
        by_id = {e["id"]: e for e in self.elements}
        for b in self.boxes.values():
            bound: list[dict] = [{"id": f"{b.id}_t", "type": "text"}]
            bound.extend({"id": a, "type": "arrow"} for a in b.arrows)
            by_id[b.id]["boundElements"] = bound
        return {
            "type": "excalidraw",
            "version": 2,
            "source": "product-os",
            "elements": self.elements,
            "appState": {"viewBackgroundColor": "#ffffff", "exportBackground": True},
            "files": {},
        }


def main() -> None:
    s = Scene()

    # --- header ---
    s.text("title", 40, 24, 400, "Product OS", 1, size=28, color="#1e293b")
    s.text("sub", 40, 58, 640, "One pipeline for bugs and features", 2, size=14)

    # --- cloud run boundary ---
    s.zone("zone", 40, 88, 1120, 300, 10)
    s.text("zone_l", 52, 98, 120, "Cloud Run", 11, size=12)

    # --- main pipeline (single row, 180px gaps) ---
    y, h = 140, 68
    ui_in = Box("ui_in", 64, y, 152, h, "#9d174d", "#fce7f3", 100, "UI Input", "Product signal")
    router = Box("router", 264, y, 176, h, "#166534", "#dcfce7", 110, "Loop Router", "ADK orchestrator")
    inv = Box("investigate", 488, y, 152, h, "#1e40af", "#dbeafe", 120, "Investigate")
    gate = Box("gate", 688, y, 152, h, "#c2410c", "#fed7aa", 130, "Risk + Approve", "HITL")
    ui_out = Box("ui_out", 888, y, 168, h, "#9d174d", "#fce7f3", 140, "UI Output", "PR + lesson")
    console = Box("console", 264, 240, 176, 60, "#0369a1", "#e0f2fe", 150, "Console", "WebSocket UI")

    for b in (ui_in, router, inv, gate, ui_out, console):
        s.box(b)

    cy = y + h / 2  # 174

    # --- integrations (right half of zone — keeps left column clear for actors) ---
    ty, th = 318, 52
    bq = Box("bq", 488, ty, 124, th, "#0369a1", "#e0f2fe", 200, "BigQuery", "signals")
    fs = Box("fs", 628, ty, 124, th, "#0369a1", "#e0f2fe", 210, "Firestore", "memory")
    gem = Box("gem", 768, ty, 136, th, "#6b21a8", "#f3e8ff", 220, "Gemini 3.5", "Flash")
    gh = Box("gh", 920, ty, 120, th, "#334155", "#f1f5f9", 230, "GitHub", "PR proof")
    for b in (bq, fs, gem, gh):
        s.box(b)

    # --- external actors (left column, below zone) ---
    cove = Box("cove", 64, 430, 168, 56, "#6b21a8", "#f3e8ff", 300, "Product Y", "Cove")
    op = Box("operator", 64, 506, 168, 56, "#6b21a8", "#f3e8ff", 310, "Operator", "approvals")
    s.box(cove)
    s.box(op)

    # --- arrows: pipeline ---
    s.hlink("a1", ui_in, router, 400, cy)
    s.hlink("a2", router, inv, 401, cy)
    s.hlink("a3", inv, gate, 402, cy)
    s.hlink("a4", gate, ui_out, 403, cy)
    s.vlink("a5", router, console, 404)

    # External bus at x=48 — avoids crossing actor/tool boxes
    bus_x = 48
    lane = ty + th + 28  # 398

    # Tap actors into left margin bus
    s.arrow("a_cove_tap", cove.x, cove.cy, bus_x, cove.cy, 409, start="cove")
    s.arrow("a_op_tap", op.x, op.cy, bus_x, op.cy, 410, start="operator")

    # Bus up to ui_in, then to gate
    s.arrow(
        "a8",
        bus_x,
        op.bottom,
        ui_in.x,
        ui_in.cy,
        407,
        end="ui_in",
        points=[
            [0, 0],
            [0, ui_in.cy - op.bottom],
            [ui_in.x - bus_x, ui_in.cy - op.bottom],
        ],
    )
    s.arrow(
        "a9",
        bus_x,
        op.bottom,
        gate.cx,
        gate.bottom,
        408,
        end="gate",
        points=[
            [0, 0],
            [0, lane - op.bottom],
            [gate.cx - bus_x, lane - op.bottom],
            [gate.cx - bus_x, gate.bottom - lane],
        ],
    )

    OUT.write_text(json.dumps(s.dump(), indent=2), encoding="utf-8")
    print(f"wrote {OUT} ({len(s.elements)} elements)")


if __name__ == "__main__":
    main()
