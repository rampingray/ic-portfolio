######################
### Module Imports ###
######################

from data_mod import *
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import linregress
import numpy as np
import requests
import sys

#################
### Constants ###
#################

### Portfolio and More###
portfolio = pd.DataFrame()                                                                                              # Dataframe giving portfolio balances of each holding
balances = pd.DataFrame()                                                                                               # Series holding the balance that created each holding in "portfolio"
holdings = {}                                                                                                           # Dictionary holding instances of Holding indexed by strings of ticker

### Sector Holdings ###
sectorHoldings = {'Staples':[], 'Discretionary':[], 'Energy':[],
    'REITs':[], 'Financials':[], 'Healthcare':[], 'Industrials':[],
    'Utilities':[], 'Macro':[], 'Technology':[], 'Fixed Income':[]}

### Risk Free Rate ###
riskFree = get_treas('10 yr')[-1] / 100                                                                                 # Annual risk free rate (percentage)
riskFreeDaily = ((riskFree + 1) ** (1/252) - 1)                                                                         # Converts annual risk free to daily (percentage)

### Market Rate ###
marketRate = 0.08                                                                                                       # Open to being changed

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

    def buy(self, shares,  price):
        self.price = (self.price * self.shares + price * shares) / (self.shares + shares)
        self.shares += shares

    def sell(self, shares):
        self.shares -= shares


############################
### Function Definitions ###
############################

### Import Excel ###
def import_excel(filename, flexCash=False):
    # Imports the excel file and turns it into a DataFrame of Daily Prices

    transactions = pd.read_excel(filename)                                                                              # Reads the excel file as a pandas dataframe
    transactions.Action = transactions.Action.str.lower()                                                               # The following 2 lines make the columns lowercase so they're easier to use
    transactions.Ticker = transactions.Ticker.str.lower()
    transactions = transactions.sort_values('Date')                                                                     # Sorts Transactions by Date
    for index, trade in transactions.iterrows():                                                                        # Iterates over the trades in the excel sheet and adds them to the portfolio
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
def buy(ticker, date, shares, price = None, sector=None, flexCash=False):
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
        dailyPrices = get_stock(ticker)[date:]                                                                          # Gets the daily closing price for the past 20ish years
        dailyPrices.name = ticker                                                                                           # Renames the Pandas Series with the ticker before appending to the portfolio
        if sector != None:                                                                                              # Adds the given ticker to the sector's list if it's not in there already
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
    if 'Cash' not in portfolio.columns and 'Cash' not in balances.columns:                                              # Checks if already in the portfolio as to not overwrite any existing holding
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
        deposit(price*shares - portfolio['Cash'].loc[date], date)

    # Removes the purchase price from cash balances in balances and cash position in portfolio
    portfolio['Cash'].loc[date:] -= price * shares
    balances['Cash'].loc[date:] -= price * shares

    # Checks for existing position in portfolio and handles accordingly
    if ticker not in portfolio.columns:                                                                                 # Checks if already in the portfolio as to not overwrite any existing holding
        portfolio = pd.concat([portfolio, dailyPrices*shares], axis=1)                                                  # Adds the total value (Share Price * Share Count) to the portfolio for tracking
    else:
        portfolio[ticker][date:] += shares * dailyPrices                                                                # Adds the holding to an existing holding

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
def sell(ticker, date, shares, price = None, sector = None):
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
        dailyprices = get_stock(ticker)[date:]                                                                          # Gets the daily closing stock price for the past 5y

    except:
        print('Not Found:', ticker)
        return None

    # Sets sales price if specified, uses closing price otherwise
    if not np.isnan(price):                                                                                             # Lets you set a price if you bought for a specific price
        portfolio[ticker][date] = price * shares
    else:
        price = dailyprices[date]

    # Subtracts the sale amount from the position in portfolio and balance in balances, then updates share count
    portfolio[ticker][date:] -= dailyprices[date:] * shares                                                             # Subtracts the value of the shares sold from future holdings
    balances['Cash'].loc[date:] -= shares * holdings[ticker].price
    holdings[ticker].sell(shares)


