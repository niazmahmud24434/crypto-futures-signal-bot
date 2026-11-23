from crypto_signal_bot.binance import BinanceDataError, BinancePublicClient

EXCHANGE_INFO = {
    "symbols": [
        {
            "symbol": "BTCUSDT",
            "contractType": "PERPETUAL",
            "quoteAsset": "USDT",
            "status": "TRADING",
            "underlyingType": "COIN",
        },
        {
            "symbol": "INTCUSDT",
            "contractType": "TRADIFI_PERPETUAL",
            "quoteAsset": "USDT",
            "status": "TRADING",
            "underlyingType": "EQUITY",
        },
        {
            "symbol": "XAUUSDT",
            "contractType": "TRADIFI_PERPETUAL",
            "quoteAsset": "USDT",
            "status": "TRADING",
            "underlyingType": "COMMODITY",
        },
        {
            "symbol": "DEADUSDT",
            "contractType": "PERPETUAL",
            "quoteAsset": "USDT",
            "status": "SETTLING",
            "underlyingType": "COIN",
        },
    ]
}

TICKERS = [
    {"symbol": "BTCUSDT", "quoteVolume": "100"},
    {"symbol": "INTCUSDT", "quoteVolume": "900"},
    {"symbol": "XAUUSDT", "quoteVolume": "800"},
    {"symbol": "DEADUSDT", "quoteVolume": "700"},
]


class StubClient(BinancePublicClient):
    def __init__(self, fail_info: bool = False) -> None:
        object.__setattr__(self, "base_url", "https://stub.invalid")
        object.__setattr__(self, "timeout_seconds", 1.0)
        object.__setattr__(self, "_fail_info", fail_info)

    def _get(self, path: str, params: dict[str, object] | None = None) -> object:
        if self._fail_info:
            raise BinanceDataError("forced failure")
        return EXCHANGE_INFO

    def ticker_24h(self) -> list[dict[str, object]]:
        return TICKERS


def test_tokenized_equities_and_commodities_are_excluded() -> None:
    client = StubClient()
    assert client.top_usdt_pairs(limit=10) == ["BTCUSDT"]


def test_universe_falls_back_to_exclusion_list_when_metadata_fails() -> None:
    client = StubClient(fail_info=True)
    pairs = client.top_usdt_pairs(limit=10, excluded_bases=("INTC", "XAU"))
    assert pairs == ["DEADUSDT", "BTCUSDT"]


def test_non_crypto_mode_keeps_all_usdt_pairs() -> None:
    client = StubClient()
    assert client.top_usdt_pairs(limit=10, crypto_only=False) == [
        "INTCUSDT",
        "XAUUSDT",
        "DEADUSDT",
        "BTCUSDT",
    ]
