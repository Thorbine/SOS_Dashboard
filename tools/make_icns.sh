#!/bin/bash
# Erzeugt aus einer SVG-Datei ein macOS-Icon (.icns). Aufruf: tools/make_icns.sh logo.svg ziel.icns
set -e
SVG="$1"; ICNS="$2"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Das Logo mit Rand mittig auf ein weißes Quadrat setzen, damit es weder verzerrt noch beschnitten wird.
python3 - "$SVG" "$TMP/icon.svg" <<'EOF'
import re
import sys
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")

def number(text):
    found = re.match(r"\s*([0-9.]+)", text or "")
    return float(found.group(1)) if found else 0.0

root = ET.parse(sys.argv[1]).getroot()
box = [float(v) for v in re.split(r"[ ,]+", root.get("viewBox", "").strip()) if v]
if len(box) != 4:
    box = [0.0, 0.0, number(root.get("width")), number(root.get("height"))]
    root.set("viewBox", " ".join(str(v) for v in box))
if box[2] <= 0 or box[3] <= 0:
    sys.exit("Die Größe des Logos ist nicht erkennbar.")
size, inner = 1024, 880
scale = inner / max(box[2], box[3])
width, height = box[2] * scale, box[3] * scale
for key, value in (("x", (size - width) / 2), ("y", (size - height) / 2), ("width", width), ("height", height)):
    root.set(key, f"{value:.2f}")
outer = ET.Element(f"{{{SVG_NS}}}svg", {"width": str(size), "height": str(size), "viewBox": f"0 0 {size} {size}"})
ET.SubElement(outer, f"{{{SVG_NS}}}rect", {"width": str(size), "height": str(size), "fill": "#ffffff"})
outer.append(root)
ET.ElementTree(outer).write(sys.argv[2], encoding="utf-8", xml_declaration=True)
EOF

qlmanage -t -s 1024 -o "$TMP" "$TMP/icon.svg" >/dev/null 2>&1
PNG="$TMP/icon.svg.png"
[ -f "$PNG" ]
SET="$TMP/icon.iconset"; mkdir "$SET"
for size in 16 32 128 256 512; do
  sips -z $size $size "$PNG" --out "$SET/icon_${size}x${size}.png" >/dev/null
  sips -z $((size * 2)) $((size * 2)) "$PNG" --out "$SET/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$SET" -o "$ICNS"