### Analytics ###
def analytics(level='basic'):
    # This should return key portfolio stats if 'basic':
    #   -Performance: Alpha, beta, sharpe, treynor
    #   -Returns: 1M, 3M, YTD, 1Y, Max *If the data goes back this far
    #   -Total Invested
    # Advanced is basic+ and includes:
    #   -Max Drawdown: From the first datapoint in the portfolio
    #   -R-Squared: Shows significance of beta and alpha
    #   -Expected Return: Calculated Cost of Equity for Portfolio
    #   -Std. Deviation of Returns

    global portfolio
    global balances

    # Daily Return Data #
    analytics = {}

    # Reindex portfolio and balances to be the same
    if not portfolio.index.equals(balances.index):
        newIndex = portfolio.index.union(balances.index)
        portfolio = portfolio.reindex(newIndex, method='pad')
        balances = balances.reindex(newIndex, method='pad')

    portfolioSum = portfolio.fillna(method='pad').sum(axis=1)
    balancesSum = balances.fillna(0)
    portfolioReturns = (portfolioSum.shift(1) - portfolioSum - (balancesSum.shift(1) - balancesSum)) / (portfolioSum + (balancesSum.shift(1) - balancesSum))
    portfolioReturns.name = 'Portfolio'
    portfolioNormalized = (portfolioReturns + 1).cumprod()

    marketReturns = get_stock('spy')[portfolioSum.index[0]:].pct_change()*100
    marketReturns.name = 'SP500'

    first_index = portfolioNormalized.first_valid_index()                                                                # Try to delete
    portfolioIndexNorm = pd.concat([portfolioNormalized[first_index:], marketReturns[first_index:]], axis=1) - riskFreeDaily
    portfolioIndexNorm = portfolioIndexNorm[1:]                                                                                     # Try to delete

    # Returns
    analytics['% Return-1M'] = (portfolioNormalized.iloc[-1] / portfolioNormalized.iloc[portfolioNormalized.index.get_loc(datetime.date.today()-datetime.timedelta(days=30), method='pad')] - 1) * 100
    analytics['% Return-3M'] = (portfolioNormalized.iloc[-1] / portfolioNormalized.iloc[portfolioNormalized.index.get_loc(datetime.date.today()-datetime.timedelta(days=90), method='pad')] - 1) * 100
    analytics['% Return-YTD'] = (portfolioNormalized.iloc[-1] / portfolioNormalized.iloc[portfolioNormalized.index.get_loc(datetime.date(datetime.date.today().year, 1, 1), method='pad')] - 1) * 100
    analytics['% Return-1Y'] = (portfolioNormalized.iloc[-1] / portfolioNormalized.iloc[portfolioNormalized.index.get_loc(datetime.date.today()-datetime.timedelta(days=365), method='pad')] - 1) * 100
    analytics['% Return-Max'] = (portfolioNormalized.iloc[-1] / portfolioNormalized.iloc[0] - 1) * 100
    analytics['% Return-CAGR'] = ((portfolioNormalized.iloc[-1] / portfolioNormalized.iloc[0])**((1/((portfolioNormalized.index[-1] - portfolioNormalized.index[0]).total_seconds()/(86400*365)))) - 1) * 100
    analytics['Portfolio Cap'] = float(portfolioSum.iloc[-1])

    # Statistics
    #   Beta = Adjusted Beta
    #   Alpha = Annualized Alpha (Based on Portfolio CAGR)
    analytics['Beta'] = portfolioIndexNorm.Portfolio.cov(portfolioIndexNorm.SP500)/portfolioIndexNorm.SP500.var() * (2 / 3) + (1 / 3)
    expected_return = (analytics["Beta"] * (marketRate - 1 - (riskFree-1)) + (riskFree-1)) * 100
    analytics['Alpha'] = (analytics['% Return-CAGR'] / 100 - expected_return / 100) * 100
    analytics['Sharpe'] = float((analytics['% Return-CAGR'] / 100 - (riskFree - 1)) / ((portfolioReturns[portfolioReturns.first_valid_index():] / 100).std() * 252**0.5))
    analytics['Treynor'] = float((analytics['% Return-CAGR'] / 100 - (riskFree - 1)) / analytics['Beta'])

    # Advanced Statistics
    #   Std. Deviation = Annualized StdDev = Daily StdDev * sqrt(# of Trading Days)
    if level == 'advanced':
        drawdown = pd.DataFrame()
        drawdown['Prices'] = portfolioNormalized
        drawdown['CumMax'] = drawdown.Prices.cummax()
        drawdown['Drawdown'] = (drawdown['Prices'] - drawdown['CumMax']) / drawdown['CumMax']
        analytics['Max Drawdown'] = float(drawdown['Drawdown'].min()) * 100
        analytics['Std. Deviation'] = float(portfolioIndexNorm.Portfolio.std() * 252**0.5)
        analytics['R-Squared'] = (portfolioIndexNorm.Portfolio.cov(portfolioIndexNorm.SP500) / (portfolioIndexNorm.Portfolio.std() * portfolioIndexNorm.SP500.std()))**2
        analytics['Expected Return'] = expected_return

    portfolioNormalized.to_excel('./outputs/portfolioNormalized.xlsx')

    return pd.Series(analytics, index = list(analytics.keys())).round(3)

