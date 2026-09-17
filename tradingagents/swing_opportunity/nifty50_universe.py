"""NIFTY 50 Universe and Derivative Contract Metadata.

Contains canonical .NS ticker identifiers for the constituent stocks of the
NIFTY 50 index (National Stock Exchange of India), along with their official
NSE F&O lot sizes, strike price step increments, sectors, and corporate names.
"""

from typing import Dict, Any, List

NIFTY_50_METADATA: Dict[str, Dict[str, Any]] = {
    "ADANIENT.NS": {
        "name": "Adani Enterprises Ltd.",
        "sector": "Metals & Mining",
        "lot_size": 300,
        "strike_step": 50.0,
    },
    "ADANIPORTS.NS": {
        "name": "Adani Ports and Special Economic Zone Ltd.",
        "sector": "Services / Infrastructure",
        "lot_size": 400,
        "strike_step": 20.0,
    },
    "APOLLOHOSP.NS": {
        "name": "Apollo Hospitals Enterprise Ltd.",
        "sector": "Healthcare",
        "lot_size": 125,
        "strike_step": 100.0,
    },
    "ASIANPAINT.NS": {
        "name": "Asian Paints Ltd.",
        "sector": "Consumer Durables",
        "lot_size": 200,
        "strike_step": 50.0,
    },
    "AXISBANK.NS": {
        "name": "Axis Bank Ltd.",
        "sector": "Financial Services",
        "lot_size": 625,
        "strike_step": 20.0,
    },
    "BAJAJ-AUTO.NS": {
        "name": "Bajaj Auto Ltd.",
        "sector": "Automobile",
        "lot_size": 75,
        "strike_step": 100.0,
    },
    "BAJFINANCE.NS": {
        "name": "Bajaj Finance Ltd.",
        "sector": "Financial Services",
        "lot_size": 125,
        "strike_step": 100.0,
    },
    "BAJAJFINSV.NS": {
        "name": "Bajaj Finserv Ltd.",
        "sector": "Financial Services",
        "lot_size": 500,
        "strike_step": 20.0,
    },
    "BEL.NS": {
        "name": "Bharat Electronics Ltd.",
        "sector": "Capital Goods / Defence",
        "lot_size": 1450,
        "strike_step": 5.0,
    },
    "BPCL.NS": {
        "name": "Bharat Petroleum Corporation Ltd.",
        "sector": "Oil & Gas",
        "lot_size": 1800,
        "strike_step": 5.0,
    },
    "BHARTIARTL.NS": {
        "name": "Bharti Airtel Ltd.",
        "sector": "Telecommunication",
        "lot_size": 475,
        "strike_step": 20.0,
    },
    "BRITANNIA.NS": {
        "name": "Britannia Industries Ltd.",
        "sector": "Fast Moving Consumer Goods",
        "lot_size": 200,
        "strike_step": 50.0,
    },
    "CIPLA.NS": {
        "name": "Cipla Ltd.",
        "sector": "Healthcare",
        "lot_size": 650,
        "strike_step": 20.0,
    },
    "COALINDIA.NS": {
        "name": "Coal India Ltd.",
        "sector": "Oil, Gas & Consumable Fuels",
        "lot_size": 2100,
        "strike_step": 5.0,
    },
    "DRREDDY.NS": {
        "name": "Dr. Reddy's Laboratories Ltd.",
        "sector": "Healthcare",
        "lot_size": 125,
        "strike_step": 50.0,
    },
    "EICHERMOT.NS": {
        "name": "Eicher Motors Ltd.",
        "sector": "Automobile",
        "lot_size": 150,
        "strike_step": 50.0,
    },
    "GRASIM.NS": {
        "name": "Grasim Industries Ltd.",
        "sector": "Construction Materials",
        "lot_size": 250,
        "strike_step": 20.0,
    },
    "HCLTECH.NS": {
        "name": "HCL Technologies Ltd.",
        "sector": "Information Technology",
        "lot_size": 350,
        "strike_step": 20.0,
    },
    "HDFCBANK.NS": {
        "name": "HDFC Bank Ltd.",
        "sector": "Financial Services",
        "lot_size": 550,
        "strike_step": 20.0,
    },
    "HDFCLIFE.NS": {
        "name": "HDFC Life Insurance Company Ltd.",
        "sector": "Financial Services",
        "lot_size": 1100,
        "strike_step": 10.0,
    },
    "HEROMOTOCO.NS": {
        "name": "Hero MotoCorp Ltd.",
        "sector": "Automobile",
        "lot_size": 150,
        "strike_step": 50.0,
    },
    "HINDALCO.NS": {
        "name": "Hindalco Industries Ltd.",
        "sector": "Metals & Mining",
        "lot_size": 700,
        "strike_step": 10.0,
    },
    "HINDUNILVR.NS": {
        "name": "Hindustan Unilever Ltd.",
        "sector": "Fast Moving Consumer Goods",
        "lot_size": 300,
        "strike_step": 20.0,
    },
    "ICICIBANK.NS": {
        "name": "ICICI Bank Ltd.",
        "sector": "Financial Services",
        "lot_size": 700,
        "strike_step": 10.0,
    },
    "ITC.NS": {
        "name": "ITC Ltd.",
        "sector": "Fast Moving Consumer Goods",
        "lot_size": 1600,
        "strike_step": 5.0,
    },
    "INDUSINDBK.NS": {
        "name": "IndusInd Bank Ltd.",
        "sector": "Financial Services",
        "lot_size": 500,
        "strike_step": 20.0,
    },
    "INFY.NS": {
        "name": "Infosys Ltd.",
        "sector": "Information Technology",
        "lot_size": 400,
        "strike_step": 20.0,
    },
    "JSWSTEEL.NS": {
        "name": "JSW Steel Ltd.",
        "sector": "Metals & Mining",
        "lot_size": 675,
        "strike_step": 10.0,
    },
    "KOTAKBANK.NS": {
        "name": "Kotak Mahindra Bank Ltd.",
        "sector": "Financial Services",
        "lot_size": 400,
        "strike_step": 20.0,
    },
    "LT.NS": {
        "name": "Larsen & Toubro Ltd.",
        "sector": "Construction",
        "lot_size": 150,
        "strike_step": 50.0,
    },
    "M&M.NS": {
        "name": "Mahindra & Mahindra Ltd.",
        "sector": "Automobile",
        "lot_size": 350,
        "strike_step": 20.0,
    },
    "MARUTI.NS": {
        "name": "Maruti Suzuki India Ltd.",
        "sector": "Automobile",
        "lot_size": 50,
        "strike_step": 100.0,
    },
    "NTPC.NS": {
        "name": "NTPC Ltd.",
        "sector": "Power",
        "lot_size": 1500,
        "strike_step": 5.0,
    },
    "NESTLEIND.NS": {
        "name": "Nestle India Ltd.",
        "sector": "Fast Moving Consumer Goods",
        "lot_size": 250,
        "strike_step": 50.0,
    },
    "ONGC.NS": {
        "name": "Oil & Natural Gas Corporation Ltd.",
        "sector": "Oil & Gas",
        "lot_size": 2250,
        "strike_step": 5.0,
    },
    "POWERGRID.NS": {
        "name": "Power Grid Corporation of India Ltd.",
        "sector": "Power",
        "lot_size": 1800,
        "strike_step": 5.0,
    },
    "RELIANCE.NS": {
        "name": "Reliance Industries Ltd.",
        "sector": "Oil, Gas & Consumable Fuels",
        "lot_size": 250,
        "strike_step": 20.0,
    },
    "SBILIFE.NS": {
        "name": "SBI Life Insurance Company Ltd.",
        "sector": "Financial Services",
        "lot_size": 750,
        "strike_step": 20.0,
    },
    "SHRIRAMFIN.NS": {
        "name": "Shriram Finance Ltd.",
        "sector": "Financial Services",
        "lot_size": 300,
        "strike_step": 20.0,
    },
    "SBIN.NS": {
        "name": "State Bank of India",
        "sector": "Financial Services",
        "lot_size": 1500,
        "strike_step": 10.0,
    },
    "SUNPHARMA.NS": {
        "name": "Sun Pharmaceutical Industries Ltd.",
        "sector": "Healthcare",
        "lot_size": 350,
        "strike_step": 20.0,
    },
    "TCS.NS": {
        "name": "Tata Consultancy Services Ltd.",
        "sector": "Information Technology",
        "lot_size": 175,
        "strike_step": 50.0,
    },
    "TATACONSUM.NS": {
        "name": "Tata Consumer Products Ltd.",
        "sector": "Fast Moving Consumer Goods",
        "lot_size": 900,
        "strike_step": 10.0,
    },
    "TMCV.NS": {
        "name": "Tata Motors Commercial Vehicles Ltd.",
        "sector": "Automobile",
        "lot_size": 700,
        "strike_step": 10.0,
    },
    "TATASTEEL.NS": {
        "name": "Tata Steel Ltd.",
        "sector": "Metals & Mining",
        "lot_size": 5500,
        "strike_step": 2.5,
    },
    "TECHM.NS": {
        "name": "Tech Mahindra Ltd.",
        "sector": "Information Technology",
        "lot_size": 600,
        "strike_step": 20.0,
    },
    "TITAN.NS": {
        "name": "Titan Company Ltd.",
        "sector": "Consumer Durables",
        "lot_size": 175,
        "strike_step": 50.0,
    },
    "TRENT.NS": {
        "name": "Trent Ltd.",
        "sector": "Consumer Services",
        "lot_size": 100,
        "strike_step": 100.0,
    },
    "ULTRACEMCO.NS": {
        "name": "UltraTech Cement Ltd.",
        "sector": "Construction Materials",
        "lot_size": 100,
        "strike_step": 100.0,
    },
    "WIPRO.NS": {
        "name": "Wipro Ltd.",
        "sector": "Information Technology",
        "lot_size": 1500,
        "strike_step": 5.0,
    },
}

NIFTY_50_TICKERS: List[str] = list(NIFTY_50_METADATA.keys())


def get_ticker_metadata(ticker: str) -> Dict[str, Any]:
    """Return metadata dict for given ticker, falling back to defaults if unknown."""
    if ticker in NIFTY_50_METADATA:
        return NIFTY_50_METADATA[ticker]
    clean_sym = ticker.replace(".NS", "")
    return {
        "name": f"{clean_sym} Ltd.",
        "sector": "NSE Equity",
        "lot_size": 250,
        "strike_step": 20.0,
    }


def get_lot_size(ticker: str) -> int:
    """Return official NSE F&O lot size for ticker."""
    return get_ticker_metadata(ticker).get("lot_size", 250)


def get_strike_step(ticker: str) -> float:
    """Return strike step increment for ticker options."""
    return get_ticker_metadata(ticker).get("strike_step", 20.0)


def get_company_name(ticker: str) -> str:
    """Return human-readable company name for ticker."""
    return get_ticker_metadata(ticker).get("name", ticker)


def get_sector(ticker: str) -> str:
    """Return sector classification for ticker."""
    return get_ticker_metadata(ticker).get("sector", "Diversified")
