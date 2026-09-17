"""CLI symbol validation/classification must agree with the data path.

Regressions for #980 (validation rejected GC=F), #981 (BTCUSD misclassified as
stock), #982 (BTC-USDT accepted but unpriceable on Yahoo).
"""
import pytest

from cli.models import AssetType
from cli.utils import detect_asset_type, is_valid_ticker_input, normalize_ticker_symbol
from tradingagents.dataflows.symbol_utils import normalize_symbol


# --- #982: stablecoin-quoted crypto normalizes to Yahoo's -USD pair ---
@pytest.mark.parametrize("raw,expected", [
    ("BTCUSD", "BTC-USD"),
    ("BTCUSDT", "BTC-USD"),
    ("BTC-USDT", "BTC-USD"),
    ("BTC-USDC", "BTC-USD"),
    ("ethusdt", "ETH-USD"),
    # non-crypto must be untouched
    ("AAPL", "AAPL"),
    ("GC=F", "GC=F"),
    ("600519.SS", "600519.SS"),
    ("EURUSD", "EURUSD=X"),
])
def test_normalize_symbol_crypto_and_passthrough(raw, expected):
    assert normalize_symbol(raw) == expected


# --- NSE validation: validation accepts .NS symbols and rejects non-.NS ---
@pytest.mark.parametrize("value,ok", [
    ("RELIANCE.NS", True),
    ("TCS.NS", True),
    ("infy.ns", True),
    ("", True),                 # empty -> defaults to RELIANCE.NS downstream
    ("AAPL", False),            # non-NSE rejected
    ("GC=F", False),            # commodity future rejected
    ("0700.HK", False),         # HK stock rejected
    ("bad symbol!", False),     # space + '!' rejected
    (".NS", False),             # empty ticker base rejected
    ("A" * 40, False),          # too long
])
def test_ticker_input_validation(value, ok):
    assert is_valid_ticker_input(value) is ok


def test_validate_nse_ticker():
    from tradingagents.dataflows.symbol_utils import validate_nse_ticker

    assert validate_nse_ticker("RELIANCE.NS") == "RELIANCE.NS"
    assert validate_nse_ticker("tcs.ns") == "TCS.NS"
    assert validate_nse_ticker("  infy.ns  ") == "INFY.NS"

    with pytest.raises(ValueError, match="TradingAgents is restricted to NSE"):
        validate_nse_ticker("AAPL")

    with pytest.raises(ValueError, match="TradingAgents is restricted to NSE"):
        validate_nse_ticker("BTC-USD")

    with pytest.raises(ValueError, match="Ticker symbol cannot be empty"):
        validate_nse_ticker("")


# --- #981/#982: asset-type classified on the canonical symbol ---
@pytest.mark.parametrize("raw,expected", [
    ("BTCUSD", AssetType.CRYPTO),
    ("BTC-USDT", AssetType.CRYPTO),
    ("BTC-USD", AssetType.CRYPTO),
    ("ETHUSD", AssetType.CRYPTO),
    ("AAPL", AssetType.STOCK),
    ("GC=F", AssetType.STOCK),
    ("600519.SS", AssetType.STOCK),
])
def test_detect_asset_type(raw, expected):
    assert detect_asset_type(raw) == expected


def test_cli_normalize_delegates_to_data_layer():
    # CLI must produce the same canonical symbol the data path will price.
    for raw in ("XAUUSD", "BTCUSD", "btc-usdt", "AAPL"):
        assert normalize_ticker_symbol(raw) == normalize_symbol(raw)
