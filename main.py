from pypm import *
# import gui

### Import Data from Excel or Pickle ###
portfolio, balances, holdings, sectorHoldings = load_data('excel')
# portfolio, balances, holdings, sectorHoldings = load_data('pickle')

print(analytics(portfolio, balances, 'advanced'))
print(ratios(portfolio))
# print(sector_analytics(portfolio, balances, 'advanced', True))
'''print(performance(portfolio, balances, 'sector', weightPortfolio={
                                                                    'Staples': 0.072,
                                                                    'Discretionary': 0.10,
                                                                    'Energy': 0.047,
                                                                    'REITs': 0.043,
                                                                    'Financials': 0.093,
                                                                    'Healthcare': 0.099,
                                                                    'Industrials': 0.071,
                                                                    'Utilities': 0.046,
                                                                    'Macro': 0.0,
                                                                    'Technology': 0.147,
                                                                    'Media': 0.087,
                                                                    'Fixed Income': 0.15
                                                                    }
                  )
      )
      '''

# gui.run()