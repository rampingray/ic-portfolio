######################
### Module Imports ###
######################

from data_mod import *
import generator
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

### Risk Free Rate ###
riskFree = get_treas('10 yr')[-1] / 100  # Annual risk free rate (percentage)
riskFreeDaily = ((riskFree + 1) ** (1 / 252) - 1)  # Converts annual risk free to daily (percentage)

### Market Rate ###
marketRate = 0.08  # Open to being changed

############################
### Function Definitions ###
############################

### Load Data ###
def load_data(type = 'excel'):
    if type == 'excel':
        return generator.import_excel('./inputs/transactions_5Y.xlsx', flexCash=True, savePickle=True)

    elif type == 'pickle':
        return generator.import_pickle('./pickles/portfolio.pkl',
                                       './pickles/balances.pkl',
                                       './pickles/holdings.pkl',
                                       './pickles/sectorHoldings.pkl')

    else:
        print('Unknown Type')


### Analytics ###
def analytics(portfolio, balances, level='basic'):
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

    # Reindex portfolio and balances to be the same
    if not portfolio.index.equals(balances.index):
        newIndex = portfolio.index.union(balances.index)
        portfolio = portfolio.reindex(newIndex, method='pad')
        balances = balances.reindex(newIndex, method='pad')

    sumPortfolio = portfolio.fillna(method='pad').sum(axis=1)
    sumBalances = balances.fillna(0).sum(axis=1)
    returnsPortfolio = (sumPortfolio - sumPortfolio.shift(1)
        - (sumBalances - sumBalances.shift(1))) / (sumPortfolio.shift(1))
    returnsPortfolio.name = 'Portfolio'
    returnsPortfolio.iloc[0] = 0
    normalizedPortfolio = (returnsPortfolio + 1).cumprod()

    returnsMarket = get_stock('spy')[sumPortfolio.index[0]:].pct_change() * 100
    returnsMarket.name = 'SP500'
    returnsMarket.iloc[0] = 0
    normalizedMarket = (returnsMarket / 100 + 1).cumprod()

    returnsPortfolioMarket = pd.concat([returnsPortfolio * 100, returnsMarket], axis=1)[1:] - riskFreeDaily

    returnsWeekly = returnsPortfolioMarket.resample('W-MON').agg(lambda x: (1 + x / 100).prod() - 1) * 100

    # Returns
    analytics['Pct. Return 1M'] = (normalizedPortfolio.iloc[-1]
        / normalizedPortfolio.iloc[normalizedPortfolio.index.get_loc(datetime.date.today()
        - datetime.timedelta(days=30), method='pad')] - 1) * 100
    analytics['Pct. Return 3M'] = (normalizedPortfolio.iloc[-1]
        / normalizedPortfolio.iloc[normalizedPortfolio.index.get_loc(datetime.date.today()
        - datetime.timedelta(days=90), method='pad')] - 1) * 100
    analytics['Pct. Return YTD'] = (normalizedPortfolio.iloc[-1]
        / normalizedPortfolio.iloc[normalizedPortfolio.index.get_loc(datetime.date(datetime.date.today().year, 1, 1),
        method='pad')] - 1) * 100
    analytics['Pct. Return 1Y'] = (normalizedPortfolio.iloc[-1]
        / normalizedPortfolio.iloc[normalizedPortfolio.index.get_loc(datetime.date.today()
        - datetime.timedelta(days=365),method='pad')] - 1) * 100
    analytics['Pct. Return 3Y'] = (normalizedPortfolio.iloc[-1]
        / normalizedPortfolio.iloc[normalizedPortfolio.index.get_loc(datetime.date.today()
        - datetime.timedelta(days=365 * 3),method='pad')] - 1) * 100
    analytics['Pct. Return Max'] = (normalizedPortfolio.iloc[-1] / normalizedPortfolio.iloc[0] - 1) * 100

    analytics['Pct. Return CAGR'] = ((normalizedPortfolio.iloc[-1] / normalizedPortfolio.iloc[0])
        ** ((1 / ((normalizedPortfolio.index[-1] - normalizedPortfolio.index[0]).total_seconds()
        / (86400 * 365)))) - 1) * 100

    analytics['Portfolio Value'] = float(sumPortfolio.iloc[-1])

    # Statistics
    #   Beta = Adjusted Beta
    #   Alpha = Annualized Alpha (Based on Portfolio CAGR)
    analytics['3Y Adj Beta'] = returnsWeekly['Portfolio'].cov(returnsWeekly.SP500) / returnsWeekly.SP500.var() * (
            2 / 3) + (1 / 3)
    expected_return = (analytics['3Y Adj Beta'] * (marketRate - riskFree) + riskFree) * 100
    analytics['Alpha'] = (analytics['Pct. Return CAGR'] / 100 - expected_return / 100) * 100
    analytics['Sharpe'] = float((analytics['Pct. Return CAGR'] / 100 - riskFree) / ((returnsPortfolio).std() * 252 ** 0.5))
    analytics['Treynor'] = float((analytics['Pct. Return CAGR'] / 100 - riskFree) / analytics['3Y Adj Beta'])

    # Advanced Statistics
    #   Std. Deviation = Annualized StdDev = Daily StdDev * sqrt(# of Trading Days)
    if level == 'advanced':
        drawdown = pd.DataFrame()
        drawdown['Prices'] = normalizedPortfolio
        drawdown['CumMax'] = drawdown.Prices.cummax()
        drawdown['Drawdown'] = (drawdown['Prices'] - drawdown['CumMax']) / drawdown['CumMax']
        analytics['Max Drawdown'] = float(drawdown['Drawdown'].min()) * 100
        analytics['Std. Deviation'] = float(returnsPortfolioMarket.Portfolio.std() * 252 ** 0.5)
        analytics['R Squared'] = (returnsPortfolioMarket.Portfolio.cov(returnsPortfolioMarket.SP500)
            / (returnsPortfolioMarket.Portfolio.std() * returnsPortfolioMarket.SP500.std())) ** 2
        analytics['Expected Return'] = expected_return

    # returnsPortfolioMarket.to_excel('./outputs/returnsPortfolioMarket.xlsx')

    return pd.Series(analytics, index=list(analytics.keys())).round(3)


