#!/usr/bin/env python3
"""Teslim klasöründeki 10 MB'tan büyük dosyaları Drive'a yüklenebilecek parçalara böler.

Kullanım: python3 drive_parca.py teslim/09-yilan-inek

Çıktı: teslim/<klasör>/_drive/ içinde
  - 10 MB'tan küçük dosyaların kopyası (aynı ad)
  - büyük dosyalar için <ad>.p01, <ad>.p02 ... parçaları
  - BIRLESTIR.ps1: bilgisayarda parçaları birleştirir, SHA-256 ile doğrular, parçaları siler
  - yukle.json: her dosyanın adı, sha256'sı ve tam yolu (Drive'a yüklemek için)
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

PARCA = 3_000_000  # Drive bağlantısı istek başına ~4,2 MB (dosya ~3,1 MB) kabul ediyor


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for blok in iter(lambda: f.read(1 << 20), b""):
            h.update(blok)
    return h.hexdigest()


def main(klasor: str) -> None:
    kaynak = Path(klasor).resolve()
    hedef = kaynak / "_drive"
    if hedef.exists():
        shutil.rmtree(hedef)
    hedef.mkdir()
    birlestir = []
    for dosya in sorted(p for p in kaynak.iterdir() if p.is_file()):
        boyut = dosya.stat().st_size
        if boyut <= PARCA:
            shutil.copy2(dosya, hedef / dosya.name)
            continue
        parcalar = []
        with dosya.open("rb") as f:
            i = 1
            while True:
                blok = f.read(PARCA)
                if not blok:
                    break
                ad = f"{dosya.name}.p{i:02d}"
                (hedef / ad).write_bytes(blok)
                parcalar.append(ad)
                i += 1
        birlestir.append((dosya.name, parcalar, sha(dosya)))

    satirlar = [
        "# Avludaki Komsular - parcalari birlestir",
        "# Calistir: powershell -ExecutionPolicy Bypass -File BIRLESTIR.ps1",
        "$ErrorActionPreference = 'Stop'",
        "Set-Location -LiteralPath $PSScriptRoot",
        "function Birlestir($ad, $parcalar, $beklenen) {",
        "  foreach ($p in $parcalar) { if (-not (Test-Path -LiteralPath $p)) { throw \"Eksik parca: $p\" } }",
        "  $cikti = [System.IO.File]::Create((Join-Path $PSScriptRoot $ad))",
        "  try { foreach ($p in $parcalar) { $b = [System.IO.File]::ReadAllBytes((Join-Path $PSScriptRoot $p)); $cikti.Write($b, 0, $b.Length) } }",
        "  finally { $cikti.Close() }",
        "  $h = (Get-FileHash -LiteralPath $ad -Algorithm SHA256).Hash.ToLower()",
        "  if ($h -ne $beklenen) { Remove-Item -LiteralPath $ad; throw \"$ad BOZUK (ozet tutmadi); parcalari yeniden indir\" }",
        "  foreach ($p in $parcalar) { Remove-Item -LiteralPath $p }",
        "  Write-Host \"$ad TAMAM\"",
        "}",
    ]
    for ad, parcalar, h in birlestir:
        liste = ", ".join(f"'{p}'" for p in parcalar)
        satirlar.append(f"Birlestir '{ad}' @({liste}) '{h}'")
    satirlar.append("Write-Host 'Butun dosyalar birlestirildi ve dogrulandi.'")
    (hedef / "BIRLESTIR.ps1").write_text("\r\n".join(satirlar) + "\r\n", encoding="ascii")

    yukle = [
        {"ad": p.name, "sha256": sha(p), "yol": str(p), "boyut": p.stat().st_size}
        for p in sorted(hedef.iterdir())
        if p.name != "yukle.json"
    ]
    (hedef / "yukle.json").write_text(json.dumps(yukle, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(yukle)} dosya hazır → {hedef}")
    for ad, parcalar, _ in birlestir:
        print(f"  {ad}: {len(parcalar)} parça")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