### Sector Analytics ###
def sector_analytics(level='basic', excel=False):
    portfolio_bysector = pd.DataFrame()
    sector_netinvested = pd.DataFrame()
    aPortfolio = portfolio.fillna(method='pad')
    for sector, holdings in sectorHoldings.items():
        portfolio_bysector[sector] = aPortfolio[holdings].sum(axis=1)
        suminvested = pd.Series()
        for ticker in holdings:
            if len(suminvested) == 0:
                suminvested = holdings[ticker].baseposition
            else:
                suminvested = suminvested.reindex(suminvested.index.union(holdings[ticker].baseposition.index), method='pad')
                base_reindexed = holdings[ticker].baseposition.reindex(suminvested.index, method='pad')
                suminvested = suminvested.add(base_reindexed, fill_value = 0)
        sector_netinvested = sector_netinvested.reindex(sector_netinvested.index.union(suminvested.index), method='pad')
        suminvested = suminvested.reindex(sector_netinvested.index, method='pad')
        sector_netinvested[sector] = suminvested
    sector_netinvested = sector_netinvested.reindex(portfolio_bysector.index, method='pad')
    sector_netinvested = sector_netinvested.fillna(method='pad')

    # Daily Return Data #
    analytics = {}
    marketReturns = get_stock('spy')
    marketReturns = marketReturns[portfolio_bysector.index[0]:].pct_change()*100
    marketReturns.name = 'SP500'
    portfolioNormalized = portfolio_bysector.divide(sector_netinvested, axis=0)
    normalized_returns = portfolioNormalized.pct_change()*100
    first_index = normalized_returns.first_valid_index()
    portfolioIndexNorm = pd.concat([normalized_returns[first_index:], marketReturns[first_index:]], axis=1) - riskFreeDaily
    portfolioIndexNorm = portfolioIndexNorm[1:]


    # Returns #
    for column in portfolioNormalized.columns:
        position = {}
        position['% Return-1M'] = (portfolioNormalized[column].iloc[-1] / portfolioNormalized[column].iloc[portfolioNormalized[column].index.get_loc(datetime.date.today()-datetime.timedelta(days=30), method='pad')] - 1) * 100
        position['% Return-3M'] = (portfolioNormalized[column].iloc[-1] / portfolioNormalized[column].iloc[portfolioNormalized[column].index.get_loc(datetime.date.today()-datetime.timedelta(days=90), method='pad')] - 1) * 100
        position['% Return-YTD'] = (portfolioNormalized[column].iloc[-1] / portfolioNormalized[column].iloc[portfolioNormalized[column].index.get_loc(datetime.date(datetime.date.today().year, 1, 1), method='pad')] - 1) * 100
        position['% Return-1Y'] = (portfolioNormalized[column].iloc[-1] / portfolioNormalized[column].iloc[portfolioNormalized[column].index.get_loc(datetime.date.today()-datetime.timedelta(days=365), method='pad')] - 1) * 100
        position['% Return-Max'] = (portfolioNormalized[column].iloc[-1] / portfolioNormalized[column].iloc[0] - 1) * 100
        position['% Return-CAGR'] = ((portfolioNormalized[column].iloc[-1] / portfolioNormalized[column].iloc[0])**((1/((portfolioNormalized[column].index[-1] - portfolioNormalized[column].index[0]).total_seconds()/(86400*365)))) - 1) * 100
        position['Sector Cap'] = float(portfolio_bysector.iloc[-1][column])

        # Statistics #
        #   Beta = Adjusted Beta
        #   Alpha = Annualized Alpha (Based on Portfolio CAGR)
        position['Beta'] = portfolioIndexNorm[column].cov(portfolioIndexNorm.SP500)/portfolioIndexNorm.SP500.var() * (2 / 3) + (1 / 3)
        expected_return = (position["Beta"] * (marketRate - 1 - (riskFree-1)) + (riskFree-1)) * 100
        position['Alpha'] = (position['% Return-CAGR'] / 100 - expected_return / 100) * 100
        position['Sharpe'] = float((position['% Return-CAGR'] / 100 - (riskFree - 1)) / ((normalized_returns[column][normalized_returns.first_valid_index():] / 100).std() * 252**0.5))
        position['Treynor'] = float((position['% Return-CAGR'] / 100 - (riskFree - 1)) / position['Beta'])

        # Advanced Statistics #
        #   Std. Deviation = Annualized StdDev = Daily StdDev * sqrt(# of Trading Days)
        if level == 'advanced':
            drawdown = pd.DataFrame()
            drawdown['Prices'] = portfolioNormalized[column]
            drawdown['CumMax'] = drawdown.Prices.cummax()
            drawdown['Drawdown'] = (drawdown['Prices'] - drawdown['CumMax']) / drawdown['CumMax']
            position['Max Drawdown'] = float(drawdown['Drawdown'].min()) * 100
            position['Std. Deviation'] = float(portfolioIndexNorm[column].std(axis=0) * (252**0.5))
            position['R-Squared'] = (portfolioIndexNorm[column].cov(portfolioIndexNorm.SP500) / (portfolioIndexNorm[column].std(axis=0) * portfolioIndexNorm.SP500.std()))**2
            position['Expected Return'] = expected_return

        analytics[column] = position

    output = pd.DataFrame(analytics, index = list(position.keys())).round(3)
    output2 = portfolioNormalized
    output3 = pd.DataFrame(requests.get(fmpurl+'historical-price-full/SPY?serietype=line').json()['historical']).set_index('date')


    if excel:
        output.to_excel('./outputs/sectorbreakdown.xlsx')
        output2.to_excel('./outputs/sector_prices.xlsx')
        output3.to_excel('./outputs/market.xlsx')
    return output

