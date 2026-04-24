/**
 * Root map canvas — loads the radar PNG + composes the player / ghost
 * / trails / heatmap layers on top. The viewport is a square that fits
 * the smaller of width/height; everything below uses normalized (0..1)
 * coords so layers are viewport-size-agnostic.
 */
import { useEffect, useRef, useState } from "react";
import { CS2_TOKENS } from "@shared/tokens";
import type {
  EventMarker,
  FramePayload,
  GhostState,
} from "../types";
import { PlayerLayer } from "./PlayerLayer";
import { TrailsLayer } from "./TrailsLayer";
import { GhostLayer } from "./GhostLayer";
import { HeatmapLayer } from "./HeatmapLayer";

export interface MapCanvasProps {
  frame: FramePayload | null;
  mapName: string;
  ghosts: GhostState[];
  showHeatmap: boolean;
  showGhosts: boolean;
  selectedPlayerId: number | null;
  onSelectPlayer: (id: number) => void;
  positionHistory: FramePayload[];
  events: EventMarker[];
}

export function MapCanvas({
  frame,
  mapName,
  ghosts,
  showHeatmap,
  showGhosts,
  selectedPlayerId,
  onSelectPlayer,
  positionHistory,
}: MapCanvasProps): JSX.Element {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [side, setSide] = useState(600);
  const [imageOk, setImageOk] = useState(true);

  useEffect(() => {
    if (!wrapperRef.current) return;
    const ro = new ResizeObserver((entries) => {
      for (const e of entries) {
        const s = Math.min(e.contentRect.width, e.contentRect.height);
        if (Number.isFinite(s) && s > 100) setSide(Math.floor(s));
      }
    });
    ro.observe(wrapperRef.current);
    return () => ro.disconnect();
  }, []);

  // Map radar source — relative path; build_web.py copies PNGs into
  // dist/maps/ at build time so `./maps/<name>.png` resolves under the
  // file:// scheme Qt serves.
  const mapFile = mapName ? `./maps/${mapName}.png` : "";

  return (
    <div
      ref={wrapperRef}
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: CS2_TOKENS.surface_sunken,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "relative",
          width: side,
          height: side,
          boxShadow: `0 0 0 1px ${CS2_TOKENS.border_subtle}`,
          borderRadius: 8,
          overflow: "hidden",
          background: CS2_TOKENS.surface_base,
        }}
      >
        {mapFile && imageOk ? (
          <img
            src={mapFile}
            alt={mapName}
            onError={() => setImageOk(false)}
            style={{
              position: "absolute",
              inset: 0,
              width: "100%",
              height: "100%",
              objectFit: "contain",
              opacity: 0.78,
              filter: "saturate(0.7) brightness(0.9)",
            }}
          />
        ) : (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: CS2_TOKENS.text_tertiary,
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 12,
              letterSpacing: 1,
            }}
          >
            {mapName ? `map ${mapName} radar missing` : "no map loaded"}
          </div>
        )}
        {showHeatmap && (
          <HeatmapLayer history={positionHistory} side={side} />
        )}
        <svg
          width={side}
          height={side}
          style={{ position: "absolute", inset: 0 }}
        >
          <TrailsLayer history={positionHistory} side={side} />
          {showGhosts && <GhostLayer ghosts={ghosts} side={side} />}
          <PlayerLayer
            players={frame?.players ?? []}
            side={side}
            selectedPlayerId={selectedPlayerId}
            onSelectPlayer={onSelectPlayer}
          />
        </svg>
      </div>
    </div>
  );
}
