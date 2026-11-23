from crypto_signal_bot.context import MarketContext, MarketRegime
from crypto_signal_bot.reporting import format_report
from crypto_signal_bot.scanner import PairScan, ScanReport


def test_empty_report_explicitly_says_hold() -> None:
    report = ScanReport(
        MarketContext(MarketRegime.HOLD, 50, "1h/4h", ("Mixed",)), (PairScan("BTCUSDT", None, ()),)
    )
    text = format_report(report)
    assert "MARKET REGIME: HOLD" in text
    assert "HOLD / WAIT" in text
