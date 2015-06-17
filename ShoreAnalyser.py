#!/usr/bin/env python

#  Created by Kleomenis Katevas on 14/08/2013.
#  Copyright (c) 2013 Queen Mary University of London. All rights reserved.

import sys
import heapq
import numpy
import json

from UserString import MutableString
from datetime import timedelta
from datetime import datetime
from math import hypot

import ShoreParser as sp


class ShoreAnalyser:
    ''' ShoreAnalyser class'''

    def __init__(self, conf_inputs):

        # init audience dict
        self.audience = {}

        # set numpy to raise an exception on all errors
        numpy.seterr(all='raise')

        # parse shoredata for each input
        for conf_input in conf_inputs:

            # access properties
            inputId = conf_input["id"]
            filename = conf_input["filename"]
            start_date = self._parseDate(conf_input["start_date"])

            # Check for optional key 'output_log'
            if "output_log" in conf_input.keys():
                output_log = conf_input["output_log"]
            else:
                output_log = None

            # Check for optional key 'start_frame'
            if "start_frame" in conf_input.keys():

                # calculate the correct date based on the starting frame
                start_frame = conf_input["start_frame"]
                delta = timedelta(milliseconds=start_frame * 1000 / 25)
                correct_date = start_date - delta

                 # print the date
                print "Corrected date: " + str(correct_date)

            else:
                correct_date = start_date

            # Check for optional key 'filters'
            if "filters" in conf_input.keys():
                filters = conf_input["filters"]
            else:
                filters = None

            # analyse audience
            self.audience[inputId] = self.analyse(filename, correct_date,
                                                  filters, output_log)


    def analyse(self, filename, start_date, filters, output_log):

        # init the Audience
        audience = Audience(filters)

        # open file
        source = open(filename, 'r')

        print "Analysing file '%s'.." % (filename)

        # parse each line
        for line in source:

            # parse the line
            measurement = sp.parseline(line, start_date)

            # read the measurement
            audience.read(measurement)

        print "Finished!"

        # close files
        source.close()

        # produce and print statistics
        statistics = audience.statistics()
        print statistics

        # write Log file
        if output_log is not None:

            print "Exporting log file '%s'." % (output_log)

            with open(output_log, "w") as logfile:
                logfile.write(statistics)

        # return the audience
        return audience


    def export(self, conf_item):

        # access properties
        file_output = conf_item["output"]
        time_ranges = conf_item["time_ranges"]

        # open output file
        output = open(file_output, 'w')

        # export the header
        self.exportHeader(output)

        # iterate through timing
        for timerange in time_ranges:

            # export the item
            self.exportTimerange(timerange, self.audience, output)

        # close output file
        output.close()


    def exportHeader(self, output):

        # write the header
        output.write("Person, TimeFrom, TimeTo, " +
                     "Happy_AVG, Sad_AVG, Angry_AVG, " +
                     "Surprise_AVG, MouthOpen_AVG, Pitch_AVG, Roll_AVG, Yaw_AVG, " +
                     "ID, Label\n")


    def exportTimerange(self, timerange, audience, output):

        # get properties
        rangeId = timerange["id"]
        inputId = timerange["inputId"]

        # parse as dates
        fromTime = self._parseTime(timerange["from"])
        toTime = self._parseTime(timerange["to"])

        # get the label from the avg timing item
        label = timerange["label"]

        # loop for every sec

        # init
        datefrom = fromTime

        while datefrom < toTime:

            # at the beginning of the loop
            dateto = datefrom + timedelta(seconds=1)

            # debug:
            # print str(datefrom) + " - " + str(dateto)

            # loop body

            # get the data of all people for this 1sec period
            data = audience[inputId].getDataForTimestamp(datefrom,
                                                         dateto)

            # iterate through the people
            for person in data:

                self.exportElements(rangeId,
                                    label,
                                    datefrom,
                                    dateto,
                                    person["DURING"],
                                    output)

            # at the end of the loop
            datefrom = dateto


    def exportElements(self, rangeId, label, timeFrom, timeTo,
                       data, output):

        # get properties
        person = data["id"]
        happy = data["happy"]
        sad = data["sad"]
        angry = data["angry"]
        surprised = data["surprised"]
        mouth_open = data["mouthOpen"]
        pitch = data["pitch"]
        roll = data["roll"]
        yaw = data["yaw"]

        # Person, TimeFrom, TimeTo, Happy, Sad, Angry, Surprise,
        # MouthOpen, Night, ID
        output.write("%s, %s, %s, %s, %s, %s, %s, %s, %s, %s %s, %s, %s\n" %
                     (person,
                      timeFrom.strftime("%H:%M:%S.%f"),
                      timeTo.strftime("%H:%M:%S.%f"),
                      happy, sad, angry, surprised,
                      mouth_open, pitch, roll, yaw,
                      rangeId, label))


    def _parseDate(self, date):
        '''Parse a date in string and return a datetime object'''

        if len(date) == 20:
            # Datetime format: '2013-Jul-02 16:32:46'
            value = datetime.strptime(date, '%Y-%b-%d %H:%M:%S')
        else:
            # Datetime format: '2013-Jul-02 16:32:46.396849'
            value = datetime.strptime(date, '%Y-%b-%d %H:%M:%S.%f')

        return value


    def _parseTime(self, time):
        '''Parse a time in string and return a datetime object'''

        if len(time) == 8:
            # Datetime format: '16:32:46'
            value = datetime.strptime(time, '%H:%M:%S')
        else:
            # Datetime format: '16:32:46.396849'
            value = datetime.strptime(time, '%H:%M:%S.%f')

        return value

    def distance(self, point1, point2):
        return hypot(point2[0] - point1[0], point2[1] - point1[1])


