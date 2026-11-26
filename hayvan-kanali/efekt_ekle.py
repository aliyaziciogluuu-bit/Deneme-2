"""Bitmiş bir Shorts'a sahne geçişlerinde ses efekti ekler (Zack D. Films tarzı tempo).

Kullanım:  python efekt_ekle.py deneme-3d/s3-geko-tavan [--parilti 3,4] [--seviye -14]
- Çekim geçişleri video.py çizelgesinden alınır; her geçişe hafif bir "whoosh" konur.
- --parilti: verilen sahne numaralarının (1'den başlar) başına ince bir parıltı eklenir (röntgen/kesit açılışı).
- Videonun ilk anına kısa bir "pop" konur (kaydırmayı durduran vurgu).
Özgün dosya video_efektsiz.mp4 olarak saklanır; yeniden çalıştırınca her zaman onun üstüne kurulur.
Efektler sesler/efekt/ altında, kanalın kendi sentezi (telifsiz).
"""
import argparse
import pathlib
import shutil
import subprocess

KOK = pathlib.Path(__file__).parent
EFEKT = KOK / "sesler" / "efekt"


def gecisler(klasor: pathlib.Path):
    """Çekim geçiş zamanları, video.py'nin kendi çizelgesinden (geçişler yumuşak olduğu için görüntüden bulunamıyor)."""
    import video
    cumleler, toplam, _, senaryo = video.cizelge(klasor)
    plan = video.cekimleri_kur(klasor, cumleler, toplam)
    return [c["bas"] for c in plan[1:]]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("klasor")
    p.add_argument("--parilti", default="")
    p.add_argument("--seviye", type=float, default=-14.0, help="efektlerin dB düzeyi (anlatımın altında)")
    g = p.parse_args()
    k = KOK / g.klasor
    asil, yedek = k / "video.mp4", k / "video_efektsiz.mp4"
    if not yedek.exists():
        shutil.copy2(asil, yedek)
    kesimler = gecisler(k)
    sahne_bas = [0.0] + kesimler
    olaylar = [("pop.wav", 0.0, g.seviye + 2)]
    for i, t in enumerate(kesimler):
        olaylar.append(("whoosh.wav" if i % 2 == 0 else "whoosh_ters.wav", max(t - 0.12, 0), g.seviye))  # konuşma bittikten sonra başlasın (ara/2 = 0,175 sn)
    for n in [int(x) for x in g.parilti.split(",") if x.strip()]:
        if 1 <= n <= len(sahne_bas):
            olaylar.append(("parilti.wav", sahne_bas[n - 1] + 0.1, g.seviye - 4))
    girdiler, filtre, etiketler = ["-i", str(yedek)], [], []
    for j, (dosya, t, db) in enumerate(olaylar, start=1):
        girdiler += ["-i", str(EFEKT / dosya)]
        ms = int(t * 1000)
        filtre.append(f"[{j}:a]volume={db}dB,adelay={ms}|{ms}[e{j}]")
        etiketler.append(f"[e{j}]")
    filtre.append(f"[0:a]{''.join(etiketler)}amix=inputs={len(etiketler) + 1}:duration=first:normalize=0,"
                  f"loudnorm=I=-14.5:TP=-1.5:LRA=11[a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *girdiler, "-filter_complex", ";".join(filtre),
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    str(asil)], check=True)
    print(f"{len(kesimler)} geçiş bulundu: {', '.join(f'{t:.1f}' for t in kesimler)} sn; {len(olaylar)} efekt eklendi → {asil.name}")


if __name__ == "__main__":
    main()
