import requests
import quandl
import pandas as pd

### Setup ###
fmpurl = 'https://financialmodelingprep.com/api/v3/'
quandl.ApiConfig.api_key = "WrfYxYjepwxbuzY9TxjP"

def get_treas(arg):
    #Possible args '1 MO','2 MO','3 MO','6 MO','1 YR','2 YR','3 YR','5 YR','7 YR','10 YR','20 YR','30 YR'
    try:
        return quandl.get('USTREASURY/YIELD', start_date='1990-05-24')[arg.upper()]
    except KeyError:
        return "Accepted Args: '1 MO','2 MO','3 MO','6 MO','1 YR','2 YR','3 YR','5 YR','7 YR','10 YR','20 YR','30 YR' "

def get_data(arg):

    # Data comes from Quandl
    # CHRIS data is the front month future from ICE or CME
    # EIA data is from the Energy Department
    # FRED data is usually quarterly, some more, some less frequent

    argmap = {
    'henryhub':'CHRIS/CME_HH1',
    'natgas':'CHRIS/CME_HH1',
    'oil':"EIA/PET_RWTC_D",
    'wti':"EIA/PET_RWTC_D",
    'gold':'LBMA/GOLD',
    'silver':'LBMA/SILVER',
    'steel':'CHRIS/CME_HR1',
    'copper':'CHRIS/CME_HG1',
    'corn':'CHRIS/CME_C1',
    'soy:':'CHRIS/CME_S1',
    'wheat':'CHRIS/CME_W1',
    'pork':'CHRIS/CME_LN1',
    'leanhogs':'CHRIS/CME_LN1',
    'cattle':'CHRIS/CME_FC1',
    'feedercattle':'CHRIS/CME_FC1',
    'soybeanoil':'CHRIS/CME_BO1',
    'cotton':'CHRIS/ICE_CT1',
    'averageoutstanding':'USTREASURY/AVMAT',
    'unemployment':'FRED/NROUST',
    'gdp':'FRED/GDP',
    'cpi':'FRED/CPIAUCSL',
    'gdpdeflator':'FRED/GDPDEF',
    'fedfunds':'FRED/DFF',
    'tedspread':'FRED/TEDRATE',
    'primerate':'FRED/DPRIME',
    'initialclaims':'FRED/ICSA',
    'realhhincome':'FRED/MEHOINUSA672N',
    'savingsrate':'FRED/PSAVERT',
    'indpro':'FRED/INDPRO',
    'feddebt':'FRED/GFDEBTN',
    'housingstarts':'FRED/HOUST',
    'shiller':'MULTPL/SHILLER_PE_RATIO_MONTH'
    }

    return quandl.get(argmap[arg.lower()], start_date='1990-05-24', column_index=1).iloc[:,0]

def get_index(index):

    argmap = {
    'sp500':'spy',
    'spx':'spy',
    'qqq':'qqq',
    'nasdaq':'qqq',
    'compq':'qqq',
    'russell':'iwm',
    'russell2000':'iwm',
    'rut':'iwm',
    'dow':'dia',
    'dowjones':'dia',
    'djia':'dia',
    'midcap':'mdy',
    'mid':'mdy',
    'smallcap':'sly',
    'small':'sly',
    'tech':'xlk',
    'technology':'xlk',
    'tmt':'xlk',
    'staples':'xlp',
    'consumerstaples':'xlp',
    'discretionary':'xly',
    'consumerdiscretionary':'xly',
    'healthcare':'xlv',
    'bio':'xbi',
    'biotech':'xbi',
    'energy':'xle',
    'financial':'xlf',
    'financials':'xlf',
    'industrial':'xli',
    'industrials':'xli',
    'materials':'xlb',
    'material':'xlb',
    'utilities':'xlu',
    'realestate':'xlre',
    'reits':'xlre',
    'macro':'vt'
    }

    try:
        dailyprices = pd.DataFrame(requests.get(fmpurl+'historical-price-full/'+argmap[index.lower()]+'?serietype=line').json()['historical']).set_index('date')      # Gets the daily closing price of a stock starting on the buy date
    except KeyError:
        print('Invalid Index for get_data')
        return None
    dailyprices.index = pd.to_datetime(dailyprices.index)
    return dailyprices.close

def get_stock(ticker):
    try:
        dailyprices = pd.DataFrame(requests.get(fmpurl+'historical-price-full/'+ticker+'?serietype=line').json()['historical']).set_index('date')
    except KeyError:
        print('Invalid Ticker for get_stock')
        return None
    dailyprices.index = pd.to_datetime(dailyprices.index)
    return dailyprices.close

def get_ratio(ticker, ratio):
    try:
        if ratio == 'pe':
            price = float(requests.get(fmpurl+'company/profile/'+ticker).json()['profile']['price'])
            eps = float(requests.get(fmpurl+'financials/income-statement/'+ticker).json()['financials'][0]['EPS'])
            ratio = price / eps
        elif ratio == 'pb':
            market_cap = float(requests.get(fmpurl+'company/profile/'+ticker).json()['profile']['mktCap'])
            book = float(requests.get(fmpurl+'financials/balance-sheet-statement/'+ticker).json()['financials'][0]['Total shareholders equity'])
            ratio = market_cap / book
        elif ratio == 'dyield':
            price = float(requests.get(fmpurl+'company/profile/'+ticker).json()['profile']['price'])
            div = float(requests.get(fmpurl+'company/profile/'+ticker).json()['profile']['lastDiv'])
            ratio = div / price * 100
    except:
        print('Call to get_ratio() failed:', ticker)
        return None

    return ratio
