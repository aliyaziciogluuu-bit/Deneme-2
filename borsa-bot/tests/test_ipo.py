"""Halka arz keşfi: olay saptama, işlem mekaniği ve ön kayıtlı yöntem (sentetik veri)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bistbot import ipo
from bistbot.config import CostConfig
from bistbot.data.panel import MarketPanel

DATES = pd.bdate_range("2022-03-01", periods=12)


def make_panel(stocks: dict[str, list[tuple | None]], markets: dict[str, str] | None = None) -> MarketPanel:
    """``stocks[sym]``: gün başına (önceki kapanış, açılış, en yüksek, en düşük, kapanış) ya da ``None``."""
    syms = sorted(stocks)
    fields = {k: pd.DataFrame(np.nan, index=DATES, columns=syms) for k in ("prev_close", "open", "high", "low", "close")}
    listed = pd.DataFrame(False, index=DATES, columns=syms)
    for sym, rows in stocks.items():
        for i, row in enumerate(rows):
            if row is None:
                continue
            listed.iat[i, syms.index(sym)] = True
            for key, val in zip(("prev_close", "open", "high", "low", "close"), row):
                fields[key].iat[i, syms.index(sym)] = val

    def const(value, dtype):
        return pd.DataFrame(value, index=DATES, columns=syms).astype(dtype)

    market = const("", object)
    for sym in syms:
        market.loc[listed[sym], sym] = (markets or {}).get(sym, "Z")
    return MarketPanel(
        vwap=fields["close"].copy(), value=const(1e6, float), volume=const(1e5, float),
        bist100=const(False, bool), bist30=const(False, bool), gross=const(False, bool),
        suspended=const(False, bool), short_ok=const(False, bool), market=market,
        method=const("SI", object), corp_action=const("", object), listed=listed,
        names={s: s for s in syms}, **fields,
    )


def flat(price: float = 10.0, n: int = len(DATES)) -> list[tuple]:
    """Hiç kıpırdamayan eski pay (kıyas getirisi sıfır olsun diye)."""
    return [(price, price, price, price, price)] * n


def hot_ipo() -> list[tuple | None]:
    """2 gün yok; 3 gün tavanda kilitli; 4. gün açılıp artıda kapatıyor; sonra dalgalanıyor."""
    return [
        None, None,
        (np.nan, 11.0, 11.0, 11.0, 11.0),      # ilk gün: tek fiyat, baz fiyat bültende yok
        (11.0, 12.1, 12.1, 12.1, 12.1),        # tavan
        (12.1, 13.3, 13.3, 13.3, 13.3),        # tavan (adım yuvarlaması: %9,9)
        (13.3, 14.6, 14.6, 13.5, 14.0),        # T: tavanın altında işlem gördü, artıda kapattı
        (14.0, 14.2, 14.5, 13.0, 13.3),        # giriş günü: açılış 14,2
        (13.3, 13.3, 13.6, 13.0, 13.5),
        (13.5, 13.5, 13.5, 12.15, 12.15),      # tabanda kapanış ama gün içinde işlem var
        (12.15, 10.94, 10.94, 10.94, 10.94),   # tabanda kilitli: satılamaz
        (10.94, 11.0, 11.5, 10.8, 11.2),
        (11.2, 11.2, 11.3, 11.0, 11.1),
    ]


@pytest.fixture()
def panel() -> MarketPanel:
    return make_panel({"OLD": flat(), "HOT": hot_ipo()})


def events_of(panel: MarketPanel) -> pd.DataFrame:
    return ipo.events(panel, ipo.find_listings(panel, first="2022-03-02"))


def test_listing_is_found_with_streak_and_open_day(panel):
    ev = events_of(panel)
    assert list(ev["symbol"]) == ["HOT"]              # OLD veri başından beri var: halka arz değil
    row = ev.iloc[0]
    assert (row["pos"], row["T"], row["S"]) == (2, 5, 3)
    assert bool(row["t_up"]) is True
    assert pd.isna(row["dip"])                        # 60 seansta zirveden %30 düşüş yok


def test_non_ipo_markets_are_excluded():
    panel = make_panel({"OLD": flat(), "PRE": hot_ipo()}, markets={"PRE": "S"})
    assert ipo.find_listings(panel, first="2022-03-02").empty


def test_trade_enters_next_open_and_exits_at_close(panel):
    mkt, rf = ipo.market_returns(panel, min_sessions=60), pd.Series(0.365, index=DATES)
    tr = ipo.trade(panel, mkt, rf, "HOT", signal=5, horizon=2, cost=CostConfig())
    assert tr["entry"] == DATES[6] and tr["exit"] == DATES[7]
    assert tr["gross"] == pytest.approx(13.5 / 14.2 - 1.0)
    assert tr["market"] == pytest.approx(0.0) and tr["abn"] == pytest.approx(tr["gross"])
    side = CostConfig().per_side
    assert tr["net"] == pytest.approx(13.5 / 14.2 * (1 - side) / (1 + side) - 1.0)
    assert tr["cash"] == pytest.approx(0.365 * 2 / 365.0)   # iki takvim günü


def test_benchmark_is_equal_weight_of_main_market_stocks(panel):
    mkt = ipo.market_returns(panel)
    assert mkt.close_to_close[DATES[6]] == pytest.approx((0.0 + 13.3 / 14.0 - 1.0) / 2)   # OLD ve HOT
    assert mkt.open_to_close[DATES[6]] == pytest.approx((0.0 + 13.3 / 14.2 - 1.0) / 2)
    assert ipo.market_returns(panel, min_sessions=60).close_to_close.abs().max() == 0.0   # yalnız OLD


def test_exit_waits_while_locked_at_floor(panel):
    mkt, rf = ipo.market_returns(panel), pd.Series(0.2, index=DATES)
    # 4 seanslık süre tabanda kilitli güne denk gelir: satış ertesi seansa kayar.
    tr = ipo.trade(panel, mkt, rf, "HOT", signal=5, horizon=4, cost=CostConfig())
    assert tr["exit"] == DATES[10]
    assert tr["gross"] == pytest.approx(11.2 / 14.2 - 1.0)


def test_no_trade_when_entry_day_is_locked_at_ceiling_or_window_incomplete(panel):
    mkt, rf = ipo.market_returns(panel), pd.Series(0.2, index=DATES)
    assert ipo.trade(panel, mkt, rf, "HOT", signal=3, horizon=2, cost=CostConfig()) is None   # ertesi gün tavan
    assert ipo.trade(panel, mkt, rf, "HOT", signal=5, horizon=20, cost=CostConfig()) is None  # veri bitiyor


def test_dip_signal_and_signal_families():
    rows = hot_ipo()
    rows[7] = (13.3, 12.0, 12.0, 9.5, 9.7)            # zirve kapanış 14,0 → %30'dan fazla düşüş
    ev = events_of(make_panel({"OLD": flat(), "HOT": rows}))
    assert ev.iloc[0]["dip"] == 7
    assert len(ipo.signal_days(ev, "B")) == 1 and ipo.signal_days(ev, "B").iloc[0]["sig"] == 5
    assert ipo.signal_days(ev, "C").empty and ipo.signal_days(ev, "D").empty
    assert ipo.signal_days(ev, "E").empty             # seri 3 gün: "uzun seri" (≥ 4) değil
    assert ipo.signal_days(ev, "F").iloc[0]["sig"] == 7


def test_clustered_t_matches_plain_t_for_singleton_clusters_and_shrinks_when_clustered():
    x = np.array([0.02, 0.04, -0.01, 0.03, 0.05, 0.01])
    plain = x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))
    assert ipo.clustered_t(x, np.arange(len(x))) == pytest.approx(plain)
    # Aynı ayın işlemleri birlikte hareket ediyorsa bağımsız gözlem sayısı azalır.
    y = np.array([0.05, 0.05, 0.05, -0.01, -0.01, -0.01])
    assert abs(ipo.clustered_t(y, np.array([0, 0, 0, 1, 1, 1]))) < abs(ipo.clustered_t(y, np.arange(6)))


def test_study_reports_no_discovery_when_nothing_clears_the_bar(panel):
    res = ipo.study(panel, pd.Series(0.2, index=DATES), first="2022-03-02")
    assert res["verdict"] == "kesif-yok" and res["candidate"] is None
    assert res["events"] == 1 and len(res["discovery"]) == 18
    assert "keşif yok" in ipo.format_study(res)
