"""Düzeltme katsayıları: ham bülten fiyatlarını toplam getiri (temettü + bedelli + bedelsiz
düzeltilmiş) seriye çevirmek için.

``düzeltilmiş fiyat = ham fiyat × katsayı``. Katsayı geriye dönüktür: son gün 1'dir, her
özsermaye olayında (hak kullanım tarihinde) basamak yapar ve iki olay arasında sabittir.

Kaynak, İş Yatırım'ın aynı güne ait düzeltilmiş ve ham kapanışlarının oranıdır. Düzeltilmiş
kapanış 4 ondalığa yuvarlandığı için (özellikle eski ve küçük fiyatlarda) oran gürültülüdür;
bu modül basamakları yuvarlama sınırından ayırır ve her basamak aralığında tek, gürültüsüz
bir katsayı tahmin eder.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

#: İş Yatırım düzeltilmiş kapanışının yuvarlama adımının yarısı (4 ondalık).
_ADJ_HALF_STEP = 0.5e-4
#: Ham kapanış bültendeki fiyat adımına tamdır; yine de küçük bir pay bırakılır.
_SAFETY = 1.5


def stepwise_factor(raw_close: pd.Series, adj_close: pd.Series) -> pd.Series:
    """Ham ve düzeltilmiş kapanıştan gürültüsüz, basamaklı katsayı serisi üretir.

    Girdi serileri aynı tarih diziniyle hizalı olmalıdır. Geçersiz (NaN, <= 0) günler
    atılır; dönen seri yalnızca geçerli günleri içerir.
    """
    df = pd.DataFrame({"raw": raw_close, "adj": adj_close}).dropna()
    df = df[(df["raw"] > 0) & (df["adj"] > 0)]
    if df.empty:
        return pd.Series(dtype=float)
    raw = df["raw"].to_numpy(dtype=float)
    adj = df["adj"].to_numpy(dtype=float)
    log_ratio = np.log(adj / raw)

    # Oranın yuvarlamadan kaynaklanan en büyük bağıl hatası: yarım adım / düzeltilmiş fiyat.
    err = _ADJ_HALF_STEP / adj
    jump = np.abs(np.diff(log_ratio))
    tol = _SAFETY * (err[1:] + err[:-1]) + 1e-9
    is_step = np.concatenate([[True], jump > tol])
    segment = np.cumsum(is_step) - 1

    # Her aralıkta fiyat ağırlıklı tek katsayı: toplam(düz.) / toplam(ham).
    n_seg = int(segment[-1]) + 1
    sum_adj = np.bincount(segment, weights=adj, minlength=n_seg)
    sum_raw = np.bincount(segment, weights=raw, minlength=n_seg)
    seg_factor = sum_adj / sum_raw
    # Geriye dönük düzeltmede son aralığın katsayısı tam 1 olmalıdır; yuvarlama sapmasını gider.
    if abs(seg_factor[-1] - 1.0) < 5e-4:
        seg_factor = seg_factor / seg_factor[-1]
    return pd.Series(seg_factor[segment], index=df.index, name="factor")


def factor_steps(factor: pd.Series) -> pd.Series:
    """Katsayının değiştiği günleri ve o günkü basamak oranını (önceki/sonraki) verir.

    Oran < 1 ise fiyat o gün olay nedeniyle düşmüştür (temettü, bedelsiz, bedelli).
    """
    if factor.empty:
        return pd.Series(dtype=float)
    ratio = factor.shift(1) / factor
    steps = ratio[(ratio - 1.0).abs() > 1e-12].dropna()
    steps.name = "step"
    return steps


def align_factor(factor: pd.Series, dates: pd.DatetimeIndex) -> pd.Series:
    """Katsayıyı bülten tarihlerine hizalar.

    Arada eksik gün varsa önceki günün katsayısı taşınır; seri bittikten sonraki günlere son
    katsayı yazılır. Seri başlamadan ÖNCEKİ günler boş (NaN) kalır: o günlerdeki özsermaye
    olayları bilinmediği için ilk katsayıyı geriye taşımak sessizce yanlış getiri üretir.
    """
    if factor.empty:
        return pd.Series(np.nan, index=dates, name="factor")
    f = factor[~factor.index.duplicated(keep="last")].sort_index()
    out = f.reindex(f.index.union(dates)).ffill().reindex(dates)
    out.name = "factor"
    return out


def _at(series: pd.Series, day) -> float:
    """Serinin ``day`` günündeki değeri; gün yoksa veya değer sayı değilse NaN."""
    try:
        value = series.get(day)
        return float(value) if value is not None else float("nan")
    except (TypeError, ValueError):
        return float("nan")


def _tolerance(prev_close: float) -> float:
    """Marj karşılaştırmasında fiyat adımı yuvarlamasına bırakılan pay."""
    tick = 0.01 if prev_close < 20 else prev_close * 0.001
    return max(0.012, 1.5 * tick / prev_close)


def repair_missing_steps(
    factor: pd.Series,
    prev_close_field: pd.Series,
    open_: pd.Series,
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    flagged: pd.Series,
    limit: pd.Series,
) -> tuple[pd.Series, list[dict]]:
    """Kaynağın atladığı veya yanlış girdiği özsermaye olaylarını bültenden onarır.

    Yalnızca bültenin "özsermaye hali" bayrağı taşıyan günlere bakılır. Her biri için
    doğru basamak (baz fiyat / bir önceki günün gerçek kapanışı) şu sırayla belirlenir:

    1. **Resmî baz fiyat.** Bülten ``önceki kapanış`` alanı o gün gerçek önceki kapanıştan
       farklıysa (2016 sonuna kadarki bültenler baz fiyatı bu alanda yayımlar) o değer
       kesindir.
    2. **Kaynağın basamağı.** Düzeltilmiş getiri günlük fiyat marjı içindeyse kaynak doğrudur.
    3. **Marj bandından tahmin.** Düzeltilmiş getiri marjın dışındaysa kaynak olayı
       atlamıştır (ör. bedelli sermaye artırımı). O gün işlemler baz fiyatın ±marj bandında
       geçtiği için baz fiyat ``[en yüksek / (1 + marj), en düşük / (1 − marj)]``
       aralığındadır; aralığın ortası alınır (aralık boşsa açılış fiyatı).

    Dönüş: (onarılmış katsayı, onarım kayıtları).
    """
    f = factor.copy()
    repairs: list[dict] = []
    true_prev = close.ffill().shift(1)
    days = flagged[flagged.fillna(False).astype(bool)].index
    for day in days:
        tp, cl, hi, lo, op = (_at(x, day) for x in (true_prev, close, high, low, open_))
        f_day = _at(f, day)
        f_prev = _at(f.ffill().shift(1), day)
        if not all(np.isfinite(x) and x > 0 for x in (tp, cl, hi, lo, f_day, f_prev)):
            continue
        vendor_step = f_prev / f_day
        field = _at(prev_close_field, day)
        lim = _at(limit, day)
        lim = lim if np.isfinite(lim) else 0.10
        if np.isfinite(field) and field > 0 and abs(field / tp - 1.0) > 1e-3:
            desired, how = field / tp, "official"
        else:
            adj_ret = cl / (tp * vendor_step) - 1.0
            if abs(adj_ret) <= lim + _tolerance(tp):
                continue
            lower, upper = hi / (1.0 + lim), lo / (1.0 - lim)
            if lower <= upper:
                base = 0.5 * (lower + upper)
            elif np.isfinite(op) and op > 0:
                base = op
            else:
                base = cl
            desired, how = base / tp, "band"
        correction = desired / vendor_step
        if abs(correction - 1.0) <= 2e-3:
            continue
        f.loc[f.index < day] *= correction
        repairs.append({"date": day, "how": how, "step_before": vendor_step, "step_after": desired})
    return f, repairs


def limit_violations(factor: pd.Series, close: pd.Series, limit: pd.Series) -> pd.Series:
    """Düzeltilmiş günlük getirinin fiyat marjını aştığı günler (veri şüphesi).

    Uzun süre işlem görmeyen bir payın yeniden açıldığı gün gibi meşru istisnalar olabilir;
    bu yüzden sonuç onarım değil yalnızca rapor amaçlıdır.
    """
    filled = (close * factor).ffill()
    prev = filled.shift(1)
    adj_ret = (close * factor) / prev - 1.0
    raw_prev = close.ffill().shift(1)
    tol = raw_prev.map(lambda x: _tolerance(x) if np.isfinite(x) and x > 0 else np.nan)
    bad = adj_ret.abs() > (limit.reindex(adj_ret.index) + tol)
    return adj_ret[bad.fillna(False)]
