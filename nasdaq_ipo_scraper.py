import pandas as pd
import requests
from datetime import datetime
import yfinance as yf
import time


class NasdaqIPOScraper:
    def __init__(self, start_date=None):
        self.ipo_url = 'https://api.nasdaq.com/api/ipo/calendar'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        }

        today = datetime.today()
        if not start_date:
            start_date = today.replace(day=1).strftime('%Y-%m-%d')

        self.start_date = start_date
        self.end_date = today.strftime('%Y-%m-%d')

    def enrich_priced_with_yfinance(self, df):
        enriched_rows = []
        for _, row in df.iterrows():
            ticker = row.get('proposedTickerSymbol')
            if not ticker or not isinstance(ticker, str):
                continue
            try:
                info = yf.Ticker(ticker).info
                row['sector'] = info.get('sector')
                row['industry'] = info.get('industry')
                row['country'] = info.get('country')
                row['website'] = info.get('website')
                row['fullTimeEmployees'] = info.get('fullTimeEmployees')
                row['marketCap'] = info.get('marketCap')
                row['fiftyTwoWeekHigh'] = info.get('fiftyTwoWeekHigh')
                row['fiftyTwoWeekLow'] = info.get('fiftyTwoWeekLow')
                row['earningsDate'] = info.get('earningsDate', [None, None])[0]
                row['previousClose'] = info.get('previousClose')

                high = info.get('fiftyTwoWeekHigh')
                low = info.get('fiftyTwoWeekLow')
                close = info.get('previousClose')

                if close and high:
                    row['pct_diff_from_52W_high'] = round((close - high) / high * 100, 2)
                else:
                    row['pct_diff_from_52W_high'] = None

                if close and low:
                    row['pct_diff_from_52W_low'] = round((close - low) / low * 100, 2)
                else:
                    row['pct_diff_from_52W_low'] = None
                if close and high and low and high != low:
                    row['position_in_52W_range'] = round((close - low) / (high - low), 4)  # 4 decimal precision
                else:
                    row['position_in_52W_range'] = None

            except Exception as e:
                print(f"Error retrieving info for {ticker}: {e}")

            enriched_rows.append(row)
            time.sleep(1)

        return pd.DataFrame(enriched_rows)

    def _fetch_data(self, section_key, nested=False):
        periods = pd.period_range(self.start_date, self.end_date, freq='M')
        dfs = []

        for period in periods:
            response = requests.get(
                self.ipo_url,
                headers=self.headers,
                params={'date': str(period)}
            )

            if response.status_code != 200:
                print(f"Failed to fetch data for {period}: {response.status_code}")
                continue

            try:
                data = response.json()
                if nested:
                    section_data = data.get('data', {}).get(section_key, {}).get('upcomingTable', {}).get('rows', [])
                else:
                    section_data = data.get('data', {}).get(section_key, {}).get('rows', [])

                if section_data:
                    df = pd.json_normalize(section_data)
                    df['Status'] = 'Upcoming' if section_key == 'upcoming' else 'Priced'
                    dfs.append(df)

            except Exception as e:
                print(f"Error parsing {section_key} data for {period}: {e}")

        if dfs:
            return pd.concat(dfs, ignore_index=True)
        else:
            print(f"No {section_key} data retrieved.")
            return pd.DataFrame()

    def scrape_all_ipos(self):
        df_priced = self._fetch_data('priced', nested=False)
        df_upcoming = self._fetch_data('upcoming', nested=True)

        df_priced['pricedDate'] = df_priced['pricedDate']
        df_upcoming['pricedDate'] = df_upcoming['expectedPriceDate']

        drop_columns = ['dealStatus', 'ipo_month', 'expectedPriceDate', 'dealID']
        for df in [df_priced, df_upcoming]:
            for col in drop_columns:
                if col in df.columns:
                    df.drop(columns=col, inplace=True)

        df_priced['Status'] = 'Priced'
        df_upcoming['Status'] = 'Upcoming'

        if not df_priced.empty:
            df_priced = self.enrich_priced_with_yfinance(df_priced)

        combined = pd.concat([df_priced, df_upcoming], ignore_index=True)
        combined.to_csv("nasdaq_ipos_combined.csv", index=False)

        # ----- Formatted Preview -----
        columns_to_show = [
            'proposedTickerSymbol', 'companyName', 'Status', 'pricedDate',
            'sector', 'industry', 'marketCap', 'position_in_52W_range'
        ]
        columns_to_show = [col for col in columns_to_show if col in combined.columns]
        df_view = combined[columns_to_show].copy()

        df_view.rename(columns={
            'proposedTickerSymbol': 'Symbol',
            'companyName': 'Company Name'
        }, inplace=True)

        if 'marketCap' in df_view.columns:
            df_view['marketCap'] = df_view['marketCap'].apply(
                lambda x: f"${x:,.0f}" if pd.notnull(x) else None
            )

        if 'pricedDate' in df_view.columns:
            df_view['pricedDate'] = pd.to_datetime(df_view['pricedDate'], errors='coerce')
            df_view.sort_values(by='pricedDate', ascending=False, inplace=True)

        pd.set_option("display.max_columns", None)
        pd.set_option("display.max_rows", 20)
        pd.set_option("display.width", 160)
        print("\n📈 Nasdaq IPOs Snapshot:\n")
        print(df_view.head(20).to_string(index=False))
        # -----------------------------

        return combined

# Example usage
if __name__ == "__main__":
    scraper = NasdaqIPOScraper(start_date="2025-05-01")
    df_combined = scraper.scrape_all_ipos()