### Sector Analytics ###
def sector_analytics(portfolio, balances, level='basic', excel=False):

    portfolioBySector, returnsPortfolio, normalizedPortfolio = generator.sectorize(portfolio, balances)

    # Daily Return Data #
    analytics = {}
    returnsMarket = get_stock('spy')
    returnsMarket = returnsMarket[returnsPortfolio.index[0]:].pct_change() * 100
    returnsMarket.name = 'SP500'

    returnsPortfolioMarket = pd.concat([returnsPortfolio * 100, returnsMarket], axis=1)[1:]
    excessReturnsPortfolioMarket = returnsPortfolioMarket - riskFreeDaily * 100

    excessReturnsWeekly = excessReturnsPortfolioMarket.resample('W-MON').agg(lambda x: (1 + x / 100).prod() - 1) * 100

    # Returns #
    for sector in normalizedPortfolio.columns:
        position = {}
        position['Pct. Return 1M'] = (normalizedPortfolio[sector].iloc[-1]
            / normalizedPortfolio[sector].iloc[normalizedPortfolio[sector].index.get_loc(datetime.date.today()
            - datetime.timedelta(days=30), method='pad')] - 1) * 100
        position['Pct. Return 3M'] = (normalizedPortfolio[sector].iloc[-1]
            / normalizedPortfolio[sector].iloc[normalizedPortfolio[sector].index.get_loc(datetime.date.today()
            - datetime.timedelta(days=90), method='pad')] - 1) * 100
        position['Pct. Return YTD'] = (normalizedPortfolio[sector].iloc[-1]
            / normalizedPortfolio[sector].iloc[normalizedPortfolio[sector].index.get_loc(datetime.date(
            datetime.date.today().year, 1, 1), method='pad')] - 1) * 100
        position['Pct. Return 1Y'] = (normalizedPortfolio[sector].iloc[-1]
            / normalizedPortfolio[sector].iloc[normalizedPortfolio[sector].index.get_loc(datetime.date.today()
            - datetime.timedelta(days=365), method='pad')] - 1) * 100
        position['Pct. Return Max'] = (normalizedPortfolio[sector].iloc[-1]
            / normalizedPortfolio[sector].iloc[0] - 1) * 100
        position['Pct. Return CAGR'] = ((normalizedPortfolio[sector].iloc[-1]
            / normalizedPortfolio[sector].iloc[0]) ** ((1 / ((normalizedPortfolio[sector].index[-1]
            - normalizedPortfolio[sector].index[0]).total_seconds() / (86400 * 365)))) - 1) * 100

        # Statistics #
        #   Beta = Adjusted Beta
        #   Alpha = Annualized Alpha (Based on Portfolio CAGR)
        position['Beta'] = excessReturnsWeekly[sector].cov(
            excessReturnsWeekly.SP500) / excessReturnsWeekly.SP500.var() * (2 / 3) + (1 / 3)
        expected_return = (position["Beta"] * (marketRate - riskFree) + riskFree) * 100
        position['Alpha'] = (position['Pct. Return CAGR'] / 100 - expected_return / 100) * 100
        position['Sharpe'] = float((position['Pct. Return CAGR'] / 100 - riskFree)
            / ((returnsPortfolio[sector]).std() * 252 ** 0.5))
        position['Treynor'] = float((position['Pct. Return CAGR'] / 100 - riskFree) / position['Beta'])

        # Advanced Statistics #
        #   Std. Deviation = Annualized StdDev = Daily StdDev * sqrt(# of Trading Days)
        if level == 'advanced':
            drawdown = pd.DataFrame()
            drawdown['Prices'] = normalizedPortfolio[sector]
            drawdown['CumMax'] = drawdown.Prices.cummax()
            drawdown['Drawdown'] = (drawdown['Prices'] - drawdown['CumMax']) / drawdown['CumMax']
            position['Max Drawdown'] = float(drawdown['Drawdown'].min()) * 100
            position['Std. Deviation'] = float(returnsPortfolioMarket[sector].std(axis=0) * (252 ** 0.5))
            position['R Squared'] = (returnsPortfolioMarket[sector].cov(returnsPortfolioMarket.SP500)
                / (returnsPortfolioMarket[sector].std(axis=0) * returnsPortfolioMarket.SP500.std())) ** 2
            position['Expected Return'] = expected_return

        analytics[sector] = position

    output = pd.DataFrame(analytics, index=list(position.keys())).round(3)
    output2 = normalizedPortfolio
    # output3 = pd.DataFrame(requests.get(fmpurl + 'historical-price-full/SPY?serietype=line').json()['historical']).set_index('date')

    if excel:
        output.to_excel('./outputs/sectorbreakdown.xlsx')
        # output2.to_excel('./outputs/sector_prices.xlsx')
        # output3.to_excel('./outputs/market.xlsx')
    return output

