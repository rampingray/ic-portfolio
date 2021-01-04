import requests
import quandl
import pandas as pd
import yfinance as yf

### Setup ###
fmpurl = 'https://financialmodelingprep.com/api/v3/'
fmpkey = 'b1a82565d318254b3c0006ec0ca43454'
quandl.ApiConfig.api_key = "WrfYxYjepwxbuzY9TxjP"
tiingourl = 'https://api.tiingo.com/tiingo/'
tiingoheaders = {'Content-Type': 'application/json'}
tiingokey = '3febee85fff805b26816ebcc81ed7fc75b9b894f'

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
    'media': 'xlc',
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
    'macro':'vt',
    'fixed income':'agg'
    }

    try:
        # dailyprices = pd.DataFrame(requests.get(fmpurl+'historical-price-full/'+argmap[index.lower()]+'?serietype=line').json()['historical']).set_index('date')      # Gets the daily closing price of a stock starting on the buy date
        dailyprices = pd.DataFrame(requests.get(tiingourl+'daily/'+argmap[index.lower()]+'/prices?token='+tiingokey+'&startDate=2015-1-1', headers=tiingoheaders).json()).set_index('date')

    except KeyError:
        print('Invalid Index for get_data')
        return None
    dailyprices.index = pd.to_datetime(dailyprices.index)
    dailyprices.index = dailyprices.index.tz_convert(None)
    return dailyprices.adjClose

def get_stock(ticker):
    try:
            # dailyprices = pd.DataFrame(requests.get(fmpurl+'historical-price-full/'+ticker+'?apikey='+fmpkey).json()['historical']).set_index('date')
            dailyprices = pd.DataFrame(requests.get(tiingourl+'daily/'+ticker+'/prices?token='+tiingokey+'&startDate=2015-1-1', headers=tiingoheaders).json()).set_index('date')
    except KeyError:
        print('Invalid Ticker for get_stock (%s)' % (ticker))
        return None
    dailyprices.index = pd.to_datetime(dailyprices.index)
    dailyprices.index = dailyprices.index.tz_convert(None)
    dailyprices = dailyprices.sort_index()
    return dailyprices.adjClose

def get_stocks(tickerList):
    dataOut = pd.DataFrame()
    errors = []
    for ticker in tickerList:
        try:
            dailyprices = pd.DataFrame(requests.get(fmpurl+'historical-price-full/'+ticker+'?apikey='+fmpkey).json()['historical']).set_index('date')
            dailyprices.index = pd.to_datetime(dailyprices.index)
            dailyprices = dailyprices.close
            dataOut = pd.concat([dataOut, dailyprices], axis=1) 
        except KeyError:
            errors.append(ticker)
    print('Error tickers:', errors)
    return dataOut


def get_ratio(ticker, ratio):
    try:
        stock = yf.Ticker(ticker)
        output = stock.info[ratio]
        if output == None:
            return 0
        return output

    except:
        print('Call to get_ratios() failed:', ratio, 'for', ticker)
        return None

def get_ratios(ticker, ratios):
    try:
        output = {}
        for ratio in ratios:
            output[ratio] = get_ratio(ticker, ratio)
        return output

    except:
        print('Call to get_ratios() failed:', ticker, ratios)
        return None