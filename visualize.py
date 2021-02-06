#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""Eventlog Visualizer

Show a graph of events over time in either of two representations:

    - 'spot': events are represented as points
    - 'density': the number of events per period is represented as a curve

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
DENSITY_WINDOW_SIZE_S = 300 # 5 minutes

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

    events_window = [] # tuple ( <datetime>, <data> )
    density_analysis = []

    if len(lines) == 0: return density_analysis

    # Start from the first datetime and walk through each subsequent time window
    window_start, data = parse_line(lines[0])
    window_count = 0
    window_size = datetime.timedelta(seconds=DENSITY_WINDOW_SIZE_S)

    for line in lines:
        d, data = parse_line(line)
        if d is None:
            lines.pop(0) # consume the line
            continue

        if d > window_start + window_size:
            # record the finishing window
            density_analysis.append( (window_start, window_count) )
            window_start += window_size # next window

            # add empty data in all windows
            while d > window_start + window_size:
                window_start += window_size
                density_analysis.append( (window_start, 0) )

            # start next window
            window_count = 0

        # TODO use regex
        if data.find(pattern_density) >= 0:
            window_count += 1

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

    color_idx = 0 # inreased for each dataset
    # Density
    ax1.set_xlabel('datetime')
    ax1.set_ylabel('density (%d s)' % (DENSITY_WINDOW_SIZE_S), color=get_color(color_idx))
    for name in analysis_density:
        data = analysis_density[name]
        color = get_color(color_idx)
        t = [d for d, _x in data] # dates for the x axis
        data_density = [dat for _x, dat in data] # values for the y axis
        ax1.plot(t, data_density, color=color, label=name, drawstyle='steps-post')
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.legend()
        color_idx += 1
    
    if len(analysis_spot):
        ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
        # each spot analysis has a different y value
        spot_value = 0
        ax2.set_ylim(-1, len(analysis_spot)+1)
        ax2.get_yaxis().set_visible(False)
    
    for name in analysis_spot:
        data = analysis_spot[name]
        color = get_color(color_idx)
        ax2.set_ylabel('spot', color=color)  # we already handled the x-label with ax1
        t = data
        data_spot = [spot_value for _x in data]
        ax2.scatter(t, data_spot, color=color, label=name)
        ax2.tick_params(axis='y', labelcolor=color)
        ax2.legend()
        spot_value += 1
        color_idx += 1

    fig.tight_layout()  # otherwise the right y-label is slightly clipped
    
    # rotates and right aligns the x labels, and moves the bottom of the
    # axes up to make room for them
    fig.autofmt_xdate()

    myFmt = mdates.DateFormatter('%Y-%m-%d %H:%M')
    ax1.xaxis.set_major_formatter(myFmt)

    pyplot.show()
    


def main():
    global DATE_FORMAT, DENSITY_WINDOW_SIZE_S
    parser = argparse.ArgumentParser(description=main.__doc__, prog='visualize')
    parser.add_argument('file', nargs=1, help='log file')
    parser.add_argument('-V', '--version', help='print version and exit',
                        action='version', version='%(prog)s' + VERSION)
    parser.add_argument('-d', '--density', nargs='+', metavar='PATTERN',
                        help='pattern(s) for density representation')
    parser.add_argument('-s', '--spot', nargs='+', metavar='PATTERN',
                        help='pattern(s) for spot representation')
    parser.add_argument('-f', '--date-format',
                        help='Date format for strptime (default %s)' % 
                             (DATE_FORMAT.replace('%', '%%')) )
    parser.add_argument('--density-window-size', type=int,
                        help='Size of the time windows for counting the density (seconds). Default is 5 min.')

    args = parser.parse_args()

    input_file = args.file[0]
    if args.date_format: DATE_FORMAT = args.date_format
    if args.density_window_size: DENSITY_WINDOW_SIZE_S = args.density_window_size

    lines = load_file(input_file)

    analysis_density = {}
    if args.density:
        for pattern_density in args.density:
            analysis = get_density_analysis(lines, pattern_density)
            analysis_density[pattern_density] = analysis

    analysis_spot = {}
    if args.spot:
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
