######################
### Module Imports ###
######################

from data_mod import *
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import linregress
import numpy as np
import requests
import sys

#################
### Constants ###
#################

### Risk Free Rate ###
riskfree = get_treas('10 yr')[-1] / 100                                         # Annual risk free rate
riskfree_daily = ((riskfree + 1) ** (1/252) - 1)                                # Converts annual risk free to daily

#########################
### Class Definitions ###
#########################

### Holding Class ###
class Holding():
    def __init__(self, ticker, shares, price):
        self.ticker = ticker
        self.shares = shares
        self.price = price

    def __str__(self):
        return f'Holding {self.shares} shares of {self.ticker} at ${self.price}'

############################
### Function Definitions ###
############################

### Import Excel ###
def import_excel(filename, flex_cash=False):
    # Imports the excel file and turns it into a DataFrame of Daily Prices
    global portfolio
    deposit(0, datetime.date(1980,1,1))                                         # Initializes the cash balance to 0 at the earliest time in python
    transactions = pd.read_excel(filename)                                      # Reads the excel file as a pandas dataframe
    transactions.Action = transactions.Action.str.lower()                       # The following 2 lines make the columns lowercase so theyre easier to use
    transactions.Ticker = transactions.Ticker.str.lower()
    transactions = transactions.sort_values('Date')                             # Sorts Transactions by Date
    for index, trade in transactions.iterrows():                                # Iterates over the trades in the excel sheet and adds them to the portfolio
        if trade.Action == 'buy':
            buy(trade.Ticker, trade.Date.date(), trade.Shares, trade.Price, trade.Sector, flex_cash)
        elif trade.Action == 'sell':
            sell(trade.Ticker, trade.Date.date(), trade.Shares, trade.Price)
        elif trade.Action == 'deposit':
            deposit(trade.Price, trade.Date.date())
        elif trade.Action == 'withdraw':
            withdraw(trade.Price, trade.Date.date())
        else:
            print('Invalid Order Type For:', trade.Ticker)

### Deposit ###
def deposit(cash, date):
    global portfolio
    global cashbalance
    global netcash
    netcash = netcash.sort_index()                                              # Sorts the netcash DF so the .get_loc can get the correct index
    if len(cashbalance) != 0:
        cashbalance.loc[date] = cashbalance.iloc[cashbalance.index.get_loc(date, method='pad')] + cash        # Adds the deposited cash to the cashbalance in the portfolio
    else:
        cashbalance.loc[date] = cash
    if len(netcash) != 0:                                                       # Sets the NCB of the given day equal to the previous NCB plus the deposit
        netcash.loc[date] = netcash.iloc[netcash.index.get_loc(date, method='pad')]+cash
    else:
        netcash.loc[date] = cash

### Withdraw ###
def withdraw(cash, date):
    global portfolio
    global netcash
    global cashbalance
    netcash = netcash.sort_index()                                              # Sorts the netcash DF so the .get_loc can get the correct index
    cashbalance.loc[date] = cashbalance.iloc[cashbalance.index.get_loc(date, method='pad')] - cash            # Subtracts the withdrawn cash to the cashbalance in the portfolio
    netcash.loc[date] = netcash.iloc[netcash.index.get_loc(date, method='pad')]-cash  # Sets the NCB of the given day equal to the previous NCB minus the withdrawal

### Buy ###
def buy(ticker, date, shares, price = None, sector=None, flex_cash=False):
    # Buys a stock in the global variable: portfolio

    global portfolio
    global sector_holdings
    global cashbalance
    try:
        dailyprices = get_stock(ticker)                                         # Gets the daily closing price for the past 5y
        dailyprices = dailyprices[date:]                                  # Adjusts stock data to start at the given date
        if sector != None:                                                      # Adds the given ticker to the sector list if it's not in there already
            if ticker not in sector_holdings[sector]:
                sector_holdings[sector].append(ticker)
    except:
        print('Not Found:', ticker)
        return None
    if not np.isnan(price):                                                     # Lets you set a price if you bought for a specific price
        dailyprices.loc[date] = price
    else:
        price = dailyprices.loc[date]
    dailyprices.name = ticker                                                   # Renames the Pandas Series with the ticker before appending to the portfolio
    if ticker not in portfolio.columns:                                         # Checks if already in the portfolio as to not overwrite any existing holding
        portfolio = pd.concat([portfolio,dailyprices*shares],axis=1)            # Adds the total value (Share Price * Share Count) to the portfolio for tracking
    else:
        portfolio[ticker][date:] += shares * dailyprices                        # Adds the holding to an existsing holding
    cashbalance.loc[date] = cashbalance.iloc[cashbalance.index.get_loc(date, method='pad')] - price*shares
    if flex_cash == True and cashbalance.loc[date] < 0:
        cash_needed = 0 - cashbalance.loc[date]
        deposit(cash_needed, date)
    if ticker in holdings_stats:
        holdings_stats[ticker].buy(date, shares, price)
    else:
        holdings_stats[ticker] = Holding(ticker, date, shares, price)

