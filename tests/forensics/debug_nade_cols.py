import pandas as pd
from demoparser2 import DemoParser

path = "Programma_CS2_RENAN/data/pro_demos/furia-vs-natus-vincere-m1-mirage.dem"
parser = DemoParser(path)

print("--- smokegrenade_detonate ---")
res = parser.parse_events(["smokegrenade_detonate"])
if res:
    df = res[0][1]
    print(df.columns.tolist())
    if not df.empty:
        print(df.iloc[0].to_dict())

print("\n--- grenade_thrown ---")
res = parser.parse_events(["grenade_thrown"])
if res:
    df = res[0][1]
    print(df.columns.tolist())
    if not df.empty:
        print(df.iloc[0].to_dict())