def performance(portfolio, balances, method = 'overall', benchmark = 'spy', weightPortfolio = None):
    #   - Returns over multiple time periods [1M, 3M, YTD, 1Y, Max] (all methods)
    #   - Contribution of stock picks (individual, both)
    #   - Contribution of sector weighting (sector, both)
    #   - Methods:
    #           - Overall: Performance of entire portfolio
    #           - Individual: Performance and contribution by holding
    #           - Sector: Performance and contribution by sector
    #           - Both: Performance and contribution by individual picks and asset allocation
    weightMarket = {
        'Staples': 0.0566,
        'Discretionary': 0.0803,
        'Energy': 0.023,
        'REITs': 0.0222,
        'Financials': 0.0811,
        'Healthcare': 0.1178,
        'Industrials': 0.0796,
        'Utilities': 0.0252,
        'Macro': 0.035,
        'Technology': 0.2792,
        'Media': 0,
        'Fixed Income': 0.15
    }

    periods = [
        'Pct. Return 1M',
        'Pct. Return 3M',
        'Pct. Return YTD',
        'Pct. Return 1Y',
        'Pct. Return Max',
        'Pct. Return CAGR'
    ]

    if method == 'overall':
        pass
    elif method == 'individual':
        pass
    elif method == 'sector':
        # Normalized Active Returns and Performance by Sector

        returnsDataByIndex = pd.DataFrame()
        normalizedByIndex = pd.DataFrame()

        portfolioBySector, returnDataBySector, normalizedBySector = generator.sectorize(portfolio, balances)
        normalizedBySector = (1 - (normalizedBySector / normalizedBySector.iloc[-1])) * 100

        for sector, holdings in sectorHoldings.items():
            returnsSector = get_index(sector)
            returnsSector = returnsSector[normalizedBySector.index[0]:].pct_change()
            returnsDataByIndex[sector] = returnsSector
        returnsDataByIndex = returnsDataByIndex.fillna(0)
        normalizedByIndex = (returnsDataByIndex + 1).cumprod()
        normalizedByIndex = (1 - (normalizedByIndex / normalizedByIndex.iloc[-1])) * 100

        returnsBySector = pd.DataFrame(index=periods, columns=sectorHoldings.keys())
        returnsByIndex = pd.DataFrame(index=periods, columns=sectorHoldings.keys())
        returnsActive = pd.DataFrame(index=periods, columns=sectorHoldings.keys())
        returnsAllocation = pd.DataFrame(index=periods, columns=sectorHoldings.keys())
        returnsSelection = pd.DataFrame(index=periods, columns=sectorHoldings.keys())

        for sector in normalizedBySector.columns:
            returnsBySector.loc['Pct. Return 1M'][sector] = (
                normalizedBySector[sector].iloc[normalizedBySector[sector].index.get_loc(
                    datetime.date.today() - datetime.timedelta(days=30), method='pad')])
            returnsBySector.loc['Pct. Return 3M'][sector] = (
                normalizedBySector[sector].iloc[normalizedBySector[sector].index.get_loc(
                    datetime.date.today() - datetime.timedelta(days=90), method='pad')])
            returnsBySector.loc['Pct. Return YTD'][sector] = (
                normalizedBySector[sector].iloc[normalizedBySector[sector].index.get_loc(
                    datetime.date(datetime.date.today().year, 1, 1), method='pad')])
            returnsBySector.loc['Pct. Return 1Y'][sector] = (
                normalizedBySector[sector].iloc[normalizedBySector[sector].index.get_loc(
                    datetime.date.today() - datetime.timedelta(days=365), method='pad')])
            returnsBySector.loc['Pct. Return Max'][sector] = (normalizedBySector[sector].iloc[0])
            returnsBySector.loc['Pct. Return CAGR'][sector] = (
                (1 + normalizedBySector[sector].iloc[0] / 100)
                ** ((1 / ((normalizedBySector[sector].index[-1]
                            - normalizedBySector[sector].index[0]).total_seconds() / (86400 * 365)))) - 1) * 100

            returnsByIndex.loc['Pct. Return 1M'][sector] = (
                normalizedByIndex[sector].iloc[normalizedByIndex[sector].index.get_loc(
                    datetime.date.today() - datetime.timedelta(days=30), method='pad')])
            returnsByIndex.loc['Pct. Return 3M'][sector] = (
                normalizedByIndex[sector].iloc[normalizedByIndex[sector].index.get_loc(
                    datetime.date.today() - datetime.timedelta(days=90), method='pad')])
            returnsByIndex.loc['Pct. Return YTD'][sector] = (
                normalizedByIndex[sector].iloc[normalizedByIndex[sector].index.get_loc(
                    datetime.date(datetime.date.today().year, 1, 1), method='pad')])
            returnsByIndex.loc['Pct. Return 1Y'][sector] = (
                normalizedByIndex[sector].iloc[normalizedByIndex[sector].index.get_loc(
                    datetime.date.today() - datetime.timedelta(days=365), method='pad')])
            returnsByIndex.loc['Pct. Return Max'][sector] = (normalizedByIndex[sector].iloc[0])
            returnsByIndex.loc['Pct. Return CAGR'][sector] = (
                (1 + normalizedByIndex[sector].iloc[0] / 100)
                ** ((1 / ((normalizedByIndex[sector].index[-1]
                            - normalizedByIndex[sector].index[0]).total_seconds() / (86400 * 365)))) - 1) * 100

        for sector, holdings in sectorHoldings.items():
            returnsActive.loc[:, sector] = (returnsBySector.loc[:, sector] * weightPortfolio[sector]
                - returnsByIndex.loc[:, sector] * weightMarket[sector])
            returnsAllocation.loc[:, sector] = (returnsByIndex.loc[:, sector]
                * (weightPortfolio[sector] - weightMarket[sector]))
            returnsSelection.loc[:, sector] = returnsActive.loc[:, sector] - returnsAllocation.loc[:, sector]


    outperformance = pd.concat({
        'Active Return':returnsActive,
        'Asset Allocation':returnsAllocation,
        'Security Selection':returnsSelection
    })

    outperformance.to_excel('./outputs/outperformance.xlsx')

    return outperformance

