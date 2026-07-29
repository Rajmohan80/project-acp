"""Add LAB PROTOTYPE docstring to all src/__init__.py files."""
import pathlib

disclaimer = (
    '"""LAB PROTOTYPE — not production ready. '
    'AbhavTech Agentic Control Plane."""\n'
)

print("Adding LAB PROTOTYPE disclaimers...\n")
for p in pathlib.Path("src").rglob("__init__.py"):
    p.write_text(disclaimer, encoding="utf-8")
    print(f"  updated: {p}")

print("\nVerifying...\n")
all_ok = True
for p in pathlib.Path("src").rglob("__init__.py"):
    text = p.read_text(encoding="utf-8")
    status = "OK" if "LAB PROTOTYPE" in text else "MISSING"
    if status == "MISSING":
        all_ok = False
    print(f"  {status}: {p}")

print()
if all_ok:
    print("All __init__.py files carry the LAB PROTOTYPE disclaimer.")
else:
    print("WARNING — some files are missing the disclaimer. Check above.")