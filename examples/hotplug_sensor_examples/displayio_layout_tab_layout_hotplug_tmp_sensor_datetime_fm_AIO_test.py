# SPDX-FileCopyrightText: 2022 PaulskPt
#
# SPDX-License-Identifier: MIT
"""
Added by @PaulskPt
This script can make use of an I2C Realtime Clock type DS3231
"""
# pylint: disable-all
import time
import gc
import displayio
import board
import terminalio
import busio
import adafruit_tmp117
from adafruit_display_text.bitmap_label import Label
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.circle import Circle
from adafruit_display_shapes.triangle import Triangle
from adafruit_ds3231 import DS3231
from digitalio import DigitalInOut
from adafruit_esp32spi import adafruit_esp32spi_socket as socket
from adafruit_esp32spi import adafruit_esp32spi
import adafruit_requests as requests
from adafruit_displayio_layout.layouts.tab_layout import TabLayout

# ----------------------------------
# Added by @PaulskPt
# This script can make use of an I2C Realtime Clock type DS3231
#

my_debug = False  # This flag controls most of the REPL print output.

# If you are using a board with pre-defined ESP32 Pins:
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
requests.set_socket(socket, esp)
# print("dir(esp) = ", dir(esp))

default_dt = None
months = {
    0: "Dum",
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}
use_txt_in_month = True
use_usa_notation = True
use_ntp = True

i2c = board.I2C()

print("\nTabLayout test with I2C Temperature sensor and I2C Realtime clock")
print(
    "Add your WiFi SSID, WiFi password, AIO username, AIO key and Timezone in file: secrets.h\n"
)


if my_debug:
    while not i2c.try_lock():
        pass

    try:
        while True:
            print(
                "I2C addresses found:",
                [hex(device_address) for device_address in i2c.scan()],
            )
            time.sleep(2)
            break

    finally:  # unlock the i2c bus when ctrl-c'ing out of the loop
        i2c.unlock()


lStart = True
rtc_present = None
rtc = None
o_secs = 0  # old seconds
c_secs = 0  # current seconds

dt_refresh = True

sDT_old = ""

t_sensor_present = None
tmp117 = None
t0 = None
t1 = None
t2 = None

degs_sign = chr(186)  # I preferred the real degrees sign which is: chr(176)

content_sensor_idx = None
pge3_lbl_dflt = "The third page is fun!"
pge4_lbl_dflt = "The fourth page is where it's at"

online_time_present = None
aio_username = None
aio_key = None
location = None

TIME_SERVICE = (
    "http://io.adafruit.com/api/v2/%s/integrations/time/strftime?x-aio-key=%s"
)
# See https://apidock.com/ruby/DateTime/strftime for full options
TIME_SERVICE_TIMESTAMP = "&fmt=%25s+%25z"

# you'll need to pass in an io username and key
# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

if my_debug:
    if esp.status == adafruit_esp32spi.WL_IDLE_STATUS:
        print("ESP32 found and in idle mode")
    print("Firmware vers.", esp.firmware_version)
    print("MAC addr:", [hex(i) for i in esp.MAC_address])

    for ap in esp.scan_networks():
        print("\t%s\t\tRSSI: %d" % (str(ap["ssid"], "utf-8"), ap["rssi"]))

# Get our username, key and desired timezone (see: get_local_timestamp())
"""
aio_username = secrets["aio_username"]
aio_key = secrets["aio_key"]
location = secrets.get("timezone", None)
"""
TIME_URL = (
    "https://io.adafruit.com/api/v2/%s/integrations/time/strftime?x-aio-key=%s"
    % (aio_username, aio_key)
)
TIME_URL += "&fmt=%25Y-%25m-%25d+%25H%3A%25M%3A%25S.%25L+%25j+%25u+%25z+%25Z"
current_time = None

print("Connecting to AP...")
while not esp.is_connected:
    try:
        esp.connect_AP(secrets["ssid"], secrets["password"])
    except RuntimeError as e:
        print("could not connect to AP, retrying: ", e)
        continue