class Audience:
    '''Audience class'''

    def __init__(self, filters):

        # init the list of Persons
        self._people = []

        # init the frames counter
        self._frames = 0
        self._lastFrame = None

        # init list for TimeStamp and DeltaTime
        self._timestamps = []
        self._deltatimes = []

        # save filters
        self._filters = filters


    def read(self, shoreDict):

        # check if it is a new frame
        if shoreDict['Frame'] != self._lastFrame:

            # increase it and save it
            self._frames += 1
            self._lastFrame = shoreDict['Frame']

            self._timestamps.append(shoreDict['TimeStamp'])
            self._deltatimes.append(shoreDict['DeltaTime'])

        # add the person to the list
        self._addPerson(shoreDict)


    def _addPerson(self, shoreDict):

        # get the frame
        frame = Frame(shoreDict['Left'], shoreDict['Top'],
                      shoreDict['Right'], shoreDict['Bottom'])

        # check if that person exists on the list
        person = self._personExists(frame)

        # if not
        if person is None:

            # create the object
            person = Person()

            # update it with current data
            person.update(frame, shoreDict)

            # add it to the list
            self._people.append(person)

        else:
            # just update it
            person.update(frame, shoreDict)
            x, y = frame.center()
            #print "x:" + str(x) + " y:" + str(y)


    def _personExists(self, frame):
        ''' check if that person exists in the list '''

        # iterate through people list
        for person in self._people:

            # if a person exists
            if (person.isCloseTo(frame)):
                return person

        return None


    def getValidPeople(self, max_people=None):
        ''' Check the people array and only return the valid ones '''

        if max_people is None:
            return self._people

        elif self._people:
            # return the max N persons of the array
            return heapq.nlargest(max_people,
                                  self._people, key=lambda x: x.identified)
        else:
            return None


    def statistics(self):

        # use MutableString for efficiency
        statistics = MutableString()

        statistics += "Frames: %d\n" % (self._frames)

        # add statistics about each identified person
        for person in self.getValidPeople():

            # get the center of the last frame
            x, y = person.frame.center()

            percentage = int(float(person.identified) / self._frames * 100)

            # statistics
            statistics += "Person_" + str(person.id) + ": "
            statistics += str(person.identified) + " (" + str(percentage) + "%) - "
            statistics += str(person.gender()) + " (" + str(person.age()) + ") - "
            statistics += str(x) + "x" + str(y) + "\n"

        return str(statistics)


    def getDataForTimestamp(self, fromTime, toTime, before, after,
                            point=None):

        # init the list
        dataList = []

        # if x is not given, get for all people
        if point is None:

            # iterate through all persons
            for person in self.getValidPeople():

                # get the data
                data = person.getData(fromTime, toTime, before, after)

                # add to the array
                dataList.append(data)

        # else, get for the specific person
        else:

            # get person closest to the point
            person = self.getClosestPerson(point)

            # get the data
            data = person.getData(fromTime, toTime, before, after)

            # add to the array
            dataList.append(data)

        # return the list
        return dataList


    def getDataForTimestamp(self, fromTime, toTime):

        # init the list
        dataList = []

        # iterate through all persons
        for person in self.getValidPeople():

            # get the data
            data = person.getData(fromTime, toTime)

            # add to the array
            dataList.append(data)

        # return the list
        return dataList


    def distance(self, point1, point2):
        return hypot(point2[0] - point1[0], point2[1] - point1[1])


    def getClosestPerson(self, point):

        # get all valid people
        validPeople = self.getValidPeople()

        # if list is not empty
        if len(validPeople) != 0:

            # init variables
            closestPerson = validPeople[0]
            minDistance = self.distance(closestPerson.frame.center(),
                                        point)

            for person in validPeople[1:]:

                # calculate the distance
                distance = self.distance(person.frame.center(),
                                         point)

                # if there is a smaller distance
                if distance < minDistance:

                    # set it
                    closestPerson = person
                    minDistance = distance

        # empty list
        else:

            # just None
            closestPerson = None

        return closestPerson


