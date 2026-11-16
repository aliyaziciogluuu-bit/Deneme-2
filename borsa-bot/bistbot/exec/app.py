"""``bistbot emir`` komutunun işlevleri: çalıştırma, hesap görüntüleme, yön testi, iptal, durum."""
from __future__ import annotations

import datetime as dt
import logging
import subprocess
from pathlib import Path

from .base import Broker, BrokerError, OrderRequest
from .dryrun import DryRunBroker, ReadOnlyBroker
from .guard import round_down_to_tick
from .journal import Journal
from .matriks import STATUS_TEXT, MatriksBroker, _number, _order_qty, mask
from .runner import (IST, AlreadyRunning, Clock, RunLock, RunResult, account_fingerprint, flush_undelivered,
                     journal_path, load_state, run_batch, save_state)
from .settings import ExecSettings, SettingsError
from .telegram import Telegram
from .ticket import Ticket, TicketError, load_ticket

log = logging.getLogger(__name__)

CALIBRATION_KEY = "yon_testi"


class VerifiedMatriksBroker(MatriksBroker):
    """Gerçek kipte kullanılan bağlantı: hesap, yön testinin yapıldığı hesapla aynı olmalıdır."""

    def __init__(self, settings, echo_buy, fingerprint: str, ids_echoed: bool = False):
        super().__init__(settings, echo_buy=echo_buy)
        self._fingerprint = fingerprint
        self._ids_echoed = bool(ids_echoed)

    def connect(self) -> None:
        super().connect()
        if account_fingerprint(self.brokage_id, self.account_id) != self._fingerprint:
            raise BrokerError("bağlanılan hesap, yön testinin yapıldığı hesap değil; 'emir --yon-testi' ile yeniden doğrulayın")


def calibration(s: ExecSettings) -> dict | None:
    """Geçerli yön testi kaydı (kodlar değişmediyse), yoksa ``None``."""
    record = load_state(s.klasor).get(CALIBRATION_KEY)
    if not isinstance(record, dict) or not record.get("dogrulandi"):
        return None
    if record.get("alis_kodu") != s.matriks.alis_kodu or record.get("satis_kodu") != s.matriks.satis_kodu:
        return None
    return record


def make_broker(s: ExecSettings, ticket: Ticket) -> Broker:
    if s.mod == "deneme":
        return DryRunBroker(ticket.positions)
    if s.mod == "salt-okunur":
        return ReadOnlyBroker(MatriksBroker(s.matriks))
    record = calibration(s)
    if record is None:
        raise SettingsError(
            "Gerçek emir kipi için önce yön testi gerekli: seans içinde 'bistbot emir --yon-testi SEMBOL --fiyat FİYAT' "
            "çalıştırın (1 lotluk, piyasanın altında bir alış emriyle alış/satış kodları doğrulanır)."
        )
    return VerifiedMatriksBroker(s.matriks, record.get("yanit_alis"), str(record.get("hesap", "")),
                                 bool(record.get("kimlik_yankisi")))


def make_telegram(s: ExecSettings) -> Telegram | None:
    t = s.telegram
    return Telegram(t.token, t.chat_id, t.approver) if t.configured else None


def resolve_ticket_source(s: ExecSettings, base: Path) -> str:
    if s.fis.startswith(("https://", "http://")):
        return s.fis
    path = Path(s.fis)
    return str(path if path.is_absolute() else base / path)


def git_pull(folder: Path) -> None:
    """Fiş yerel depodan okunuyorsa önce depoyu günceller (başarısızlık ölümcül değildir:
    fişin tarihi ve tazeliği ayrıca denetlenir)."""
    try:
        out = subprocess.run(["git", "-C", str(folder), "pull", "--ff-only", "--quiet"], capture_output=True,
                             text=True, timeout=120)
        if out.returncode != 0:
            log.warning("git pull başarısız: %s", (out.stderr or out.stdout).strip()[:200])
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("git pull çalıştırılamadı: %s", type(exc).__name__)