print("Connected to", str(esp.ssid, "utf-8"), "\tRSSI:", esp.rssi)
if my_debug:
    print("My IP address is", esp.pretty_ip(esp.ip_address))
    print(
        "IP lookup adafruit.com: %s"
        % esp.pretty_ip(esp.get_host_by_name("adafruit.com"))
    )
    print("Ping google.com: %d ms" % esp.ping("google.com"))

# -----------------------------------

# built-in display
display = board.DISPLAY
# display.rotation = 90
display.rotation = 0

# create and show main_group
main_group = displayio.Group()
display.show(main_group)

# font = bitmap_font.load_font("fonts/Helvetica-Bold-16.bdf")
font = terminalio.FONT

# create the page layout
test_page_layout = TabLayout(
    x=0,
    y=0,
    display=board.DISPLAY,
    tab_text_scale=2,
    custom_font=font,
    inactive_tab_spritesheet="lib/adafruit_displayio_layout/examples/bmps/inactive_tab_sprite.bmp",
    showing_tab_spritesheet="lib/adafruit_displayio_layout/examples/bmps/active_tab_sprite.bmp",
    showing_tab_text_color=0x00AA59,
    inactive_tab_text_color=0xEEEEEE,
    inactive_tab_transparent_indexes=(0, 1),
    showing_tab_transparent_indexes=(0, 1),
    tab_count=4,
)

# make 3 pages of content
pge1_group = displayio.Group()
pge2_group = displayio.Group()
pge3_group = displayio.Group()
pge4_group = displayio.Group()

# labels
pge1_lbl = Label(
    font=terminalio.FONT,
    scale=2,
    text="This is the first page!",
    anchor_point=(0, 0),
    anchored_position=(10, 10),
)
pge1_lbl2 = Label(
    font=terminalio.FONT,
    scale=2,
    text="Please wait...",
    anchor_point=(0, 0),
    anchored_position=(10, 150),
)
pge2_lbl = Label(
    font=terminalio.FONT,
    scale=2,
    text="This page is the second page!",
    anchor_point=(0, 0),
    anchored_position=(10, 10),
)
pge3_lbl = Label(
    font=terminalio.FONT,
    scale=2,
    text=pge3_lbl_dflt,  # Will be "Date/time:"
    anchor_point=(0, 0),
    anchored_position=(10, 10),
)
pge3_lbl2 = Label(
    font=terminalio.FONT,
    scale=2,
    text="",  # pge3_lbl2_dflt,   # Will be DD-MO-YYYY or Month-DD-YYYY
    anchor_point=(0, 0),
    anchored_position=(10, 40),
)
pge3_lbl3 = Label(
    font=terminalio.FONT,
    scale=2,
    text="",  # pge3_lbl3_dflt,  # Will be HH:MM:SS
    anchor_point=(0, 0),
    anchored_position=(10, 70),
)
pge4_lbl = Label(
    font=terminalio.FONT,
    scale=2,
    text=pge4_lbl_dflt,
    anchor_point=(0, 0),
    anchored_position=(10, 10),
)
pge4_lbl2 = Label(
    font=terminalio.FONT,
    scale=2,
    text="",  # Will be "Temperature"
    anchor_point=(0, 0),
    anchored_position=(10, 130),
)
pge4_lbl3 = Label(
    font=terminalio.FONT,
    scale=2,
    text="",  # Will be  "xx.yy C"
    anchor_point=(0, 0),
    anchored_position=(10, 160),
)

# shapes
square = Rect(x=20, y=70, width=40, height=40, fill=0x00DD00)
circle = Circle(50, 100, r=30, fill=0xDD00DD)
triangle = Triangle(50, 0, 100, 50, 0, 50, fill=0xDDDD00)
rectangle = Rect(x=80, y=60, width=100, height=50, fill=0x0000DD)

triangle.x = 80
triangle.y = 70

