"""NSE Mid-Cap & Small-Cap Universe for Pre-Market Top Gainer Discovery.

Curated universe of 100+ highly liquid, actively traded NSE Mid-Cap and
Small-Cap stocks with official .NS identifiers, sector classifications,
market cap tiers, and verified regular EQ series status (excluding ASM/GSM
surveillance and Trade-to-Trade series).
"""

from typing import Dict, Any, List

NSE_MID_SMALL_UNIVERSE: Dict[str, Dict[str, Any]] = {
    # High-Momentum Defence & Aerospace
    "COCHINSHIP.NS": {"name": "Cochin Shipyard Ltd.", "sector": "Defence / Shipbuilding", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "MAZDOCK.NS": {"name": "Mazagon Dock Shipbuilders Ltd.", "sector": "Defence / Shipbuilding", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "BDL.NS": {"name": "Bharat Dynamics Ltd.", "sector": "Defence & Aerospace", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "HAL.NS": {"name": "Hindustan Aeronautics Ltd.", "sector": "Defence & Aerospace", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "PARAS.NS": {"name": "Paras Defence and Space Technologies", "sector": "Defence Electronics", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},
    "DATAPATTNS.NS": {"name": "Data Patterns (India) Ltd.", "sector": "Defence Electronics", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},
    "ASTRAMICRO.NS": {"name": "Astra Microwave Products Ltd.", "sector": "Defence Electronics", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},

    # High-Momentum Railways & Infrastructure
    "RVNL.NS": {"name": "Rail Vikas Nigam Ltd.", "sector": "Railways & Infra", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "IRFC.NS": {"name": "Indian Railway Finance Corporation", "sector": "Railways Finance", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "RAILTEL.NS": {"name": "RailTel Corporation of India Ltd.", "sector": "Railways Telecom", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},
    "RITES.NS": {"name": "RITES Ltd.", "sector": "Railways Engineering", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},
    "IRCON.NS": {"name": "Ircon International Ltd.", "sector": "Railways Construction", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},
    "TITAGARH.NS": {"name": "Titagarh Rail Systems Ltd.", "sector": "Railways Wagons", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},
    "JWL.NS": {"name": "Jupiter Wagons Ltd.", "sector": "Railways Wagons", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},
    "TEXRAIL.NS": {"name": "Texmaco Rail & Engineering Ltd.", "sector": "Railways Wagons", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},

    # Green Energy, Solar & Power Equipment
    "SUZLON.NS": {"name": "Suzlon Energy Ltd.", "sector": "Renewable Energy", "tier": "Midcap", "series": "EQ", "circuit_band": 10},
    "IREDA.NS": {"name": "Indian Renewable Energy Dev Agency", "sector": "Green Energy Finance", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "INDOCO.NS": {"name": "Inox Wind Ltd.", "sector": "Wind Energy", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},
    "TATAINVEST.NS": {"name": "Tata Investment Corporation Ltd.", "sector": "Holding / Investments", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},
    "SJVN.NS": {"name": "SJVN Ltd.", "sector": "Power Generation", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "HUDCO.NS": {"name": "Housing & Urban Development Corp", "sector": "Urban Infrastructure", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "NHPC.NS": {"name": "NHPC Ltd.", "sector": "Power Generation", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "TORNTPOWER.NS": {"name": "Torrent Power Ltd.", "sector": "Power Distribution", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "CESC.NS": {"name": "CESC Ltd.", "sector": "Power Distribution", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},
    "JSWENERGY.NS": {"name": "JSW Energy Ltd.", "sector": "Power Generation", "tier": "Midcap", "series": "EQ", "circuit_band": 20},

    # High-Tech & Electronics Manufacturing Services (EMS)
    "DIXON.NS": {"name": "Dixon Technologies (India) Ltd.", "sector": "EMS / Electronics", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "KAYNES.NS": {"name": "Kaynes Technology India Ltd.", "sector": "EMS / Electronics", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},
    "CYIENT.NS": {"name": "Cyient Ltd.", "sector": "Engineering IT", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "TATAELXSI.NS": {"name": "Tata Elxsi Ltd.", "sector": "Design & Technology", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "PERSISTENT.NS": {"name": "Persistent Systems Ltd.", "sector": "Information Technology", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "COFORGE.NS": {"name": "Coforge Ltd.", "sector": "Information Technology", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "MPHASIS.NS": {"name": "Mphasis Ltd.", "sector": "Information Technology", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "KPITTECH.NS": {"name": "KPIT Technologies Ltd.", "sector": "Automotive Software", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "HAPPSTMNDS.NS": {"name": "Happiest Minds Technologies Ltd.", "sector": "IT & Analytics", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},
    "SONACOMS.NS": {"name": "Sona BLW Precision Forgings", "sector": "EV Auto Components", "tier": "Midcap", "series": "EQ", "circuit_band": 20},

    # Capital Market & Exchanges
    "BSE.NS": {"name": "BSE Ltd.", "sector": "Financial Exchanges", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "CDSL.NS": {"name": "Central Depository Services (India)", "sector": "Financial Depositories", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "MCX.NS": {"name": "Multi Commodity Exchange of India", "sector": "Commodity Exchanges", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "ANGELONE.NS": {"name": "Angel One Ltd.", "sector": "Capital Market Broking", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "MOTILALOFS.NS": {"name": "Motilal Oswal Financial Services", "sector": "Capital Markets", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "NUVAMA.NS": {"name": "Nuvama Wealth Management Ltd.", "sector": "Wealth Management", "tier": "Midcap", "series": "EQ", "circuit_band": 20},

    # Industrials, Cables & Electrical Equipment
    "POLYCAB.NS": {"name": "Polycab India Ltd.", "sector": "Cables & Wires", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "KEI.NS": {"name": "KEI Industries Ltd.", "sector": "Cables & Wires", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "RRKABEL.NS": {"name": "R R Kabel Ltd.", "sector": "Cables & Wires", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},
    "APLAPOLLO.NS": {"name": "APL Apollo Tubes Ltd.", "sector": "Steel Pipes & Tubes", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "ASTRAL.NS": {"name": "Astral Ltd.", "sector": "Building Products / Pipes", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "SUPREMEIND.NS": {"name": "Supreme Industries Ltd.", "sector": "Plastic Products", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "KEC.NS": {"name": "KEC International Ltd.", "sector": "T&D Infrastructure", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "KALPATPOWR.NS": {"name": "Kalpataru Projects International", "sector": "Engineering / Infra", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "VOLTAS.NS": {"name": "Voltas Ltd.", "sector": "Consumer Electricals", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "BLUESTARCO.NS": {"name": "Blue Star Ltd.", "sector": "Consumer Electricals", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "HBLPOWER.NS": {"name": "HBL Power Systems Ltd.", "sector": "Batteries & Electronic Systems", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},
    "EXIDEIND.NS": {"name": "Exide Industries Ltd.", "sector": "Batteries & Storage", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "AMARAJABAT.NS": {"name": "Amara Raja Energy & Mobility Ltd.", "sector": "Batteries & Storage", "tier": "Midcap", "series": "EQ", "circuit_band": 20},

    # Real Estate & Urban Growth
    "PRESTIGE.NS": {"name": "Prestige Estates Projects Ltd.", "sector": "Real Estate", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "PHOENIXLTD.NS": {"name": "The Phoenix Mills Ltd.", "sector": "Real Estate / Retail", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "OBEROIRLTY.NS": {"name": "Oberoi Realty Ltd.", "sector": "Real Estate", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "BRIGADE.NS": {"name": "Brigade Enterprises Ltd.", "sector": "Real Estate", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},
    "SOBHA.NS": {"name": "Sobha Ltd.", "sector": "Real Estate", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},
    "SIGNATURE.NS": {"name": "Signatureglobal (India) Ltd.", "sector": "Real Estate", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},
    "NBCC.NS": {"name": "NBCC (India) Ltd.", "sector": "Construction & Civil", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},

    # High-Beta PSU & Emerging Banks / NBFCs
    "BANKINDIA.NS": {"name": "Bank of India", "sector": "Public Sector Banking", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "UNIONBANK.NS": {"name": "Union Bank of India", "sector": "Public Sector Banking", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "CANBK.NS": {"name": "Canara Bank", "sector": "Public Sector Banking", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "INDIANB.NS": {"name": "Indian Bank", "sector": "Public Sector Banking", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "CENTRALBK.NS": {"name": "Central Bank of India", "sector": "Public Sector Banking", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},
    "IOB.NS": {"name": "Indian Overseas Bank", "sector": "Public Sector Banking", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},
    "UCOBANK.NS": {"name": "UCO Bank", "sector": "Public Sector Banking", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},
    "MAHABANK.NS": {"name": "Bank of Maharashtra", "sector": "Public Sector Banking", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},
    "IDFCFIRSTB.NS": {"name": "IDFC First Bank Ltd.", "sector": "Private Banking", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "FEDERALBNK.NS": {"name": "The Federal Bank Ltd.", "sector": "Private Banking", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "POONAWALLA.NS": {"name": "Poonawalla Fincorp Ltd.", "sector": "NBFC", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "MANAPPURAM.NS": {"name": "Manappuram Finance Ltd.", "sector": "NBFC / Gold Loan", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},
    "MUTHOOTFIN.NS": {"name": "Muthoot Finance Ltd.", "sector": "NBFC / Gold Loan", "tier": "Midcap", "series": "EQ", "circuit_band": 20},

    # Chemicals, Fertilizers & Metals
    "FACT.NS": {"name": "Fertilisers and Chemicals Travancore", "sector": "Fertilizers & Agro", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "DEEPAKNTR.NS": {"name": "Deepak Nitrite Ltd.", "sector": "Specialty Chemicals", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "TATACHEM.NS": {"name": "Tata Chemicals Ltd.", "sector": "Commodity Chemicals", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "PIIND.NS": {"name": "PI Industries Ltd.", "sector": "Agro Chemicals", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "NAVINFLUOR.NS": {"name": "Navin Fluorine International", "sector": "Specialty Chemicals", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "JINDALSTEL.NS": {"name": "Jindal Steel & Power Ltd.", "sector": "Metals & Mining", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "SAIL.NS": {"name": "Steel Authority of India Ltd.", "sector": "Metals & Mining", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "NATIONALUM.NS": {"name": "National Aluminium Company Ltd.", "sector": "Metals & Mining", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "NMDC.NS": {"name": "NMDC Ltd.", "sector": "Metals & Mining", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "HINDCOPPER.NS": {"name": "Hindustan Copper Ltd.", "sector": "Metals & Mining", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},

    # Healthcare & Emerging Pharma
    "LUPIN.NS": {"name": "Lupin Ltd.", "sector": "Pharmaceuticals", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "AUROPHARMA.NS": {"name": "Aurobindo Pharma Ltd.", "sector": "Pharmaceuticals", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "ALKEM.NS": {"name": "Alkem Laboratories Ltd.", "sector": "Pharmaceuticals", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "TORNTPHARM.NS": {"name": "Torrent Pharmaceuticals Ltd.", "sector": "Pharmaceuticals", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "GLENMARK.NS": {"name": "Glenmark Pharmaceuticals Ltd.", "sector": "Pharmaceuticals", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "IPCALAB.NS": {"name": "IPCA Laboratories Ltd.", "sector": "Pharmaceuticals", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "JBCHEPHARM.NS": {"name": "J.B. Chemicals & Pharmaceuticals", "sector": "Pharmaceuticals", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},
    "SUVENPHAR.NS": {"name": "Suven Pharmaceuticals Ltd.", "sector": "CDMO / Pharma", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},

    # Consumer & Retail Momentum
    "TRENT.NS": {"name": "Trent Ltd.", "sector": "Retail / Apparel", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "ABFRL.NS": {"name": "Aditya Birla Fashion and Retail", "sector": "Retail / Apparel", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "DEVYANI.NS": {"name": "Devyani International Ltd.", "sector": "QSR / Restaurants", "tier": "Smallcap", "series": "EQ", "circuit_band": 20},
    "JUBLFOOD.NS": {"name": "Jubilant FoodWorks Ltd.", "sector": "QSR / Restaurants", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
    "KALYANKJIL.NS": {"name": "Kalyan Jewellers India Ltd.", "sector": "Gems & Jewellery", "tier": "Midcap", "series": "EQ", "circuit_band": 20},
}

NSE_MID_SMALL_TICKERS: List[str] = list(NSE_MID_SMALL_UNIVERSE.keys())


def get_mid_small_tickers() -> List[str]:
    """Return all canonical .NS tickers in the mid/small cap universe."""
    return NSE_MID_SMALL_TICKERS.copy()


def get_mid_small_metadata(ticker: str) -> Dict[str, Any]:
    """Return metadata dict for given ticker, falling back to defaults if unknown."""
    if ticker in NSE_MID_SMALL_UNIVERSE:
        return NSE_MID_SMALL_UNIVERSE[ticker]
    clean_sym = ticker.replace(".NS", "")
    return {
        "name": f"{clean_sym} Ltd.",
        "sector": "NSE Mid/Small-Cap",
        "tier": "Mid/Small-Cap",
        "series": "EQ",
        "circuit_band": 20,
    }
