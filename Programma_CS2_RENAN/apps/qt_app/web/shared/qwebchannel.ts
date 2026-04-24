/**
 * Typed wrapper over `qwebchannel.js` (shipped by Qt at
 * ``qrc:///qtwebchannel/qwebchannel.js``). The marquee host screen
 * registers a single ``MarqueeBridge`` object on the channel under the
 * name ``"bridge"``; this module imports that global, awaits connection,
 * and exposes a strongly-typed handle.
 *
 * Layout mirrors ``apps/qt_app/core/web_bridge.py::MarqueeBridge`` —
 * keep them in lockstep when evolving the protocol.
 */

export interface MarqueeBridge {
  // Observable properties (read-only on JS side — updates propagate
  // from Python via the *changed signals).
  current_tick: number;
  frame_payload: string;
  coach_state: string;
  ready: boolean;
  map_name: string;
  segments: string;
  events: string;
  ghost: string;

  // Signals — connect via ``bridge.tick_changed.connect(cb)``.
  tick_changed: Signal1<number>;
  frame_ready: Signal1<string>;
  coach_state_changed: Signal1<string>;
  ready_changed: Signal1<boolean>;
  map_name_changed: Signal1<string>;
  segments_ready: Signal1<string>;
  events_ready: Signal1<string>;
  ghost_ready: Signal1<string>;

  // Slots — callable from JS; await the returned promise for the reply
  // even though Python returns synchronously, the transport is async.
  seek_to_tick(tick: number): void;
  select_player(player_id: number): void;
  request_ghost(tick: number): void;
  log(level: LogLevel, message: string): void;
}

export type LogLevel = "debug" | "info" | "warn" | "error";

export interface Signal1<T> {
  connect(handler: (value: T) => void): void;
  disconnect(handler: (value: T) => void): void;
}

interface QWebChannelGlobal {
  objects: Record<string, unknown>;
}

declare global {
  // Injected by Qt at `qrc:///qtwebchannel/qwebchannel.js`.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const QWebChannel: new (
    transport: unknown,
    callback: (channel: QWebChannelGlobal) => void,
  ) => unknown;
  interface Window {
    // Qt injects this onto the page before the HTML loads.
    qt: {
      webChannelTransport: unknown;
    };
  }
}

/**
 * Returns a promise that resolves to the typed ``MarqueeBridge`` once
 * Qt's channel has handshaked. Callers should ``await connectBridge()``
 * early in their entry point.
 */
export async function connectBridge(
  name = "bridge",
): Promise<MarqueeBridge> {
  // qwebchannel.js is injected by Qt; we reference the global.
  return new Promise<MarqueeBridge>((resolve, reject) => {
    try {
      new QWebChannel(window.qt.webChannelTransport, (channel) => {
        const bridge = channel.objects[name] as MarqueeBridge | undefined;
        if (!bridge) {
          reject(new Error(`MarqueeBridge ${name} not registered on channel`));
          return;
        }
        resolve(bridge);
      });
    } catch (err) {
      reject(err as Error);
    }
  });
}