### Performance ###
def performancePosition(ticker, select_date='present'):
    # This function gives the performance of a certain holding
    #   -Stock Price Return: Gives the performance based on average share price
    #   -Average Share Price: Gives the average holding price at that date
    analytics = {}
    try:
        stock_value = portfolio[ticker]
    except KeyError:
        return f'{ticker} not found'
    returnsMarket = get_stock('spy')
    returnsMarket = returnsMarket[stock_value.index[0]:].pct_change() * 100
    returnsMarket.name = 'SP500'
    amountinvested = holdings[ticker].baseposition.reindex(stock_value.index, method='pad')
    normalizedPortfolio = stock_value.divide(amountinvested, axis=0)
    normalized_returns = normalizedPortfolio.pct_change() * 100
    normalized_returns.name = ticker
    returnsPortfolioMarket = pd.concat([normalized_returns, returnsMarket], axis=1) - riskFreeDaily
    returnsPortfolioMarket = returnsPortfolioMarket[1:]

    # Returns
    analytics['Pct. Return 1M'] = (normalizedPortfolio.iloc[-1] / normalizedPortfolio.iloc[
        normalizedPortfolio.index.get_loc(datetime.date.today() - datetime.timedelta(days=30), method='pad')] - 1) * 100
    analytics['Pct. Return 3M'] = (normalizedPortfolio.iloc[-1] / normalizedPortfolio.iloc[
        normalizedPortfolio.index.get_loc(datetime.date.today() - datetime.timedelta(days=90), method='pad')] - 1) * 100
    analytics['Pct. Return YTD'] = (normalizedPortfolio.iloc[-1] / normalizedPortfolio.iloc[
        normalizedPortfolio.index.get_loc(datetime.date(datetime.date.today().year, 1, 1), method='pad')] - 1) * 100
    analytics['Pct. Return 1Y'] = (normalizedPortfolio.iloc[-1] / normalizedPortfolio.iloc[
        normalizedPortfolio.index.get_loc(datetime.date.today() - datetime.timedelta(days=365),
                                          method='pad')] - 1) * 100
    analytics['Pct. Return Max'] = (normalizedPortfolio.iloc[-1] / normalizedPortfolio[0] - 1) * 100
    analytics['Pct. Return CAGR'] = ((normalizedPortfolio[-1] / normalizedPortfolio[0]) ** (
        (1 / ((normalizedPortfolio.index[-1] - normalizedPortfolio.index[0]).total_seconds() / (
                86400 * 365)))) - 1) * 100
    analytics['Beta'] = returnsPortfolioMarket[ticker].cov(
        returnsPortfolioMarket.SP500) / returnsPortfolioMarket.SP500.var() * (2 / 3) + (1 / 3)
    expected_return = (analytics["Beta"] * (marketRate - riskFree) + riskFree) * 100
    analytics['Alpha'] = (analytics['Pct. Return CAGR'] / 100 - expected_return / 100) * 100

    return pd.Series(analytics, index=list(analytics.keys())).round(3)


