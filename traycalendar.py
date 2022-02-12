#!/usr/bin/env python3
########################################################################
# Copyright (C) 2015-2022 Wojciech Siewierski                          #
#                                                                      #
# This program is free software; you can redistribute it and/or        #
# modify it under the terms of the GNU General Public License          #
# as published by the Free Software Foundation; either version 3       #
# of the License, or (at your option) any later version.               #
#                                                                      #
# This program is distributed in the hope that it will be useful,      #
# but WITHOUT ANY WARRANTY; without even the implied warranty of       #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the        #
# GNU General Public License for more details.                         #
#                                                                      #
# You should have received a copy of the GNU General Public License    #
# along with this program. If not, see <http://www.gnu.org/licenses/>. #
########################################################################


import functools
import glob
import os.path
import re
import sys
import socket
from collections import defaultdict
from os import getenv

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

WM_CLASS = "TrayCalendar"
TOGGLE_INSTRUCTION = "TC_DIE"

DEFAULT_ORG_DIRECTORY = os.path.join(getenv('HOME'), "org")
ORG_GLOB = '*.org'
ORG_ARCHIVE_SUFFIX = '_archive.org'


def org_agenda_files(directory):
    org_abs = functools.partial(os.path.join, directory)
    agenda_files_path = org_abs('.agenda-files')
    try:
        with open(agenda_files_path) as agenda_files:
            yield from (org_abs(f.rstrip('\n')) for f in agenda_files)
    except FileNotFoundError:
        for filename in glob.iglob(os.path.join(directory, ORG_GLOB)):
            if not filename.endswith(ORG_ARCHIVE_SUFFIX):
                yield filename


def scan_org_for_events(org_directories):
    """Search the org files for the calendar events.

    Scans the passed directories for the .org files and saves the events
    found there into a multilevel dict of lists: events[year][month][day]

    The returned dict uses defaultdict so *do not* rely on the
    KeyError exception etc.! Check if the element exists with
    .get(key) before accessing it!

    """

    def year_dict():
        return defaultdict(month_dict)
    def month_dict():
        return defaultdict(day_dict)
    def day_dict():
        return defaultdict(event_list)
    def event_list():
        return list()

    events = year_dict()
    for org_directory in org_directories:
        for filename in org_agenda_files(org_directory):
            with open(filename, "r") as filehandle:
                last_heading = None
                for line in filehandle:
                    heading_match = re.search(r'^\*+\s+(.*)', line)
                    if heading_match:
                        last_heading = heading_match.group(1)
                        # strip the tags
                        last_heading = re.sub(r'\s*\S*$', last_heading, '')
                    match = re.search(r'<(\d{4})-(\d{2})-(\d{2}).*?>', line)
                    if match:
                        year, month, day = [ int(field) for field in match.group(1,2,3) ]
                        month -= 1      # months are indexed from 0 in Gtk.Calendar
                        events[year][month][day].append(last_heading)
    return events

