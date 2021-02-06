#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""Eventlog Visualizer

Supported input format:
    YYYY-mm-ddTHH:MM:SS.msec text ...

"""

import sys
import argparse
import datetime
import matplotlib.pyplot as pyplot
import matplotlib.dates as mdates

VERSION = '1.0'
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"

def die(msg):
    sys.stderr.write('Fatal Error: ' + msg + '\n')
    sys.exit(1)


def load_file(input_file):
    try:
        f = open(input_file)
    except Exception as e:
        die(str(e))

    lines = f.readlines()
    f.close()
    # remove EOL CR/LF
    lines = [line.rstrip() for line in lines]
    return lines

def parse_line(line):
    """Return the date and data."""
    try:
        date_str, data = line.split(' ', 1)
        date_object = datetime.datetime.strptime(date_str, DATE_FORMAT)
        return date_object, data
    except:
        return None, None

def get_density_analysis(lines, pattern_density):
    """Return the density analysis of a pattern.

    This tells how frequent a pattern is in a period of time.
    At each timepoint is computed how many times the pattern has been encountered
    in the previous period. When the number is zero, the count is not stored.
    """

    WINDOW_SIZE_S = 300 # 5 minutes
    WINDOW_START = None # start of the time window
    events_window = [] # tuple ( <datetime>, <data> )
    density_analysis = []

    for line in lines:
        d, data = parse_line(line)
        if d is None: continue

        # Remove events older that the window size
        WINDOW_START = d - datetime.timedelta(seconds=WINDOW_SIZE_S)
        while len(events_window) and events_window[0][0] < WINDOW_START:
            events_window.pop(0)

        if data.find(pattern_density) >= 0:
            # Add the event
            events_window.append( (d, data) )

        # Compute the density
        density = len(events_window)
        density_analysis.append( (d, density) )
        # TODO may possibliy be optimized not storing all zeros
        # TODO may possibliy be smoother if we inserted dates for decreasing
        #      gradually the density during long inactivity

    return density_analysis


def get_spot_analysis(lines, pattern_spot):
    """Return the list of the dates when the event is matching the pattern."""
    spot_analysis = [] # [ <datetime> ]
    for line in lines:
        d, data = parse_line(line)
        if d is None: continue

        if data.find(pattern_spot) >= 0:
            spot_analysis.append(d)

    return spot_analysis

def get_color(id):
    Colors = [ 'b', 'g', 'r', 'c', 'm', 'y', 'k' ]
    if id >= len(Colors): die('Not nough colors to represent data')
    return Colors[id]

def display_graph(analysis_density, analysis_spot, date_start, date_end):
    """Display a graph with the curve of the density and the spots.
    
    Arguments:
        analysis_density : Dictionary
                           <pattern> => List of tuple (<datetime>, <density>)
        analysis_spot    : Dictionary
                           <pattern> => List of datetimes
    """

    fig, ax1 = pyplot.subplots()

    ax1.format_xdata = mdates.DateFormatter('%Y-%m-%d %H:%M')

    # Density
    color = 'tab:red'
    ax1.set_xlabel('datetime')
    ax1.set_ylabel('density', color=color)
    for name in analysis_density:
        data = analysis_density[name]
        t = [d for d, _x in data] # dates for the x axis
        data_density = [dat for _x, dat in data] # values for the y axis
        ax1.plot(t, data_density, color=color, label=name)
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.legend()
    
    if len(analysis_spot):
        ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
        spot_value = 0
    
    for name in analysis_spot:
        data = analysis_spot[name]
        # each spot analysis has a different y value and color
        color = get_color(spot_value)
        ax2.set_ylabel('spot', color=color)  # we already handled the x-label with ax1
        t = data
        data_spot = [spot_value for _x in data]
        ax2.scatter(t, data_spot, color=color, label=name)
        ax2.tick_params(axis='y', labelcolor=color)
        ax2.legend()
        spot_value += 1
    
    fig.tight_layout()  # otherwise the right y-label is slightly clipped
    
    # rotates and right aligns the x labels, and moves the bottom of the
    # axes up to make room for them
    fig.autofmt_xdate()

    myFmt = mdates.DateFormatter('%Y-%m-%d %H:%M')
    ax1.xaxis.set_major_formatter(myFmt)

    pyplot.show()
    


def main():
    global DATE_FORMAT
    parser = argparse.ArgumentParser(description=main.__doc__, prog='visualize')
    parser.add_argument('file', nargs=1, help='log file')
    parser.add_argument('-V', '--version', help='print version and exit',
                        action='version', version='%(prog)s' + VERSION)
    parser.add_argument('-d', '--density', nargs='+',
                        help='pattern for density representation')
    parser.add_argument('-s', '--spot', nargs='+',
                        help='pattern for spot representation')
    parser.add_argument('-f', '--date-format',
                        help='Date format for strptime (default %s)' % 
                             (DATE_FORMAT.replace('%', '%%')) )

    args = parser.parse_args()

    input_file = args.file[0]
    if args.date_format: DATE_FORMAT = args.date_format

    lines = load_file(input_file)

    analysis_density = {}
    for pattern_density in args.density:
        analysis = get_density_analysis(lines, pattern_density)
        analysis_density[pattern_density] = analysis

    analysis_spot = {}
    for pattern_spot in args.spot:
        analysis = get_spot_analysis(lines, pattern_spot)
        analysis_spot[pattern_spot] = analysis

    # Add starting point and ending point to have a global duration covering
    # the whole period.
    date_start, _x = parse_line(lines[0])
    date_end, _x = parse_line(lines[-1])

    display_graph(analysis_density, analysis_spot, date_start, date_end)

    

if __name__ == "__main__":
    main()
