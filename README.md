# portfolio-tracker
 A simple portfolio tracking tool--buy, sell, and track stocks with real time prices (hypothetically, of course)

DIrectories:
1. static: contains the css file for the entire web program
2. templates: contains all the html files for the webpages (including a layout page, home, buy/sell, login, etc)

Files:
1. apitoken.txt: contains the API key required to access real time stock prices from a separate database online
2. application.py: the program created with Flask, Python, and SQL which defines functions all web pages and links them together
3. finance.db: a database which contains relevant tables to the web program such as user and portfolio data
4. helpers.py: a secondary file which defines other helpful functions to be used in application.py (look up stocks, convert prices to USD, apology messages, and a login requirement across certain pages for security)