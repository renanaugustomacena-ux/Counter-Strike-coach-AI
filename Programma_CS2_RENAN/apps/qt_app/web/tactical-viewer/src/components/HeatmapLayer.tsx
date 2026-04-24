/**
 * Heatmap accumulator — bins all recorded positions in ``history`` into
 * a 40×40 grid and paints alpha cells on a Canvas overlay. Kept inside
 * the <img>-sibling layer (absolute-positioned) so SVG player dots
 * still compose above it.
 */
import { useEffect, useRef } from "react";
import type { FramePayload } from "../types";

export interface HeatmapLayerProps {
  history: FramePayload[];
  side: number;
}

const GRID = 40;

export function HeatmapLayer({ history, side }: HeatmapLayerProps): JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.width = side;
    canvas.height = side;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, side, side);
    if (history.length === 0) return;

    // Count positions per cell.
    const bins = new Uint32Array(GRID * GRID);
    let maxCount = 1;
    for (const frame of history) {
      for (const p of frame.players) {
        if (!p.is_alive) continue;
        const gx = Math.min(GRID - 1, Math.max(0, Math.floor(p.nx * GRID)));
        const gy = Math.min(GRID - 1, Math.max(0, Math.floor(p.ny * GRID)));
        const idx = gy * GRID + gx;
        bins[idx] += 1;
        if (bins[idx] > maxCount) maxCount = bins[idx];
      }
    }

    const cell = side / GRID;
    for (let y = 0; y < GRID; y += 1) {
      for (let x = 0; x < GRID; x += 1) {
        const count = bins[y * GRID + x];
        if (count === 0) continue;
        const t = count / maxCount;
        // Accent-primary → hot cyan as intensity climbs.
        const r = Math.round(255 * (1 - t * 0.4));
        const g = Math.round(106 + (217 - 106) * t);
        const b = Math.round(0 + 255 * t);
        ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${0.25 + 0.4 * t})`;
        ctx.fillRect(x * cell, y * cell, cell, cell);
      }
    }
  }, [history, side]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: "absolute",
        inset: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none",
        mixBlendMode: "screen",
      }}
    />
  );
}
