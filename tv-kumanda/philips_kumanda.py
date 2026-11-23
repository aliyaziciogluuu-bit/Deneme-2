#!/usr/bin/env python3
"""
Philips Android TV Kumandası
============================

Philips Android TV / Google TV'ler için telefondan kullanılan kumanda ve Ambilight paneli.

Çalıştırma (bilgisayarda veya Android telefonda Termux ile, TV ile AYNI Wi-Fi ağında):

    python3 philips_kumanda.py

Sonra telefonun tarayıcısında ekranda yazan adresi açın (ör. http://192.168.1.20:8000).
İlk açılışta TV'yi bulup eşleştirirsiniz; TV ekranında çıkan 4 haneli kodu girmeniz yeterli.

Yalnızca Python 3'ün kendi kütüphanelerini kullanır, ek kurulum gerekmez.
"""

import argparse
import base64
import hashlib
import hmac
import ipaddress
import json
import os
import random
import socket
import ssl
import string
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AYAR_DOSYASI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "philips_ayar.json")
TV_PORTU = 1926
API_SURUMU = 6

# Philips JointSpace eşleştirmesinde kullanılan, tüm istemcilerin paylaştığı herkese açık anahtar.
PAYLASILAN_ANAHTAR = base64.b64decode(
    "ZmVay1EQVFOaZhwQ4Kv81ypLAZNczV9sG4KkseXWn1NEk6cXmPKO/MCa9sryslvLCFMnNe4Z4CPXzToowvhHvA=="
)


class TvHatasi(Exception):
    """Kullanıcıya gösterilecek Türkçe hata mesajı."""


# --------------------------------------------------------------------------- TV istemcisi


class PhilipsTv:
    def __init__(self, adres, cihaz_kimligi=None, yetki_anahtari=None):
        self.ip, self.port = adres_ayir(adres)
        self.cihaz_kimligi = cihaz_kimligi
        self.yetki_anahtari = yetki_anahtari
        self._eslesme_zamani = None

    @property
    def taban(self):
        return f"https://{self.ip}:{self.port}/{API_SURUMU}/"

    def _acici(self):
        # TV kendi imzaladığı bir sertifika kullanır; yalnızca evdeki TV'ye bağlandığımız için
        # sertifika doğrulaması bu bağlantıda kapatılır.
        baglam = ssl.create_default_context()
        baglam.check_hostname = False
        baglam.verify_mode = ssl.CERT_NONE
        isleyiciler = [
            urllib.request.ProxyHandler({}),  # TV ev ağında; sistem proxy'sini atla
            urllib.request.HTTPSHandler(context=baglam),
        ]
        if self.cihaz_kimligi and self.yetki_anahtari:
            sifreler = urllib.request.HTTPPasswordMgrWithDefaultRealm()
            sifreler.add_password(None, f"https://{self.ip}:{self.port}/", self.cihaz_kimligi, self.yetki_anahtari)
            isleyiciler.append(urllib.request.HTTPDigestAuthHandler(sifreler))
        return urllib.request.build_opener(*isleyiciler)

    def istek(self, yol, veri=None, zaman_asimi=6):
        govde = json.dumps(veri).encode() if veri is not None else None
        istek = urllib.request.Request(
            self.taban + yol,
            data=govde,
            method="POST" if govde is not None else "GET",
            headers={"Content-Type": "application/json"},
        )
        try:
            with self._acici().open(istek, timeout=zaman_asimi) as yanit:
                icerik = yanit.read()
        except urllib.error.HTTPError as h:
            if h.code == 401:
                raise TvHatasi("TV bu kumandayı tanımıyor. Ayarlar'dan yeniden eşleştirin.") from h
            if h.code == 404:
                raise TvHatasi("Bu özellik TV'nizde desteklenmiyor.") from h
            raise TvHatasi(f"TV isteği reddetti (HTTP {h.code}).") from h
        except (urllib.error.URLError, socket.timeout, OSError) as h:
            raise TvHatasi(
                "TV'ye ulaşılamadı. TV açık mı ve aynı Wi-Fi ağında mı? "
                "(TV kapalıyken uzaktan açmak için: TV Ayarları > Kablosuz ve ağlar > "
                "'Wi-Fi ile aç (WoWLAN)' seçeneğini açın.)"
            ) from h
        if not icerik.strip():
            return {}
        try:
            return json.loads(icerik)
        except ValueError:
            return {}

    # ---- eşleştirme

    def _cihaz(self):
        return {
            "device_name": "telefon",
            "device_os": "Android",
            "app_name": "Philips Kumanda",
            "app_id": "app.id",
            "id": self.cihaz_kimligi,
            "type": "native",
        }

    def eslesme_baslat(self):
        self.cihaz_kimligi = "".join(random.choices(string.ascii_letters + string.digits, k=16))
        self.yetki_anahtari = None
        yanit = self.istek("pair/request", {"scope": ["read", "write", "control"], "device": self._cihaz()})
        if yanit.get("error_id") != "SUCCESS":
            raise TvHatasi(f"TV eşleşmeyi başlatmadı ({yanit.get('error_id', 'bilinmeyen yanıt')}).")
        self.yetki_anahtari = yanit["auth_key"]
        self._eslesme_zamani = yanit["timestamp"]

    def eslesme_bitir(self, pin):
        if self._eslesme_zamani is None:
            raise TvHatasi("Önce eşleştirmeyi başlatın.")
        pin = str(pin).strip()
        imza = hmac.new(
            PAYLASILAN_ANAHTAR, (str(self._eslesme_zamani) + pin).encode(), hashlib.sha1
        ).hexdigest()
        veri = {
            "auth": {
                "auth_AppId": "1",
                "pin": pin,
                "auth_timestamp": self._eslesme_zamani,
                "auth_signature": imza,
            },
            "device": self._cihaz(),
        }
        try:
            yanit = self.istek("pair/grant", veri)
        except TvHatasi as h:
            raise TvHatasi("Kod kabul edilmedi. Kodu kontrol edip tekrar deneyin. " + str(h)) from h
        if yanit.get("error_id", "SUCCESS") != "SUCCESS":
            raise TvHatasi(f"Kod kabul edilmedi ({yanit['error_id']}).")
        self._eslesme_zamani = None

    # ---- komutlar

    def tus(self, tus_adi):
        self.istek("input/key", {"key": tus_adi})

    def ses_oku(self):
        return self.istek("audio/volume")

    def ses_ayarla(self, seviye=None, sessiz=None):
        simdiki = self.ses_oku()
        if seviye is not None:
            enaz, encok = simdiki.get("min", 0), simdiki.get("max", 60)
            simdiki["current"] = max(enaz, min(encok, int(seviye)))
        if sessiz is not None:
            simdiki["muted"] = bool(sessiz)
        self.istek("audio/volume", {"muted": simdiki.get("muted", False), "current": simdiki.get("current", 0)})
        return simdiki

    def guc_durumu(self):
        return self.istek("powerstate").get("powerstate", "Bilinmiyor")

    def guc(self, durum):
        try:
            self.istek("powerstate", {"powerstate": durum})
        except TvHatasi:
            if durum == "Standby":
                self.tus("Standby")
            else:
                raise

    def ambilight_ac_kapat(self, acik):
        try:
            self.istek("ambilight/power", {"power": "On" if acik else "Off"})
        except TvHatasi:
            if acik:
                self.ambilight_stil("FOLLOW_VIDEO", "STANDARD")
            else:
                self.istek("ambilight/currentconfiguration", {"styleName": "OFF", "isExpert": False})

    def ambilight_stil(self, stil, ayar):
        self.istek("ambilight/mode", {"current": "internal"})
        self.istek(
            "ambilight/currentconfiguration",
            {"styleName": stil, "isExpert": False, "menuSetting": ayar},
        )

    def ambilight_renk(self, r, g, b):
        try:
            self.istek("ambilight/power", {"power": "On"})
        except TvHatasi:
            pass
        self.istek("ambilight/mode", {"current": "manual"})
        self.istek("ambilight/cached", {"r": int(r), "g": int(g), "b": int(b)})

    def uygulamalar(self):
        liste = self.istek("applications", zaman_asimi=10).get("applications", [])
        sonuc = []
        for uygulama in liste:
            if uygulama.get("label") and uygulama.get("intent"):
                sonuc.append({"ad": uygulama["label"], "intent": uygulama["intent"]})
        sonuc.sort(key=lambda u: u["ad"].casefold())
        return sonuc

    def uygulama_ac(self, intent):
        self.istek("activities/launch", {"intent": intent})


