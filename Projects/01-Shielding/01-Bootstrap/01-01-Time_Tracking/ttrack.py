#!/bin/env python2

import argparse, time, sys, tty

parser = argparse.ArgumentParser(description='Tracks time')
parser.add_argument('-d', '--details', default='hours_details.csv', type=argparse.FileType('a+'), help='csv to store details in')
parser.add_argument('-p', '--priorities', default='goals_priorities.csv', type=argparse.FileType('a+'), help='csv to read priorities from')
pgroup = parser.add_mutually_exclusive_group(required=True)
pgroup.add_argument('-w', '--work', metavar=('GOAL', 'TASK'), nargs='+', help='track work towards a goal')
pgroup.add_argument('-r', '--report', action='store_true', help='report on time usage')
pgroup.add_argument('-s', '--suggest', action='store_true', help='recommend goal to work toward')

TIME_COL = 'Time'
EVENT_COL = 'Action'
GOAL_COL = 'Goal'
TASK_COL = 'Task'
RATIO_COL = 'Ratio'
EVENT_START = 'start'
EVENT_HEARTBEAT = 'heartbeat'
EVENT_STOP = 'stop'

class CSV(object):
    def __init__(self, file, format=None):
        self.file = file
        self.format = format
        self.file.seek(0)
        header = self.file.readline()[0:-1].split(',')
        if header[0] == '':
            self.file.write(','.join(self.format))
            self.file.write('\n')
            self.file.seek(0)
            header = self.file.readline()[0:-1].split(',')
        if self.format == None:
            self.format = header
    def read_all(self):
        self.file.seek(0)
        header = self.file.readline()[0:-1].split(',')
        for line in self.file.readlines():
            row = line[0:-1].split(',')
            fullrow = dict()
            for i in range(len(row)):
                fullrow[self.format[i]] = row[i]
            yield fullrow
    def output(self, cols):
        self.file.seek(0, 2)
        self.file.write(','.join([str(cols[x]) for x in self.format]))
        self.file.write('\n')
        self.file.flush()

class Format1(CSV):
    FORMAT1 = [TIME_COL, EVENT_COL, GOAL_COL, TASK_COL]
    def __init__(self, file):
        super(Format1, self).__init__(file, Format1.FORMAT1)

class Data():
    def __init__(self, args):
        self.csv_details = Format1(args.details)
        self.csv_prio = CSV(args.priorities, [GOAL_COL, RATIO_COL])
        self.prios = {}
        self.prios_total = 0
        
        for prio in self.csv_prio.read_all():
            goal = prio[GOAL_COL]
            prio = float(prio[RATIO_COL])
            self.prios[goal] = prio
            self.prios_total += prio

        if args.work:
            goal = args.work.pop(0)
            goal = goal.upper()
            tasks = ' '.join(args.work)
            self.do_work(goal, tasks)
        elif args.report:
            self.do_report()
        elif args.suggest:
            self.do_suggest()

    def cumulate(self):
        self.total = 0
        self.cumulated = {}
        started = {}
        for goal in self.prios:
            self.cumulated[goal] = 0
        for detail in self.csv_details.read_all():
            goal = detail[GOAL_COL]
            event = detail[EVENT_COL]
            time = float(detail[TIME_COL])
            amt = 0
            if event == EVENT_START:
                started[goal] = time
                if goal not in self.cumulated:
                    self.cumulated[goal] = 0
                if goal not in self.prios:
                    self.prios[goal] = 0
            elif event == EVENT_HEARTBEAT:
                amt = time - started[goal]
                started[goal] = time
            elif event == EVENT_STOP:
                amt = time - started[goal]
                del started[goal]
            self.total += amt
            self.cumulated[goal] += amt
    
    def do_report(self):
        self.cumulate()
        for goal in self.cumulated:
            print('%s: %g hours (%f%% vs goal of %f%%)' % (goal, self.cumulated[goal]/60/60, self.cumulated[goal]*100/self.total, self.prios[goal]*100/self.prios_total))

    def do_suggest(self):
        self.cumulate()
        needed = {}
        for goal in self.cumulated:
            #needed[goal] = self.prios[goal]*self.total/self.prios_total - self.cumulated[goal]
            desiredpct = self.prios[goal] / self.prios_total
            needed[goal] = (self.cumulated[goal] - self.total * desiredpct) / (desiredpct - 1)
        order = needed.keys()
        order.sort(lambda a, b: cmp(needed[b], needed[a]))
        for goal in order[0:4]:
            print('%s needs at least %f more hours' % (goal, needed[goal] / 60 / 60))

    def do_work(self, goal, tasks):
        fd = sys.stdin.fileno()
        old = tty.tcgetattr(fd)
        tty.setcbreak(fd)
        getchar = lambda: sys.stdin.read(1)
        try:
            ts = time.time()
            if goal not in self.prios:
                self.csv_prio.output({GOAL_COL: goal, RATIO_COL: 1})
            print('Beginning work on %s towards %s at %s' % (tasks, goal, time.ctime(ts)))
            self.csv_details.output({TIME_COL: ts, EVENT_COL: EVENT_START, GOAL_COL: goal, TASK_COL: tasks})
            print('Press spacebar to indicate you are still working.')
            print('Press enter to indicate you have stopped.')
            #key = 
            while True:
                key = getchar()
                if key == '\n':
                    break
                if key != ' ':
                    print('!! Unrecognized keypress.  Working on %s for %s.  Press enter to stop, space to continue.' % (tasks, goal))
                    continue
                ts = time.time()
                print('Still working on %s towards %s at %s' % (tasks, goal, time.ctime(ts)))
                self.csv_details.output({TIME_COL: ts, EVENT_COL: EVENT_HEARTBEAT, GOAL_COL: goal, TASK_COL: tasks})
            ts = time.time()
            print('Stopped working on %s towards %s at %s' % (tasks, goal, time.ctime(ts)))
            self.csv_details.output({TIME_COL: ts, EVENT_COL: EVENT_STOP, GOAL_COL: goal, TASK_COL: tasks})
        finally:
            tty.tcsetattr(fd, tty.TCSAFLUSH, old)
    

data = Data(parser.parse_args())