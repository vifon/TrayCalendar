TrayCalendar
============

[![](https://raw.githubusercontent.com/Vifon/TrayCalendar/master/examples/screenshot.jpg)](https://raw.githubusercontent.com/Vifon/TrayCalendar/master/examples/screenshot.jpg)

TrayCalendar is a minimal popup calendar designed to work in
environments that lack an easy access to a calendar, like i3wm, XMonad
or Awesome.

It is capable of reading the Emacs org-mode files (by default from
`~/org/*.org`) and displaying the events found in them.

To display the calendar, left-click on its tray icon. Right-click to
close TrayCalendar completely.

For now TrayCalendar assumes the system tray is located in the upper
right corner of the screen.

The calendar window should be ignored by the window manager. In XMonad it can be achieved by adding the following rule to `manageHook`:

```haskell
className =? "TrayCalendar" --> doIgnore
```

Suggested configuration for `xmobar` as the clock:

```
<action=`traycalendar --no-tray &> /dev/null`><action=`traycalendar &> /dev/null` button=3>%date%</action></action>
```

DEPENDENCIES
------------

- Python 3
- PyGObject

AUTHOR
------

Wojciech 'vifon' Siewierski \<wojciech dot siewierski at onet dot pl\>

COPYRIGHT
---------

Copyright (C) 2015-2018  Wojciech Siewierski

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