class Person:
    '''Person class'''
    _counter = 0

    def __init__(self):

        # set the id
        self.id = Person._counter
        Person._counter += 1

        # init the identified
        self.identified = 0

        # init list structures
        self._timestamp = []
        self._deltatime = []
        self._uptime = []
        self._score = []
        self._gender = []
        self._surprised = []
        self._sad = []
        self._happy = []
        self._angry = []
        self._age = []
        self._mouthOpen = []
        self._leftEyeClosed = []
        self._rightEyeClosed = []
        self._pitch = []
        self._roll = []
        self._yaw = []


    def update(self, frame, shoreDict):

        # increase the identified var
        self.identified += 1

        # update the frame
        self.frame = frame

        # add values to buffer lists
        self._addToBuffer(shoreDict, 'TimeStamp', self._timestamp)
        self._addToBuffer(shoreDict, 'DeltaTime', self._deltatime)
        self._addToBuffer(shoreDict, 'Uptime', self._uptime)
        self._addToBuffer(shoreDict, 'Score', self._score)
        self._addToBuffer(shoreDict, 'Gender', self._gender)
        self._addToBuffer(shoreDict, 'Surprised', self._surprised)
        self._addToBuffer(shoreDict, 'Sad', self._sad)
        self._addToBuffer(shoreDict, 'Happy', self._happy)
        self._addToBuffer(shoreDict, 'Angry', self._angry)
        self._addToBuffer(shoreDict, 'Age', self._age)
        self._addToBuffer(shoreDict, 'MouthOpen', self._mouthOpen)
        self._addToBuffer(shoreDict, 'LeftEyeClosed', self._leftEyeClosed)
        self._addToBuffer(shoreDict, 'RightEyeClosed', self._rightEyeClosed)
        self._addToBuffer(shoreDict, 'Pitch', self._pitch)
        self._addToBuffer(shoreDict, 'Roll', self._roll)
        self._addToBuffer(shoreDict, 'Yaw', self._yaw)


    def _addToBuffer(self, shoreDict, dictkey, bufferlist):

        # check if the key exists
        if dictkey in shoreDict.keys():

            # add it the the appropriate  list
            bufferlist.append(shoreDict[dictkey])

        else:

            # add None
            bufferlist.append(None)


    def getData(self, fromTime, toTime):

        # init the list
        dataDict = {}

        # find the indexes
        fromIndex, toIndex = self.searchForIndexes(fromTime, toTime)

        # DURING
        dataDict["DURING"] = self.getDataFromIndexRange(fromIndex, toIndex)

        # Save person as a ref
        dataDict["PERSON"] = self

        # return the dict
        return dataDict


    def searchForIndexes(self, fromTime, toTime):

        # init the indexes
        fromIndex = None
        toIndex = None

        # iterate from begin index
        for index, item in enumerate(self._deltatime[:]):

            # iterate until you find an item > timestamp
            if item <= fromTime:
                fromIndex = index
                toIndex = index

            if item < toTime:
                toIndex = index

            # once you find it, break
            else:
                break

        # return the last item
        return fromIndex, toIndex


    def searchForDeltaTimeIndex(self, deltatime):

        # iterate from begin index
        for index, item in enumerate(self._deltatime[:]):

            # iterate until you find an item == timestamp
            if item == deltatime:
                return index

        # Couldn't be found
        return None


    def getDataFromIndexRange(self, fromIndex, toIndex):

        # init data dictionary
        dataDict = {}

        # save the person id
        dataDict["id"] = self.id

        # get the AVG of all useful values and save them on the dict
        dataDict["happy"] = self.happy(fromIndex, toIndex)
        dataDict["sad"] = self.sad(fromIndex, toIndex)
        dataDict["angry"] = self.angry(fromIndex, toIndex)
        dataDict["surprised"] = self.surprised(fromIndex, toIndex)
        dataDict["mouthOpen"] = self.mouthOpen(fromIndex, toIndex)
        dataDict["pitch"] = self.pitch(fromIndex, toIndex)
        dataDict["roll"] = self.roll(fromIndex, toIndex)
        dataDict["yaw"] = self.yaw(fromIndex, toIndex)

        # return the dictionary
        return dataDict


    def isCloseTo(self, frame):

        midX, midY = self.frame.center()
        midXframe, midYframe = frame.center()

        # Optimal value for Person classification
        return (abs(midX - midXframe) < 80 and
                abs(midY - midYframe) < 30)


    def surprised(self, fromIndex, toIndex):

        filtered = filter(lambda x: x is not None,
                          self._surprised[fromIndex:toIndex])

        if len(filtered) > 0:
            return numpy.mean(filtered)
        else:
            return None


    def sad(self, fromIndex, toIndex):

        filtered = filter(lambda x: x is not None,
                          self._sad[fromIndex:toIndex])

        if len(filtered) > 0:
            return numpy.mean(filtered)
        else:
            return None


    def happy(self, fromIndex, toIndex):

        filtered = filter(lambda x: x is not None,
                          self._happy[fromIndex:toIndex])

        if len(filtered) > 0:
            return numpy.mean(filtered)
        else:
            return None


    def angry(self, fromIndex, toIndex):

        filtered = filter(lambda x: x is not None,
                          self._angry[fromIndex:toIndex])

        if len(filtered) > 0:
            return numpy.mean(filtered)
        else:
            return None


    def pitch(self, fromIndex, toIndex):

        filtered = filter(lambda x: x is not None,
                          self._pitch[fromIndex:toIndex])

        if len(filtered) > 0:
            return numpy.mean(filtered)
        else:
            return None


    def roll(self, fromIndex, toIndex):

        filtered = filter(lambda x: x is not None,
                          self._roll[fromIndex:toIndex])

        if len(filtered) > 0:
            return numpy.mean(filtered)
        else:
            return None


    def yaw(self, fromIndex, toIndex):

        filtered = filter(lambda x: x is not None,
                          self._yaw[fromIndex:toIndex])

        if len(filtered) > 0:
            return numpy.mean(filtered)
        else:
            return None


    def mouthOpen(self, fromIndex, toIndex):

        filtered = filter(lambda x: x is not None,
                          self._mouthOpen[fromIndex:toIndex])

        if len(filtered) > 0:
            return numpy.mean(filtered)
        else:
            return None


    def gender(self):

        filtered = filter(lambda x: x is not None,
                          self._gender[:])

        if len(filtered) > 0:

            count_male = filtered.count("Male")
            count_female = filtered.count("Female")

            if count_male > count_female:
                return "Male"
            else:
                return "Female"

        else:
            return None


    def age(self):

        filtered = filter(lambda x: x is not None,
                          self._age[:])

        if len(filtered) > 0:
            return numpy.mean(filtered)
        else:
            return None


