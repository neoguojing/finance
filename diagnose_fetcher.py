import yfinance as yf
import akshare as ak
import pandas as pd
import requests

session = requests.Session()
session.headers.update(
    {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
)

ETF_FACTOR_FIELDS = [
    # 当前价格
    "regularMarketPrice",

    # 估值
    "trailingPE",
    "trailingPegRatio",

    # 趋势
    "fiftyDayAverage",
    "twoHundredDayAverage",

    # 分红
    "dividendYield",

    # 规模
    "totalAssets",

    # 费用
    "netExpenseRatio",

    # 风险
    "beta3Year",

    # 收益
    "ytdReturn",
    "fiveYearAverageReturn"
]

def get_etf_factors(symbol):

    print(
        f"--- Getting ETF Factors: {symbol} ---"
    )

    try:

        ticker = yf.Ticker(
            symbol,
            session=session
        )


        # info只请求一次
        info = ticker.info

        print(f"{symbol}: {info.keys()}")
        
        result = {
            "symbol": symbol
        }


        for field in ETF_FACTOR_FIELDS:

            result[field] = info.get(
                field,
                None
            )

        print(f"Retrieved factors for {symbol}: {result}")
        return result


    except Exception as e:

        print(
            f"Error getting {symbol}: {e}"
        )

        return {
            "symbol": symbol,
            "error": str(e)
        }

def get_vix():

    vix = yf.Ticker(
        "^VIX",
        session=session
    )

    return vix.history(
        period="5d"
    )["Close"].iloc[-1]
    
def diagnose_ashare(symbol):
    print(f"\n--- Diagnosing A-Share Symbol: {symbol} ---")
    try:
        df = ak.fund_etf_hist_em(
            symbol=symbol,
        )
        print("DataFrame Head:")
        print(df.head())
        print("Columns:", df.columns.tolist())
        
        # df = ak.index_value_hist_funddb(
        #     symbol=symbol,
        # )
        # print(df.head())
        
    except Exception as e:
        print(f"Error in A-share diagnostic: {e}")

if __name__ == "__main__":
    # get_etf_factors("QQQM")
    print(get_vix())
    # diagnose_ashare("588000")