def adres_ayir(adres):
    adres = str(adres).strip()
    if adres.count(":") == 1:
        ip, port = adres.split(":")
        return ip.strip(), int(port)
    return adres, TV_PORTU


# --------------------------------------------------------------------------- ağ taraması


def yerel_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))  # paket gönderilmez, sadece çıkış arayüzü seçilir
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def tv_ara():
    ip = yerel_ip()
    ag = ipaddress.ip_network(f"{ip}/24", strict=False)

    def dene(aday):
        aday = str(aday)
        try:
            with socket.create_connection((aday, TV_PORTU), timeout=0.6):
                pass
        except OSError:
            return None
        ad = "Philips TV"
        try:
            bilgi = PhilipsTv(aday).istek("system", zaman_asimi=3)
            ad = bilgi.get("name") or ad
        except TvHatasi:
            pass
        return {"ip": aday, "ad": ad}

    with ThreadPoolExecutor(max_workers=64) as havuz:
        bulunanlar = [b for b in havuz.map(dene, ag.hosts()) if b]
    return bulunanlar


# --------------------------------------------------------------------------- uygulama durumu


class Durum:
    def __init__(self):
        self.kilit = threading.Lock()
        self.tv = None
        self.ad = ""
        self.eslesmis = False
        self.uyku_bitis = None
        self.uyku_zamanlayici = None
        self.uygulama_onbellek = []
        self.bekleyen = None  # eşleştirmesi süren (tv, ad)
        self.yukle()

    def yukle(self):
        try:
            with open(AYAR_DOSYASI, encoding="utf-8") as f:
                ayar = json.load(f)
            self.tv = PhilipsTv(ayar["adres"], ayar["cihaz_kimligi"], ayar["yetki_anahtari"])
            self.ad = ayar.get("ad", "Philips TV")
            self.eslesmis = True
        except (OSError, ValueError, KeyError):
            pass

    def kaydet(self):
        ayar = {
            "adres": f"{self.tv.ip}:{self.tv.port}",
            "ad": self.ad,
            "cihaz_kimligi": self.tv.cihaz_kimligi,
            "yetki_anahtari": self.tv.yetki_anahtari,
        }
        with open(AYAR_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(ayar, f, ensure_ascii=False, indent=2)

    def sifirla(self):
        self.uyku_iptal()
        self.tv, self.ad, self.eslesmis, self.uygulama_onbellek = None, "", False, []
        try:
            os.remove(AYAR_DOSYASI)
        except OSError:
            pass

    def eslesmis_tv(self):
        if not self.eslesmis or self.tv is None:
            raise TvHatasi("Önce TV'yi eşleştirin.")
        return self.tv

    # ---- uyku zamanlayıcısı

    def uyku_kur(self, dakika):
        self.uyku_iptal()
        if dakika <= 0:
            return
        self.uyku_bitis = time.time() + dakika * 60
        self.uyku_zamanlayici = threading.Timer(dakika * 60, self._uyku_vakti)
        self.uyku_zamanlayici.daemon = True
        self.uyku_zamanlayici.start()

    def uyku_iptal(self):
        if self.uyku_zamanlayici:
            self.uyku_zamanlayici.cancel()
        self.uyku_zamanlayici, self.uyku_bitis = None, None

    def _uyku_vakti(self):
        self.uyku_zamanlayici, self.uyku_bitis = None, None
        tv = self.tv
        if not tv:
            return
        try:
            if tv.guc_durumu() == "On":
                try:
                    tv.ambilight_ac_kapat(False)
                except TvHatasi:
                    pass
                tv.guc("Standby")
        except TvHatasi as h:
            print("Uyku zamanlayıcısı TV'yi kapatamadı:", h)

    def uyku_kalan(self):
        if self.uyku_bitis is None:
            return None
        return max(0, int(self.uyku_bitis - time.time()))


DURUM = Durum()

IZINLI_TUSLAR = {
    "Standby", "Home", "Back", "Confirm", "CursorUp", "CursorDown", "CursorLeft", "CursorRight",
    "VolumeUp", "VolumeDown", "Mute", "ChannelStepUp", "ChannelStepDown", "PlayPause", "Play",
    "Pause", "Stop", "FastForward", "Rewind", "Next", "Previous", "Options", "Info", "Source",
    "Adjust", "WatchTV", "Find", "AmbilightOnOff", "Online", "Subtitle", "Teletext",
    "RedColour", "GreenColour", "YellowColour", "BlueColour",
    "Digit0", "Digit1", "Digit2", "Digit3", "Digit4", "Digit5", "Digit6", "Digit7", "Digit8", "Digit9",
}

AMBILIGHT_STILLERI = {
    ("FOLLOW_VIDEO", "STANDARD"), ("FOLLOW_VIDEO", "NATURAL"), ("FOLLOW_VIDEO", "IMMERSIVE"),
    ("FOLLOW_VIDEO", "GAME"), ("FOLLOW_VIDEO", "COMFORT"), ("FOLLOW_VIDEO", "RELAX"),
    ("FOLLOW_AUDIO", "ENERGY_ADAPTIVE_BRIGHTNESS"), ("FOLLOW_AUDIO", "ENERGY_ADAPTIVE_COLORS"),
    ("FOLLOW_AUDIO", "VU_METER"), ("FOLLOW_AUDIO", "SPECTRUM_ANALYZER"),
    ("FOLLOW_COLOR", "HOT_LAVA"), ("FOLLOW_COLOR", "DEEP_WATER"), ("FOLLOW_COLOR", "FRESH_NATURE"),
}


# --------------------------------------------------------------------------- yerel web sunucusu


def api(yol, veri):
    d = DURUM
    if yol == "durum":
        return {"eslesmis": d.eslesmis, "ad": d.ad, "ip": d.tv.ip if d.tv else "", "uyku": d.uyku_kalan()}

    if yol == "tara":
        return {"tvler": tv_ara()}

    if yol == "eslesme/baslat":
        adres = (veri.get("ip") or "").strip()
        if not adres:
            raise TvHatasi("TV'nin IP adresini girin.")
        tv = PhilipsTv(adres)
        tv.eslesme_baslat()
        with d.kilit:
            d.bekleyen = (tv, veri.get("ad") or "Philips TV")
        return {"tamam": True}

    if yol == "eslesme/bitir":
        if d.bekleyen is None:
            raise TvHatasi("Önce eşleştirmeyi başlatın.")
        tv, ad = d.bekleyen
        tv.eslesme_bitir(veri.get("pin", ""))
        with d.kilit:
            d.sifirla()
            d.tv, d.ad, d.eslesmis, d.bekleyen = tv, ad, True, None
            d.kaydet()
        return {"tamam": True}

    if yol == "eslesme/sil":
        with d.kilit:
            d.sifirla()
        return {"tamam": True}

    tv = d.eslesmis_tv()

    if yol == "tus":
        tus = veri.get("tus")
        if tus not in IZINLI_TUSLAR:
            raise TvHatasi("Bilinmeyen tuş.")
        tv.tus(tus)
        return {"tamam": True}

    if yol == "ses":
        if "seviye" in veri or "sessiz" in veri:
            return tv.ses_ayarla(veri.get("seviye"), veri.get("sessiz"))
        return tv.ses_oku()

    if yol == "guc":
        if tv.guc_durumu() == "On":
            tv.guc("Standby")
            return {"durum": "Standby"}
        tv.guc("On")
        return {"durum": "On"}

    if yol == "ambilight":
        islem = veri.get("islem")
        if islem == "renk":
            renk = [max(0, min(255, int(veri.get(k, 0)))) for k in ("r", "g", "b")]
            tv.ambilight_renk(*renk)
        elif islem == "stil":
            stil, ayar = veri.get("stil"), veri.get("ayar")
            if (stil, ayar) not in AMBILIGHT_STILLERI:
                raise TvHatasi("Bilinmeyen Ambilight stili.")
            tv.ambilight_stil(stil, ayar)
        elif islem in ("ac", "kapat"):
            tv.ambilight_ac_kapat(islem == "ac")
        else:
            raise TvHatasi("Bilinmeyen Ambilight işlemi.")
        return {"tamam": True}

    if yol == "uygulamalar":
        if veri.get("yenile") or not d.uygulama_onbellek:
            d.uygulama_onbellek = tv.uygulamalar()
        return {"uygulamalar": [{"no": i, "ad": u["ad"]} for i, u in enumerate(d.uygulama_onbellek)]}

    if yol == "uygulama-ac":
        try:
            uygulama = d.uygulama_onbellek[int(veri.get("no"))]
        except (TypeError, ValueError, IndexError):
            raise TvHatasi("Uygulama listesi eskimiş, yenileyin.")
        tv.uygulama_ac(uygulama["intent"])
        return {"tamam": True}

    if yol == "uyku":
        dakika = int(veri.get("dakika", 0))
        d.uyku_kur(dakika)
        return {"uyku": d.uyku_kalan()}

    raise LookupError(yol)


class Isleyici(BaseHTTPRequestHandler):
    server_version = "PhilipsKumanda/1.0"

    def log_message(self, bicim, *args):
        pass  # terminali sessiz tut

    def _gonder(self, kod, govde, tur="application/json; charset=utf-8"):
        if isinstance(govde, (dict, list)):
            govde = json.dumps(govde, ensure_ascii=False)
        veri = govde.encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", tur)
        self.send_header("Content-Length", str(len(veri)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(veri)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._gonder(200, SAYFA, "text/html; charset=utf-8")
        elif self.path == "/manifest.webmanifest":
            self._gonder(200, MANIFEST, "application/manifest+json; charset=utf-8")
        elif self.path.startswith("/api/"):
            self._api({})
        else:
            self._gonder(404, {"hata": "Bulunamadı"})

    def do_POST(self):
        if not self.path.startswith("/api/"):
            self._gonder(404, {"hata": "Bulunamadı"})
            return
        try:
            uzunluk = int(self.headers.get("Content-Length") or 0)
            veri = json.loads(self.rfile.read(uzunluk) or b"{}") if uzunluk else {}
            if not isinstance(veri, dict):
                raise ValueError
        except ValueError:
            self._gonder(400, {"hata": "Geçersiz istek"})
            return
        self._api(veri)

    def _api(self, veri):
        try:
            self._gonder(200, api(self.path[len("/api/"):], veri))
        except TvHatasi as h:
            self._gonder(502, {"hata": str(h)})
        except LookupError:
            self._gonder(404, {"hata": "Bilinmeyen işlem"})
        except (TypeError, ValueError):
            self._gonder(400, {"hata": "Geçersiz değer"})


MANIFEST = json.dumps(
    {
        "name": "TV Kumandası",
        "short_name": "Kumanda",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0e1116",
        "theme_color": "#0e1116",
        "icons": [],
    },
    ensure_ascii=False,
)

SAYFA = r"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover, user-scalable=no">
<meta name="theme-color" content="#0e1116">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<link rel="manifest" href="/manifest.webmanifest">
<title>TV Kumandası</title>
<style>
:root{
  --zemin:#0e1116; --kart:#181c24; --tus:#232936; --tus-bas:#2f3748; --yazi:#e8ebf1; --soluk:#8a93a6;
  --vurgu:#4f8cff; --kirmizi:#e5484d; --yesil:#30a46c; --kenar:#2a3040;
}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;background:var(--zemin);color:var(--yazi);font:16px/1.4 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
body{padding:12px 16px calc(24px + env(safe-area-inset-bottom));max-width:480px;margin:0 auto;user-select:none}
header{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}
header h1{font-size:18px;margin:0;font-weight:600}
header small{color:var(--soluk);display:block;font-size:12px;font-weight:400}
.kart{background:var(--kart);border:1px solid var(--kenar);border-radius:18px;padding:14px;margin-bottom:12px}
.kart h2{font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--soluk);margin:0 0 10px;font-weight:600}
button{font:inherit;color:var(--yazi);background:var(--tus);border:0;border-radius:14px;min-height:48px;padding:0 12px;cursor:pointer;touch-action:manipulation}
button:active{background:var(--tus-bas);transform:scale(.97)}
button.vurgu{background:var(--vurgu);color:#fff}
button.kirmizi{background:var(--kirmizi);color:#fff}
button.kucuk{min-height:36px;font-size:14px;border-radius:10px}
.satir{display:flex;gap:8px}
.satir>*{flex:1}
.izgara{display:grid;gap:8px}
.ust{grid-template-columns:repeat(4,1fr)}
.ust button{font-size:13px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;min-height:58px}
.ust b{font-size:20px;font-weight:400}
.yon{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;max-width:300px;margin:4px auto 12px}
.yon button{min-height:68px;font-size:22px}
.yon .ok{background:var(--vurgu);color:#fff;border-radius:50%;aspect-ratio:1;font-size:17px;font-weight:600}
.cift{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.dikey{display:flex;flex-direction:column;gap:8px;align-items:stretch}
.dikey span{text-align:center;color:var(--soluk);font-size:13px}
.oynat{grid-template-columns:repeat(4,1fr)}
.oynat button{font-size:18px}
.rakam{grid-template-columns:repeat(3,1fr)}
.renkler{grid-template-columns:repeat(4,1fr)}
.renkler button{min-height:52px;font-size:12px;font-weight:600;color:#fff;text-shadow:0 1px 2px #0008}
.stiller{grid-template-columns:repeat(2,1fr)}
.stiller button{font-size:14px}
.uygulamalar{grid-template-columns:repeat(3,1fr)}
.uygulamalar button{font-size:13px;min-height:56px;line-height:1.2;overflow:hidden;text-overflow:ellipsis}
input[type=range]{width:100%;accent-color:var(--vurgu)}
input[type=color]{width:100%;height:48px;border:0;border-radius:14px;background:var(--tus);padding:4px}
input[type=text],input[type=tel]{width:100%;font:inherit;color:var(--yazi);background:var(--tus);border:1px solid var(--kenar);border-radius:12px;padding:12px;margin:6px 0}
details summary{cursor:pointer;color:var(--soluk);font-size:14px;padding:4px 0;list-style:none}
details summary::before{content:"▸ "}
details[open] summary::before{content:"▾ "}
.etiket{display:flex;justify-content:space-between;font-size:14px;color:var(--soluk);margin:8px 0 2px}
.bilgi{color:var(--soluk);font-size:14px;margin:6px 0}
.gizli{display:none!important}
.liste button{width:100%;margin-bottom:8px;text-align:left;display:flex;justify-content:space-between;align-items:center}
.liste small{color:var(--soluk)}
#mesaj{position:fixed;left:50%;bottom:calc(20px + env(safe-area-inset-bottom));transform:translateX(-50%) translateY(150%);background:#2b3142;color:var(--yazi);padding:12px 16px;border-radius:12px;max-width:min(440px,calc(100% - 32px));font-size:14px;transition:transform .25s;box-shadow:0 8px 24px #0008;z-index:9}
#mesaj.goster{transform:translateX(-50%) translateY(0)}
#mesaj.hata{background:#5a1f24}
.uyku-durum{color:var(--yesil);font-size:14px;text-align:center;margin-top:8px}
</style>
</head>
<body>

<header>
  <h1>📺 TV Kumandası<small id="tvAdi">Philips</small></h1>
  <button class="kucuk" id="ayarDugme" aria-label="Ayarlar">⚙️</button>
</header>

<!-- ============ EŞLEŞTİRME ============ -->
<section id="eslesme" class="gizli">
  <div class="kart">
    <h2>1. TV'yi bul</h2>
    <p class="bilgi">TV açık olsun ve bu cihazla aynı Wi-Fi ağına bağlı olsun.</p>
    <button class="vurgu" id="taraDugme" style="width:100%">🔍 Ağda TV ara</button>
    <div id="bulunanlar" class="liste" style="margin-top:10px"></div>
    <details>
      <summary>IP adresini elle gir</summary>
      <p class="bilgi">TV'de: Ayarlar → Kablosuz ve ağlar → Kablolu veya Wi-Fi → Ağ ayarlarını göster</p>
      <input type="text" id="elleIp" inputmode="decimal" placeholder="ör. 192.168.1.35">
      <button id="elleDugme" style="width:100%">Bu TV ile eşleştir</button>
    </details>
  </div>
  <div class="kart gizli" id="pinKart">
    <h2>2. TV'deki kodu gir</h2>
    <p class="bilgi">TV ekranında 4 haneli bir kod çıktı. Kodu buraya yazın (60 saniye içinde).</p>
    <input type="tel" id="pin" inputmode="numeric" maxlength="6" placeholder="Kod" style="font-size:24px;text-align:center;letter-spacing:.3em">
    <button class="vurgu" id="pinDugme" style="width:100%">Eşleştir</button>
  </div>
</section>

<!-- ============ KUMANDA ============ -->
<main id="kumanda" class="gizli">

  <div class="kart">
    <div class="izgara ust">
      <button id="gucDugme" class="kirmizi"><b>⏻</b>Güç</button>
      <button data-tus="Home"><b>⌂</b>Ana ekran</button>
      <button data-tus="Source"><b>⇄</b>Kaynak</button>
      <button data-tus="Options"><b>☰</b>Seçenek</button>
    </div>
  </div>

  <div class="kart">
    <div class="yon">
      <span></span><button data-tus="CursorUp" aria-label="Yukarı">▲</button><span></span>
      <button data-tus="CursorLeft" aria-label="Sol">◀</button>
      <button data-tus="Confirm" class="ok">OK</button>
      <button data-tus="CursorRight" aria-label="Sağ">▶</button>
      <span></span><button data-tus="CursorDown" aria-label="Aşağı">▼</button><span></span>
    </div>
    <div class="satir">
      <button data-tus="Back">↩ Geri</button>
      <button data-tus="Info">ⓘ Bilgi</button>
      <button data-tus="WatchTV">📡 TV</button>
    </div>
  </div>

  <div class="kart">
    <div class="cift">
      <div class="dikey">
        <span>SES <b id="sesSeviye"></b></span>
        <button data-tus="VolumeUp" data-tekrar>＋</button>
        <button id="sessizDugme">🔇 Sessiz</button>
        <button data-tus="VolumeDown" data-tekrar>－</button>
      </div>
      <div class="dikey">
        <span>KANAL</span>
        <button data-tus="ChannelStepUp">▲</button>
        <button data-tus="Find">≡ Liste</button>
        <button data-tus="ChannelStepDown">▼</button>
      </div>
    </div>
    <input type="range" id="sesKaydirac" min="0" max="60" value="0" style="margin-top:12px" aria-label="Ses seviyesi">
  </div>

  <div class="kart">
    <div class="izgara oynat">
      <button data-tus="Rewind" aria-label="Geri sar">⏪</button>
      <button data-tus="PlayPause" aria-label="Oynat / Duraklat">⏯</button>
      <button data-tus="Stop" aria-label="Durdur">⏹</button>
      <button data-tus="FastForward" aria-label="İleri sar">⏩</button>
    </div>
    <details style="margin-top:10px">
      <summary>Rakamlar ve renkli tuşlar</summary>
      <div class="izgara rakam" style="margin-top:8px">
        <button data-tus="Digit1">1</button><button data-tus="Digit2">2</button><button data-tus="Digit3">3</button>
        <button data-tus="Digit4">4</button><button data-tus="Digit5">5</button><button data-tus="Digit6">6</button>
        <button data-tus="Digit7">7</button><button data-tus="Digit8">8</button><button data-tus="Digit9">9</button>
        <button data-tus="Subtitle">Altyazı</button><button data-tus="Digit0">0</button><button data-tus="Teletext">Teletekst</button>
      </div>
      <div class="izgara oynat" style="margin-top:8px">
        <button data-tus="RedColour" style="background:#c62828"></button>
        <button data-tus="GreenColour" style="background:#2e7d32"></button>
        <button data-tus="YellowColour" style="background:#f9a825"></button>
        <button data-tus="BlueColour" style="background:#1565c0"></button>
      </div>
    </details>
  </div>

  <div class="kart">
    <h2>✨ <span lang="en">Ambilight</span></h2>
    <div class="satir" style="margin-bottom:8px">
      <button data-ambi="ac">Aç</button>
      <button data-ambi="kapat">Kapat</button>
    </div>
    <div class="izgara stiller">
      <button data-stil="FOLLOW_VIDEO" data-ayar="STANDARD">🎬 Videoyu takip et</button>
      <button data-stil="FOLLOW_VIDEO" data-ayar="RELAX">😌 Rahat (göz dostu)</button>
      <button data-stil="FOLLOW_VIDEO" data-ayar="IMMERSIVE">🔥 Canlı</button>
      <button data-stil="FOLLOW_VIDEO" data-ayar="GAME">🎮 Oyun</button>
      <button data-stil="FOLLOW_AUDIO" data-ayar="ENERGY_ADAPTIVE_COLORS">🎉 Müziğe göre</button>
      <button data-stil="FOLLOW_AUDIO" data-ayar="SPECTRUM_ANALYZER">🎵 Ekolayzır</button>
      <button data-stil="FOLLOW_COLOR" data-ayar="HOT_LAVA">🌋 Lav</button>
      <button data-stil="FOLLOW_COLOR" data-ayar="DEEP_WATER">🌊 Okyanus</button>
    </div>
    <h2 style="margin-top:14px">Sabit renk</h2>
    <div class="izgara renkler">
      <button data-renk="255,140,40" style="background:#ff8c28">Sinema</button>
      <button data-renk="120,0,0" style="background:#780000">Gece</button>
      <button data-renk="255,255,255" style="background:#d9d9d9;color:#111;text-shadow:none">Beyaz</button>
      <button data-renk="255,190,120" style="background:#ffbe78;color:#111;text-shadow:none">Sıcak</button>
      <button data-renk="0,90,255" style="background:#005aff">Mavi</button>
      <button data-renk="150,0,255" style="background:#9600ff">Mor</button>
      <button data-renk="0,200,80" style="background:#00c850">Yeşil</button>
      <button data-renk="255,0,120" style="background:#ff0078">Pembe</button>
    </div>
    <div class="etiket"><span>Kendi rengin</span></div>
    <input type="color" id="renkSecici" value="#4f8cff" aria-label="Renk seç">
    <div class="etiket"><span>Parlaklık</span><span id="parlaklikYazi">100%</span></div>
    <input type="range" id="parlaklik" min="5" max="100" value="100" aria-label="Parlaklık">
  </div>

  <div class="kart">
    <h2>📱 Uygulamalar</h2>
    <div id="uygulamaListesi" class="izgara uygulamalar"><span class="bilgi">Yükleniyor…</span></div>
    <button class="kucuk" id="uygulamaYenile" style="margin-top:8px;width:100%">↻ Listeyi yenile</button>
  </div>

  <div class="kart">
    <h2>🌙 Uyku zamanlayıcısı</h2>
    <div class="satir">
      <button data-uyku="15">15 dk</button>
      <button data-uyku="30">30 dk</button>
      <button data-uyku="60">1 sa</button>
      <button data-uyku="90">1,5 sa</button>
    </div>
    <div id="uykuDurum" class="uyku-durum gizli"></div>
    <button class="kucuk gizli" id="uykuIptal" style="width:100%;margin-top:8px">Zamanlayıcıyı iptal et</button>
    <p class="bilgi">Süre dolunca Ambilight ve TV kapanır. Bu program çalışır durumda kalmalı.</p>
  </div>
</main>

<!-- ============ AYARLAR ============ -->
<section id="ayarlar" class="gizli">
  <div class="kart">
    <h2>Ayarlar</h2>
    <p class="bilgi" id="ayarBilgi"></p>
    <button id="yenidenEslestir" style="width:100%;margin-bottom:8px">Başka TV ile eşleştir</button>
    <button class="kirmizi" id="eslesmeSil" style="width:100%">Eşleştirmeyi sil</button>
  </div>
  <button id="ayarKapat" style="width:100%">← Kumandaya dön</button>
</section>

<div id="mesaj" role="status"></div>

<script>
const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);
let durum = {eslesmis:false};
let secilenAd = "";

function mesaj(yazi, hata){
  const m = $("#mesaj");
  m.textContent = yazi;
  m.classList.toggle("hata", !!hata);
  m.classList.add("goster");
  clearTimeout(mesaj.z);
  mesaj.z = setTimeout(() => m.classList.remove("goster"), hata ? 5000 : 1800);
}

async function api(yol, veri){
  const ayar = veri === undefined ? {} : {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(veri)};
  let yanit;
  try { yanit = await fetch("/api/" + yol, ayar); }
  catch(e){ throw new Error("Kumanda programına ulaşılamadı. Bilgisayardaki program açık mı?"); }
  const j = await yanit.json().catch(() => ({}));
  if (!yanit.ok) throw new Error(j.hata || "Bir hata oluştu");
  return j;
}

async function dene(is, basari){
  try { const s = await is(); if (basari) mesaj(basari); return s; }
  catch(e){ mesaj(e.message, true); }
}

function goster(bolum){
  for (const id of ["eslesme","kumanda","ayarlar"]) $("#"+id).classList.toggle("gizli", id !== bolum);
}

async function baslat(){
  durum = await dene(() => api("durum")) || {eslesmis:false};
  $("#tvAdi").textContent = durum.eslesmis ? `${durum.ad} · ${durum.ip}` : "Eşleştirilmedi";
  if (!durum.eslesmis){ goster("eslesme"); return; }
  goster("kumanda");
  sesOku();
  uygulamalariYukle(false);
  uykuGoster(durum.uyku);
}

/* ---------- eşleştirme ---------- */
$("#taraDugme").onclick = async () => {
  const d = $("#taraDugme"); d.disabled = true; d.textContent = "Aranıyor… (10–20 sn)";
  const kutu = $("#bulunanlar"); kutu.innerHTML = "";
  const s = await dene(() => api("tara", {}));
  d.disabled = false; d.textContent = "🔍 Ağda TV ara";
  if (!s) return;
  if (!s.tvler.length){ kutu.innerHTML = '<p class="bilgi">TV bulunamadı. TV açık mı? IP adresini elle girmeyi deneyin.</p>'; return; }
  for (const tv of s.tvler){
    const b = document.createElement("button");
    b.innerHTML = `<span></span><small></small>`;
    b.firstChild.textContent = tv.ad; b.lastChild.textContent = tv.ip;
    b.onclick = () => eslesmeBaslat(tv.ip, tv.ad);
    kutu.appendChild(b);
  }
};
$("#elleDugme").onclick = () => eslesmeBaslat($("#elleIp").value, "Philips TV");

async function eslesmeBaslat(ip, ad){
  secilenAd = ad;
  const s = await dene(() => api("eslesme/baslat", {ip, ad}));
  if (!s) return;
  $("#pinKart").classList.remove("gizli");
  $("#pin").value = ""; $("#pin").focus();
  $("#pinKart").scrollIntoView({behavior:"smooth"});
}
$("#pinDugme").onclick = async () => {
  const s = await dene(() => api("eslesme/bitir", {pin: $("#pin").value}), "Eşleşti! 🎉");
  if (s){ $("#pinKart").classList.add("gizli"); baslat(); }
};
$("#pin").addEventListener("keydown", e => { if (e.key === "Enter") $("#pinDugme").click(); });

/* ---------- tuşlar ---------- */
function titret(){ if (navigator.vibrate) navigator.vibrate(12); }
async function tus(ad){ titret(); await dene(() => api("tus", {tus: ad})); if (ad.startsWith("Volume")) sesOkuGecikmeli(); }

for (const b of $$("[data-tus]")){
  if (b.hasAttribute("data-tekrar")){
    // basılı tutunca tekrar et (ses)
    let z1, z2;
    const bitir = () => { clearTimeout(z1); clearInterval(z2); };
    b.addEventListener("pointerdown", e => { e.preventDefault(); tus(b.dataset.tus); z1 = setTimeout(() => z2 = setInterval(() => tus(b.dataset.tus), 180), 450); });
    for (const o of ["pointerup","pointerleave","pointercancel"]) b.addEventListener(o, bitir);
  } else {
    b.onclick = () => tus(b.dataset.tus);
  }
}

$("#gucDugme").onclick = async () => {
  titret();
  const s = await dene(() => api("guc", {}));
  if (s) mesaj(s.durum === "On" ? "TV açılıyor" : "TV kapatıldı");
};

/* ---------- ses ---------- */
let sesBilgi = null;
async function sesOku(){
  try {
    sesBilgi = await api("ses");
    const k = $("#sesKaydirac");
    k.min = sesBilgi.min ?? 0; k.max = sesBilgi.max ?? 60; k.value = sesBilgi.current ?? 0;
    $("#sesSeviye").textContent = sesBilgi.muted ? "🔇" : (sesBilgi.current ?? "");
  } catch(e){ $("#sesSeviye").textContent = ""; }
}
function sesOkuGecikmeli(){ clearTimeout(sesOkuGecikmeli.z); sesOkuGecikmeli.z = setTimeout(sesOku, 400); }
$("#sesKaydirac").oninput = e => { $("#sesSeviye").textContent = e.target.value; };
$("#sesKaydirac").onchange = async e => { await dene(() => api("ses", {seviye: +e.target.value})); sesOku(); };
$("#sessizDugme").onclick = async () => {
  titret();
  const sessiz = !(sesBilgi && sesBilgi.muted);
  await dene(() => api("ses", {sessiz}));
  sesOku();
};

/* ---------- ambilight ---------- */
for (const b of $$("[data-ambi]")) b.onclick = () => dene(() => api("ambilight", {islem: b.dataset.ambi}), b.dataset.ambi === "ac" ? "Ambilight açıldı" : "Ambilight kapatıldı");
for (const b of $$("[data-stil]")) b.onclick = () => dene(() => api("ambilight", {islem:"stil", stil:b.dataset.stil, ayar:b.dataset.ayar}), b.textContent.trim());

let sonRenk = [255,140,40];
function renkGonder(){
  const p = +$("#parlaklik").value / 100;
  const [r,g,b] = sonRenk.map(x => Math.round(x * p));
  return dene(() => api("ambilight", {islem:"renk", r, g, b}));
}
for (const b of $$("[data-renk]")) b.onclick = () => { sonRenk = b.dataset.renk.split(",").map(Number); titret(); renkGonder(); };
$("#renkSecici").addEventListener("input", e => {
  const h = e.target.value;
  sonRenk = [1,3,5].map(i => parseInt(h.substr(i,2), 16));
  clearTimeout(renkGonder.z); renkGonder.z = setTimeout(renkGonder, 150);
});
$("#parlaklik").addEventListener("input", e => {
  $("#parlaklikYazi").textContent = e.target.value + "%";
  clearTimeout(renkGonder.z); renkGonder.z = setTimeout(renkGonder, 150);
});

/* ---------- uygulamalar ---------- */
async function uygulamalariYukle(yenile){
  const kutu = $("#uygulamaListesi");
  try {
    const s = await api("uygulamalar", {yenile});
    kutu.innerHTML = "";
    if (!s.uygulamalar.length){ kutu.innerHTML = '<span class="bilgi">Uygulama bulunamadı.</span>'; return; }
    for (const u of s.uygulamalar){
      const b = document.createElement("button");
      b.textContent = u.ad;
      b.onclick = () => { titret(); dene(() => api("uygulama-ac", {no: u.no}), u.ad + " açılıyor"); };
      kutu.appendChild(b);
    }
  } catch(e){ kutu.innerHTML = ""; const p = document.createElement("span"); p.className = "bilgi"; p.textContent = e.message; kutu.appendChild(p); }
}
$("#uygulamaYenile").onclick = () => uygulamalariYukle(true);

/* ---------- uyku ---------- */
let uykuBitis = null;
function uykuGoster(saniye){
  uykuBitis = saniye == null ? null : Date.now() + saniye * 1000;
  uykuYaz();
}
function uykuYaz(){
  const yok = uykuBitis == null || uykuBitis <= Date.now();
  $("#uykuDurum").classList.toggle("gizli", yok);
  $("#uykuIptal").classList.toggle("gizli", yok);
  if (yok) return;
  const k = Math.round((uykuBitis - Date.now()) / 1000);
  const dk = Math.floor(k / 60), sn = String(k % 60).padStart(2, "0");
  $("#uykuDurum").textContent = `🌙 TV ${dk}:${sn} sonra kapanacak`;
}
setInterval(uykuYaz, 1000);
for (const b of $$("[data-uyku]")) b.onclick = async () => {
  const s = await dene(() => api("uyku", {dakika: +b.dataset.uyku}), "Zamanlayıcı kuruldu");
  if (s) uykuGoster(s.uyku);
};
$("#uykuIptal").onclick = async () => { const s = await dene(() => api("uyku", {dakika: 0}), "Zamanlayıcı iptal edildi"); if (s) uykuGoster(null); };

/* ---------- ayarlar ---------- */
$("#ayarDugme").onclick = () => {
  if (!durum.eslesmis){ goster("eslesme"); return; }
  $("#ayarBilgi").textContent = `Eşleşmiş TV: ${durum.ad} (${durum.ip})`;
  goster("ayarlar");
};
$("#ayarKapat").onclick = () => goster("kumanda");
$("#yenidenEslestir").onclick = () => goster("eslesme");
$("#eslesmeSil").onclick = async () => {
  if (!confirm("Eşleştirme silinsin mi? Tekrar kullanmak için TV'deki kodla yeniden eşleştirmeniz gerekir.")) return;
  await dene(() => api("eslesme/sil", {}), "Eşleştirme silindi");
  baslat();
};

document.addEventListener("visibilitychange", () => { if (!document.hidden && durum.eslesmis) sesOku(); });
baslat();
</script>
</body>
</html>
"""


# --------------------------------------------------------------------------- başlatma


def main():
    ayristirici = argparse.ArgumentParser(description="Philips Android TV için telefon kumandası")
    ayristirici.add_argument("--port", type=int, default=8000, help="Panelin açılacağı port (varsayılan 8000)")
    secenekler = ayristirici.parse_args()

    try:
        sunucu = ThreadingHTTPServer(("0.0.0.0", secenekler.port), Isleyici)
    except OSError:
        print(f"{secenekler.port} portu kullanımda. Başka port deneyin: python3 philips_kumanda.py --port 8080")
        sys.exit(1)

    ip = yerel_ip()
    print()
    print("  📺 Philips TV kumandası çalışıyor")
    print()
    print(f"  Telefonun tarayıcısında açın:  http://{ip}:{secenekler.port}")
    print(f"  Bu cihazda açmak için:         http://localhost:{secenekler.port}")
    print()
    if DURUM.eslesmis:
        print(f"  Eşleşmiş TV: {DURUM.ad} ({DURUM.tv.ip})")
    else:
        print("  Henüz TV eşleştirilmedi; sayfayı açınca adım adım eşleştirebilirsiniz.")
    print()
    print("  Kapatmak için Ctrl+C")
    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        print("\nKapatılıyor.")
        sunucu.server_close()


if __name__ == "__main__":
    main()
