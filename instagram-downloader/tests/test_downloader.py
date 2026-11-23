import sys, unicodedata
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import downloader as d


def test_gueltige_links():
    assert d.pruefe_url("https://www.instagram.com/reel/ABC123/?igsh=xyz") == "https://www.instagram.com/reel/ABC123/"
    assert d.pruefe_url("instagram.com/p/XyZ_9-a") == "https://www.instagram.com/p/XyZ_9-a/"
    assert d.pruefe_url("https://www.instagram.com/sossport/reel/ABC/") == "https://www.instagram.com/reel/ABC/"


def test_ungueltige_links():
    for x in ["", "https://evil.com/reel/ABC/", "https://instagram.com.evil.com/reel/A/",
              "https://www.instagram.com/sossport/", "ftp://instagram.com/p/A/", "file:///etc/passwd"]:
        assert d.pruefe_url(x) is None


def test_mehrere_links_ohne_doppelte():
    text = "https://www.instagram.com/reel/A1/ \n instagram.com/reel/A1 ,https://www.instagram.com/p/B2/ blabla"
    assert d.urls_aus_text(text) == ["https://www.instagram.com/reel/A1/", "https://www.instagram.com/p/B2/"]


def test_nfc():
    zerlegt = unicodedata.normalize("NFD", "Müller")
    assert d.dateiname_nfc(zerlegt) == "Müller"


def test_optionen(tmp_path):
    o = d.optionen(tmp_path, "Safari")
    assert o["cookiesfrombrowser"] == ("safari",) and o["noplaylist"]
    assert "cookiesfrombrowser" not in d.optionen(tmp_path, "Keiner")