### Correlation ###
def correlation(ticker=None, index='SPX', sector=None, commodity=None, econ=None, treas=None):
    # Gives the correlation of a given ticker to a given index, defaulting as
    # the SP500 for a total market proxy. Designed to be used to get sector
    # correlations to their respective index
    outputs = pd.DataFrame()
    data_ticker = get_stock(ticker)  # Gets the daily closing price of a stock starting on the buy date
    data_ticker = data_ticker
    data_index = get_index(index)
    index_coef, index_int, index_corr, index_p, index_std = linregress(data_index, data_ticker)
    index_vals = pd.Series(
        {'Coefficient': index_coef, 'Intercept': index_int, 'Correlation': index_corr, 'R-Squared': index_corr ** 2})
    index_vals.name = 'Index: ' + index
    outputs = outputs.append(index_vals, sort=False)
    if sector != None:
        data_sector = get_index(sector)
        sector_coef, sector_int, sector_corr, sector_p, sector_std = linregress(data_sector, data_ticker)
        sector_vals = pd.Series({'Coefficient': sector_coef, 'Intercept': sector_int, 'Correlation': sector_corr,
                                 'R-Squared': sector_corr ** 2})
        sector_vals.name = 'Sector: ' + sector
        outputs = outputs.append(sector_vals, sort=False)
    if commodity != None:
        data_commodity = get_data(commodity)
        data_commodity = data_commodity.reindex(data_ticker.index, method='pad')
        commodity_coef, commodity_int, commodity_corr, commodity_p, commodity_std = linregress(data_commodity,
                                                                                               data_ticker)
        commodity_vals = pd.Series(
            {'Coefficient': commodity_coef, 'Intercept': commodity_int, 'Correlation': commodity_corr,
             'R-Squared': commodity_corr ** 2})
        commodity_vals.name = 'Commodity: ' + commodity
        outputs = outputs.append(commodity_vals, sort=False)
    if econ != None:
        data_econ = get_data(econ)
        data_econ = data_econ.reindex(index=data_ticker.index, method='pad')
        econ_coef, econ_int, econ_corr, econ_p, econ_std = linregress(data_econ, data_ticker)
        econ_vals = pd.Series(
            {'Coefficient': econ_coef, 'Intercept': econ_int, 'Correlation': econ_corr, 'R-Squared': econ_corr ** 2})
        econ_vals.name = 'Econ: ' + econ
        outputs = outputs.append(econ_vals, sort=False)
    if treas != None:
        data_treas = get_treas(treas)
        data_treas = data_treas.reindex(index=data_ticker.index, method='pad')
        treas_coef, treas_int, treas_corr, treas_p, treas_std = linregress(data_treas, data_ticker)
        treas_vals = pd.Series({'Coefficient': treas_coef, 'Intercept': treas_int, 'Correlation': treas_corr,
                                'R-Squared': treas_corr ** 2})
        treas_vals.name = 'Treas: ' + treas
        outputs = outputs.append(treas_vals, sort=False)
    return outputs


