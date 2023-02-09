'''

@author: ashay

'''

import pandas as pd, os, pytz
import numpy as np, datetime as dt
import pytz

from backtest.core import port, trade
from backtest.utils import date, path
from backtest.data import eod_data
import pyfolio as py

class Backtester(object):
    '''
    Class for  backtesting
    '''


    def __init__(self, back_param, logger):
        
        self.aum = back_param['aum']
        self.maxTradeADV = back_param['maxTradeADV']/100
        self.maxDollarTrade = back_param['maxDollarTrade']
        self.trade_file = back_param['trade_file']
        self.write_stats = back_param['write_stats']
        self.pyfolio_analysis = back_param['pyfolio_analysis']
        self.logger = logger
        
        
        
        # initiate port and trade objects
        self.trades = trade.Trade(self.trade_file, self.maxDollarTrade)
        self.portfolio = port.Portfolio(aum = self.aum, symbol_list = self.trades.symbol)
        
        
        # find the first and last trade date
        self.startdate = self.trades.startdate
        self.enddate = self.trades.enddate
        
        #self.portfolio.add(date.yesterday(self.startdate), {'cash':self.aum})
        # load eod data from IEX website
        self.eod_data = eod_data.Eod_Data(self.trades.symbol, logger)
        self.eod_data.load()
        
        # initiate a dataframe to keep daily PL
        self.pl = pd.DataFrame(columns = ['tradePL','positionPL','totalPL','aum','total_ret'])
        # keep track of all the transactions
        self.transactions = pd.DataFrame(columns = ['amount','price','symbol'])
        
        d = path.DataDirPath()
        self.result_dir = d.result_dir
     
     
    def execute(self, tradedate, open_trades):
        # executes the trade and return completed and leftover trades
        
        # drop zero trades
        open_trades = open_trades[open_trades !=0]
        if open_trades.empty:
            return pd.DataFrame(), pd.DataFrame()
        
        
        # get previous day and tradedate eod data
        price_data_yest = self.eod_data.get_data(date.yesterday(tradedate), list(open_trades.index))
        price_data_trade = self.eod_data.get_data(tradedate, list(open_trades.index))
        # maximum allowed trade as per maxTradeADV and ADV 
        max_trade = self.maxTradeADV * price_data_yest['adv']
        
        allow_trade = np.minimum(max_trade,np.abs(open_trades['trade']) ).multiply( open_trades['trade'].apply(np.sign))
       
        # to calculate the executed notional for trade date , calculate the number of shares from max_trade and previous close.
        # use the number of shares and multiply it by tradedate VWAP to get the executed notional
        # price_data_yest['close'] is the decision price. Number of shares are calculated from the decision price
        # int(allow_trade / price_data_yest['close']) is the number of shares executed
        num_shares_executed = (allow_trade / price_data_yest['close']).apply(int)
        executed_trades = pd.DataFrame(num_shares_executed * price_data_trade['vwap'], columns = ['trade'])
        executed_trades.loc[:,'execution_price'] = price_data_trade['vwap']
        transactions = pd.DataFrame({'amount':num_shares_executed, 'price':price_data_trade['vwap'],'date':tradedate}).reset_index().set_index('date')

        
        self.transactions = pd.concat([self.transactions, transactions])
        
        # the left_overs are traded next day 
        # to preserve the number of shares, multiply the leftover number of shares with tradedate close price
        left_overs = pd.DataFrame((open_trades['trade']/  price_data_yest['close'] - num_shares_executed) * price_data_trade['close'], columns = ['trade'])
        
        # drop small left over trades. don't trade left_overs less than 10bps of the original intended trade 
        left_overs = left_overs.loc[np.abs(left_overs['trade'])> self.maxDollarTrade/1000,: ]
        
        return executed_trades, left_overs
    
    
    def update_stats(self, tradedate, trade_execute = pd.DataFrame()):
        # update portfolio and PL stats
      
        
        price_data = self.eod_data.get_data(tradedate)
        # get previous day portfolio
        port = self.portfolio.get_data(date.yesterday(tradedate))
        
        if not port.empty:
            previous_notional = np.sum(port)
            today_pos = port.multiply(1 + price_data['ret'].fillna(0))
            position_pl = np.sum(today_pos) - previous_notional
        else:
            # first day of backtest
            today_pos = pd.DataFrame()
            position_pl = 0
             
        if not trade_execute.empty:
            trade_eod = pd.DataFrame(trade_execute['trade'])
            trade_notional = np.nansum(trade_execute['trade'])
            trade_eod['trade'] = trade_execute['trade'].multiply(price_data['close'] / trade_execute['execution_price']  )
            trade_pl = np.sum(trade_eod['trade']) - trade_notional
        else:
            trade_eod = pd.DataFrame()
            trade_pl = 0
            
         
        
        self.pl.loc[tradedate,'tradePL'] = trade_pl
        self.pl.loc[tradedate,'positionPL'] = position_pl
        self.pl.loc[tradedate,'totalPL'] = trade_pl + position_pl
        
        if date.yesterday(tradedate) in self.pl.index:
            prev_aum = self.pl.loc[date.yesterday(tradedate),'aum']
        else:
            # first day of backtest
            prev_aum = self.aum
         
        self.pl.loc[tradedate,'aum'] = prev_aum + trade_pl + position_pl
        self.pl.loc[tradedate,'total_ret'] = (trade_pl + position_pl) / prev_aum
        
        total_pos = pd.DataFrame()
        
        
        if not trade_eod.empty:
            trade_eod = trade_eod.reindex(self.trades.symbol).fillna(0)
        
        if today_pos.empty:
            if not trade_eod.empty:
                total_pos = trade_eod
        else:
            if not trade_eod.empty:
                total_pos = today_pos.add(trade_eod['trade'])
            else:
                total_pos = today_pos
            
        if not total_pos.empty:
            self.portfolio.add(tradedate, total_pos)
        
    def get_stats(self, tradedate):
        
        return self.pl.loc[tradedate].to_dict()
    
    
    def create_trade(self, tradedate):
        
        """ figure out the trade for today
            new trades have a target size of maxDollarTrade
            old trades are unwindeded in full. So target size for an unwind could be > maxDollarTrade
            there could also be some left over trades from the previous day
            any leftover trade for a given symbol is over-written by a new trade, or the unwind trade """
        today_trades = self.trades.get(tradedate)
        
        yesterday_port = self.portfolio.get_data(date.yesterday(tradedate))
        
        if not today_trades.empty:    
            if not yesterday_port.empty:
                # over-write any old flag(unwind) with yesterday position
                unwind_trades = today_trades[today_trades['flag'] == 'old']
                if not unwind_trades.empty:
                    # update the unwind trade value to previous day position
                    unwind_trades.loc[:, 'trade'] =  -yesterday_port.reindex(unwind_trades['symbol']).values

                
                """ I have choosen to aggregate  unwind and  new trades. 
                    This is a choice, any other business logic can be incorporated to handle an unwind
                    and a new trade on same day
                """
                
                new_trades = today_trades[today_trades['flag'] == 'new']    
                if not unwind_trades.empty:
                    unwind_new = pd.concat([new_trades, unwind_trades])
                    unwind_new['flag'] = 'new'
                else:
                    unwind_new = new_trades
                
                
                """ a new trade denotes new conviction/alpha.
                     cancel any left over trade if there is also a 
                     new trade for the same symbol 
                """
                    
                
                left_over_trades = today_trades[today_trades['flag'] == 'left']
                if not  left_over_trades.empty:
                    # drop any left_over_trade which is also in unwind_new
                    left_over_trades = left_over_trades.loc[~left_over_trades['symbol'].isin(unwind_new['symbol'].values),:]
                     
                
                today_trades = pd.concat([left_over_trades, unwind_new])
        
        return today_trades
    
    def analysis(self):
        df_pl = self.pl
        
        full_stats = pd.DataFrame(columns = ['Backtest'])
        
        full_stats.loc['Start',:] = self.startdate.strftime('%Y-%m-%d')
        full_stats.loc['End',:] = self.enddate.strftime('%Y-%m-%d')
        full_stats.loc['Annual Return',:] = df_pl['total_ret'].mean()*252
        full_stats.loc['Cummulative Return',:] = df_pl['total_ret'].sum()
        full_stats.loc['Volatility',:] = df_pl['total_ret'].std()*np.sqrt(252)
        
        full_stats.loc['Sharpe Ratio',:] = df_pl['total_ret'].mean() / df_pl['total_ret'].std() * np.sqrt(252)
        
        full_stats.loc['Sortino Ratio',:] = df_pl['total_ret'].mean() / df_pl.loc[df_pl['total_ret']<0,'total_ret' ].std() * np.sqrt(252)
        
        
        
        yearly_stats = df_pl.groupby(lambda x:x.year)[['tradePL','positionPL','totalPL','total_ret']].sum()
        
        yearly_stats['vol'] = df_pl.groupby(lambda x:x.year)['total_ret'].apply(np.std)*np.sqrt(252)
        
        yearly_stats['Sharpe'] = df_pl.groupby(lambda x : x.year)['total_ret'].agg(lambda x : x.mean()/x.std()*np.sqrt(252))
        yearly_stats['skew'] = df_pl.groupby(lambda x : x.year)['total_ret'].agg(lambda x : x.skew())
        yearly_stats['kurtosis'] = df_pl.groupby(lambda x : x.year)['total_ret'].agg(lambda x : x.kurt())
        
        yearly_stats['sortino'] = df_pl.groupby(lambda x : x.year)['total_ret'].agg(lambda x : x.mean()) / df_pl.loc[df_pl['total_ret']<0, :].groupby(lambda x : x.year)['total_ret'].agg(lambda x : x.std()) * np.sqrt(252)
        
        return full_stats, yearly_stats
    
    def create_pyfolio_analysis(self):
        
        # get data in format required by pyfolio
        returns = self.pl['total_ret'].apply(np.float)
        returns.index = [pd.to_datetime(x) for x in returns.index]
        
        positions = self.portfolio.__port__
        positions.index = [pd.to_datetime(x) for x in positions.index] 
        """ I am not sure how Quantopians-pyfolio calculates cash.Ideally cash should incorporate 
         the leverage, and margining """
        positions.loc[:,'cash'] = np.float(self.aum)
        transactions = self.transactions
        
         
        temp_data = self.eod_data.data[['close','volume','symbol','date']]
        
        price = temp_data.pivot_table(index = 'date', columns = 'symbol', values = 'close')
        volume = temp_data.pivot_table(index = 'date', columns = 'symbol', values = 'volume')
        
        price = price.loc[(price.index>=pd.to_datetime(self.startdate)) & (price.index<=pd.to_datetime(self.enddate)),:]
        volume = volume.loc[(volume.index>=pd.to_datetime(self.startdate)) & (volume.index<=pd.to_datetime(self.enddate)),:]

        # Pyfolio analysis
        # pyfolio needs data in a certain format
        # market_cata is a multiindex
        price['attr'] = 'price'
        price.index = price.index.tz_localize(pytz.timezone('America/New_York'))

        volume['attr'] = 'volume'
        volume.index = volume.index.tz_localize(pytz.timezone('America/New_York'))

        market_data = pd.concat([price, volume])
        market_data.reset_index(inplace=True)
        market_data.set_index(['date', 'attr'], inplace = True)

        # transaction index needs to be in timestamp format
        transactions.index = pd.to_datetime(transactions.index)
        transactions.index = transactions.index.tz_localize(pytz.timezone('America/New_York'))


        positions.index = positions.index.tz_localize(pytz.timezone('America/New_York'))
        returns.index = returns.index.tz_localize(pytz.timezone('America/New_York'))

        # some features of the pyfolios are not working with the relabled pyfolio-reloaded
        # There is an open github issue.  This code is just a demonstration code, and I have not attempted to fix the pyfolio errors
        try:
            py.create_full_tear_sheet(returns,
                               positions=positions,
                               transactions=transactions,
                               market_data=market_data
                               )
        except Exception:
            self.logger.logger.info('Pyfolio exception. It''s possible that all the tearsheets were not generated')



    
    def run(self):
        # this function runs the backtester
        
        self.logger.logger.info('Running backtest for {0} from {1} to {2}'.format(self.trade_file, self.startdate.strftime('%Y-%m-%d'), self.enddate.strftime('%Y-%m-%d')))
        
        tradedate = self.startdate
        while tradedate <= self.enddate:

            today_trades = self.create_trade(tradedate)
            # initiate empty dataframe for trades executed today
            trade_execute = pd.DataFrame()
            if not today_trades.empty:        
                today_trades.set_index('symbol', inplace = True) 

                if today_trades['trade'].abs().sum() >0:
                    # get execution details
                    trade_execute, trade_left = self.execute(tradedate, today_trades)
                    
                    total_trades = np.sum(today_trades['trade'] !=0)
                    notional_trades = today_trades['trade'].abs().sum()
                    
                    total_executed = np.sum(trade_execute['trade'] !=0)
                    notional_executed = np.sum(np.abs(trade_execute['trade']))
                    
                    total_left = np.sum(trade_left['trade'] !=0)
                    notional_left = np.sum(np.abs(trade_left['trade']))
                    # log execution stats
                    self.logger.logger.info(tradedate.strftime('%Y-%m-%d') +' : Stats Total # trades {0} | Total # Executed {1} | Incomplete # Execution {2} '.format(total_trades, total_executed, total_left))
                    self.logger.logger.info(tradedate.strftime('%Y-%m-%d') +' : Stats Total trades ${0:,.0f} | Total Executed ${1:,.0f} | Incomplete Execution ${2:,.0f} '.format(notional_trades, notional_executed, notional_left))
                    
                   
                    # add left over trades to Trade object
                    if not trade_left.empty:
                        self.trades.update(trade_left, tradedate)
               
            else:
                self.logger.logger.info(tradedate.strftime('%Y-%m-%d') +' No trades to execute ')

            # update trade and portfolio satts
            self.update_stats(tradedate, trade_execute)
            stats = self.get_stats(tradedate) 
            # log stats
            self.logger.logger.info(tradedate.strftime('%Y-%m-%d') +' : Trade PL ${0:,.0f} | Position PL ${1:,.0f} | Total PL ${2:,.0f} | AUM ${3:,.0f} | Return on AUM {4:2.2f}% '
                            .format(stats['tradePL'],  stats['positionPL'], stats['totalPL'], stats['aum'], stats['total_ret']*100))   
             
            tradedate = date.tomorrow(tradedate) 
            
        # create portfolio stats
        full_stats, yearly_stats = self.analysis()
        self.yearly_stats = yearly_stats
        self.full_stats = full_stats
        
        # output  file
        d, f = os.path.split(self.trade_file)
        
        if self.write_stats:
            yearly_stats_file = os.path.join(self.result_dir, 'Yearly_Stats_' + dt.datetime.now().strftime('%Y%m%d_%H%M%S') + '_' +  f)
            yearly_stats.to_csv(yearly_stats_file)
        
            full_stats_file = os.path.join(self.result_dir, 'Full_Stats_' + dt.datetime.now().strftime('%Y%m%d_%H%M%S') + '_' +  f)
            full_stats.to_csv(full_stats_file)
        
        self.logger.logger.info(full_stats)
        self.logger.logger.info(yearly_stats)
        
        
        
        
        if self.write_stats:
            
            port_file = os.path.join(self.result_dir, 'Portfolio_' + dt.datetime.now().strftime('%Y%m%d_%H%M%S') + '_' +  f)
            self.portfolio.__port__.to_csv(port_file)
            
            # out put daily PL file
            pl_file = os.path.join(self.result_dir, 'PL_' + dt.datetime.now().strftime('%Y%m%d_%H%M%S') + '_' +  f)
            self.pl.to_csv(pl_file)
        
        if self.pyfolio_analysis:
            self.create_pyfolio_analysis()
        
        
        
        
        