### Sell ###
def sell(ticker, date, shares, price = None, sector = None):
    # Sells a stock in the global variable: portfolio
    #   -Returns?
    global portfolio
    global cashbalance
    nextday = date + datetime.timedelta(days=1)
    try:
        dailyprices = get_stock(ticker)                                         # Gets the daily closing stock price for the past 5y
        dailyprices = dailyprices[date:]                                  # Adjusts stock data to start at the given date
        if not np.isnan(price):                                                 # Lets you set a price if you bought for a specific price
            portfolio[ticker][date] = price * shares
        else:
            price = dailyprices[date]
    except:
        print('Not Found:', ticker)
        return None
    portfolio[ticker][nextday:] -= dailyprices[nextday:] * shares               # Subtracts the value of the shares sold from future holdings
    cashbalance.loc[date] = cashbalance.iloc[cashbalance.index.get_loc(date, method='pad')] + price*shares
    holdings_stats[ticker].sell(date, shares)

### Analytics ###
def analytics(level = 'basic'):
    # This should return key portfolio stats if 'basic':
    #   -Performance: Alpha, beta, sharpe, treynor
    #   -Returns: 1M, 3M, YTD, 1Y, Max *If the data goes back this far
    #   -Total Invested
    # Advanced is basic+ and includes:
    #   -Max Drawdown: From the first datapoint in the portfolio
    #   -R-Squared: Shows significance of beta and alpha
    #   -Expected Return: Calculated Cost of Equity for Portfolio
    #   -Std. Deviation of Returns

    # Daily Return Data #
    analytics = {}
    a_portfolio = portfolio.fillna(method = 'pad')
    a_portfolio['CashBalance'] = cashbalance.reindex(a_portfolio.index, method='pad')
    a_portfolio_sum = a_portfolio.sum(axis=1)
    market_returns = get_stock('spy')
    market_returns = market_returns[a_portfolio_sum.index[0]:].pct_change()*100
    market_returns.name = 'SP500'
    netcash_reindexed = netcash.reindex(a_portfolio.index, method='pad')
    normalized_prices = (a_portfolio_sum / netcash_reindexed)
    normalized_returns = normalized_prices.pct_change()*100
    normalized_returns.name = 'Portfolio'
    first_index = normalized_returns.first_valid_index()
    normal_index = pd.concat([normalized_returns[first_index:], market_returns[first_index:]], axis=1) - riskfree_daily
    normal_index = normal_index[1:]

    # Returns
    analytics['% Return-1M'] = (normalized_prices.iloc[-1] / normalized_prices.iloc[normalized_prices.index.get_loc(datetime.date.today()-datetime.timedelta(days=30), method='pad')] - 1) * 100
    analytics['% Return-3M'] = (normalized_prices.iloc[-1] / normalized_prices.iloc[normalized_prices.index.get_loc(datetime.date.today()-datetime.timedelta(days=90), method='pad')] - 1) * 100
    analytics['% Return-YTD'] = (normalized_prices.iloc[-1] / normalized_prices.iloc[normalized_prices.index.get_loc(datetime.date(datetime.date.today().year, 1, 1), method='pad')] - 1) * 100
    analytics['% Return-1Y'] = (normalized_prices.iloc[-1] / normalized_prices.iloc[normalized_prices.index.get_loc(datetime.date.today()-datetime.timedelta(days=365), method='pad')] - 1) * 100
    analytics['% Return-Max'] = (normalized_prices.iloc[-1] / normalized_prices[0] - 1) * 100
    analytics['% Return-CAGR'] = ((normalized_prices[-1] / normalized_prices[0])**((1/((normalized_prices.index[-1] - normalized_prices.index[0]).total_seconds()/(86400*365)))) - 1) * 100
    analytics['Portfolio Cap'] = float(a_portfolio_sum.iloc[-1])

    # Statistics
    #   Beta = Adjusted Beta
    #   Alpha = Annualized Alpha (Based on Portfolio CAGR)
    analytics['Beta'] = normal_index.Portfolio.cov(normal_index.SP500)/normal_index.SP500.var() * (2 / 3) + (1 / 3)
    expected_return = (analytics["Beta"] * (market_rate - 1 - (riskfree-1)) + (riskfree-1)) * 100
    analytics['Alpha'] = (analytics['% Return-CAGR'] / 100 - expected_return / 100) * 100
    analytics['Sharpe'] = float((analytics['% Return-CAGR'] / 100 - (riskfree - 1)) / ((normalized_returns[normalized_returns.first_valid_index():] / 100).std() * 252**0.5))
    analytics['Treynor'] = float((analytics['% Return-CAGR'] / 100 - (riskfree - 1)) / analytics['Beta'])

    # Advanced Statistics
    #   Std. Deviation = Annualized StdDev = Daily StdDev * sqrt(# of Trading Days)
    if level == 'advanced':
        drawdown = pd.DataFrame()
        drawdown['Prices'] = normalized_prices
        drawdown['CumMax'] = drawdown.Prices.cummax()
        drawdown['Drawdown'] = (drawdown['Prices'] - drawdown['CumMax']) / drawdown['CumMax']
        analytics['Max Drawdown'] = float(drawdown['Drawdown'].min()) * 100
        analytics['Std. Deviation'] = float(normal_index.Portfolio.std() * 252**0.5)
        analytics['R-Squared'] = (normal_index.Portfolio.cov(normal_index.SP500) / (normal_index.Portfolio.std() * normal_index.SP500.std()))**2
        analytics['Expected Return'] = expected_return

    normalized_prices.to_excel('./outputs/normalized_prices.xlsx')

    return pd.Series(analytics, index = list(analytics.keys())).round(3)

