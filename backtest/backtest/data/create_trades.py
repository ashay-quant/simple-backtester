'''


@author: ashay
creates a list of fictitious trades 
'''
from backtest.utils import date, path
import datetime as dt, pandas as pd, numpy as np
import os


if __name__ == '__main__':
    
    list_names = ['AAPL', 'AMZN', 'CAT', 'GOOG', 'JPM', 'META', 'MRK', 'MSFT', 'NVDA', 'TSLA']
    
    d = path.DataDirPath()
    
    start_date = date.tomorrow(dt.date(2021,12,31))
    end_date = date.yesterday(dt.date(2023,1,1))
    
    # create random trades between start_date and end_date for names in list_names 
    # trades is list of dictionary of all trades
    trades = []
    for symbol in list_names:
        first_date = start_date
        while first_date <= end_date:
            # first create the trade side
            prob = np.random.uniform(0,1)  
            if prob <0.4:
                side = -1
            elif prob>0.6:
                side = 1
            else:
                side = 0
                
            # first date is trade initiation date. 
            # randomly create trade out date (last_date)
            # if side is in (-1,1), holding_period is the holding period
            # of trade initiated on first_date
            # if side == 0, holding_period is no trade period
            # all parameters are random 
            if side == 0:
                holding_period = np.random.randint(20,40)
                first_date = date.addDays(first_date, holding_period)
            else:
                holding_period = np.random.randint(30,60)
                last_date = date.addDays(first_date, holding_period)
                
                trades.append({'Symbol':symbol,'StartDate':first_date, 'EndDate':last_date, 'Trade' : side})
                
                # move the first_date to next trade date
                first_date =  date.addDays(last_date, np.random.randint(5,20))
    
    
    trade_pd = pd.DataFrame(trades)
    trade_pd = trade_pd[['Symbol','StartDate', 'EndDate', 'Trade' ]].sort_values(by = ['StartDate', 'Symbol'])
    trade_pd.to_csv(os.path.join(d.data_dir,   dt.datetime.now().strftime('%Y%m%d_%H%M%S' + '.csv')), index = False)
    
    
    
                
                
            
                
    
    