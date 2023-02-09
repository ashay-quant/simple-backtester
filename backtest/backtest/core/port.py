'''


@author: ashay
'''

import pandas as pd, datetime as dt
from backtest.utils import date

class Portfolio(object):
    '''
    This class maintains the daily porfolio and calculates statistics for the portfolio
    '''


    def __init__(self, aum, symbol_list):
        
        self.aum = aum
        # initiate a dataframe to keep all the positions
        
        self.__port__ = pd.DataFrame(columns = symbol_list)
        
        
    def add(self, dateint, positions):
        # position is a dataframe
        if type(dateint) != dt.date:
            dateint = dateint.date()
        
        
        self.__port__.loc[dateint, positions.index] = positions.T.values
        self.__port__.fillna(0,inplace = True)
        
    def get_data(self, dateint):
        
        # get position for a given day
        if dateint in self.__port__.index:
            return self.__port__.loc[dateint,:]
        else:
            return pd.DataFrame()
        
        