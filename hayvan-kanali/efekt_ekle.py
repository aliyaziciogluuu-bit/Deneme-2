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
    return [(c["bas"], bool(c.get("kesme"))) for c in plan[1:]]  # kesme: hızlı kurgudaki alt çekim (sert kesme)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("klasor")
    p.add_argument("--parilti", default="")
    p.add_argument("--seviye", type=float, default=-14.0, help="efektlerin dB düzeyi (anlatımın altında)")
    p.add_argument("--whoosh", dest="yumusak", action="store_false", help="eski güçlü whoosh (varsayılan: yumuşak fısıltı)")
    p.add_argument("--muzik", default=None, help="sesler/muzik/ altındaki altlık (ör. lyria_merak); verilmezse senaryo.json 'muzik' alanı")
    p.add_argument("--muzik-seviye", type=float, default=-21.0, help="müziğin dB düzeyi; konuşma sırasında ayrıca bastırılır")
    g = p.parse_args()
    k = KOK / g.klasor
    asil, yedek = k / "video.mp4", k / "video_efektsiz.mp4"
    if not yedek.exists():
        shutil.copy2(asil, yedek)
    plan = gecisler(k)
    kesimler = [t for t, _ in plan]
    sahne_bas = [0.0] + kesimler
    olaylar = [("pop.wav", 0.0, g.seviye + 2)]
    for i, (t, alt) in enumerate(plan):
        if alt:  # cümle içindeki sert kesme: efekt yok (28 Kasım, kanal sahibi: geçiş efektleri rahatsız edici)
            continue
        if g.yumusak:  # cümle aralarındaki kesmede kısa, alçak "fısıltı"
            olaylar.append(("fisilti.wav", max(t - 0.08, 0), g.seviye - 6))
        else:
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
    import json
    muzik = g.muzik or json.loads((k / "senaryo.json").read_text(encoding="utf-8")).get("muzik")
    ana = "[0:a]"
    if muzik:  # müzik altlığı: döngüde çalar, konuşma varken sidechain ile bastırılır, sonda 1 sn kısılarak biter
        yol = next((KOK / "sesler" / "muzik").glob(muzik + ".*"))
        sure = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(yedek)],
                                    capture_output=True, text=True, check=True).stdout)
        m = len(girdiler) // 2
        girdiler += ["-stream_loop", "-1", "-i", str(yol)]
        filtre.append("[0:a]asplit=2[konus][anahtar]")
        filtre.append(f"[{m}:a]aformat=channel_layouts=stereo,volume={g.muzik_seviye}dB,atrim=0:{sure:.2f},"
                      f"afade=t=in:d=0.3,afade=t=out:st={max(sure - 1.2, 0):.2f}:d=1.2[muz0]")
        filtre.append("[muz0][anahtar]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[muz]")
        ana, etiketler = "[konus]", etiketler + ["[muz]"]
    filtre.append(f"{ana}{''.join(etiketler)}amix=inputs={len(etiketler) + 1}:duration=first:normalize=0,"
                  f"loudnorm=I=-14.5:TP=-1.5:LRA=11[a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *girdiler, "-filter_complex", ";".join(filtre),
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    str(asil)], check=True)
    print(f"{len(kesimler)} geçiş bulundu: {', '.join(f'{t:.1f}' for t in kesimler)} sn; {len(olaylar)} efekt eklendi → {asil.name}")


if __name__ == "__main__":
    main()
