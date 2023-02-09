'''

@author: ashay
'''


import  dateutil
import pandas as pd, datetime as dt, numpy as np
import yfinance as yf

class Eod_Data(object):
    '''
    Datamanagement class. It loads eod pricing data from IEX website
    This is called at the start of the backtester. 
    It  relies on trade file to find a list of symbols to be downloaded
    
    '''


    def __init__(self, symbols, logger):
        '''
        symbols is list of symbols for which data is required
        '''
        self.symbols = symbols
        self.logger = logger
        
        
    def load(self):
        # loads eod data from IEX website for symbols



        data_list = []
        self.logger.logger.info('Downloading historical EOD data from Yahoo Finance ... ')

        for symbol in self.symbols:


            obj = yf.Ticker(symbol.lower())
            data_pd = obj.history(period='5Y', auto_adjust=True)
            data_pd.reset_index(inplace=True)
            data_pd.columns = data_pd.columns.str.lower()
            data_pd['ret'] = data_pd['close'].pct_change()

            data_pd['symbol'] = symbol
            # parse string dates to datetime type
            data_pd['date'] = pd.to_datetime(data_pd['date'])

            data_pd = data_pd[['date', 'high', 'low', 'open', 'volume','close', 'symbol']]
            
            data_pd['ret'] = data_pd['close'].pct_change()
            # since yahoo doesn't provide vwap data, I have assumed vwap price = avg(Open, High, Low, Close)
            data_pd['vwap'] = data_pd[['open','high','low','close']].mean(axis = 1)
            # return on trade assuming trade is executed at VWAP price
            data_pd['trade_ret'] = data_pd['close'] / data_pd['vwap'] - 1
            
            # calculate daily dollar volume. This is used in ADV calculation
            data_pd['dollar_volume'] = data_pd['volume'] * data_pd['vwap']
            # ADV is 63 days median dollar volume
            data_pd['adv'] = data_pd['dollar_volume'].rolling(window = 63).apply(np.nanmedian)
            
            data_list.append(data_pd)
            
        self.data = pd.concat(data_list).reset_index()
        self.logger.logger.info('Finished downloading historical data.')
        
    
    def get_data(self, dateint, symbol_list = None):    
        # this function returns eod data for dateint
        # returns data for all the symbols or only for subset in symbol_list
        
        try:
            data = self.data.loc[self.data['date'] == pd.Timestamp(dateint), :]
            if symbol_list and (not data.empty):
                # convert string into list
                if type(symbol_list) == str:
                    symbol_list = [symbol_list]
                # get symbols in symbol_list
                data = data.loc[data['symbol'].isin(symbol_list),:]
            data.set_index('symbol',inplace = True)        
        except:
            # date not found. Return empty dataframe
            return pd.DataFrame()
        
        return data
            
      
if __name__=='__main__':
    
    data = Eod_Data(['AAPL','FB','MSFT','PTY','V'])
    data.load()
    
    a = data.get_data(dt.date(2022,2,20), symbol_list='AAPL')
    q = 1
    
      