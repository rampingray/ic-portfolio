from pypm import *

### Import Data from Excel or Pickle ###
# portfolio, balances, holdings, sectorHoldings = load_data('excel')
portfolio, balances, holdings, sectorHoldings = load_data('pickle')

# print(analytics(portfolio, balances, 'advanced'))
print(ratios(portfolio))
# print(sector_analytics(portfolio, balances, 'advanced', True))
'''
print(performance(portfolio, balances, sectorHoldings, 'sector', weightPortfolio={
                                                                    'Staples': 0.074,
                                                                    'Discretionary': 0.103,
                                                                    'Energy': 0.048,
                                                                    'REITs': 0.04,
                                                                    'Financials': 0.10,
                                                                    'Healthcare': 0.102,
                                                                    'Industrials': 0.074,
                                                                    'Utilities': 0.055,
                                                                    'Technology': 0.146,
                                                                    'Media': 0.094,
                                                                    'Fixed Income': 0.15,
                                                                    'Macro': 0.0
                                                                    }
                  )
      )'''