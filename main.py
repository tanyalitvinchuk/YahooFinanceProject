#!/bin/python

from bs4 import BeautifulSoup
import requests
import yfinance as yf
import pandas as pd
import mysql.connector
from datetime import datetime, timedelta
from scipy.stats import linregress
import matplotlib.pyplot as plt
import os
import matplotlib.dates as mdates
import numpy as np
from nasdaq_ipo_scraper import NasdaqIPOScraper
from nasdaq_earnings_scraper import NasdaqEarningsScraper
from get_news import GetNews
from tickers import Tickers


class GetStockData:
    def __init__(self, type: str):
        self.tickers_list = Tickers().get_tickers_list(type)
        self.load_company_info()
        self.getting_the_data()

    def load_company_info(self):
        try:
            self.company_info_df = pd.read_csv("company_info.csv")
        except FileNotFoundError:
            self.company_info_df = pd.DataFrame(columns=["Ticker", "Short Name", "Industry", "Sector", "Country"])

    def get_company_info(self, ticker):
        # Check if info is already in the CSV
        if ticker in self.company_info_df["Ticker"].values:
            row = self.company_info_df[self.company_info_df["Ticker"] == ticker].iloc[0]
            return {
                "Short Name": row["Short Name"],
                "Industry": row["Industry"],
                "Sector": row["Sector"],
            }
        else:
            # Fetch data from yfinance
            company = yf.Ticker(ticker)
            info = company.info
            company_data = {
                "Ticker": ticker,
                "Short Name": info.get("shortName"),
                "Industry": info.get("industry"),
                "Sector": info.get("sector"),
            }
            # Append to DataFrame and save to CSV
            self.company_info_df = pd.concat([self.company_info_df, pd.DataFrame([company_data])], ignore_index=True)
            self.company_info_df.to_csv("company_info.csv", index=False)
            return company_data

    def getting_the_data(self):
        today = datetime.today()
        five_years_ago = today - timedelta(days=5 * 365)
        data = yf.download(self.tickers_list, start=five_years_ago, end=today, group_by='ticker')
        all_data = []

        for ticker in self.tickers_list:
            ticker_data = data[ticker].reset_index()
            ticker_data['Symbol'] = ticker

            ticker_data['EMA_12'] = ticker_data['Close'].ewm(span=12, adjust=False).mean()
            ticker_data['EMA_26'] = ticker_data['Close'].ewm(span=26, adjust=False).mean()
            ticker_data['MACD_Line'] = ticker_data['EMA_12'] - ticker_data['EMA_26']
            ticker_data['MACD_Signal'] = ticker_data['MACD_Line'].ewm(span=9, adjust=False).mean()
            ticker_data['MACD_Histogram'] = ticker_data['MACD_Line'] - ticker_data['MACD_Signal']

            # Rolling Moving Averages for Stock Price
            ticker_data['5_Day_MA'] = ticker_data['Close'].rolling(window=5).mean()
            ticker_data['50_Day_MA'] = ticker_data['Close'].rolling(window=50).mean()
            ticker_data['250_Day_MA'] = ticker_data['Close'].rolling(window=250).mean()

            # Rolling Moving Averages for Volume
            ticker_data['5_Day_Volume_MA'] = ticker_data['Volume'].rolling(window=5).mean()
            ticker_data['50_Day_Volume_MA'] = ticker_data['Volume'].rolling(window=50).mean()
            ticker_data['250_Day_Volume_MA'] = ticker_data['Volume'].rolling(window=250).mean()

            # Daily Percent Change for Volume
            ticker_data['Daily_Volume_%_Change'] = ticker_data['Volume'].pct_change() * 100

            # Rolling Min/Max for 3-Month and 52-Week Periods
            ticker_data['3_Month_Low'] = ticker_data['Low'].rolling(window=63, min_periods=1).min()
            ticker_data['3_Month_High'] = ticker_data['High'].rolling(window=63, min_periods=1).max()
            ticker_data['1_Month_Low'] = ticker_data['Low'].rolling(window=21, min_periods=1).min()
            ticker_data['1_Month_High'] = ticker_data['High'].rolling(window=21, min_periods=1).max()
            ticker_data['5_Years_Low'] = ticker_data['Low'].rolling(window=1250, min_periods=1).min()
            ticker_data['5_Years_High'] = ticker_data['High'].rolling(window=1250, min_periods=1).max()
            ticker_data['Percent_Diff_3M_Low'] = (ticker_data['Close'] - ticker_data['3_Month_Low']) / ticker_data[
                '3_Month_Low'] * 100
            ticker_data['Percent_Diff_3M_High'] = (ticker_data['Close'] - ticker_data['3_Month_High']) / ticker_data[
                '3_Month_High'] * 100
            ticker_data['52_Week_Low'] = ticker_data['Low'].rolling(window=252, min_periods=1).min()
            ticker_data['52_Week_High'] = ticker_data['High'].rolling(window=252, min_periods=1).max()
            ticker_data['Percent_Diff_From_52_Week_Low'] = (ticker_data['Close'] - ticker_data['52_Week_Low']) / \
                                                           ticker_data['52_Week_Low'] * 100
            ticker_data['Percent_Diff_From_52_Week_High'] = (ticker_data['Close'] - ticker_data['52_Week_High']) / \
                                                            ticker_data['52_Week_High'] * 100
            # Binary fields for 52 Week Low/High
            ticker_data['Hit_52_Week_Low'] = (ticker_data['Low'] == ticker_data['52_Week_Low']).astype(int)
            ticker_data['Hit_52_Week_High'] = (ticker_data['High'] == ticker_data['52_Week_High']).astype(int)

            # Daily Percentage Change in Closing Price
            ticker_data['Percent_Change'] = ticker_data['Close'].pct_change() * 100

            # Linear Regression on a 5-day rolling basis
            slopes = []
            r_squareds = []
            p_values = []

            for i in range(len(ticker_data)):
                if i >= 4:  # Start calculating after at least 5 days of data
                    y = ticker_data['Close'].iloc[i - 4:i + 1].values
                    x = range(len(y))
                    regression_result = linregress(x, y)
                    slopes.append(regression_result.slope)
                    r_squareds.append(regression_result.rvalue ** 2)
                    p_values.append(regression_result.pvalue)
                else:
                    slopes.append(None)
                    r_squareds.append(None)
                    p_values.append(None)

            ticker_data['5_Day_Slope'] = slopes
            ticker_data['5_Day_R_Squared'] = r_squareds
            ticker_data['5_Day_P_Value'] = p_values

            all_data.append(ticker_data)

        # Combine all ticker data into one DataFrame
        self.stock_prices_df = pd.concat(all_data, ignore_index=True)

        # Save DataFrame to CSV
        self.stock_prices_df.to_csv("stock_prices_data.csv", index=False)
        print("Stock prices data saved to 'stock_prices_data.csv'")

        # Save only the latest available date's data for each ticker
        latest_data = self.stock_prices_df.sort_values('Date').groupby('Symbol', as_index=False).last()
        latest_data.to_csv("latest_stock_prices_data.csv", index=False)
        print("Latest stock prices data saved to 'latest_stock_prices_data.csv'")

    def get_top_movers(self, date_str):
        # Filter for the selected date
        date_data = self.stock_prices_df[self.stock_prices_df['Date'] == date_str]

        # Ensure Percent_Change is numeric
        date_data['Percent_Change'] = pd.to_numeric(date_data['Percent_Change'], errors='coerce')

        # Sort for top gainers and losers
        top_10_risers = date_data.sort_values(by='Percent_Change', ascending=False).head(10)
        top_10_fallers = date_data.sort_values(by='Percent_Change', ascending=True).head(10)
        top_10_closest_to_52_week_low = date_data.sort_values(by='Percent_Diff_From_52_Week_Low', ascending=True).head(
            10)
        top_10_closest_to_52_week_high = date_data.sort_values(by='Percent_Diff_From_52_Week_High',
                                                               ascending=False).head(10)

        # Add Short Name, Industry, and Sector information to each DataFrame
        top_10_risers = self.add_company_info(top_10_risers)
        top_10_fallers = self.add_company_info(top_10_fallers)
        top_10_closest_to_52_week_low = self.add_company_info(top_10_closest_to_52_week_low)
        top_10_closest_to_52_week_high = self.add_company_info(top_10_closest_to_52_week_high)

        # Print the results
        print(f"Top 10 Stocks that Rose the Most on {date_str}:")
        print(top_10_risers[['Symbol', 'Short Name', 'Sector', 'Industry', 'Percent_Change', 'Close', '52_Week_Low',
                             '52_Week_High']])

        print(f"\nTop 10 Stocks that Fell the Most on {date_str}:")
        print(top_10_fallers[['Symbol', 'Short Name', 'Sector', 'Industry', 'Percent_Change', 'Close', '52_Week_Low',
                              '52_Week_High']])

        print(f"\nTop 10 Stocks That Were Closest to 52 Week Low on {date_str}:")
        print(top_10_closest_to_52_week_low[
                  ['Symbol', 'Short Name', 'Sector', 'Industry', 'Percent_Change', 'Close', '52_Week_Low',
                   '52_Week_High']])

        print(f"\nTop 10 Stocks That Were Closest to 52 Week High on {date_str}:")
        print(top_10_closest_to_52_week_high[
                  ['Symbol', 'Short Name', 'Sector', 'Industry', 'Percent_Change', 'Close', '52_Week_Low',
                   '52_Week_High']])

        top_10_risers['List'] = 'Top 10 Risers'
        top_10_fallers['List'] = 'Top 10 Fallers'
        top_10_closest_to_52_week_low['List'] = 'Closest to 52 Week Low'
        top_10_closest_to_52_week_high['List'] = 'Closest to 52 Week High'

        # Concatenate all DataFrames
        all_top_10_data = pd.concat(
            [top_10_risers, top_10_fallers, top_10_closest_to_52_week_low, top_10_closest_to_52_week_high])

        # Save to a single CSV file
        all_top_10_data.to_csv("top_10_stocks_analysis.csv", index=False)

        print("Data saved to top_10_stocks_analysis.csv with all lists combined.")

    def add_company_info(self, df):
        # Merge the stock DataFrame with the company info based on Symbol
        merged_df = df.merge(self.company_info_df[['Ticker', 'Short Name', 'Sector', 'Industry']],
                             left_on='Symbol', right_on='Ticker', how='left').drop(columns=['Ticker'])

        # Fill missing information from yfinance if not present in company_info_df
        for index, row in merged_df.iterrows():
            if pd.isna(row['Short Name']):
                info = self.get_company_info(row['Symbol'])
                merged_df.at[index, 'Short Name'] = info['Short Name']
                merged_df.at[index, 'Sector'] = info['Sector']
                merged_df.at[index, 'Industry'] = info['Industry']
        return merged_df

    def get_companies_hit_52_week_extremes(self):
        # Get the last trading day
        last_trading_day = self.stock_prices_df['Date'].max()

        # Filter for companies that hit 52-week low or high
        hit_52_week_low = self.stock_prices_df[
            (self.stock_prices_df['Date'] == last_trading_day) & (self.stock_prices_df['Hit_52_Week_Low'] == 1)
            ]
        hit_52_week_high = self.stock_prices_df[
            (self.stock_prices_df['Date'] == last_trading_day) & (self.stock_prices_df['Hit_52_Week_High'] == 1)
            ]

        # Print results
        print(f"Companies that hit 52-week low on {last_trading_day}:")
        print(hit_52_week_low[['Symbol', 'Close', '52_Week_Low']])

        print(f"\nCompanies that hit 52-week high on {last_trading_day}:")
        print(hit_52_week_high[['Symbol', 'Close', '52_Week_High']])

        # Return results as DataFrames for further use
        return hit_52_week_low, hit_52_week_high

