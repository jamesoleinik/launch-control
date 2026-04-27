"""Patch the Dataverse SDK filters.py for Python 3.11 compatibility."""
import pathlib

p = pathlib.Path(
    r"C:\Users\jamesol\AppData\Local\Packages"
    r"\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0"
    r"\LocalCache\local-packages\Python311\site-packages"
    r"\PowerPlatform\Dataverse\models\filters.py"
)
text = p.read_text(encoding="utf-8")
lines = text.split("\n")
count = 0
for i, line in enumerate(lines):
    if "strip" in line and "_format_value" in line and "parts" in line:
        indent = " " * (len(line) - len(line.lstrip()))
        lines[i] = indent + 'parts = [\'"\' + _format_value(v).strip("\'") + \'"\' for v in self.values]'
        print(f"Patched line {i+1}")
        count += 1

if count:
    p.write_text("\n".join(lines), encoding="utf-8")
    print(f"Patched {count} lines.")
else:
    print("No lines to patch.")
