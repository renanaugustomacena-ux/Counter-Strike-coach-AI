import { useEffect, useRef, useState } from "react";
import { connectBridge, type Signal1 } from "@shared/qwebchannel";
import type { MatchDetailPayload } from "./types";

export interface MatchDetailBridge {
  match_data: string;
  is_loading: boolean;
  error_msg: string;

  data_ready: Signal1<string>;
  loading_changed: Signal1<boolean>;
  error_changed: Signal1<string>;

  load_detail(demo_name: string): void;
}

export interface MatchDetailState {
  bridge: MatchDetailBridge | null;
  data: MatchDetailPayload | null;
  isLoading: boolean;
  error: string | null;
}

const EMPTY: MatchDetailState = {
  bridge: null,
  data: null,
  isLoading: false,
  error: null,
};

function safeParse<T>(payload: string, fallback: T): T {
  try {
    return JSON.parse(payload) as T;
  } catch {
    return fallback;
  }
}

export function useMatchDetailBridge(): MatchDetailState {
  const [state, setState] = useState<MatchDetailState>(EMPTY);
  const connected = useRef(false);

  useEffect(() => {
    let mounted = true;
    if (connected.current) return;
    connected.current = true;

    connectBridge<MatchDetailBridge>("bridge")
      .then((bridge) => {
        if (!mounted) return;
        setState((s) => ({ ...s, bridge }));

        bridge.data_ready.connect((payload) => {
          if (!mounted) return;
          const data = safeParse<MatchDetailPayload | null>(payload, null);
          setState((s) => ({ ...s, data }));
        });
        bridge.loading_changed.connect((loading) => {
          if (!mounted) return;
          setState((s) => ({ ...s, isLoading: loading }));
        });
        bridge.error_changed.connect((msg) => {
          if (!mounted) return;
          setState((s) => ({
            ...s,
            error: msg || null,
          }));
        });
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
