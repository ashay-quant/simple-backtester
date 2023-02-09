'''

@author: ashay
'''

import pandas as pd, numpy as np, datetime as dt
from backtest.utils import date

class Trade(object):
    '''
    This class reads the trade file and maintain a record of trades executed and leftover trades 
    '''


    def __init__(self, tradefilename, maxDollarTrade):
        
        # read data from the provided trade file
        # trade file has buy and sell signals.
        # it doesn't have trade notionals. It also has start and end dates.
        # each row in trade file could be split into two trades --  trade-in at the start_date
        #  and   trade-out on the end_date
        read_data = pd.read_csv(tradefilename, parse_dates = ['StartDate','EndDate'])
        
        # split the data into trade in and trade out.
        # change columns name to lower case
        read_data.columns = [c.lower() for c in read_data.columns]
        
        trade_in = read_data[['symbol','startdate','trade']].rename(columns  = {'startdate':'tradedate'})
        # flag column denotes if it's a new trade or unwind of an old position
        trade_in['flag'] = 'new'
        trade_out = read_data[['symbol','enddate','trade']].rename(columns  = {'enddate':'tradedate'})
        # flag column denotes if it's a new trade or unwind of an old position
        trade_out['flag'] = 'old'
        # flip the trade for tradeout
        trade_out.loc[:,'trade'] = -trade_out.loc[:,'trade']
        
        trades = pd.concat([trade_in, trade_out])

        trades['trade'] = maxDollarTrade * trades['trade']
        # save data frame with all the trades 
        self.__trades__ = trades.reset_index(drop = True)
        self.symbol = list(self.__trades__['symbol'].unique()) 

        
        self.startdate = trades['tradedate'].min().to_pydatetime().date()
        # run backtest up to yesterday
        self.enddate = np.minimum(trades['tradedate'].max().to_pydatetime().date(), date.yesterday(dt.date.today()))
    
        
    def get(self, tradedate):
        # get trades for tradedate
        if self.__trades__['tradedate'].isin([tradedate]).any():
            return self.__trades__.loc[self.__trades__['tradedate'] == pd.Timestamp(tradedate),:]
        else:
            return pd.DataFrame()
        
        
    def update(self, unexecutedtrades, dateint):
        # this function carry overs the unexecuted trades for next day
        # unexecutedtrades is a dataframe with symbol as index and trade column as the intended trade
        
    
        next_day = pd.Timestamp(date.tomorrow(dateint))
        
        unexecutedtrades = unexecutedtrades.reset_index()
        unexecutedtrades['flag'] = 'left'
        unexecutedtrades['tradedate'] = next_day
        
        self.__trades__ = pd.concat([self.__trades__, unexecutedtrades]).reset_index().drop(columns=['index']) 


if __name__ == "__main__":

    t = Trade('Y:\\Interviews\\zGithub\\backtest\\data\\20230208_095226.csv', 1000000)