#!/bin/python

import pandas as pd


class Tickers:
    def __init__(self):
        self.sp500url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        self.sp400url = 'https://en.wikipedia.org/wiki/List_of_S%26P_400_companies'
        self.sp600url = 'https://en.wikipedia.org/wiki/List_of_S%26P_600_companies'

        self.stocks_interest_file = "stocks_interest.csv"
        self.my_stocks_file = "my_stocks.csv"

        self.magnificent_seven = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]
        self.bitcoin = ["GBTC", "IBIT", "FBTC", "ARKB", "BITB", "BTCO", "HODL", "BRRR", "MARA", "COIN", "MSTR"]

        self.tickers_cache = {}

        # Load from CSVs
        self.stocks_interest = self.load_tickers_from_csv(self.stocks_interest_file)
        self.my_stocks = self.load_tickers_from_csv(self.my_stocks_file)

    def __str__(self):
        return "Available tickers' lists are: 'sp500_tickers', 'sp400_tickers', 'sp600_tickers', 'sp_1500', " \
               "'magnificent_seven', 'bitcoin', 'stocks_interest', 'my_stocks', 'big_list'"

    def fetch_tickers(self, url, force_refresh=False):
        if force_refresh or url not in self.tickers_cache:
            data = pd.read_html(url)[0]['Symbol'].tolist()
            self.tickers_cache[url] = [ticker.replace(".", "-") for ticker in data]
        return self.tickers_cache[url]

    def load_tickers_from_csv(self, filename):
        try:
            df = pd.read_csv(filename)
            if "ticker" in df.columns:
                return df["ticker"].dropna().astype(str).str.strip().tolist()
            else:
                return []
        except FileNotFoundError:
            return []

    def get_tickers_list(self, type: str):
        if type == 'sp500_tickers':
            return self.fetch_tickers(self.sp500url)
        elif type == 'sp400_tickers':
            return self.fetch_tickers(self.sp400url)
        elif type == 'sp600_tickers':
            return self.fetch_tickers(self.sp600url)
        elif type == 'sp_1500':
            return self.get_tickers_list('sp500_tickers') + \
                   self.get_tickers_list('sp400_tickers') + \
                   self.get_tickers_list('sp600_tickers')
        elif type == 'big_list':
            return list(set(
                self.get_tickers_list('sp_1500') +
                self.magnificent_seven +
                self.bitcoin +
                self.stocks_interest +
                self.my_stocks
            ))
        else:
            return getattr(self, type, [])