import { useEffect, useRef, useState } from "react";
import { connectBridge, type Signal1 } from "@shared/qwebchannel";
import type { ChatMessage } from "./types";

export interface CoachChatBridge {
  messages: string;
  is_loading: boolean;
  is_available: boolean;
  session_active: boolean;

  messages_changed: Signal1<string>;
  loading_changed: Signal1<boolean>;
  available_changed: Signal1<boolean>;
  session_active_changed: Signal1<boolean>;

  send_message(text: string): void;
  start_session(player_name: string, demo_name: string): void;
  clear_session(): void;
  check_availability(): void;
}

export interface CoachChatState {
  bridge: CoachChatBridge | null;
  messages: ChatMessage[];
  isLoading: boolean;
  isAvailable: boolean;
  sessionActive: boolean;
  error: string | null;
}

const EMPTY: CoachChatState = {
  bridge: null,
  messages: [],
  isLoading: false,
  isAvailable: false,
  sessionActive: false,
  error: null,
};

function safeParse<T>(payload: string, fallback: T): T {
  try {
    return JSON.parse(payload) as T;
  } catch {
    return fallback;
  }
}

export function useCoachChatBridge(): CoachChatState {
  const [state, setState] = useState<CoachChatState>(EMPTY);
  const connected = useRef(false);

  useEffect(() => {
    let mounted = true;
    if (connected.current) return;
    connected.current = true;

    connectBridge<CoachChatBridge>("bridge")
      .then((bridge) => {
        if (!mounted) return;
        setState((s) => ({ ...s, bridge }));

        bridge.messages_changed.connect((payload) => {
          if (!mounted) return;
          const messages = safeParse<ChatMessage[]>(payload, []);
          setState((s) => ({ ...s, messages }));
        });
        bridge.loading_changed.connect((loading) => {
          if (!mounted) return;
          setState((s) => ({ ...s, isLoading: loading }));
        });
        bridge.available_changed.connect((available) => {
          if (!mounted) return;
          setState((s) => ({ ...s, isAvailable: available }));
        });
        bridge.session_active_changed.connect((active) => {
          if (!mounted) return;
          setState((s) => ({ ...s, sessionActive: active }));
        });

        bridge.check_availability();
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
