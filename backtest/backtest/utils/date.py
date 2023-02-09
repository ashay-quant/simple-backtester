'''

@author: ashay
module to handle business day operations.
'''

import datetime as dt
from pandas.tseries.offsets import CustomBusinessDay



from pandas.tseries.holiday import AbstractHolidayCalendar, Holiday, nearest_workday, \
    USMartinLutherKingJr, USPresidentsDay, GoodFriday, USMemorialDay, \
    USLaborDay, USThanksgivingDay


class USTradingCalendar(AbstractHolidayCalendar):
    rules = [
        Holiday('NewYearsDay', month=1, day=1, observance=nearest_workday),
        USMartinLutherKingJr,
        USPresidentsDay,
        GoodFriday,
        USMemorialDay,
        Holiday('USIndependenceDay', month=7, day=4, observance=nearest_workday),
        USLaborDay,
        USThanksgivingDay,
        Holiday("Juneteenth", month=6, day=19, start_date="2022-06-20", observance=nearest_workday),
        Holiday('Christmas', month=12, day=25, observance=nearest_workday),
        Holiday('911-1', month=9, day=11, year=2001),
        Holiday('911-2', month=9, day=12, year=2001),
        Holiday('911-3', month=9, day=13, year=2001),
        Holiday('911-4', month=9, day=14, year=2001),
        Holiday('Ford', month=1, day=2, year=2007),
        Holiday('Reagan', month=6, day=11, year=2004),
        Holiday('Sandy1', month=10, day=29, year=2012),
        Holiday('Sandy2', month=10, day=30, year=2012),
        Holiday('GeorgeHWB', month=12, day=5, year=2018)
    ]

BDay = CustomBusinessDay(calendar=USTradingCalendar())    
    

def addDays(d,numDays):
        
    q = d + numDays*BDay
    q = q.to_pydatetime()
    if type(d) == dt.date:
        q = q.date()
        
    return q
    


def yesterday(d):
    
    return addDays(d,-1)

def tomorrow(d):
    
    return addDays(d,1)