### Performance ###
def performance(ticker, select_date = 'present'):
    # This function gives the performance of a certain holding
    #   -Stock Price Return: Gives the performance based on average share price
    #   -Average Share Price: Gives the average holding price at that date
    analytics = {}
    try:
        stock_value = portfolio[ticker]
    except KeyError:
        return f'{ticker} not found'
    marketReturns = get_stock('spy')
    marketReturns = marketReturns[stock_value.index[0]:].pct_change()*100
    marketReturns.name = 'SP500'
    amountinvested = holdings[ticker].baseposition.reindex(stock_value.index, method='pad')
    portfolioNormalized = stock_value.divide(amountinvested, axis=0)
    normalized_returns = portfolioNormalized.pct_change()*100
    normalized_returns.name = ticker
    first_index = normalized_returns.first_valid_index()
    portfolioIndexNorm = pd.concat([normalized_returns[first_index:], marketReturns[first_index:]], axis=1) - riskFreeDaily
    portfolioIndexNorm = portfolioIndexNorm[1:]

    # Returns
    analytics['% Return-1M'] = (portfolioNormalized.iloc[-1] / portfolioNormalized.iloc[portfolioNormalized.index.get_loc(datetime.date.today()-datetime.timedelta(days=30), method='pad')] - 1) * 100
    analytics['% Return-3M'] = (portfolioNormalized.iloc[-1] / portfolioNormalized.iloc[portfolioNormalized.index.get_loc(datetime.date.today()-datetime.timedelta(days=90), method='pad')] - 1) * 100
    analytics['% Return-YTD'] = (portfolioNormalized.iloc[-1] / portfolioNormalized.iloc[portfolioNormalized.index.get_loc(datetime.date(datetime.date.today().year, 1, 1), method='pad')] - 1) * 100
    analytics['% Return-1Y'] = (portfolioNormalized.iloc[-1] / portfolioNormalized.iloc[portfolioNormalized.index.get_loc(datetime.date.today()-datetime.timedelta(days=365), method='pad')] - 1) * 100
    analytics['% Return-Max'] = (portfolioNormalized.iloc[-1] / portfolioNormalized[0] - 1) * 100
    analytics['% Return-CAGR'] = ((portfolioNormalized[-1] / portfolioNormalized[0])**((1/((portfolioNormalized.index[-1] - portfolioNormalized.index[0]).total_seconds()/(86400*365)))) - 1) * 100
    analytics['Beta'] = portfolioIndexNorm[ticker].cov(portfolioIndexNorm.SP500)/portfolioIndexNorm.SP500.var() * (2 / 3) + (1 / 3)
    expected_return = (analytics["Beta"] * (marketRate - 1 - (riskFree-1)) + (riskFree-1)) * 100
    analytics['Alpha'] = (analytics['% Return-CAGR'] / 100 - expected_return / 100) * 100

    return pd.Series(analytics, index=list(analytics.keys())).round(3)