def get_last_trading_day():
    reference_stock = "AAPL"  # Use Apple as the reference stock
    data = yf.download(reference_stock, period="5d")  # Download the last 5 days of data
    last_available_date = max(data.index)  # Get the most recent date from the data
    return last_available_date

while True:
    print("\nWhat would you like to do?")
    main_actions_dictionary = {1: 'Download data for a list of tickers',
                               2: 'Review Stocks of Special Interest list',
                               3: 'Add tickers to Stocks of Special Interest list',
                               4: 'Delete tickers from Stocks of Special Interest list',
                               5: 'Review My Stocks list',
                               6: 'Add tickers to My Stocks list',
                               7: 'Delete tickers from My Stocks list',
                               8: 'Clear My Stocks list',
                               9: 'Get earnings calendar',
                               10: 'Check earnings date for a specific stock',
                               11: 'Get list of recent IPOs (priced and upcoming)',
                               12: 'Get news for a certain ticker or a list of tickers',
                               0: 'Exit'}

    dictionary_for_choosing_tickers = {1: 'sp500_tickers', 2: 'sp400_tickers', 3: 'sp600_tickers', 4: 'sp_1500',
                                       5: 'magnificent_seven', 6: 'bitcoin', 7: 'stocks_interest', 8: 'my_stocks',
                                       9: 'big_list', 10: 'all_stocks'}

    for k, v in main_actions_dictionary.items():
        print(f" {k} - {v}")
    try:
        chosen_number = int(input("Your choice: "))
    except ValueError:
        print("Invalid input. Please enter a number.")
        continue

    if chosen_number == 0:
        print("Goodbye!")
        break
    if chosen_number == 1:
        if chosen_number == 1:
            print("Please enter a number corresponding to the tickers list you want to use.")
            for k, v in dictionary_for_choosing_tickers.items():
                print(f" {k} - {v};")
            tickers = dictionary_for_choosing_tickers[int(input("Your choice: "))]
            a = GetStockData(tickers)

            # Determine the latest trading day based on available data for a reference stock
            last_trading_day = get_last_trading_day()
            last_trading_day_str = last_trading_day.strftime('%Y-%m-%d')

            # Get top movers and extremes
            a.get_top_movers(last_trading_day_str)
            hit_low, hit_high = a.get_companies_hit_52_week_extremes()
    elif chosen_number == 2 or chosen_number == 5:
        if chosen_number == 2:
            print("Here are the stocks you are interested in:")
            df = pd.read_csv("stocks_interest.csv")
            for ticker in df['ticker'].dropna():
                print(ticker.strip())
        elif chosen_number == 5:
            print("Here are the stocks you are invested in:")
            df = pd.read_csv("my_stocks.csv")
            for ticker in df['ticker'].dropna():
                print(ticker.strip())
    elif chosen_number == 3 or chosen_number == 6:
        tickers_to_add = input(f"Provide tickers to add to a list: ")
        filename = ""
        if chosen_number == 3:
            filename = "stocks_interest.csv"
        if chosen_number == 6:
            filename = "my_stocks.csv"
        try:
            df = pd.read_csv(filename)
        except FileNotFoundError:
            df = pd.DataFrame(columns=["ticker"])
        # Clean and split the input string
        new_tickers = [ticker.strip().upper() for ticker in tickers_to_add.split(",") if ticker.strip()]
        # Combine and remove duplicates
        all_tickers = pd.Series(df["ticker"].tolist() + new_tickers).drop_duplicates().sort_values()
        # Save back to CSV
        all_tickers.to_frame(name="ticker").to_csv(filename, index=False)
        print("Tickers added and file updated.")
    elif chosen_number == 4 or chosen_number == 7:
        tickers_to_delete = input(f"Provide tickers to delete from a list: ")
        filename = ""
        if chosen_number == 4:
            filename = "stocks_interest.csv"
        if chosen_number == 7:
            filename = "my_stocks.csv"
        # Load existing tickers
        df = pd.read_csv(filename)
        # Clean and split the input string
        tickers_to_delete_list = [ticker.strip().upper() for ticker in tickers_to_delete.split(",") if ticker.strip()]
        # Filter out the tickers to be deleted
        df_filtered = df[~df["ticker"].isin(tickers_to_delete_list)]
        # Save back to CSV
        df_filtered.to_csv(filename, index=False)
        print("Tickers deleted and file updated.")
    elif chosen_number == 8:
        df = pd.read_csv("my_stocks.csv")
        empty_df = pd.DataFrame(columns=df.columns)
        empty_df.to_csv("my_stocks.csv", index=False)
        print("My Stocks list cleared")
    elif chosen_number == 9:
        output_file = 'nasdaq_earnings_calendar.csv'
        chosen_timeframe = input("Choose timeframe (today, tomorrow, this week, next week, this month, next month, this and next month): ")
        if chosen_timeframe == 'today':
            scraper = NasdaqEarningsScraper()
            scraper.run(output_file)
            scraper.print_reporting_companies()
        else:
            scraper = NasdaqEarningsScraper(chosen_timeframe)
            scraper.run(output_file)
    elif chosen_number == 10:
        chosen_ticker = input("Provide a ticker: ")
        a = yf.Ticker(chosen_ticker)
        print(a.earnings_dates)
    elif chosen_number == 11:
        priced_ipos_scraper = NasdaqIPOScraper()
        df = priced_ipos_scraper.scrape_all_ipos()
        print(df)
    elif chosen_number == 12:
        chosen_option = input("Provide a list of tickers (e.g., TSLA,AAPL) or choose one of the existing lists "
                              "(sp500_tickers, sp400_tickers, sp600_tickers, sp_1500, magnificent_seven, bitcoin, "
                              "stocks_interest, my_stocks, big_list): ").strip()

        predefined_lists = [
            'sp500_tickers', 'sp400_tickers', 'sp600_tickers', 'sp_1500',
            'magnificent_seven', 'bitcoin', 'stocks_interest', 'my_stocks', 'big_list'
        ]

        if chosen_option in predefined_lists:
            news = GetNews(ticker_list_name=chosen_option)
        else:
            # Split user input like "TDUP, WGS" into ['TDUP', 'WGS']
            custom_tickers = [t.strip().upper() for t in chosen_option.split(",") if t.strip()]
            news = GetNews(tickers=custom_tickers)

        news.run()
    else:
        print("Invalid option. Please choose from the list.")