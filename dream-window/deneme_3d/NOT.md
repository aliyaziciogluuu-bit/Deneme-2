# 2.5D derinlik (paralaks) denemesi – 27 Kasım 2026

- Derinlik: Depth Anything V2 Small (ONNX, huggingface.co/onnx-community/depth-anything-v2-small), onnxruntime ile CPU'da; sahne.png üzerinde tek sefer.
- Video: paket dongu.mp4 (4K, canlı kar/ateş/aurora) → 1080x1920; kadraj sağa kayar, yakın nesneler disparite × T kadar fazladan kayar, hafif yaklaşma (yakın nesneler daha çok büyür). cv2.remap ile geri eşleme.
- Kullanım: `python3 paralaks.py <derinlik_klasoru(d29.npy)> <dongu.mp4> <ses_1.aac> <cikti.mp4>`; 15 sn ~30 sn'de üretiliyor.
- Durum: kanal sahibine deneme olarak gönderildi; karar bekleniyor. Yayına girerse tam 48 sn sürüm kontrol.py'den geçmeli.
