"""Erzeugt aus referenz/schlaeger-beispiel.json die HTML-Druckseite des Schlaeger-Generators (gleiches CSS und
gleiche Bausteine wie doPrint() in referenz/SOS_Tennis_Generator.html). Dann in Chrome drucken:

  python tools/schlaeger_referenz.py referenz/schlaeger-beispiel.json /tmp/ref.html
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --no-pdf-header-footer \\
      --print-to-pdf=referenz/schlaeger-chrome-druck.pdf file:///tmp/ref.html
"""
import re, json, sys, subprocess
from pathlib import Path
src=open(str(Path(__file__).resolve().parent.parent / 'referenz' / 'SOS_Tennis_Generator.html'),encoding='utf-8').read()
logos=dict(re.findall(r'^\s*(\w+):\s*"data:image/png;base64,([A-Za-z0-9+/=]+)"',src,re.M))
# CSS aus doPrint wortgleich uebernehmen
i=src.index('function doPrint()'); body=src[i:src.index("var gridHTML = '<div",i)]
css=''.join(re.findall(r'"((?:[^"\\]|\\.)*)"',body.split('var css =')[1]))
css=css.replace('\\"','"')
cards=json.load(open(sys.argv[1]))
def fmt(v,u): return f"{v} {u}" if v else "—"
def fmtP(v): return f"{v} €" if v else "—"
def kopf(c):
    p=[]
    if c.get('kopfIn'): p.append(c['kopfIn']+" in²")
    if c.get('kopfCm'): p.append(c['kopfCm']+" cm²")
    return " / ".join(p) or "—"
def bodyhtml(c):
    return ('<div class="pcard-body"><div class="pcard-name">'+c['name']+'</div><div class="pcard-specs">'
      '<div class="psl">Kopf</div><div class="psl">Gewicht</div>'
      '<div class="psv">'+kopf(c)+'</div><div class="psv">'+fmt(c.get('gewicht'),"g")+'</div>'
      '<div class="psl">Besaitung</div><div class="psl">Balance</div>'
      '<div class="psv">'+(c.get('besaitung') or "—")+'</div><div class="psv">'+fmt(c.get('balance'),"mm")+'</div></div>'
      '<div class="pcard-price-row"><div><span class="pcard-sos-label">UNSER PREIS</span><span class="pcard-price">'+fmtP(c.get('preis'))+'</span></div>'
      +('<div class="pcard-uvp-wrap"><span class="pcard-uvp-label">UVP</span><span class="pcard-uvp">'+fmtP(c['uvp'])+'</span></div>' if c.get('uvp') else '')
      +'</div></div>')
g='<div class="grid">'
for c in cards:
    g+=('<div class="pcard"><div class="pcard-header" style="background:'+(c.get('color') or '#555')+';">'
        '<img class="pcard-logo-img" src="data:image/png;base64,'+logos[c['brand']]+'" alt="'+c['brand']+'"></div>'+bodyhtml(c)+'</div>')
g+='</div>'
html='<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Preisschilder SOS Sport</title><style>'+css+'</style></head><body>'+g+'</body></html>'
Path(sys.argv[2]).write_text(html,encoding='utf-8')