# add everything to their page groups
pge1_group.append(square)
pge1_group.append(pge1_lbl)
pge1_group.append(pge1_lbl2)
pge2_group.append(pge2_lbl)
pge2_group.append(circle)
pge3_group.append(pge3_lbl)
pge3_group.append(pge3_lbl2)
pge3_group.append(pge3_lbl3)
pge3_group.append(triangle)
pge4_group.append(pge4_lbl)
pge4_group.append(pge4_lbl2)
pge4_group.append(pge4_lbl3)
pge4_group.append(rectangle)

pages = {0: "One", 1: "Two", 2: "Thr", 3: "For"}

# add the pages to the layout, supply your own page names
test_page_layout.add_content(pge1_group, pages[0])
test_page_layout.add_content(pge2_group, pages[1])
test_page_layout.add_content(pge3_group, pages[2])
test_page_layout.add_content(pge4_group, pages[3])

# test_page_layout.add_content(displayio.Group(), "page_5")

# add it to the group that is showing on the display
main_group.append(test_page_layout)

# test_page_layout.tab_tilegrids_group[3].x += 50

# change page with function by name
test_page_layout.show_page(page_name=pages[2])
print("showing page index:{}".format(test_page_layout.showing_page_index))
time.sleep(1)

# change page with function by index
test_page_layout.show_page(page_index=0)
print("showing page name: {}".format(test_page_layout.showing_page_name))
time.sleep(1)

# change page by updating the page name property
test_page_layout.showing_page_name = pages[2]
print("showing page index: {}".format(test_page_layout.showing_page_index))
time.sleep(1)

# change page by updating the page index property
test_page_layout.showing_page_index = 1
print("showing page name: {}".format(test_page_layout.showing_page_name))
time.sleep(5)

"""
another_text = Label(terminalio.FONT, text="And another thing!", scale=2, \
    color=0x00ff00, anchor_point=(0, 0), \
    anchored_position=(100, 100))
test_page_layout.showing_page_content.append(another_text)
"""
print("starting loop")

temp_update_cnt = 0
old_temp = 0.00


def get_creds_and_tz():
    global aio_username, aio_key, location
    try:
        aio_username = secrets["aio_username"]
        aio_key = secrets["aio_key"]
        location = secrets["timezone"]
    except Exception as exc:
        raise KeyError(
            "\n\nOur time service requires a login/password to rate-limit. Please register for \
            a free adafruit.io account and place the user/key in your secrets file \
            under 'aio_username' and 'aio_key'"
        ) from exc


def get_local_timestamp():
    global online_time_present, default_dt

    # pylint: disable=line-too-long
    """Fetch and "set" the local time of this microcontroller to the local time
       at the location, using an internet time API.
    location: Your city and country, e.g. ``"New York, US"``.
    """
    # pylint: enable=line-too-long
    api_url = None
    get_creds_and_tz()
    # pylint: disable=line-too-long

    if location:
        if my_debug:
            print("Getting time for timezone", location)
        api_url = (TIME_SERVICE + "&tz=%s") % (aio_username, aio_key, location)
    else:  # we'll try to figure it out from the IP address
        if my_debug:
            print("Getting time from IP address")
        api_url = TIME_SERVICE % (aio_username, aio_key)
    api_url += TIME_SERVICE_TIMESTAMP
    try:
        if my_debug:
            print("api_url:", api_url)
        response = requests.get(api_url)
        if my_debug:
            print("response from (TIME_SERVICE) = ", response.text)
        times = response.text.split(" ")
        seconds = int(times[0])
        tzoffset = times[1]
        tzhours = int(tzoffset[0:3])
        tzminutes = int(tzoffset[3:5])
        tzseconds = tzhours * 60 * 60
        if tzseconds < 0:
            tzseconds -= tzminutes * 60
        else:
            tzseconds += tzminutes * 60
        if my_debug:
            print("seconds + tzseconds, tzoffset, tzhours, tzminutes =")
            print(seconds + tzseconds, tzoffset, tzhours, tzminutes)
        default_dt = time.struct_time(
            (2022, 5, 2, tzhours, tzminutes, tzseconds, 0, -1, -1)
        )

    except Exception as exc:
        raise KeyError(
            "Was unable to lookup the time, try setting secrets['timezone'] \
            according to http://worldtimeapi.org/timezones"
        ) from exc
    # pylint: disable=line-too-long

    if response is not None:
        online_time_present = (
            True  # Set flag for main() to indicate that calls to get_dt() can be done
        )

    # clean up
    response.close()
    response = None
    gc.collect()


