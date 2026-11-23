"""Crypto Time Machine: replay a historical window with live decision rules.

The Time Machine is decision support, not evidence of future returns. It reports
sample size, cost assumptions, and per-pair results so a small or unprofitable
sample cannot be mistaken for an edge.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

from .backtest import BacktestStats, TradeOutcome, summarize
from .backtest_runner import BacktestResult, BacktestTrade, RegimeTimeline, replay_pair
from .binance import BinancePublicClient, drop_forming_candle
from .config import Settings

#: Binance USDⓈ-M futures taker fee, in basis points, per side.
DEFAULT_FEE_BPS = 5.0
#: Assumed adverse slippage per side, in basis points.
DEFAULT_SLIPPAGE_BPS = 2.0
#: Extra history loaded so EMA-50 and the 4h regime are warm at window start.
WARMUP_DAYS = 15


@dataclass(frozen=True, slots=True)
class TimeMachineReport:
    days: int
    start: datetime
    end: datetime
    results: tuple[BacktestResult, ...]
    regime_counts: dict[str, int]
    fee_bps: float = DEFAULT_FEE_BPS
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS

    @property
    def trades(self) -> tuple[BacktestTrade, ...]:
        return tuple(trade for result in self.results for trade in result.trades)

    @property
    def candidates(self) -> int:
        return sum(result.candidates for result in self.results)

    @property
    def blocked(self) -> int:
        return sum(result.blocked for result in self.results)

    @property
    def no_fills(self) -> int:
        return sum(result.no_fills for result in self.results)

    def _cost_r(self, trade: BacktestTrade) -> float:
        """Round-trip cost expressed in units of initial risk."""

        risk = trade.outcome.risk
        if risk <= 0:
            return 0.0
        fraction = 2 * (self.fee_bps + self.slippage_bps) / 10_000
        return trade.outcome.entry * fraction / risk

    @property
    def gross_stats(self) -> BacktestStats:
        return summarize([trade.outcome for trade in self.trades])

    @property
    def net_stats(self) -> BacktestStats:
        adjusted: list[TradeOutcome] = [
            replace(trade.outcome, r_multiple=trade.outcome.r_multiple - self._cost_r(trade))
            for trade in self.trades
        ]
        return summarize(adjusted)


def _trim(result: BacktestResult, start: datetime) -> BacktestResult:
    trades = tuple(
        trade
        for trade in result.trades
        if trade.signal.candle_open_time is None or trade.signal.candle_open_time >= start
    )
    return replace(
        result,
        trades=trades,
        stats=summarize([trade.outcome for trade in trades]),
    )


def run_time_machine(
    client: BinancePublicClient,
    settings: Settings,
    pairs: tuple[str, ...] | None = None,
    days: int | None = None,
    now: datetime | None = None,
    fee_bps: float = DEFAULT_FEE_BPS,
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
) -> TimeMachineReport:
    """Replay the live rules over the last ``days`` of Binance history."""

    window_days = days or settings.time_machine_days
    end = now or datetime.now(UTC)
    start = end - timedelta(days=window_days)
    history_start = start - timedelta(days=WARMUP_DAYS)

    btc_1h = drop_forming_candle(
        client.klines_history(
            "BTCUSDT",
            settings.confirmation_timeframe,
            history_start,
            end,
            settings.request_pause_seconds,
        )
    )
    btc_4h = drop_forming_candle(
        client.klines_history(
            "BTCUSDT", settings.regime_timeframe, history_start, end, settings.request_pause_seconds
        )
    )
    timeline = RegimeTimeline(btc_1h, btc_4h)

    results: list[BacktestResult] = []
    for pair in pairs or settings.pairs:
        entry = drop_forming_candle(
            client.klines_history(
                pair, settings.entry_timeframe, history_start, end, settings.request_pause_seconds
            )
        )
        confirmation = drop_forming_candle(
            client.klines_history(
                pair,
                settings.confirmation_timeframe,
                history_start,
                end,
                settings.request_pause_seconds,
            )
        )
        if entry.empty or confirmation.empty:
            continue
        result = replay_pair(pair, entry, confirmation, settings, timeline)
        results.append(_trim(result, start))

    return TimeMachineReport(
        window_days,
        start,
        end,
        tuple(results),
        timeline.counts(),
        fee_bps,
        slippage_bps,
    )


def _rate(value: float) -> str:
    return f"{value * 100:.1f}%"


def _factor(value: float) -> str:
    return "∞" if value == float("inf") else f"{value:.2f}"


def format_time_machine_markdown(report: TimeMachineReport) -> str:
    """Full report, suitable for saving next to the journal."""

    gross = report.gross_stats
    net = report.net_stats
    lines = [
        "# Crypto Time Machine",
        "",
        f"Window: {report.start:%Y-%m-%d %H:%M} UTC → {report.end:%Y-%m-%d %H:%M} UTC",
        f"Days: {report.days} · Pairs: {len(report.results)}",
        f"Regime distribution: UP {report.regime_counts.get('UP', 0)} · "
        f"HOLD {report.regime_counts.get('HOLD', 0)} · DOWN {report.regime_counts.get('DOWN', 0)}",
        "",
        "## Overall",
        "",
        f"- Candidates: {report.candidates} · blocked by gates: {report.blocked}",
        f"- Trades: {gross.trades} (wins {gross.wins}, losses {gross.losses}, "
        f"timeouts {gross.timeouts}) · no-fill cancellations: {report.no_fills}",
        f"- Win rate: {_rate(gross.win_rate)} · average R: {gross.average_r:+.2f} · "
        f"profit factor: {_factor(gross.profit_factor)}",
        f"- Max consecutive losses: {gross.max_consecutive_losses}",
        f"- Cost model: {report.fee_bps:.1f} bps fee + "
        f"{report.slippage_bps:.1f} bps slippage per side",
        f"- Net average R after costs: {net.average_r:+.2f} · "
        f"net profit factor: {_factor(net.profit_factor)}",
        "",
        "## Per pair",
        "",
        "| Pair | Trades | Win rate | Avg R (net) | Profit factor (net) | Max loss streak |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for result in report.results:
        pair_net = summarize(
            [
                replace(trade.outcome, r_multiple=trade.outcome.r_multiple - report._cost_r(trade))
                for trade in result.trades
            ]
        )
        lines.append(
            f"| {result.pair} | {pair_net.trades} | {_rate(pair_net.win_rate)} | "
            f"{pair_net.average_r:+.2f} | {_factor(pair_net.profit_factor)} | "
            f"{pair_net.max_consecutive_losses} |"
        )

    ordered = sorted(report.trades, key=lambda trade: trade.outcome.r_multiple, reverse=True)
    if ordered:
        lines += ["", "## Best and worst trades", ""]
        for trade in ordered[:3]:
            lines.append(
                f"- Best: {trade.signal.pair} {trade.signal.side.value} "
                f"{trade.outcome.result} {trade.outcome.r_multiple:+.2f}R "
                f"({trade.outcome.bars_held} bars)"
            )
        for trade in ordered[-3:][::-1]:
            lines.append(
                f"- Worst: {trade.signal.pair} {trade.signal.side.value} "
                f"{trade.outcome.result} {trade.outcome.r_multiple:+.2f}R "
                f"({trade.outcome.bars_held} bars)"
            )

    lines += [
        "",
        "## Read this before using the numbers",
        "",
        "- Fills happen only inside the published entry zone and are cancelled if",
        "  price does not return within the wait window; a bar that touches both the",
        "  zone and the stop is counted as a stop.",
        "- Costs are subtracted from R, but funding payments are not included.",
        "- The replay uses the same `build_signal`, gates, cooldown, and stop-first",
        "  outcome contract as the live scanner.",
        "- Fewer than 30 trades is a sample, not an edge. Do not size risk from it.",
        "- Past behaviour of this ruleset is not a forecast.",
        "",
        "Manual execution only. No order was placed. Not financial advice.",
    ]
    return "\n".join(lines)


def format_time_machine_message(report: TimeMachineReport) -> str:
    """Compact version for Telegram."""

    gross = report.gross_stats
    net = report.net_stats
    return "\n".join(
        [
            "🕰️ <b>CRYPTO TIME MACHINE</b>",
            f"Window: {report.days} days · {len(report.results)} pairs",
            f"Candidates: {report.candidates} · blocked: {report.blocked}",
            f"Trades: {gross.trades} · win rate: {_rate(gross.win_rate)}",
            f"Gross avg R: {gross.average_r:+.2f} · net avg R: {net.average_r:+.2f}",
            f"Profit factor: {_factor(gross.profit_factor)} gross · "
            f"{_factor(net.profit_factor)} net",
            f"Max loss streak: {gross.max_consecutive_losses}",
            "",
            "Replay only. Manual execution. Not financial advice.",
        ]
    )
