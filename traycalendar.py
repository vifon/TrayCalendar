#!/usr/bin/env python3
########################################################################
# Copyright (C) 2015 Wojciech Siewierski                               #
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


import glob
import re
from collections import defaultdict
from os import getenv

from gi.repository import Gtk, Gdk


ORG_DIRECTORY = getenv('HOME') + '/org/'
ORG_GLOB = '*.org'
ORG_ARCHIVE_SUFFIX = '_archive.org'


def scan_org_for_events():
    """Search the org files for the calendar events"""

    def year_dict():
        return defaultdict(month_dict)
    def month_dict():
        return defaultdict(day_dict)
    def day_dict():
        return defaultdict(event_list)
    def event_list():
        return list()

    events = year_dict()
    for filename in glob.iglob(ORG_DIRECTORY + '/' + ORG_GLOB):
        if filename.endswith(ORG_ARCHIVE_SUFFIX):
            continue
        with open(filename, "r") as filehandle:
            last_heading = None
            for line in filehandle:
                heading_match = re.search(r'^\*+\s+(.*)', line)
                if heading_match:
                    last_heading = heading_match.group(1)
                    # strip the tags
                    last_heading = re.sub(r'\s*\S*$', last_heading, '')
                match = re.search(r'<(\d{4})-(\d{2})-(\d{2}) \w+.*?>', line)
                if match:
                    year, month, day = [ int(field) for field in match.group(1,2,3) ]
                    month -= 1      # months are indexed from 0 in Gtk.Calendar
                    events[year][month][day].append(last_heading)
    return events

class CalendarWindow(object):

    def __init__(self):
        self.window = Gtk.Window()

        self.window.connect('focus-out-event', self.destroy)

        self.window.set_resizable(False)
        self.window.set_decorated(False)
        self.window.set_gravity(Gdk.Gravity.STATIC)

        # Set the window geometry.
        geometry = Gdk.Geometry()
        geometry.min_width = 300
        geometry.max_width = 300
        geometry.base_width = 300
        self.window.set_geometry_hints(
            None, geometry,
            Gdk.WindowHints.MIN_SIZE |
            Gdk.WindowHints.MAX_SIZE |
            Gdk.WindowHints.BASE_SIZE)

        # Create the listview for the calendar events.
        list_model = Gtk.ListStore(str)
        list_view = Gtk.TreeView(list_model)
        list_column = Gtk.TreeViewColumn("Events", Gtk.CellRendererText(), text=0)
        list_column.set_fixed_width(300)
        list_view.append_column(list_column)

        # Create the calendar widget.
        calendar = Gtk.Calendar()
        self.calendar_events = scan_org_for_events()
        calendar.connect('month-changed', self.mark_calendar_events)
        calendar.connect('day-selected', self.display_event_list, list_model)
        self.mark_calendar_events(calendar)
        self.display_event_list(calendar, list_model)

        vbox = Gtk.VBox()
        vbox.add(calendar)
        vbox.add(list_view)

        self.window.add(vbox)

        # deprecated and hack FIXME
        # Show the window right beside the cursor.
        rootwin = self.window.get_screen().get_root_window()
        screen, x, y, mask = rootwin.get_pointer()
        x -= 300
        self.window.move(x,y)

        self.window.show_all()

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

    def destroy(self, widget, event):
        """Destroy this window on Gtk event."""
        self.window.destroy()


def on_left_click(event):
    window = CalendarWindow()

def on_right_click(button, time, data):
    Gtk.main_quit()

def main(argv=None):
    statusicon = Gtk.StatusIcon()
    statusicon.set_from_icon_name('x-office-calendar')
    statusicon.connect('activate', on_left_click)
    statusicon.connect('popup-menu', on_right_click)
    Gtk.main()

if __name__ == "__main__":
    from sys import argv

    # workaround for a pygobject bug
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    main(argv)