def cmd_run(s: ExecSettings, base: Path, clock: Clock | None = None) -> RunResult:
    """Günün emir fişini işler."""
    clock = clock or Clock()
    tg = make_telegram(s)
    if tg is not None:
        # Önceki çalıştırmadan iletilemeyen rapor/uyarı varsa (emir olmayan günlerde de) önce o gönderilir.
        try:
            flush_undelivered(s.klasor, tg)
        except OSError:
            log.exception("iletilemeyen bildirimler okunamadı")
    if s.git_guncelle and not s.fis.startswith("https://"):
        git_pull(base)
    try:
        ticket = load_ticket(resolve_ticket_source(s, base))
    except TicketError as exc:
        return RunResult("error", f"Emir fişi okunamadı: {exc}")
    if not ticket.orders:
        return RunResult("no_orders", "Bugün için emir yok.")
    try:
        broker = make_broker(s, ticket)
    except SettingsError as exc:
        if tg is not None:
            tg.try_send(f"⛔ Emirler GÖNDERİLMEDİ: {exc}")
        return RunResult("error", str(exc))
    try:
        with RunLock(s.klasor):
            return run_batch(s, ticket, broker, tg, Journal(journal_path(s)), clock)
    except AlreadyRunning as exc:
        return RunResult("error", str(exc))


def cmd_account(s: ExecSettings, out=print) -> int:
    """Matriks IQ'daki hesapları, pozisyonları ve hesap bilgisi anahtarlarını ekrana yazar (yalnızca okur)."""
    broker = MatriksBroker(s.matriks)
    try:
        broker.wire.connect()
        accounts = broker.accounts()
        out("Matriks IQ'da giriş yapılmış hesaplar:")
        for a in accounts:
            out(f"  kurum {a['BrokageId']} ({a['BrokageName']})  hesap {a['AccountId']}  borsa {a['ExchangeId']}"
                + ("   <- BIST Pay" if a["ExchangeId"] == s.matriks.borsa_id else ""))
        if not accounts:
            out("  (hesap yok: Matriks IQ'da aracı kurum girişi yapın)")
            return 1
        broker._select_account(accounts)
        out(f"\nSeçilen hesap: kurum {broker.brokage_id}, hesap {broker.account_id}")
        rows = broker.raw_positions()
        out(f"\nPozisyonlar ({len(rows)} satır) — satılabilir lot '{', '.join(s.matriks.lot_alanlari)}' alanından okunur:")
        for r in rows:
            out("  {:<8} QtyAvailable={} QtyT={} QtyT1={} QtyT2={} LastPx={} IsSymbol={}".format(
                str(r.get("Symbol")), r.get("QtyAvailable"), r.get("QtyT"), r.get("QtyT1"), r.get("QtyT2"),
                r.get("LastPx"), r.get("IsSymbol")))
        sellable = broker.positions()
        out("\nBotun gördüğü satılabilir lotlar: " + (", ".join(f"{k} {v}" for k, v in sorted(sellable.items())) or "(yok)"))
        try:
            info = broker.account_info()
            out("\nHesap bilgisi (bakiyeyi okutmak için uygun satırın anahtarını [matriks] nakit_anahtari olarak yazın):")
            for item in info:
                out(f"  anahtar={item.get('Key')!r} kod={item.get('Code')!r} değer={item.get('Value')!r}")
            if s.matriks.nakit_anahtari:
                out(f"\nBotun okuduğu bakiye: {broker.cash()}")
        except BrokerError as exc:
            out(f"\nHesap bilgisi alınamadı: {exc}")
        return 0
    except BrokerError as exc:
        out(f"HATA: {exc}")
        return 1
    finally:
        broker.close()


