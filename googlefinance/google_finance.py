import urllib.request
from urllib.error import HTTPError
from datetime import datetime
import json
from bs4 import BeautifulSoup

DESCRIPTIVE_KEYS = {
    'id': 'ID',
    't': 'TickerSymbol',
    'e': 'Exchange',
    'l': 'LastTradePrice',
    'lt_dts': 'LastTradeDateTime',
    'c': 'Change',
    'cp': 'ChangePercent',
    'pcls_fix': 'PreviousCloseFix',
    'div': 'Dividend',
    'yld': 'Dividend Yield'
}

class Stock:

    """Class contains functions to pull current and historical pricing data from Google Finance

    Methods:
        get_quote: returns the most recent market quote of the stock
        get_historical_prices: retrieves historical close prices
        get_stock_news: returns recent relevant company news

    Attributes:
        ticker (String): market ticker
        valid (boolean): ticker is a valid ticker
        name (String): long company name
        description (String): Brief description of company

    """

    def __init__(self, ticker):

        self.ticker = ticker
        self.valid = self._validate_ticker()
        self.name, self.description = self._get_desc_details()

    def get_quote(self):

        """Retrieves most recent stock price"""

        quote_url = 'http://finance.google.com/finance/info?client=ig'

        if self.valid:
            with urllib.request.urlopen(quote_url + '&q=' + self.ticker) as quote_response:
                quotes = quote_response.read().decode('ascii', 'ignore').replace('\n', '')[3:]
                return self._replace_keys(json.loads(quotes))


    def get_historical_prices(self, start_date, end_date):

        """Class retrives historical stock prices between the two dates provided

        arguments:
        start_date -- String representation of the opening historical date to retrieve prices
        end_date -- String representation of the closing historical date to retrive prices

        """

        if self.valid is True:
            historic_url = 'https://www.google.com/finance/historical?&q={0}&startdate={1}&enddate={2}&output=csv'.format(self.ticker, start_date, end_date)
            response_data = []
            try:
                with urllib.request.urlopen(historic_url) as response:
                    page = response.read().decode('utf-8-sig').splitlines()

                headers = page[0].split(',')
                response_data = self._parse_hist_data(page[1:], headers, ',')

            except urllib.error.HTTPError:

                more_data = True
                start = 0
                while more_data:
                    historic_url = 'https://www.google.com/finance/historical?&q={0}&startdate={1}&enddate={2}&num=200&start={3}'.format(self.ticker, start_date, end_date, start)
                    with urllib.request.urlopen(historic_url) as response:
                        page = response.read()

                    soup = BeautifulSoup(page, 'html.parser')
                    table = soup.find("table", class_='gf-table historical_price')
                    text = table.text.split('\n\n')
                    headers = text[1].split('\n')

                    response_data = response_data \
                        + self._parse_hist_data(text[2:], headers, '\n', date_format='%b %d, %Y')

                    if len(response_data) < 200:
                        more_data = False
                    elif len(response_data) % 200 != 0:
                        more_data = False
                    else:
                        start = start + 200

            return response_data

    def get_stock_news(self):

        """function will scrape google news to pull relelvant news stories

        arguments:
            ticker (string): ticker symbol to pull company news about
        """

        if self.valid is False:
            return "Invalid Stock"

        url = 'https://www.google.com/finance/company_news?q={0}&start=0&num=20'.format(self.ticker)
        with urllib.request.urlopen(url) as response:
            res = response.read()

        soup = BeautifulSoup(res, 'html.parser')
        scraped_articles = []
        articles = soup.find(id='news-main')

        for article in articles.find_all(class_='g-section news sfe-break-bottom-16'):
            header = article.find(class_='name')
            details = header.select('a')
            headline = details[0].getText()
            url = details[0]['href']

            byline = article.find(class_='byline')
            src = byline.find(class_='src').getText()
            article_date = byline.find(class_='date').getText()

            scraped_articles.append(
                {
                    'headline': headline,
                    'url': url,
                    'src': src,
                    'date': article_date
                }
            )
        return scraped_articles

    def _get_desc_details(self):
        desc_url = 'https://www.google.com/finance?q='
        try:
            with urllib.request.urlopen(desc_url + self.ticker) as response:
                soup = BeautifulSoup(response.read(), 'html.parser')
        except urllib.error.HTTPError as error:
            self.valid = False
            print(error.reason)

        try:
            title = soup.title.text
            company_name = title[:title.find(':')]
        except AttributeError:
            company_name = 'Company Name Unavailable'

        try:
            description = soup.find('div', class_='companySummary').text
        except AttributeError:
            description = 'Description Unavailable'

        return (company_name, description)

    def _validate_ticker(self):
        url = 'http://finance.google.com/finance/info?client=ig'

        try:
            with urllib.request.urlopen(url + '&q=' + self.ticker) as _:
                return True
        except HTTPError as _:
            return False

    @staticmethod
    def _parse_hist_data(data, headers, delimiter, date_format='%d-%b-%y'):

        parsed_data = []
        for row in data:
            cell = row.split(delimiter)
            row_contents = {}
            row_contents[headers[0]] = datetime.strptime(cell[0], date_format)
            row_contents[headers[1]] = cell[1].replace(',', '')
            row_contents[headers[2]] = cell[2].replace(',', '')
            row_contents[headers[3]] = cell[3].replace(',', '')
            row_contents[headers[4]] = cell[4].replace(',', '')
            row_contents[headers[5]] = cell[5].replace(',', '')
            parsed_data.append(row_contents)

        return parsed_data

    @staticmethod
    def _replace_keys(quote):
        updated_quote = {}
        for key in quote[0]:
            if key in DESCRIPTIVE_KEYS:
                updated_quote[DESCRIPTIVE_KEYS[key]] = quote[0][key]
        return updated_quote
