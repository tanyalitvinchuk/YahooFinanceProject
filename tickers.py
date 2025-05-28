#!/bin/python

import pandas as pd
import os
import requests
import yfinance as yf
from datetime import datetime, timedelta



class Tickers:
    def __init__(self):
        self.sp500url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        self.sp400url = 'https://en.wikipedia.org/wiki/List_of_S%26P_400_companies'
        self.sp600url = 'https://en.wikipedia.org/wiki/List_of_S%26P_600_companies'

        self.magnificent_seven = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]
        self.bitcoin = ["GBTC", "IBIT", "FBTC", "ARKB", "BITB", "BTCO", "HODL", "BRRR", "MARA", "COIN", "MSTR"]

        self.tickers_cache = {}

        # Get the directory where the currently running script is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Construct the full path to the CSV file
        csv_file_path1 = os.path.join(current_dir, 'real_my_stocks.csv')
        csv_file_path2 = os.path.join(current_dir, 'real_stocks_interest.csv')
        # Check if the file exists and set the parameter
        self.stocks_interest_file = 'real_stocks_interest.csv' if os.path.isfile(csv_file_path2) else 'stocks_interest.csv'
        self.my_stocks_file = 'real_my_stocks.csv' if os.path.isfile(csv_file_path1) else 'my_stocks.csv'

        # Load from CSVs
        self.stocks_interest = self.load_tickers_from_csv(self.stocks_interest_file)
        self.my_stocks = self.load_tickers_from_csv(self.my_stocks_file)

        self.headers = {
            "User-Agent": (
                f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/113.0.0.0 Safari/537.36 "
                f"(Contact: your-email@example.com)"
            )
        }
        self.all_us_tickers = self.get_sec_tickers()


    def __str__(self):
        return "Available tickers' lists are: 'sp500_tickers', 'sp400_tickers', 'sp600_tickers', 'sp_1500', " \
               "'magnificent_seven', 'bitcoin', 'stocks_interest', 'my_stocks', 'big_list', 'all_us_tickers'"

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

    def get_sec_tickers(self):
        """
        Downloads a list of tickers from the SEC's public company dataset.

        Returns:
            list of str: Ticker symbols.
        """
        url = "https://www.sec.gov/files/company_tickers.json"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            tickers = [entry['ticker'] for entry in data.values()]
            return tickers

        except Exception as e:
            print(f"Error fetching tickers: {e}")
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
        elif type == 'all_us_tickers':
            return self.all_us_tickers
        else:
            return getattr(self, type, [])