### Sector Analytics ###
def sector_analytics(level = 'basic', excel = False):
    portfolio_bysector = pd.DataFrame()
    sector_netinvested = pd.DataFrame()
    a_portfolio = portfolio.fillna(method='pad')
    for sector, holdings in sector_holdings.items():
        portfolio_bysector[sector] = a_portfolio[holdings].sum(axis=1)
        suminvested = pd.Series()
        for ticker in holdings:
            if len(suminvested) == 0:
                suminvested = holdings_stats[ticker].baseposition
            else:
                suminvested = suminvested.reindex(suminvested.index.union(holdings_stats[ticker].baseposition.index), method='pad')
                base_reindexed = holdings_stats[ticker].baseposition.reindex(suminvested.index, method='pad')
                suminvested = suminvested.add(base_reindexed, fill_value = 0)
        sector_netinvested = sector_netinvested.reindex(sector_netinvested.index.union(suminvested.index), method='pad')
        suminvested = suminvested.reindex(sector_netinvested.index, method='pad')
        sector_netinvested[sector] = suminvested
    sector_netinvested = sector_netinvested.reindex(portfolio_bysector.index, method='pad')
    sector_netinvested = sector_netinvested.fillna(method='pad')

    # Daily Return Data #
    analytics = {}
    market_returns = get_stock('spy')
    market_returns = market_returns[portfolio_bysector.index[0]:].pct_change()*100
    market_returns.name = 'SP500'
    normalized_prices = portfolio_bysector.divide(sector_netinvested, axis=0)
    normalized_returns = normalized_prices.pct_change()*100
    first_index = normalized_returns.first_valid_index()
    normal_index = pd.concat([normalized_returns[first_index:], market_returns[first_index:]], axis=1) - riskfree_daily
    normal_index = normal_index[1:]


    # Returns #
    for column in normalized_prices.columns:
        position = {}
        position['% Return-1M'] = (normalized_prices[column].iloc[-1] / normalized_prices[column].iloc[normalized_prices[column].index.get_loc(datetime.date.today()-datetime.timedelta(days=30), method='pad')] - 1) * 100
        position['% Return-3M'] = (normalized_prices[column].iloc[-1] / normalized_prices[column].iloc[normalized_prices[column].index.get_loc(datetime.date.today()-datetime.timedelta(days=90), method='pad')] - 1) * 100
        position['% Return-YTD'] = (normalized_prices[column].iloc[-1] / normalized_prices[column].iloc[normalized_prices[column].index.get_loc(datetime.date(datetime.date.today().year, 1, 1), method='pad')] - 1) * 100
        position['% Return-1Y'] = (normalized_prices[column].iloc[-1] / normalized_prices[column].iloc[normalized_prices[column].index.get_loc(datetime.date.today()-datetime.timedelta(days=365), method='pad')] - 1) * 100
        position['% Return-Max'] = (normalized_prices[column].iloc[-1] / normalized_prices[column].iloc[0] - 1) * 100
        position['% Return-CAGR'] = ((normalized_prices[column].iloc[-1] / normalized_prices[column].iloc[0])**((1/((normalized_prices[column].index[-1] - normalized_prices[column].index[0]).total_seconds()/(86400*365)))) - 1) * 100
        position['Sector Cap'] = float(portfolio_bysector.iloc[-1][column])

        # Statistics #
        #   Beta = Adjusted Beta
        #   Alpha = Annualized Alpha (Based on Portfolio CAGR)
        position['Beta'] = normal_index[column].cov(normal_index.SP500)/normal_index.SP500.var() * (2 / 3) + (1 / 3)
        expected_return = (position["Beta"] * (market_rate - 1 - (riskfree-1)) + (riskfree-1)) * 100
        position['Alpha'] = (position['% Return-CAGR'] / 100 - expected_return / 100) * 100
        position['Sharpe'] = float((position['% Return-CAGR'] / 100 - (riskfree - 1)) / ((normalized_returns[column][normalized_returns.first_valid_index():] / 100).std() * 252**0.5))
        position['Treynor'] = float((position['% Return-CAGR'] / 100 - (riskfree - 1)) / position['Beta'])

        # Advanced Statistics #
        #   Std. Deviation = Annualized StdDev = Daily StdDev * sqrt(# of Trading Days)
        if level == 'advanced':
            drawdown = pd.DataFrame()
            drawdown['Prices'] = normalized_prices[column]
            drawdown['CumMax'] = drawdown.Prices.cummax()
            drawdown['Drawdown'] = (drawdown['Prices'] - drawdown['CumMax']) / drawdown['CumMax']
            position['Max Drawdown'] = float(drawdown['Drawdown'].min()) * 100
            position['Std. Deviation'] = float(normal_index[column].std(axis=0) * (252**0.5))
            position['R-Squared'] = (normal_index[column].cov(normal_index.SP500) / (normal_index[column].std(axis=0) * normal_index.SP500.std()))**2
            position['Expected Return'] = expected_return

        analytics[column] = position

    output = pd.DataFrame(analytics, index = list(position.keys())).round(3)
    output2 = normalized_prices
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
    market_returns = get_stock('spy')
    market_returns = market_returns[stock_value.index[0]:].pct_change()*100
    market_returns.name = 'SP500'
    amountinvested = holdings_stats[ticker].baseposition.reindex(stock_value.index, method='pad')
    normalized_prices = stock_value.divide(amountinvested, axis=0)
    normalized_returns = normalized_prices.pct_change()*100
    normalized_returns.name = ticker
    first_index = normalized_returns.first_valid_index()
    normal_index = pd.concat([normalized_returns[first_index:], market_returns[first_index:]], axis=1) - riskfree_daily
    normal_index = normal_index[1:]

    # Returns
    analytics['% Return-1M'] = (normalized_prices.iloc[-1] / normalized_prices.iloc[normalized_prices.index.get_loc(datetime.date.today()-datetime.timedelta(days=30), method='pad')] - 1) * 100
    analytics['% Return-3M'] = (normalized_prices.iloc[-1] / normalized_prices.iloc[normalized_prices.index.get_loc(datetime.date.today()-datetime.timedelta(days=90), method='pad')] - 1) * 100
    analytics['% Return-YTD'] = (normalized_prices.iloc[-1] / normalized_prices.iloc[normalized_prices.index.get_loc(datetime.date(datetime.date.today().year, 1, 1), method='pad')] - 1) * 100
    analytics['% Return-1Y'] = (normalized_prices.iloc[-1] / normalized_prices.iloc[normalized_prices.index.get_loc(datetime.date.today()-datetime.timedelta(days=365), method='pad')] - 1) * 100
    analytics['% Return-Max'] = (normalized_prices.iloc[-1] / normalized_prices[0] - 1) * 100
    analytics['% Return-CAGR'] = ((normalized_prices[-1] / normalized_prices[0])**((1/((normalized_prices.index[-1] - normalized_prices.index[0]).total_seconds()/(86400*365)))) - 1) * 100
    analytics['Beta'] = normal_index[ticker].cov(normal_index.SP500)/normal_index.SP500.var() * (2 / 3) + (1 / 3)
    expected_return = (analytics["Beta"] * (market_rate - 1 - (riskfree-1)) + (riskfree-1)) * 100
    analytics['Alpha'] = (analytics['% Return-CAGR'] / 100 - expected_return / 100) * 100

    return pd.Series(analytics, index = list(analytics.keys())).round(3)