### Correlation Matrix ###
def correlation_matrix(group_by="portfolio", excel=False):
    if group_by == 'portfolio':
        aPortfolio = portfolio
        sumPortfolio = aPortfolio.sum(axis=1)
        netcash_reindexed = netcash.reindex(aPortfolio.index, method='pad')
        normalizedPortfolio = (sumPortfolio / netcash_reindexed)
        normalized_returns = normalizedPortfolio.pct_change() * 100
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
                    suminvested = suminvested.reindex(suminvested.index.union(holdings[ticker].baseposition.index),
                                                      method='pad')
                    base_reindexed = holdings[ticker].baseposition.reindex(suminvested.index, method='pad')
                    suminvested = suminvested.add(base_reindexed, fill_value=0)
            sector_netinvested = sector_netinvested.reindex(sector_netinvested.index.union(suminvested.index),
                                                            method='pad')
            suminvested = suminvested.reindex(sector_netinvested.index, method='pad')
            sector_netinvested[sector] = suminvested
            sector_netinvested = sector_netinvested.reindex(portfolio_bysector.index, method='pad')
            sector_netinvested = sector_netinvested.fillna(method='pad')

        # Daily Return Data #
        normalizedPortfolio = portfolio_bysector.divide(sector_netinvested, axis=0)
        normalized_returns = normalizedPortfolio.pct_change()
        normalized_returns = normalized_returns[normalized_returns.first_valid_index():]

        output = normalized_returns.corr()

        if excel == True:
            output.to_excel('./outputs/intersector_corr.xlsx')

    elif group_by == 'intrasector':
        pass

    return output


