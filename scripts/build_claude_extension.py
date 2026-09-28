"""Build the dependency-free Claude Desktop extension."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import json


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "claude-desktop"
OUTPUT = ROOT / "dist" / "NeonLedger-ClaudeDesktop.mcpb"


def main():
    manifest = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
    entry = SOURCE / manifest["server"]["entry_point"]
    if not entry.is_file():
        raise SystemExit(f"Missing extension entry point: {entry}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as bundle:
        for file in (SOURCE / "manifest.json", entry):
            bundle.write(file, file.relative_to(SOURCE).as_posix())
    print(OUTPUT)


if __name__ == "__main__":
    main()
