import yfinance as yf
from datetime import datetime
import csv
from tickers import Tickers


class GetNews:
    AVAILABLE_LISTS = [
        "sp500_tickers", "sp400_tickers", "sp600_tickers", "sp_1500",
        "magnificent_seven", "bitcoin", "stocks_interest", "my_stocks", "big_list"
    ]

    def __init__(self, tickers=None, ticker_list_name="sp500_tickers"):
        if tickers is not None:
            self.ticker_symbols = tickers
        else:
            if ticker_list_name not in self.AVAILABLE_LISTS:
                raise ValueError(
                    f"Invalid list name: '{ticker_list_name}'. Choose one of: {', '.join(self.AVAILABLE_LISTS)}"
                )
            self.ticker_symbols = Tickers().get_tickers_list(ticker_list_name)

        self.apply_publisher_filters = len(self.ticker_symbols) >= 10

        self.excluded_publishers = {p.lower().strip() for p in {"motley fool", "insider monkey"}}
        self.preferred_publishers = {
            p.lower().strip()
            for p in {"bloomberg", "reuters", "the wall street journal", "barrons.com", "cnn business", "fortune"}
        }

        self.articles = []

    def fetch_news(self):
        for symbol in self.ticker_symbols:
            ticker = yf.Ticker(symbol)
            try:
                news_items = ticker.news
            except Exception as e:
                print(f"⚠️ Failed to fetch news for {symbol}: {e}")
                continue

            for article in news_items:
                content = article.get("content", {})
                publisher = content.get("provider", {}).get("displayName", "").lower().strip()

                if self.apply_publisher_filters and publisher in self.excluded_publishers:
                    continue

                publish_time_str = content.get("pubDate")
                try:
                    publish_datetime = datetime.strptime(publish_time_str, '%Y-%m-%dT%H:%M:%SZ')
                except Exception:
                    continue

                article["datetime_obj"] = publish_datetime
                article["tickers"] = article.get("tickers", []) or [symbol]
                self.articles.append(article)

    def deduplicate_articles(self):
        seen = set()
        unique_articles = []
        for article in self.articles:
            content = article.get("content", {})
            title = content.get("title", "").strip()
            summary = content.get("summary", "").strip()

            key = (title.lower(), summary.lower())
            if key not in seen:
                seen.add(key)
                unique_articles.append(article)
        self.articles = unique_articles

    def sort_articles(self):
        self.articles.sort(key=lambda x: x.get("datetime_obj", datetime.min), reverse=True)

    def print_preview(self, max_items=50):
        print(f"\n📰 Showing first {min(max_items, len(self.articles))} articles:\n" + "-"*80)
        for i, article in enumerate(self.articles[:max_items]):
            content = article.get("content", {})
            title = content.get("title", "No title")
            summary = content.get("summary", "No summary")
            publisher = content.get("provider", {}).get("displayName", "Unknown publisher")
            publish_datetime = article.get("datetime_obj", "N/A")
            tickers = ", ".join(article.get("tickers", []))

            print(f"{i+1}. [{publish_datetime.strftime('%Y-%m-%d %H:%M')}] {tickers} | {publisher}")
            print(f"   🗞️ Title: {title}")
            print(f"   ✏️ Summary: {summary[:200]}{'...' if len(summary) > 200 else ''}")
            print("-" * 80)

    def save_to_csv(self, filename="news_articles.csv"):
        with open(filename, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Title", "Summary", "Publisher", "Published At", "Tickers", "Link"])

            for article in self.articles:
                try:
                    content = article.get("content", {})
                    publisher = content.get("provider", {}).get("displayName", "Unknown publisher").strip().lower()

                    if self.apply_publisher_filters and publisher not in self.preferred_publishers:
                        continue

                    title = content.get("title", "No title available")
                    summary = content.get("summary", "No summary available")
                    link = (content.get("clickThroughUrl") or {}).get("url", "No link available")
                    publish_datetime = article["datetime_obj"].strftime('%Y-%m-%d %H:%M:%S')
                    tickers = ", ".join(sorted(set(article.get("tickers", []))))

                    writer.writerow([title, summary, publisher, publish_datetime, tickers, link])

                except Exception as e:
                    print(f"⚠️ Skipping article due to error: {e}")
                    print(f"Raw article content:\n{article}")

    def run(self, filename="news_articles.csv"):
        self.fetch_news()
        self.deduplicate_articles()
        self.sort_articles()
        self.print_preview()
        self.save_to_csv(filename)

if __name__ == "__main__":
    news = GetNews(['TSLA'])
    news.run()