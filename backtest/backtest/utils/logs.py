"""
 Created by ashay at 2/8/2023
 
"""

import logging


class Logs(object):

    def __init__(self, log_file, time_stamp=True):

        print('log file : ' + log_file)
        if time_stamp:
            logging.basicConfig(filename=log_file, filemode='w', format=' %(asctime)s - %(levelname)s - %(message)s',
                                level=logging.INFO)
        else:
            logging.basicConfig(filename=log_file, filemode='w', format='%(levelname)s - %(message)s',
                                level=logging.INFO)

        # stop matplotlib from crapping all over the log file
        logging.getLogger('matplotlib.font_manager').disabled = True
        # Create a backtest logger
        logger = logging.getLogger(__file__)

        # Create handlers
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.DEBUG)

        # Create formatters and add it to handlers
        if time_stamp:
            stream_format = logging.Formatter('%(asctime)s -  %(levelname)s - %(message)s')
        else:
            stream_format = logging.Formatter('%(levelname)s - %(message)s')

        stream_handler.setFormatter(stream_format)

        # Add handlers to the logger
        logger.addHandler(stream_handler)

        self.logger = logger

