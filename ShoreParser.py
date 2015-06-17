#  Created by Kleomenis Katevas on 14/08/2013.
#  Copyright (c) 2013 Queen Mary University of London. All rights reserved.


import sys
import re
from datetime import datetime


def parsefile(inputFile, start_date=None):
    '''Parse a complete file and return as a list
       of dictionaries '''

    # open file
    source = open(inputFile, 'r')

    # init list
    shoreList = []

    # parse each line
    for line in source:

        # parse the line
        dictionary = parseline(line, start_date)

        # add it to the list
        shoreList.append(dictionary)

    # close files
    source.close()

    # return the list
    return shoreList


def parseline(line, start_date=None):
    '''Parse the line and return in dictionary'''

    # use ', ' as a separator
    line = _transformline(line)

    # empty dict
    dictionary = {}

    # iterate through items
    for item in line.split(', '):

        # get the key and value from the item
        key, value = _parseitem(item)

        # cast value based on the key
        if (key in ['Left', 'Top', 'Right', 'Bottom']):

            # float to int value
            if value:
                value = int(float(value) * 1000)

        elif (key in ['Uptime', 'Score', 'Surprised', 'Sad', 'Happy', 'Angry',
                      'Age', 'MouthOpen', 'LeftEyeClosed', 'RightEyeClosed']):

            # float value
            if value:
                value = float(value)

        elif (key in ['Id', 'Frame', 'Roll', 'Yaw', 'Pitch']):

            # int value
            if value:
                value = int(value)

        elif key == 'TimeStamp':

            # parse it as a date value
            value = _parsedate(value)

            # if a start_date is provided
            if start_date:

                # find the deltatime
                deltatime = value - start_date

            else:

                # just provide the original date
                deltatime = value

            # also add the DeltaTime to the dictionary
            dictionary["DeltaTime"] = _parsetime(str(deltatime))

        # add to the dictionary
        dictionary[key] = value

    # return dictionary
    return dictionary


def _parsedate(date):
    '''Parse a date in string and return a datetime object'''

    if len(date) == 20:
        # Datetime format: '2013-Jul-02 16:32:46'
        value = datetime.strptime(date, '%Y-%b-%d %H:%M:%S')
    else:
        # Datetime format: '2013-Jul-02 16:32:46.396849'
        value = datetime.strptime(date, '%Y-%b-%d %H:%M:%S.%f')

    return value


def _parsetime(time):
    '''Parse a time in string and return a datetime object'''

    if len(time) <= 8:
        # Datetime format: '16:32:46'
        value = datetime.strptime(time, '%H:%M:%S')
    elif len(time) <= 15:
        # Datetime format: '16:32:46.396849'
        value = datetime.strptime(time, '%H:%M:%S.%f')
    else:
        # Datetime format: '2013-06-12 13:24:30.310070'
        value = datetime.strptime(time, '%Y-%m-%d %H:%M:%S.%f')

    return value


def _parseitem(item):
    '''Parse the item and return key, value (in string)'''

    # format should be key=value
    itemList = item.split('=')

    # normal case (key=value)
    if len(itemList) == 2:

        # set the key
        key = itemList[0]

        # set the value
        if itemList[1] == 'nil':
            value = None
        else:
            value = itemList[1]

    # handle the case where value is missing (e.g. 'Gender=')
    elif len(itemList) == 1:

        # set the key
        key = itemList[0]

        # set the value to None
        value = None

    else:
        sys.exit('Error: structure of input file is invalid. Item: ' + item)

    # return
    return key, value


def _transformline(line):
    '''Replace space separators with ", "
       and only use space in the TimeStamp'''

    return re.sub(r'[ ]([a-zA-Z])', r', \1', line)
