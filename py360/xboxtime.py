""" Collection of functions to handle the various time formats that Xbox 360s have """

import time

def parse_fat_date(date):
    """
    #Date: 0-5 Day of month, 6-9 month of year, 10-15 number of years (from 1-1-1980)
    #Turns out that it is bigendian and the least significant bit is 0 and the most significant bit
    # '0b11001101110110' is (22, 11, 2005)
    """
    day = (0x001f & date)
    month = (0x01e0 & date) >> 5
    year = (0xfe00 & date) >> 9
    return day, month, year # Return some relevant date format

def parse_fat_time(time):
    """
    #TODO: Millisecond accuracy, optional parameter?
    #Time: 0-4 2 second count (0-29 == 0-58 seconds), 5-10 minutes, 11-15 hours
    """
    seconds = 2 * (0x001f & time)
    minutes = (0x07e0 & time) >> 5
    hours = (0xf800 & time) >> 11
    
    return hours, minutes, seconds # Return some relevant time format
    
def fat2unixtime(t, d):
    """ Turns date/time members from a FileRecord into unix time """
    # Not currently accurate past 2 seconds
    # TODO: Millisecond accuracy
    # FAT times are generally UTC on disk
    a = parse_fat_time(t)
    b = parse_fat_date(d)
    return time.mktime((1980 + b[2], b[1], b[0], a[0], a[1], a[2], 0, 0, 0))

def filetime2unixtime(filetime):
    """ Convert GPD times to unix time (Windows File Times, 100ms since 1601) """
    return max(0, (filetime * 10**-7) - 11644505694L) # Convert 100s ms since 1601 to unix epoch