### Ratios ###
def ratios(portfolio, method='total'):
    if method == 'total':
        notfound = 0
        ratios = {'pe': 0, 'pb': 0, 'dyield': 0}
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
def chart(topic, beta_method='market', period='ytd'):
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
        returnsMarket = get_stock('spy')
        returnsMarket = returnsMarket[returnsMarket.index.get_loc(date, method='nearest'):]
        returnsMarket = returnsMarket[returnsMarket.index[0]:] / returnsMarket[returnsMarket.index[0]] * 10000
        returnsMarket.name = 'SP500'
        netcash_reindexed = netcash.reindex(c_portfolio_sum.index, method='nearest')
        normalizedPortfolio = (c_portfolio_sum / netcash_reindexed)
        normalized_returns = normalizedPortfolio / normalizedPortfolio[0] * 10000
        normalized_returns.name = 'Portfolio'
        first_index = normalized_returns.first_valid_index()
        returnsPortfolioMarket = pd.concat([normalized_returns[first_index:], returnsMarket[first_index:]], axis=1)
        returnsPortfolioMarket = returnsPortfolioMarket[1:]
        returnsPortfolioMarket.plot()
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
def holdingsStatistics(date='present'):
    # Returns every holding in the portfolio:
    #   -Ticker and Company Name
    #   -Price and Shares Purchased (Price here is average holding price)
    #   -Total value of the holding and its percentage of the portfolio
    #   -Total gain/loss in dollars and percentage
    #   -Dividend Yield
    pass


### Holdings Sector ###
def holdings_sector(date='present'):
    # Returns the same metrics as holdings, but broken into sectors
    pass


########################
### Function Running ###
########################

### Running if  ###
if __name__ == '__main__':

    ### Import Data from Excel or Pickle ###
    # portfolio, balances, holdings, sectorHoldings = load_data('excel')
    portfolio, balances, holdings, sectorHoldings = load_data('pickle')

    print(analytics(portfolio, balances, 'advanced'))
    # print(ratios(portfolio))
    print(sector_analytics(portfolio, balances, 'advanced', True))
    '''print(performance(portfolio, balances, 'sector', weightPortfolio={
                                                                        'Staples': 0.08,
                                                                        'Discretionary': 0.10,
                                                                        'Energy': 0.04,
                                                                        'REITs': 0.035,
                                                                        'Financials': 0.09,
                                                                        'Healthcare': 0.105,
                                                                        'Industrials': 0.07,
                                                                        'Utilities': 0.045,
                                                                        'Macro': 0,
                                                                        'Technology': 0.145,
                                                                        'Media': 0.09,
                                                                        'Fixed Income': 0.15
                                                                        }
                      )
          )
    '''
