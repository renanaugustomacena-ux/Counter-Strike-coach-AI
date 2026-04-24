/**
 * React hook wrapping the typed `MarqueeBridge`. Subscribes to every
 * observable payload the host Python screen publishes (tick, frame,
 * map name, segments, events, ghost). All JSON payloads are parsed
 * once at the boundary so downstream components deal in typed objects.
 */
import { useEffect, useRef, useState } from "react";
import { connectBridge, type MarqueeBridge } from "@shared/qwebchannel";
import type { EventMarker, FramePayload, GhostState } from "./types";

export type BridgeState = {
  bridge: MarqueeBridge | null;
  currentTick: number;
  frame: FramePayload | null;
  mapName: string;
  segments: Record<string, number>;
  events: EventMarker[];
  ghosts: GhostState[];
  error: string | null;
};

const EMPTY: BridgeState = {
  bridge: null,
  currentTick: 0,
  frame: null,
  mapName: "",
  segments: {},
  events: [],
  ghosts: [],
  error: null,
};

function safeParse<T>(payload: string, fallback: T): T {
  try {
    return JSON.parse(payload) as T;
  } catch {
    return fallback;
  }
}

export function useMarqueeBridge(): BridgeState {
  const [state, setState] = useState<BridgeState>(EMPTY);
  const connected = useRef(false);

  useEffect(() => {
    let mounted = true;
    if (connected.current) return;
    connected.current = true;

    connectBridge("bridge")
      .then((bridge) => {
        if (!mounted) return;
        setState((s) => ({ ...s, bridge }));

        bridge.tick_changed.connect((tick) => {
          if (!mounted) return;
          setState((s) => ({ ...s, currentTick: tick }));
        });
        bridge.frame_ready.connect((payload) => {
          if (!mounted) return;
          const frame = safeParse<FramePayload>(payload, {
            tick: 0,
            players: [],
            nades: [],
          });
          setState((s) => ({ ...s, frame }));
        });
        bridge.map_name_changed.connect((name) => {
          if (!mounted) return;
          setState((s) => ({ ...s, mapName: name }));
        });
        bridge.segments_ready.connect((payload) => {
          if (!mounted) return;
          const segments = safeParse<Record<string, number>>(payload, {});
          setState((s) => ({ ...s, segments }));
        });
        bridge.events_ready.connect((payload) => {
          if (!mounted) return;
          const events = safeParse<EventMarker[]>(payload, []);
          setState((s) => ({ ...s, events }));
        });
        bridge.ghost_ready.connect((payload) => {
          if (!mounted) return;
          const ghosts = safeParse<GhostState[]>(payload, []);
          setState((s) => ({ ...s, ghosts }));
        });
        bridge.log("info", "[tactical-viewer] bridge connected");
      })
      .catch((err: Error) => {
        if (!mounted) return;
        setState((s) => ({ ...s, error: err.message }));
      });

    return () => {
      mounted = false;
    };
  }, []);

  return state;
}