"""
  If the temperature sensor has been disconnected,
  this function will try to reconnect (test if the sensor is present by now)
  If reconnected this function sets the global variable t_sensor_present
  If failed to reconnect the function clears t_sensor_present
"""


def connect_temp_sensor():
    global t_sensor_present, tmp117, t0, t1, t2
    t = "temperature sensor found"
    t_sensor_present = False
    tmp117 = None

    try:
        tmp117 = adafruit_tmp117.TMP117(i2c)
    except ValueError:  # ValueError occurs if the temperature sensor is not connected
        pass

    if tmp117 is not None:
        t_sensor_present = True

    if t_sensor_present:
        print(t)
        print("temperature sensor connected")
        t0 = "Temperature"
        t1 = " C"
        t2 = 27 * "_"
    else:
        print("no " + t)
        print("failed to connect temperature sensor")
        t0 = None
        t1 = None
        t2 = None


"""
  If the external rtc has been disconnected,
  this function will try to reconnect (test if the external rtc is present by now)
  If reconnected this function sets the global variable rtc_present
  If failed to reconnect the function clears rtc_present
"""


def connect_rtc():
    global rtc_present, rtc, lStart
    t = "RTC found"
    rtc_present = False
    rtc = None
    try:
        rtc = DS3231(i2c)  # i2c addres 0x68
    except ValueError:
        pass

    if rtc is not None:
        rtc_present = True
        print(t)
        print("RTC connected")
        if lStart:
            lStart = False
            rtc.datetime = default_dt
    else:
        print("no " + t)
        print("Failed to connect RTC")


temp_in_REPL = False

"""
   Function gets a value from the external temperature sensor
   It only updates if the value has changed compared to the previous value
   If no value obtained (for instance if the sensor is disconnected)
   the function sets the page_4 label to a default text
"""


def get_temp():
    global t_sensor_present, old_temp, tmp117, pge4_lbl, pge4_lbl2, pge4_lbl3, temp_in_REPL
    showing_page_idx = test_page_layout.showing_page_index
    RetVal = False
    if t_sensor_present:
        try:
            temp = tmp117.temperature
            t = "{:5.2f} ".format(temp) + t1
            if my_debug and temp is not None and not temp_in_REPL:
                temp_in_REPL = True
                print("get_temp(): {} {}".format(t0, t))
            if showing_page_idx == 3:  # show temperature on most right Tab page
                if temp is not None:
                    if (
                        temp != old_temp
                    ):  # Only update if there is a change in temperature
                        old_temp = temp
                        t = "{:5.2f} ".format(temp) + t1
                        pge4_lbl.text = ""
                        pge4_lbl2.text = t0
                        pge4_lbl3.text = t
                        # if not my_debug:
                        # print("pge4_lbl.text = {}".format(pge4_lbl.text))
                        # time.sleep(2)
                        RetVal = True
                else:
                    t = ""
                    pge4_lbl.text = pge4_lbl_dflt
        except OSError:
            print("Temperature sensor has disconnected")
            t = ""
            t_sensor_present = False
            tmp117 = None
            pge4_lbl.text = pge4_lbl_dflt  # clean the line  (eventually: t2)
            pge4_lbl2.text = ""
            pge4_lbl3.text = ""

    return RetVal


yy = 0
mo = 1
dd = 2
hh = 3
mm = 4
ss = 5


"""
    Function called by get_dt()
    Created to repair pylint error R0912: Too many branches (13/12)
"""


