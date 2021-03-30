# SPDX-FileCopyrightText: 2021 Tim Cocks
#
# SPDX-License-Identifier: MIT
"""
Creates two animated icons with touch response: zoom and shrink animations.
"""
import gc
import time
import board
import displayio
import adafruit_touchscreen
from adafruit_displayio_layout.widgets.icon_widget import IconWidget

display = board.DISPLAY

ts = adafruit_touchscreen.Touchscreen(
    board.TOUCH_XL,
    board.TOUCH_XR,
    board.TOUCH_YD,
    board.TOUCH_YU,
    calibration=((5200, 59000), (5800, 57000)),
    size=(display.width, display.height),
)



icon_left = IconWidget(
    "Zoom",
    "icons/Play_48x48_small.bmp",
    x=50,
    y=40,
    on_disk=True,
)

icon_right = IconWidget(
    "Shrink",
    "icons/Play_48x48_small.bmp",
    x=180,
    y=40,
    on_disk=True,
    scale=0.7,  # shrink animation
    angle=-10,
)

icons = [icon_left, icon_right]

main_group = displayio.Group(max_size=2)
main_group.append(icon_left)
main_group.append(icon_right)

display.show(main_group)

COOLDOWN_TIME = 0.25
LAST_PRESS_TIME = -1

display.auto_refresh = True

while True:
    time.sleep(0.05)
    p = ts.touch_point
    if p:
        _now = time.monotonic()
        if _now - LAST_PRESS_TIME > COOLDOWN_TIME:
            for icon in icons:
                if icon.contains(p):

                    LAST_PRESS_TIME = time.monotonic()

    else:
        for icon in icons:
            icon.zoom_out_animation(p)
