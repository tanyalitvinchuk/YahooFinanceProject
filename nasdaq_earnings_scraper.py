#!/bin/python
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from tickers import Tickers
import time
import calendar
class NasdaqEarningsScraper:
    def __init__(self, date_input=None):
        self.date_input = date_input or "today"
        today = datetime.today()
        self.tickers = Tickers()
        self.url = 'https://api.nasdaq.com/api/calendar/earnings?'

        # Default
        start_date = today
        end_date = today

        if isinstance(date_input, str):
            date_input = date_input.lower().strip()

            if date_input == "tomorrow":
                start_date = today + timedelta(days=1)
                end_date = start_date

            elif date_input == "this week":
                start_date = today  # Start today, not Monday
                end_date = today + timedelta(days=(6 - today.weekday()))  # End of the week (Sunday)

            elif date_input == "next week":
                next_monday = today - timedelta(days=today.weekday()) + timedelta(days=7)
                start_date = next_monday
                end_date = next_monday + timedelta(days=6)

            elif date_input == "this month":
                start_date = today
                end_day = calendar.monthrange(today.year, today.month)[1]
                end_date = today.replace(day=end_day)

            elif date_input == "next month":
                year = today.year + (today.month // 12)
                month = today.month % 12 + 1
                start_date = datetime(year, month, 1)
                end_day = calendar.monthrange(year, month)[1]
                end_date = datetime(year, month, end_day)

            elif date_input in ["this and next month", "next and this month"]:
                # Start from today (this month)
                this_month_end_day = calendar.monthrange(today.year, today.month)[1]
                this_month_end = today.replace(day=this_month_end_day)

                # Calculate next month start and end
                next_year = today.year + (today.month // 12)
                next_month = today.month % 12 + 1
                next_month_start = datetime(next_year, next_month, 1)
                next_month_end_day = calendar.monthrange(next_year, next_month)[1]
                next_month_end = datetime(next_year, next_month, next_month_end_day)

                start_date = today  # Start from today
                end_date = next_month_end  # End at end of next month


            elif "to" in date_input:
                try:
                    parts = [x.strip() for x in date_input.split("to")]
                    start_date = datetime.strptime(parts[0], '%Y-%m-%d')
                    end_date = datetime.strptime(parts[1], '%Y-%m-%d')
                except Exception as e:
                    raise ValueError(f"Invalid custom date range: {e}")

        self.start_date = start_date
        self.end_date = end_date
        self.tickers = Tickers()
        self.url = 'https://api.nasdaq.com/api/calendar/earnings?'

        # Headers for the HTTP request
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://www.nasdaq.com",
            "Referer": "https://www.nasdaq.com",
            "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        }

    def fetch_earnings(self):
        date_list = [(self.start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range((self.end_date - self.start_date).days + 1)]
        all_data = []

        for date in date_list:
            payload = {"date": date}
            response = requests.get(url=self.url, headers=self.headers, params=payload, verify=True)

            if response.status_code == 200:
                try:
                    data = response.json()
                    earnings_data = data.get('data', {}).get('rows', [])
                    if earnings_data:
                        # Add the earnings date to each entry
                        for entry in earnings_data:
                            entry['earnings_date'] = date
                        all_data.extend(earnings_data)
                    else:
                        continue
                except Exception as e:
                    print(f"Error parsing data for {date}: {e}")
            else:
                print(f"Failed to fetch data for {date}. Status code: {response.status_code}")

        return all_data

    def enrich_data(self, earnings_data):
        sp500_tickers = self.tickers.get_tickers_list('sp500_tickers')
        sp400_tickers = self.tickers.get_tickers_list('sp400_tickers')
        sp600_tickers = self.tickers.get_tickers_list('sp600_tickers')

        for entry in earnings_data:
            ticker = entry.get('symbol', '')  # Adjust 'symbol' if your API uses a different key

            # Determine the index membership
            if ticker in sp500_tickers:
                entry['index'] = 'S&P 500'
            elif ticker in sp400_tickers:
                entry['index'] = 'S&P 400'
            elif ticker in sp600_tickers:
                entry['index'] = 'S&P 600'
            else:
                entry['index'] = 'None'

            # Calculate the Week of (Monday of the same week)
            earnings_date_str = entry.get('earnings_date', '')
            if earnings_date_str:
                earnings_date = datetime.strptime(earnings_date_str, '%Y-%m-%d')
                week_of = earnings_date - timedelta(days=earnings_date.weekday())
                entry['week_of'] = week_of.strftime('%Y-%m-%d')
            else:
                entry['week_of'] = 'Unknown'

        return earnings_data

    def run(self, output_file, printing=True):
        earnings_data = self.fetch_earnings()
        if earnings_data:
            enriched_data = self.enrich_data(earnings_data)
            df = pd.DataFrame(enriched_data)
            df.to_csv(output_file, index=False)
            print(f"Earnings data saved to {output_file}")
        else:
            print("No data to save.")

        if printing:
            self.print_reporting_companies()

    def print_reporting_companies(self):
        earnings_data = self.fetch_earnings()
        if not earnings_data:
            print("No data found for the specified date range.")
            return

        enriched_data = self.enrich_data(earnings_data)

        # Filter data by index
        sp500_companies = [entry for entry in enriched_data if entry['index'] == 'S&P 500']
        sp400_companies = [entry for entry in enriched_data if entry['index'] == 'S&P 400']
        sp600_companies = [entry for entry in enriched_data if entry['index'] == 'S&P 600']

        # Print results
        print(f"\nS&P 500 Companies Reporting Earnings ({self.date_input}):")
        for company in sp500_companies:
            print(
                f"{company.get('symbol', 'Unknown')} - {company.get('name', 'No Name')} - {company.get('earnings_date')}")

        print(f"\nS&P 400 Companies Reporting Earnings ({self.date_input}):")
        for company in sp400_companies:
            print(
                f"{company.get('symbol', 'Unknown')} - {company.get('name', 'No Name')} - {company.get('earnings_date')}")

        print(f"\nS&P 600 Companies Reporting Earnings ({self.date_input}):")
        for company in sp600_companies:
            print(
                f"{company.get('symbol', 'Unknown')} - {company.get('name', 'No Name')} - {company.get('earnings_date')}")


# Usage for Class Earnings Scraper
if __name__ == "__main__":
    output_file = 'nasdaq_earnings_calendar.csv'
    scraper = NasdaqEarningsScraper('this and next month')
    scraper.run(output_file)