class CalendarWindow(object):

    def __init__(self, org_directories, toggle=False, fixed_pos=False, pos=None):
        if toggle:
            self.get_lock()

        self.window = Gtk.Window()
        self.window.set_wmclass("traycalendar", WM_CLASS)

        self.window.set_resizable(False)
        self.window.set_decorated(False)

        window_width = 300

        # Set the window geometry.
        geometry = Gdk.Geometry()
        geometry.min_width = window_width
        geometry.max_width = window_width
        geometry.base_width = window_width
        self.window.set_geometry_hints(
            None, geometry,
            Gdk.WindowHints.MIN_SIZE |
            Gdk.WindowHints.MAX_SIZE |
            Gdk.WindowHints.BASE_SIZE)

        # Create the listview for the calendar events.
        list_model = Gtk.ListStore(str)
        list_view = Gtk.TreeView(list_model)
        list_column = Gtk.TreeViewColumn("Events", Gtk.CellRendererText(), text=0)
        list_column.set_fixed_width(window_width)
        list_view.append_column(list_column)

        # Create the calendar widget.
        calendar = Gtk.Calendar()
        self.calendar_events = scan_org_for_events(org_directories)
        calendar.connect('month-changed', self.mark_calendar_events)
        calendar.connect('day-selected', self.display_event_list, list_model)
        self.mark_calendar_events(calendar)
        self.display_event_list(calendar, list_model)

        close_button = Gtk.Button("Close")
        close_button.connect('clicked', lambda event: self.window.destroy())

        vbox = Gtk.VBox()
        vbox.add(close_button)
        vbox.add(calendar)
        vbox.add(list_view)

        self.window.add(vbox)

        rootwin = self.window.get_screen().get_root_window()
        # get_pointer is deprecated but using Gdk.Device.get_position
        # is not viable here: we have no access to the pointing device.
        screen, x, y, mask = rootwin.get_pointer()

        if fixed_pos:
            self.position_fixed(pos, window_width, x, y)
        else:
            self.window.set_gravity(Gdk.Gravity.STATIC)
            x -= window_width
            # Show the window right beside the cursor.
            self.window.move(x,y)

        self.window.show_all()

    def position_fixed(self, pos, window_width, x, y):
        if pos[1] >= 0:
            self.window.set_gravity(Gdk.Gravity.NORTH_EAST)
            # Gdk.Screen.get_width() is deprecated
            # The preferred method appears to be as follows
            screen_width = self.window.get_screen().get_display().get_monitor_at_point(x, y).get_geometry().width
            self.window.move(screen_width - window_width - pos[1], pos[0])
        else:
            self.window.set_gravity(Gdk.Gravity.NORTH_WEST)
            self.window.move(pos[2], pos[0])

    def get_lock(self):
        self._lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)

        try:
            # Bind socket to an abstract socket address.
            self._lock_socket.bind('\0' + WM_CLASS)
            # Attach a listener to glib's event loop.
            GLib.io_add_watch(GLib.IOChannel(self._lock_socket.fileno()), 0, GLib.IOCondition.IN, self.toggle_listener, self._lock_socket)
        except socket.error:
            # Since the address was already taken, connect to it and send the toggle-signal.
            self._lock_socket.connect('\0' + WM_CLASS)
            self._lock_socket.send(TOGGLE_INSTRUCTION.encode())
            sys.exit()

    def toggle_listener(self, io, cond, socket):
        connection = socket.recvfrom(len(TOGGLE_INSTRUCTION))
        instruction = connection[0].decode()
        # Quit the app upon receiving the toggle-signal.
        if TOGGLE_INSTRUCTION == instruction:
            Gtk.main_quit()
        return True

    def mark_calendar_events(self, calendar):
        """Update the days with calendar events list for the selected month."""
        year, month, day = calendar.get_date()
        calendar.freeze_notify()
        calendar.clear_marks()
        for day in self.calendar_events[year][month]:
            calendar.mark_day(day)
        calendar.thaw_notify()

    def display_event_list(self, calendar, event_list):
        """Update the calendar event list for the selected day."""
        year, month, day = calendar.get_date()
        event_list.clear()

        # get(day) used instead of [day] because we use defaultdict
        # and it would create a new element.
        events = self.calendar_events[year][month].get(day)
        if events:
            for event in events:
                event_list.append([event])


def tray_mode(org_directories):
    def on_left_click(event):
        window = CalendarWindow(org_directories)
    def on_right_click(button, time, data):
        Gtk.main_quit()
    statusicon = Gtk.StatusIcon()
    statusicon.set_from_icon_name('x-office-calendar')
    statusicon.connect('activate', on_left_click)
    statusicon.connect('popup-menu', on_right_click)
    Gtk.main()

def window_mode(org_directories, toggle, fixed_pos, pos):
    window = CalendarWindow(org_directories, toggle, fixed_pos, pos)
    window.window.connect('destroy', Gtk.main_quit)
    Gtk.main()

def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-tray",
        help="Show the calendar windows immediately and quit after it's closed.",
        action='store_true',
    )
    parser.add_argument(
        "--toggle",
        help="When started with this argument, the will quit if another process is started with --toggle",
        action='store_true',
    )
    parser.add_argument("--top", "-t",
            type=int,
            help="The distance from the top of the screen (Enables absolute positioning).",
            dest='d_top',
            action='store')
    parser.add_argument("--left", "-l",
            type=int,
            help="The distance from the left of the screen (Enables absolute positioning).",
            dest='d_left',
            action='store')
    parser.add_argument("--right", "-r",
            type=int,
            help="The distance from the right of the screen (Enables absolute positioning).",
            dest='d_right',
            action='store')

    parser.add_argument(
        "--org-directory", "-d",
        help="Directories to search for *.org; default: ~/org/.",
        action='append',
        dest='org_directories',
    )
    args = parser.parse_args()

    if not args.org_directories:
        args.org_directories = [DEFAULT_ORG_DIRECTORY]

    fixed_pos = not (args.d_top is None and args.d_right is None and args.d_left is None)
    if args.d_top is None:
        args.d_top = 0
    if args.d_left is None:
        args.d_left = 0
    if args.d_right is None:
        args.d_right = -1
    pos = (args.d_top, args.d_right, args.d_left)

    if args.no_tray:
        window_mode(args.org_directories, args.toggle, fixed_pos, pos)
    else:
        tray_mode(args.org_directories)

if __name__ == "__main__":
    from sys import argv

    # workaround for a pygobject bug
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    main(argv)
