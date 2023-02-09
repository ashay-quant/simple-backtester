'''

This is command line script that takes a config file path as an argument and run the backtest based on that
The function can also take overrides for config file
the arguments supported are 
    --config_file - default config file is in the same directory as this file
The arguments below can be set in config_file. The command line argument takes precedence over the config_file
    --aum (default $100M)
    --maxTradeADV  (default 5 %, pass 10 to change it to 10%)
    --maxDollarTrade (default $10M)
    --trade_file
    --write_stats (default True) write backtest stats to the result directory  
    --pyfolio_analysis (default True) create full tear sheet using Pyfolio analysis
 
The command line can also take optional --startdate and --endate arguments
In case they are not provided, the backtester runs from minimum tradedate to the maximum tradedate
from the trade_file
    
    @author: ashay
'''
import argparse, os, configparser, sys
import datetime as dt
from backtest.utils import path,  logs

d = path.DataDirPath()
result_dir = d.result_dir





from backtest.core import backtester

def main(args):
    
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--config_file')
    parser.add_argument('--aum')
    parser.add_argument('--maxTradeADV')
    parser.add_argument('--maxDollarTrade')
    parser.add_argument('--trade_file')
    parser.add_argument('--write_stats')
    parser.add_argument('--pyfolio_analysis')
    
    args = parser.parse_args(args)
    
    
    default_config = os.path.join(os.path.dirname(__file__),'config.cfg')
    
    config_file = args.config_file or default_config 
    
    # parse the config file
    config = configparser.ConfigParser()
    config.read(config_file)
    
    # now get the required parameters for Backtester object
    # override config file parameters with command like arguments
    aum = float(args.aum or config['port']['aum'])
    maxTradeADV = float(args.maxTradeADV or config['trade']['maxTradeADV'])
    maxDollarTrade = float(args.maxDollarTrade or config['trade']['maxDollarTrade'])
    trade_file = args.trade_file or config['trade']['tradeFile']
    
    
    if (type(args.write_stats) == str) and (args.write_stats.lower() in ['true', 'false']):
        write_stats = eval(args.write_stats.title())
    else:
        write_stats = True
        
    if (type(args.pyfolio_analysis) == str) and (args.pyfolio_analysis.lower() in ['true', 'false']):
        pyfolio_analysis = eval(args.pyfolio_analysis.title())
    else:
        pyfolio_analysis = True    
    
    # backtest takes a dictionary of parameters
    back_param =  {'aum':aum,'maxTradeADV':maxTradeADV,'maxDollarTrade':maxDollarTrade,'trade_file':trade_file,'write_stats':write_stats,'pyfolio_analysis':pyfolio_analysis}

    log_file = os.path.join(result_dir, dt.datetime.now().strftime('%Y%m%d_%H%M%S') + '.log')
    logger = logs.Logs(log_file)

    # log backtest params
    logger.logger.info('Backtest params :')
    logger.logger.info(back_param)
    
    back = backtester.Backtester(back_param, logger)
    back.run()

    return back




if __name__ == '__main__':
    
    main(sys.argv[1:])
    
    
    
    