### Correlation ###
def correlation(ticker = None, index = 'SPX', sector = None, commodity = None, econ = None, treas = None):
    # Gives the correlation of a given ticker to a given index, defaulting as
    # the SP500 for a total market proxy. Designed to be used to get sector
    # correlations to their respective index
    outputs = pd.DataFrame()
    data_ticker = get_stock(ticker)                                                                                     # Gets the daily closing price of a stock starting on the buy date
    data_ticker = data_ticker
    data_index = get_index(index)
    index_coef, index_int, index_corr, index_p, index_std = linregress(data_index, data_ticker)
    index_vals = pd.Series({'Coefficient':index_coef, 'Intercept':index_int, 'Correlation':index_corr, 'R-Squared':index_corr**2})
    index_vals.name = 'Index: ' + index
    outputs = outputs.append(index_vals, sort=False)
    if sector != None:
            data_sector = get_index(sector)
            sector_coef, sector_int, sector_corr, sector_p, sector_std = linregress(data_sector, data_ticker)
            sector_vals = pd.Series({'Coefficient':sector_coef, 'Intercept':sector_int, 'Correlation':sector_corr, 'R-Squared':sector_corr**2})
            sector_vals.name = 'Sector: ' + sector
            outputs = outputs.append(sector_vals, sort=False)
    if commodity != None:
        data_commodity = get_data(commodity)
        data_commodity = data_commodity.reindex(data_ticker.index, method='pad')
        commodity_coef, commodity_int, commodity_corr, commodity_p, commodity_std = linregress(data_commodity, data_ticker)
        commodity_vals = pd.Series({'Coefficient':commodity_coef, 'Intercept':commodity_int, 'Correlation':commodity_corr, 'R-Squared':commodity_corr**2})
        commodity_vals.name = 'Commodity: ' + commodity
        outputs = outputs.append(commodity_vals, sort=False)
    if econ != None:
        data_econ = get_data(econ)
        data_econ = data_econ.reindex(index = data_ticker.index, method = 'pad')
        econ_coef, econ_int, econ_corr, econ_p, econ_std = linregress(data_econ, data_ticker)
        econ_vals = pd.Series({'Coefficient':econ_coef, 'Intercept':econ_int, 'Correlation':econ_corr, 'R-Squared':econ_corr**2})
        econ_vals.name = 'Econ: ' + econ
        outputs = outputs.append(econ_vals, sort=False)
    if treas != None:
        data_treas = get_treas(treas)
        data_treas = data_treas.reindex(index = data_ticker.index, method = 'pad')
        treas_coef, treas_int, treas_corr, treas_p, treas_std = linregress(data_treas, data_ticker)
        treas_vals = pd.Series({'Coefficient':treas_coef, 'Intercept':treas_int, 'Correlation':treas_corr, 'R-Squared':treas_corr**2})
        treas_vals.name = 'Treas: ' + treas
        outputs = outputs.append(treas_vals, sort=False)
    return outputs

