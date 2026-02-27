import os

import pandas as pd
from demoparser2 import DemoParser

demo_path = r"E:\Renan\project\Macena_cs2_analyzer\Programma_CS2_RENAN\data\demos_to_process\ingest\match730_003739054579921191006_0270250829_273.dem"

if os.path.exists(demo_path):
    parser = DemoParser(demo_path)

    print("--- Testing parse_ticks ---")
    try:
        # Try a single known field first
        t = parser.parse_ticks(["player_name"])
        print(f"parse_ticks(['player_name']) success. Type: {type(t)}")
        if isinstance(t, pd.DataFrame):
            print(f"Columns: {t.columns.tolist()}")
    except Exception as e:
        print(f"parse_ticks(['player_name']) FAILED: {e}")

    print("\n--- Testing multiple fields ---")
    fields = ["player_name", "damage_total", "kills_total", "deaths_total"]
    for f in fields:
        try:
            parser.parse_ticks([f])
            print(f"Field '{f}' is valid.")
        except Exception as e:
            print(f"Field '{f}' is INVALID: {e}")

    print("\n--- Testing parse_events structure ---")
    evs = parser.parse_events(["round_end"])
    print(f"Type of parse_events result: {type(evs)}")
    if isinstance(evs, list) and len(evs) > 0:
        print(f"Type of first element: {type(evs[0])}")
        if isinstance(evs[0], tuple):
            print(f"Tuple length: {len(evs[0])}")
            print(f"Tuple[0]: {evs[0][0]}")
            print(f"Tuple[1] Type: {type(evs[0][1])}")

else:
    print(f"File not found: {demo_path}")