def cmd_side_test(s: ExecSettings, symbol: str, price: float, ask=input, out=print) -> int:
    """Yön testi: 1 lotluk, piyasanın %5 altında bir ALIŞ emri gönderir, kullanıcıya Matriks IQ'da
    nasıl göründüğünü sorar ve emri iptal eder. Onaylanırsa gerçek kipin kilidi açılır."""
    symbol = symbol.strip().upper()
    if not (price > 0):
        out("HATA: --fiyat hissenin şu anki fiyatı olmalı (ör. 123.40)")
        return 1
    limit = round_down_to_tick(price * 0.95)
    broker = MatriksBroker(s.matriks)
    try:
        broker.connect()
        for row in broker.raw_positions():
            if str(row.get("Symbol") or "").upper() == symbol and any(
                    isinstance(row.get(k), (int, float)) and row.get(k) for k in ("QtyT", "QtyT1", "QtyT2", "QtyAvailable")):
                out(f"HATA: {symbol} hesabınızda var. Test için ELİNİZDE OLMAYAN bir hisse seçin "
                    "(kod ters yorumlanırsa satış emri reddedilsin diye).")
                return 1
        out(f"Hesap: kurum {broker.brokage_id}, hesap {mask(broker.account_id)}")
        out(f"Gönderilecek test emri: {symbol} 1 lot ALIŞ, limit {limit:.2f} TL (piyasanın yaklaşık %5 altında; "
            "gerçekleşmesi beklenmez). Test seans içinde (10:00-18:00) yapılmalıdır.")
        if ask("Devam edilsin mi? (evet/hayır): ").strip().lower() not in ("evet", "e"):
            out("Vazgeçildi.")
            return 1
        key = f"yon-testi|{dt.datetime.now(IST):%Y%m%d%H%M%S}"
        state = broker.place(OrderRequest(key, symbol, "buy", 1, limit))
        echo = state.raw.get("OrderSide")
        out(f"Matriks IQ yanıtı: {state.status} — {state.message} (OrderSide={echo!r}, emir no {state.broker_id})")
        if state.status == "unknown":
            out("Matriks IQ emri doğrulamadı. Emir penceresinden böyle bir emir olup olmadığına bakın; varsa elle iptal edin.")
            return 1
        if state.status == "rejected":
            out("Emir reddedildi. Olası nedenler: seans kapalı, fiyat günlük sınırların dışında ya da yön kodu ters "
                "yorumlandı (satış sayıldı). Seans içinde yeniden deneyin; yine reddedilirse yön kodlarını Matriks'e sorun.")
            return 1
        if state.filled_lots:
            out("UYARI: test emri GERÇEKLEŞTİ. Hesabınızı kontrol edin; yön kodları doğrulanmadı.")
            return 1
        answer = ask(f"Matriks IQ'nun emir penceresinde {symbol} 1 lot emri ALIŞ olarak mı görünüyor? (evet/hayır): ")
        confirmed = answer.strip().lower() in ("evet", "e")
        # Kullanıcı yanıt verirken emir reddedilmiş ya da gerçekleşmiş olabilir: durumu yeniden oku.
        try:
            state = broker.refresh(state)
        except BrokerError as exc:
            out(f"UYARI: emir durumu okunamadı ({exc}); Matriks IQ'dan emri kontrol edip elle iptal edin.")
            return 1
        echo = state.raw.get("OrderSide")
        if state.status == "rejected":
            out(f"Emir sonradan REDDEDİLDİ ({state.message}); yön doğrulanmadı.")
            return 1
        if state.filled_lots:
            out("UYARI: test emri GERÇEKLEŞTİ. Hesabınızı kontrol edin; yön kodları doğrulanmadı.")
            return 1
        if state.done:
            out(f"Test emri kendiliğinden kapandı ({state.message}); yön doğrulanmadı. Testi yineleyin.")
            return 1
        cancelled = False
        try:
            final = broker.cancel(state)
            out(f"Test emri iptali: {final.status} — {final.message}")
            cancelled = final.status == "cancelled" and final.filled_lots == 0
            if final.filled_lots:
                out("UYARI: test emri iptal edilemeden GERÇEKLEŞTİ. Hesabınızı kontrol edin.")
            elif not cancelled:
                out("UYARI: iptal doğrulanamadı; emri Matriks IQ'dan elle iptal edin.")
        except BrokerError as exc:
            out(f"UYARI: test emri iptal edilemedi ({exc}); Matriks IQ'dan elle iptal edin.")
        if not confirmed:
            out("Yön doğrulanmadı; gerçek emir kipi kapalı kalacak. [matriks] alis_kodu / satis_kodu değerlerini "
                "Matriks'in güncel belgesine göre düzeltip testi yineleyin.")
            return 1
        if not cancelled:
            out("Test emri temiz biçimde iptal edilemediği için yön doğrulaması kaydedilmedi; testi yineleyin.")
            return 1
        state_file = load_state(s.klasor)
        state_file[CALIBRATION_KEY] = {
            "dogrulandi": True, "alis_kodu": s.matriks.alis_kodu, "satis_kodu": s.matriks.satis_kodu,
            "yanit_alis": echo, "hesap": account_fingerprint(broker.brokage_id, broker.account_id),
            # Matriks IQ istemci emir kimliğini geri gönderiyor mu? Gönderiyorsa içerikle eşleştirme hiç kullanılmaz.
            "kimlik_yankisi": bool(str(state.raw.get("ClientOrderId") or "").strip()),
            "tarih": dt.datetime.now(IST).isoformat(timespec="seconds"), "sembol": symbol,
        }
        save_state(s.klasor, state_file)
        out("Yön doğrulandı ve kaydedildi. emir-ayar.toml içinde mod = \"gercek\" yaparak gerçek emir kipini açabilirsiniz.")
        return 0
    except BrokerError as exc:
        out(f"HATA: {exc}")
        return 1
    finally:
        broker.close()


