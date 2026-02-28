import os
import sys

print("--- PYTHON DEBUG INFO ---")
print(f"Executable: {sys.executable}")
print(f"Version: {sys.version}")
print(f"CWD: {os.getcwd()}")
print("\n--- SYS.PATH ---")
for p in sys.path:
    print(p)

print("\n--- ATTEMPTING IMPORT ---")
try:
    import kivy

    print(f"SUCCESS: Kivy found at {kivy.__file__}")
    print(f"Kivy Version: {kivy.__version__}")
except ImportError as e:
    print(f"FAILURE: {e}")
except Exception as e:
    print(f"ERROR: {e}")

try:
    import kivymd

    print(f"SUCCESS: KivyMD found at {kivymd.__file__}")
except ImportError:
    print("FAILURE: KivyMD not found")

print("--- END DEBUG ---")
