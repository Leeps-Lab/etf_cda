import datetime

epoch = datetime.datetime.utcfromtimestamp(0)
def unix_time_millis(dt):
    '''turn a datetime.datetime object into ms since unix epoch'''
    return (dt - epoch).total_seconds() * 1000.0