def handle_dt(dt):
    global sDT_old, o_secs, c_secs, dt_refresh, pge3_lbl, pge3_lbl2, pge3_lbl3
    RetVal = False
    s = "Date/time: "
    sYY = str(dt[yy])
    sMO = (
        months[dt[mo]]
        if use_txt_in_month
        else "0" + str(dt[mo])
        if dt[mo] < 10
        else str(dt[mo])
    )

    dt_dict = {}

    for _ in range(dd, ss + 1):
        dt_dict[_] = "0" + str(dt[_]) if dt[_] < 10 else str(dt[_])

    if my_debug:
        print("dt_dict = ", dt_dict)

    c_secs = dt_dict[ss]
    sDT = (
        sMO + "-" + dt_dict[dd] + "-" + sYY
        if use_usa_notation
        else sYY + "-" + sMO + "-" + dt_dict[dd]
    )

    if sDT_old != sDT:
        sDT_old = sDT
        dt_refresh = True  # The date has changed, set the refresh flag
    sDT2 = dt_dict[hh] + ":" + dt_dict[mm] + ":" + dt_dict[ss]

    if dt_refresh:  # only refresh when needed
        dt_refresh = False
        pge3_lbl.text = s
        pge3_lbl2.text = sDT

    if c_secs != o_secs:
        o_secs = c_secs
        sDT3 = s + "{} {}".format(sDT, sDT2)
        print(sDT3)

        pge3_lbl3.text = sDT2
        if my_debug:
            print("pge3_lbl.text = {}".format(pge3_lbl.text))
            print("pge3_lbl2.text = {}".format(pge3_lbl2.text))
            print("pge3_lbl3.text = {}".format(pge3_lbl3.text))
        RetVal = True

    # Return from here with a False but don't set the pge3_lbl to default.
    # It is only to say to the loop() that we did't update the datetime
    return RetVal


"""
   Function gets the date and time:
   a) if an rtc is present from the rtc;
   b) if using online NTP pool server then get the date and time from the function time.localtime
   This time.localtime has before been set with data from the NTP server.
   In both cases the date and time will be set to the page3_lbl, lbl12 and lbl3
   If no (valid) date and time has been received then a default text will be shown on the page3_lbl
"""


def get_dt():
    global rtc_present, pge3_lbl, pge3_lbl2, pge3_lbl3
    dt = None
    RetVal = False

    if rtc_present:
        try:
            dt = rtc.datetime
        except OSError as exc:
            if my_debug:
                print("Error number: ", exc.args[0])
            if exc.args[0] == 5:  # Input/output error
                rtc_present = False
                print("get_dt(): OSError occurred. RTC probably is disconnected")
                pge3_lbl.text = pge3_lbl_dflt
                return RetVal
            raise  # Handle other errors

    elif online_time_present or use_ntp:
        dt = time.localtime()

    if dt is not None:
        RetVal = handle_dt(dt)
    else:
        pge3_lbl.text = pge3_lbl_dflt
        pge3_lbl2.text = ""
        pge3_lbl3.text = ""
    return RetVal


def setup():
    # Get the current time in seconds since Jan 1, 1970
    get_local_timestamp()
    if my_debug:
        print(
            "default_dt (from AIO TIME service - set to the internal RTC: {}".format(
                default_dt
            )
        )


def main():
    # global test_page_layout, another_text
    cnt = 0
    setup()
    while True:
        try:
            print("Loop nr: {:03d}".format(cnt))

            if rtc_present or online_time_present:
                get_dt()
            else:
                connect_rtc()

            if t_sensor_present:
                get_temp()
            else:
                connect_temp_sensor()

            cnt += 1
            if cnt > 999:
                cnt = 0
            # change page by next page function. It will loop by default
            time.sleep(2)
            test_page_layout.next_page()
        except KeyboardInterrupt as exc:
            raise KeyboardInterrupt("Keyboard interrupt...exiting...") from exc
            # raise SystemExit


if __name__ == "__main__":
    main()
