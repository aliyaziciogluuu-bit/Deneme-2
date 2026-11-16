"""Gerçek emir katmanı: emir fişini aracı kuruma ileten, sınırlarla ve onayla korunan parça.

Bu paket, Matriks IQ'nun açık olduğu bilgisayarda çalışır. Bulut tarafının ürettiği emir fişini
okur, işlem öncesi kontrolleri uygular, Telegram'dan onay ister, emirleri gönderir ve sonucu
raporlar. Varsayılan kip "kuru çalıştırma"dır; gerçek emir yalnızca açıkça istenince gider.
"""
