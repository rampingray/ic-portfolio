######################
### Module Imports ###
######################

from data_mod import *
import datetime
import pandas as pd
import numpy as np
import requests
import sys
import pickle

#################
### Constants ###
#################

### Portfolio and More###
portfolio = pd.DataFrame()  # Dataframe giving portfolio balances of each holding
balances = pd.DataFrame()  # Series holding the balance that created each holding in "portfolio"
holdings = {}  # Dictionary holding instances of Holding indexed by strings of ticker

### Sector Holdings ###
sectorHoldings = {'Staples': [], 'Discretionary': [], 'Energy': [],
                  'REITs': [], 'Financials': [], 'Healthcare': [], 'Industrials': [],
                  'Utilities': [], 'Macro': [], 'Technology': [], 'Fixed Income': []}

#########################
### Class Definitions ###
#########################

### Holding Class ###
class Holding():
    # Simply holds the current cost basis (price) and share count (shares)

    def __init__(self, ticker, shares, price):
        self.ticker = ticker
        self.shares = shares
        self.price = price

    def __str__(self):
        return f'Holding {self.shares} shares of {self.ticker} at ${self.price}'

    def buy(self, shares, price):
        self.price = (self.price * self.shares + price * shares) / (self.shares + shares)
        self.shares += shares

    def sell(self, shares):
        self.shares -= shares


############################
### Function Definitions ###
############################

### Import Excel ###
def import_excel(filename, flexCash=False, savePickle=False):
    # Imports the excel file of transactions data and turns it into a DataFrame of Daily Prices

    global portfolio
    global balances
    global holdings
    global sectorHoldings

    transactions = pd.read_excel(filename)  # Reads the excel file as a pandas dataframe
    transactions.Action = transactions.Action.str.lower()  # The following 2 lines make the columns lowercase so they're easier to use
    transactions.Ticker = transactions.Ticker.str.lower()
    transactions = transactions.sort_values('Date')  # Sorts Transactions by Date
    for index, trade in transactions.iterrows():  # Iterates over the trades in the excel sheet and adds them to the portfolio
        if trade.Action == 'buy':
            buy(trade.Ticker, trade.Date, trade.Shares, trade.Price, trade.Sector, flexCash)
        elif trade.Action == 'sell':
            sell(trade.Ticker, trade.Date, trade.Shares, trade.Price)
        elif trade.Action == 'deposit':
            deposit(trade.Price, trade.Date)
        elif trade.Action == 'withdraw':
            withdraw(trade.Price, trade.Date)
        else:
            print('Invalid Order Type For:', trade.Ticker)

    if savePickle:
        portfolio.to_pickle('./pickles/portfolio.pkl')
        balances.to_pickle('./pickles/balances.pkl')
        with open('./pickles/holdings.pkl', 'wb') as holdingsPickle:
            pickle.dump(holdings, holdingsPickle)
        with open('./pickles/sectorHoldings.pkl', 'wb') as sectorHoldingsPickle:
            pickle.dump(sectorHoldings, sectorHoldingsPickle)

    return portfolio, balances, holdings, sectorHoldings



### Import Pickle ###
def import_pickle(portfolioPickle, balancesPickle, holdingsPickle, sectorHoldingsPickle):
    # Imports portfolio, balances, holdings, and sectorHoldings from pickle form

    global portfolio
    global balances
    global holdings
    global sectorHoldings

    portfolio = pd.read_pickle(portfolioPickle)
    balances = pd.read_pickle(balancesPickle)
    with open('./pickles/holdings.pkl', 'rb') as holdingsPickle:
        holdings = pickle.load(holdingsPickle)
    with open('./pickles/sectorHoldings.pkl', 'rb') as sectorHoldingsPickle:
        sectorHoldings = pickle.load(sectorHoldingsPickle)

    return portfolio, balances, holdings, sectorHoldings

### Deposit ###
def deposit(cash, date):
    global portfolio
    global balances

    # Adds cash to the cash position in portfolio
    if 'Cash' in portfolio.columns:
        portfolio['Cash'].loc[date:] += cash
    else:
        portfolio['Cash'].loc[date] = cash

    # Adds cash to the cash balance in balances
    if 'Cash' in balances.columns:
        balances['Cash'].loc[date:] += cash
    else:
        balances['Cash'].loc[date] = cash


### Withdraw ###
def withdraw(cash, date):
    global portfolio
    global balances

    # Withdraws cash from the cash position in portfolio
    portfolio['Cash'].loc[date:] -= cash

    # Withdraws cash from the cash balance in balances
    balances['Cash'].loc[date:] -= cash


