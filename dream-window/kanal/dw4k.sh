#!/data/data/com.termux/files/usr/bin/bash
# Dream Window – 4K paketini telefonda (Termux) birleştirir.
# Kullanım (Termux'ta):  bash ~/storage/downloads/dw4k.sh
#   İndirilenler klasöründeki en yeni *_4K_paket.zip dosyasını açar, parçaları kalite kaybı olmadan
#   3 saatlik 4K videoya birleştirir ve videoyu Filmler/DreamWindow klasörüne koyar. Geçici dosyaları siler.
#   Belirli bir paket için:  bash ~/storage/downloads/dw4k.sh cati_kati
set -e
DL="${DL:-$HOME/storage/downloads}"
OUT="${OUT:-$HOME/storage/shared/Movies/DreamWindow}"
ISLEM="${ISLEM:-$HOME/dw4k_islem}"

command -v ffmpeg >/dev/null || { echo "ffmpeg yok. Önce şunu çalıştır: pkg install -y ffmpeg unzip"; exit 1; }
[ -d "$DL" ] || { echo "İndirilenler klasörüne erişim yok. Önce şunu çalıştır: termux-setup-storage (izin ver)"; exit 1; }

if [ -n "$1" ]; then ZIP=$(ls -t "$DL"/*"$1"*_4K_paket.zip 2>/dev/null | head -1)
else ZIP=$(ls -t "$DL"/*_4K_paket.zip 2>/dev/null | head -1); fi
[ -n "$ZIP" ] || { echo "İndirilenler'de *_4K_paket.zip bulunamadı. Önce Claude'un gönderdiği zip'i indir."; exit 1; }
AD=$(basename "$ZIP" _paket.zip); AD=${AD#*_UZUN_}
echo "Paket: $(basename "$ZIP")"

mkdir -p "$OUT"
BOS=$(df -k "$OUT" | awk 'NR==2{print $4}')
if [ "${BOS:-0}" -lt "${DW_MIN_KB:-5500000}" ]; then echo "Telefonda en az 5,5 GB boş yer gerekli (şu an yaklaşık $((BOS/1048576)) GB). Yer açıp tekrar dene."; exit 1; fi

rm -rf "$ISLEM"; mkdir -p "$ISLEM"
echo "Zip açılıyor..."
unzip -q "$ZIP" -d "$ISLEM"
KLASOR=$(dirname "$(find "$ISLEM" -name liste.txt | head -1)")
[ -f "$KLASOR/liste.txt" ] || { echo "Paket bozuk görünüyor (liste.txt yok). Zip'i tekrar indir."; exit 1; }

echo "Birleştiriliyor (1-3 dakika sürer, ekranı kapatma)..."
cd "$KLASOR"
SINIR=(); [ -n "$DW_TEST_SURE" ] && SINIR=(-t "$DW_TEST_SURE")
ffmpeg -v error -y -f concat -safe 0 -i liste.txt -i ses.m4a -map 0:v -map 1:a -c copy -shortest "${SINIR[@]}" -movflags +faststart "$OUT/$AD.mp4"
cd "$HOME"; rm -rf "$ISLEM"

SURE=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/$AD.mp4" 2>/dev/null | cut -d. -f1)
echo ""
echo "HAZIR: Filmler/DreamWindow/$AD.mp4  ($(du -m "$OUT/$AD.mp4" | cut -f1) MB, $((SURE/3600)) saat $(((SURE%3600)/60)) dk)"
echo "Yüklemek için: Dosyalarım > Filmler > DreamWindow > videoya uzun bas > Paylaş > YouTube"
echo "Yükledikten sonra yer açmak için videoyu ve zip'i silebilirsin."