def _today_orders(journal: Journal, day: dt.date) -> dict[str, dict]:
    """Bugünün seansında gönderilen emirler: ``{anahtar: {symbol, side, lots, limit, broker_id, event}}``."""
    out: dict[str, dict] = {}
    for e in journal.entries():
        key = e.get("key") or ""
        if e.get("event") == "sending" and e.get("session") == day.isoformat():
            out[key] = {"symbol": e.get("symbol"), "side": e.get("side"), "lots": e.get("lots"),
                        "limit": e.get("limit"), "event": "sending", "filled": 0}
        elif key in out:
            row = out[key]
            if e.get("broker_id"):
                row["broker_id"] = str(e["broker_id"])
            row["event"] = e.get("event")
            row["filled"] = e.get("filled", row.get("filled", 0))
    return out


def cmd_status(s: ExecSettings, out=print, today: dt.date | None = None) -> int:
    today = today or dt.datetime.now(IST).date()
    rows = _today_orders(Journal(journal_path(s)), today)
    out(f"Kip: {s.mod} — {today:%d.%m.%Y} günlüğü ({journal_path(s)})")
    if not rows:
        out("  bugün gönderilmiş emir yok")
    for key, r in rows.items():
        out(f"  {r.get('side', '?'):<4} {r.get('symbol', key):<6} {r.get('lots', '?')} lot limit {r.get('limit', '?')}: "
            f"{r.get('event')} (gerçekleşen {r.get('filled') or 0}, emir no {r.get('broker_id', '-')})")
    return 0


def cmd_cancel(s: ExecSettings, out=print, today: dt.date | None = None) -> int:
    """Botun bugün gönderdiği ve hâlâ bekleyen emirleri iptal eder."""
    if not s.live:
        out("İptal yalnızca gerçek kipte anlamlıdır (deneme kiplerinde emir gönderilmez).")
        return 0
    today = today or dt.datetime.now(IST).date()
    journal = Journal(journal_path(s))
    mine = _today_orders(journal, today)
    # Emir numarası -> yön: iptal isteğinde yön, yeni emirdeki kodlamayla gönderilir.
    sides = {r["broker_id"]: r.get("side") for r in mine.values() if r.get("broker_id")}
    record = calibration(s) or {}
    broker = MatriksBroker(s.matriks, echo_buy=record.get("yanit_alis"))
    try:
        broker.connect()
        waiting = broker.open_orders()
        targets = [o for o in waiting if str(o.get("OrderId") or "") in sides]
        # Emir numarası günlüğe düşmemiş (ilk yanıtta gelmemiş) emirler içerikle aranır.
        for row in mine.values():
            if row.get("broker_id") or row.get("event") not in ("accepted", "partial") or not row.get("symbol"):
                continue
            same = [o for o in waiting if o not in targets and str(o.get("Symbol") or "").upper() == row["symbol"]
                    and abs(_number(o.get("Price")) - float(row.get("limit") or 0)) < 1e-6
                    and int(_order_qty(o) + 1e-9) == int(row.get("lots") or 0)]
            if len(same) == 1:
                targets.append(same[0])
                sides[str(same[0].get("OrderId"))] = row.get("side")
        if not targets:
            out(f"İptal edilecek bekleyen bot emri bulunamadı (Matriks IQ'da {len(waiting)} bekleyen emir var).")
            return 0
        for o in targets:
            side = sides[str(o.get("OrderId"))]
            code = {"buy": s.matriks.alis_kodu, "sell": s.matriks.satis_kodu}.get(side)
            broker.cancel_raw(o, code)
            journal.record("cancel_requested", broker_id=str(o.get("OrderId")), symbol=o.get("Symbol"))
            out(f"İptal istendi: {o.get('Symbol')} {o.get('LeavesQty') or o.get('OrderQty')} lot "
                f"({STATUS_TEXT.get(str(o.get('OrdStatus')), '?')})")
        out("İptallerin gerçekleştiğini Matriks IQ emir penceresinden doğrulayın.")
        return 0
    except BrokerError as exc:
        out(f"HATA: {exc}")
        return 1
    finally:
        broker.close()
