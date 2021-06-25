from pypm import *

### Import Data from Excel or Pickle ###
portfolio, balances, holdings, sectorHoldings = load_data('excel') # Use if portfolio pickle out of date
# portfolio, balances, holdings, sectorHoldings = load_data('pickle') # Use if portfolio pickle is up to date

print(analytics(portfolio, balances, 'advanced'))
# print(ratios(portfolio))
# print(performanceByPosition(portfolio, balances, 'advanced', True))
# print(sector_analytics(portfolio, balances, 'advanced', True))
'''
print(outperformance(portfolio, balances, sectorHoldings, 'sector', weightPortfolio={
                                                                    'Staples': 0.061,
                                                                    'Discretionary': 0.094,
                                                                    'Energy': 0.063,
                                                                    'REITs': 0.045,
                                                                    'Financials': 0.099,
                                                                    'Healthcare': 0.109,
                                                                    'Industrials': 0.072,
                                                                    'Utilities': 0.056,
                                                                    'Technology': 0.116,
                                                                    'Media': 0.087,
                                                                    'Fixed Income': 0.148,
                                                                    'Macro': 0.0
                                                                    }
                  )
      )'''