### Correlation Matrix ###
def correlation_matrix(group_by="portfolio", excel=False):
    if group_by == 'portfolio':
        aPortfolio = portfolio
        portfolioSum = aPortfolio.sum(axis=1)
        netcash_reindexed = netcash.reindex(aPortfolio.index, method='pad')
        portfolioNormalized = (portfolioSum / netcash_reindexed)
        normalized_returns = portfolioNormalized.pct_change()*100
        normalized_returns.name = 'Portfolio'
        first_index = normalized_returns.first_valid_index()
        normalized_returns = normalized_returns[first_index:]
        print(normalized_returns)
        output = normalized_returns.corr()

        if excel == True:
            output.to_excel('./outputs/portfolio_corr.xlsx')

    elif group_by == 'intersector':
        portfolio_bysector = pd.DataFrame()
        sector_netinvested = pd.DataFrame()
        for sector, holdings in sectorHoldings.items():
            portfolio_bysector[sector] = portfolio[holdings].sum(axis=1)
            suminvested = pd.Series()
            for ticker in holdings:
                if len(suminvested) == 0:
                    suminvested = holdings[ticker].baseposition
                else:
                    suminvested = suminvested.reindex(suminvested.index.union(holdings[ticker].baseposition.index), method='pad')
                    base_reindexed = holdings[ticker].baseposition.reindex(suminvested.index, method='pad')
                    suminvested = suminvested.add(base_reindexed, fill_value = 0)
            sector_netinvested = sector_netinvested.reindex(sector_netinvested.index.union(suminvested.index), method='pad')
            suminvested = suminvested.reindex(sector_netinvested.index, method='pad')
            sector_netinvested[sector] = suminvested
            sector_netinvested = sector_netinvested.reindex(portfolio_bysector.index, method='pad')
            sector_netinvested = sector_netinvested.fillna(method='pad')

        # Daily Return Data #
        portfolioNormalized = portfolio_bysector.divide(sector_netinvested, axis=0)
        normalized_returns = portfolioNormalized.pct_change()
        normalized_returns = normalized_returns[normalized_returns.first_valid_index():]

        output = normalized_returns.corr()

        if excel == True:
            output.to_excel('./outputs/intersector_corr.xlsx')

    elif group_by == 'intrasector':
        pass

    return output

