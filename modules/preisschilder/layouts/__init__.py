"""Layouts der Schildtypen. draw(c, w, h, item) zeichnet ein Schild; Koordinaten in Punkt, Ursprung links unten."""
from . import baelle, helme, schlaeger, ski

DRAW = {"helme": helme.draw, "baelle": baelle.draw, "ski": ski.draw, "snowboard": ski.draw, "schlaeger": schlaeger.draw}