### Buy ###
def buy(ticker, date, shares, price=None, sector=None, flexCash=False):
    # 1) Handles running out of cash or flexCash scneario
    # 2) Adds stock to sector dictionary if it is not there already
    # 3) Adds stock to balances/portfolio if it is not in either already
    # 4) Adds stock to sector dictionary if it is not there already
    # 5) Updates the position/balance with new purchase data

    global portfolio
    global sectorHoldings
    global balances

    # Tries to get pricing data and add ticker to sectorHoldings, returns None if not found
    try:
        dailyPrices = get_stock(ticker)[date:]  # Gets the daily closing price for the past 20ish years
        dailyPrices.name = ticker  # Renames the Pandas Series with the ticker before appending to the portfolio
        if sector != None:  # Adds the given ticker to the sector's list if it's not in there already
            if ticker not in sectorHoldings[sector]:
                sectorHoldings[sector].append(ticker)
    except:
        print('Not Found:', ticker)
        return None

    # Sets the purchase price if specified, otherwise sets the purchase price as the daily close
    if not np.isnan(price):
        dailyPrices.loc[date] = price
    else:
        price = dailyPrices.loc[date]

    # Checks if portfolio / balances have entries for cash
    if 'Cash' not in portfolio.columns and 'Cash' not in balances.columns:  # Checks if already in the portfolio as to not overwrite any existing holding
        portfolio.loc[date, 'Cash'] = 0
        balances.loc[date, 'Cash'] = 0
    elif 'Cash' not in portfolio.columns:
        portfolio.loc[date, 'Cash'] = 0
    elif 'Cash' not in balances.columns:
        balances.loc[date, 'Cash'] = 0

    # Reindexes balances and portfolio with each other
    if not balances.index.equals(portfolio.index):
        newIndex = balances.index.union(portfolio.index)
        portfolio = portfolio.reindex(newIndex, method='pad')
        balances = balances.reindex(newIndex, method='pad')

    # Checks for enough cash and handles problem according to flexCash setting
    if (portfolio['Cash'].loc[date] < price * shares) and flexCash == False:
        print('Not enough cash to buy', ticker, "on", str(date))
        return None
    elif (portfolio['Cash'].loc[date] < price * shares) and flexCash == True:
        deposit(price * shares - portfolio['Cash'].loc[date], date)

    # Removes the purchase price from cash balances in balances and cash position in portfolio
    portfolio['Cash'].loc[date:] -= price * shares
    balances['Cash'].loc[date:] -= price * shares

    # Checks for existing position in portfolio and handles accordingly
    if ticker not in portfolio.columns:  # Checks if already in the portfolio as to not overwrite any existing holding
        portfolio = pd.concat([portfolio, dailyPrices * shares],
                              axis=1)  # Adds the total value (Share Price * Share Count) to the portfolio for tracking
    else:
        portfolio[ticker][date:] += shares * dailyPrices  # Adds the holding to an existing holding

    # Checks for existing balance in balances and handles accordingly
    if ticker not in balances.columns:
        balances.loc[date:, ticker] = price * shares
    else:
        balances[ticker][date:] += price * shares

    # Checks for existing holding value and handles accordingly
    if ticker in holdings:
        holdings[ticker].buy(shares, price)
    else:
        holdings[ticker] = Holding(ticker, shares, price)

    # Fills out any missing data (might be able to delete)
    portfolio = portfolio.fillna(method='pad').fillna(0)
    balances = balances.fillna(method='pad').fillna(0)


### Sell ###
def sell(ticker, date, shares, price=None, sector=None):
    # Assumes the position already exists (doesn't allow shorts yet)
    # 1) Checks if portfolio has enough shares to sell
    # 2)
    # 3)

    global portfolio
    global balances

    # Tries to get pricing data for ticker, returns None if fails (should always succeed in theory)
    try:

        # Checks if portfolio has enough shares to sell
        if shares > holdings[ticker].shares:
            print('Error: Tried to sell', shares, 'shares of', ticker, 'but only had', holdings[ticker].shares)
            return None
        dailyprices = get_stock(ticker)[date:]  # Gets the daily closing stock price for the past 5y

    except:
        print('Not Found:', ticker)
        return None

    # Sets sales price if specified, uses closing price otherwise
    if np.isnan(price):  # Lets you set a price if you bought for a specific price
        price = dailyprices[date]

    # Subtracts the sale amount from the position in portfolio and balance in balances, then updates share count
    portfolio[ticker][date:] -= dailyprices[
                                date:] * shares  # Subtracts the value of the shares sold from future holdings
    portfolio['Cash'].loc[date:] += shares * price

    balances['Cash'].loc[date:] += shares * price
    balances[ticker].loc[date:] -= shares * holdings[ticker].price

    holdings[ticker].sell(shares)

### Sectorize ###
def sectorize(portfolio, balances):
    # Combines holdings into their respective sectors
    # Returns normalized returns of each sector in the portfolio

    portfolioBySector = pd.DataFrame()
    balancesBySector = pd.DataFrame()

    if not portfolio.index.equals(balances.index):
        newIndex = portfolio.index.union(balances.index)
        portfolio = portfolio.reindex(newIndex, method='pad')
        balances = balances.reindex(newIndex, method='pad')

    for sector, holdings in sectorHoldings.items():
        portfolioBySector[sector] = portfolio[holdings].sum(axis=1)
        balancesBySector[sector] = balances[holdings].sum(axis=1)

    returnsPortfolio = (portfolioBySector - portfolioBySector.shift(1) - (balancesBySector - balancesBySector.shift(1))) \
                       / portfolioBySector.shift(1)
    returnsPortfolio.name = 'Portfolio'
    returnsPortfolio.iloc[0] = 0
    returnsPortfolio = returnsPortfolio.fillna(0)
    normalizedPortfolio = (returnsPortfolio + 1).cumprod()

    return returnsPortfolio, normalizedPortfolio


### Testing ###
if __name__ == '__main__':

    # import_excel('./inputs/transactions_5Y.xlsx', flexCash=True, savePickle=True)
    # import_pickle('./pickles/portfolio.pkl', './pickles/balances.pkl', './pickles/holdings.pkl', './pickles/sectorHoldings.pkl')

    print('That is all')