### Ratios ###
def ratios(method='total'):
    if method == 'total':
        notfound = 0
        ratios = {'pe':0, 'pb':0, 'dyield':0}
        cap = 0
        tickers = set(portfolio.columns.tolist())
        for ticker in tickers:
            try:
                weight = portfolio[ticker][-2]
                pe = get_ratio(ticker, 'pe')
                pb = get_ratio(ticker, 'pb')
                div = get_ratio(ticker, 'dyield')
                if pe >= 0:
                    ratios['pe'] += pe * weight
                if pb >= 0:
                    ratios['pb'] += pb * weight
                ratios['dyield'] += div * weight
                cap += weight
            except:
                notfound += 1
        ratios = pd.Series(ratios)
        ratios /= cap
    return ratios

### Historical Analytics ###
def historical_analytics(date):
    # This should return basic analytics for a certain date
    #   -May not be operational until AlphaVantage is linked
    pass

### Chart ###
def chart(topic, beta_method='market', period = 'ytd'):
    # This should return a chart of the desired stat:
    #   -Holdings: Probably a pie chart by sector
    #   -Returns: Bar chart of the returns over
    #   -Beta: Should return a linear regression of the daily returns, which
    #   is the chart used to show the beta.
    #       - Point out beta in chart
    #       - Methods: market, sector, custom?
    #   -Alpha: Should return the Security Characteristic Line
    #       - Point out the alpha and beta
    #   -Correlation: Visual version of the correlation function
    if period == 'ytd':
        date = datetime.date(datetime.date.today().year, 1, 1)
    elif period == '1m':
        date = datetime.date.today() - datetime.timedelta(days=30)
    elif period == '3m':
        date = datetime.date.today() - datetime.timedelta(days=90)
    elif period == 'year':
        date = datetime.date.today() - datetime.timedelta(days=365)
    else:
        return "Invalid Date"

    if topic == 'holdings':
        pass
    elif topic == 'returns':
        c_portfolio = portfolio
        c_portfolio['CashBalance'] = cashbalance.reindex(c_portfolio.index, method='nearest')
        c_portfolio_sum = c_portfolio.sum(axis=1)
        c_portfolio_sum = c_portfolio_sum[c_portfolio_sum.index.get_loc(date, method='nearest'):]
        marketReturns = get_stock('spy')
        marketReturns = marketReturns[marketReturns.index.get_loc(date, method='nearest'):]
        marketReturns = marketReturns[marketReturns.index[0]:] / marketReturns[marketReturns.index[0]] * 10000
        marketReturns.name = 'SP500'
        netcash_reindexed = netcash.reindex(c_portfolio_sum.index, method='nearest')
        portfolioNormalized = (c_portfolio_sum / netcash_reindexed)
        normalized_returns = portfolioNormalized / portfolioNormalized[0] * 10000
        normalized_returns.name = 'Portfolio'
        first_index = normalized_returns.first_valid_index()
        portfolioIndexNorm = pd.concat([normalized_returns[first_index:], marketReturns[first_index:]], axis=1)
        portfolioIndexNorm = portfolioIndexNorm[1:]
        portfolioIndexNorm.plot()
        plt.show()
        return None
    elif topic == 'beta':
        pass
    elif topic == 'alpha':
        pass
    elif topic == 'correlation':
        pass
    else:
        return 'Invalid argument passed as topic in chart(topic)'

### Holdings ###
def holdingsStatistics(date = 'present'):
    # Returns every holding in the portfolio:
    #   -Ticker and Company Name
    #   -Price and Shares Purchased (Price here is average holding price)
    #   -Total value of the holding and its percentage of the portfolio
    #   -Total gain/loss in dollars and percentage
    #   -Dividend Yield
    pass

### Holdings Sector ###
def holdings_sector(date = 'present'):
    # Returns the same metrics as holdings, but broken into sectors
    pass


########################
### Function Running ###
########################

### Running if  ###
if __name__ == '__main__':

    ### Import Data from Excel ###
    if len(sys.argv) > 1:
        import_excel(sys.argv[1], flexCash=True)
    else:
        import_excel('./inputs/transactions2.xlsx', flexCash=True)

    print(analytics('advanced'))