### Correlation ###
def correlation(ticker = None, index = 'SPX', sector = None, commodity = None, econ = None, treas = None):
    # Gives the correlation of a given ticker to a given index, defaulting as
    # the SP500 for a total market proxy. Designed to be used to get sector
    # correlations to their respective index
    outputs = pd.DataFrame()
    data_ticker = get_stock(ticker)                                             # Gets the daily closing price of a stock starting on the buy date
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
        a_portfolio = portfolio
        a_portfolio_sum = a_portfolio.sum(axis=1)
        netcash_reindexed = netcash.reindex(a_portfolio.index, method='pad')
        normalized_prices = (a_portfolio_sum / netcash_reindexed)
        normalized_returns = normalized_prices.pct_change()*100
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
        for sector, holdings in sector_holdings.items():
            portfolio_bysector[sector] = portfolio[holdings].sum(axis=1)
            suminvested = pd.Series()
            for ticker in holdings:
                if len(suminvested) == 0:
                    suminvested = holdings_stats[ticker].baseposition
                else:
                    suminvested = suminvested.reindex(suminvested.index.union(holdings_stats[ticker].baseposition.index), method='pad')
                    base_reindexed = holdings_stats[ticker].baseposition.reindex(suminvested.index, method='pad')
                    suminvested = suminvested.add(base_reindexed, fill_value = 0)
            sector_netinvested = sector_netinvested.reindex(sector_netinvested.index.union(suminvested.index), method='pad')
            suminvested = suminvested.reindex(sector_netinvested.index, method='pad')
            sector_netinvested[sector] = suminvested
            sector_netinvested = sector_netinvested.reindex(portfolio_bysector.index, method='pad')
            sector_netinvested = sector_netinvested.fillna(method='pad')

        # Daily Return Data #
        normalized_prices = portfolio_bysector.divide(sector_netinvested, axis=0)
        normalized_returns = normalized_prices.pct_change()
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
        market_returns = get_stock('spy')
        market_returns = market_returns[market_returns.index.get_loc(date, method='nearest'):]
        market_returns = market_returns[market_returns.index[0]:] / market_returns[market_returns.index[0]] * 10000
        market_returns.name = 'SP500'
        netcash_reindexed = netcash.reindex(c_portfolio_sum.index, method='nearest')
        normalized_prices = (c_portfolio_sum / netcash_reindexed)
        normalized_returns = normalized_prices / normalized_prices[0] * 10000
        normalized_returns.name = 'Portfolio'
        first_index = normalized_returns.first_valid_index()
        normal_index = pd.concat([normalized_returns[first_index:], market_returns[first_index:]], axis=1)
        normal_index = normal_index[1:]
        normal_index.plot()
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
def holdings(date = 'present'):
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

    ### Portfolio ###
    portfolio = pd.DataFrame()                                                  # Dataframe giving portfolio balances of each holding
    balances = pd.DataFrame()                                                   # Series holding the balance that created each holding in "portfolio"
    pBalance = pd.Series()                                                      # Series storing the balance of the overall portfolio

    ### Sector Holdings ###
    sector_holdings = {'Staples':[], 'Discretionary':[], 'Energy':[],
    'REITs':[], 'Financials':[], 'Healthcare':[], 'Industrials':[],
    'Utilities':[], 'Macro':[], 'Technology':[], 'Fixed Income':[]}

    ### Import Data from Excel ###
    if len(sys.argv) > 1:
        import_excel(sys.argv[1], flex_cash=True)
    else:
        import_excel('./inputs/transactions2.xlsx', flex_cash=True)