class Frame:
    '''Frame class'''

    def __init__(self, left, top, right, bottom):

        # save the properties
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom

    def width(self):
        return self.right - self.left

    def height(self):
        return self.bottom - self.top

    def center(self):

        # calculate middle point of X and Y
        midX = self.left + self.width() / 2
        midY = self.top + self.height() / 2

        return midX, midY


''' main '''
if __name__ == '__main__':

    # check if the the input filename exists as a parameter
    if len(sys.argv) < 2:
        sys.exit('Missing input file')

    # read configuration file from arguments
    inputFile = sys.argv[1]

    # open configuration source file
    conf_source = open(inputFile, 'r')

    # convert json file to python object
    configuration = json.loads(conf_source.read())

    # close configuration source file
    conf_source.close()

    # get the inputs from the configuration file
    conf_inputs = configuration["inputs"]

    # init the Comedy Analyser with given inputs
    analyser = ShoreAnalyser(conf_inputs)

    # Use ShoreAnalyser to produce the outputs
    # using the configuration as a guidance
    # -----------------------------------------

    # iterate through items in configuration json file
    for conf_item in configuration["configurations"]:

        print "Exporting to '%s'.." % (conf_item["output"])

        # export the output files
        analyser.export(conf_item)

        print "Exporting completed!"

    print "ShoreAnalyser is complete."
