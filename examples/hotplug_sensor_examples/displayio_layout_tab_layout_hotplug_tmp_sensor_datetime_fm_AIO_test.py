# SPDX-FileCopyrightText: 2022 PaulskPt
#
# SPDX-License-Identifier: MIT
"""
Added by @PaulskPt
This script can make use of an I2C Realtime Clock type DS3231
"""
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
from adafruit_esp32spi import adafruit_esp32spi  # , adafruit_esp32spi_wifimanager
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

i2c = board.I2C()

print("\nTabLayout test with I2C Temperature sensor and I2C Realtime clock")
print(
    "Add your WiFi SSID, WiFi password, AIO username, AIO key and Timezone in file: secrets.h\n"
)

if my_debug:
    dev_list = []
    try:
        while not i2c.try_lock():
            i2c.try_lock()
            time.sleep(0.5)
        print("Start scan for connected I2C devices...")
        dev_list = i2c.scan()
        if dev_list is not None:
            le = len(dev_list)
            print("{} I2C device{} found:".format(le, "s" if le > 1 else ""))
            for i in range(le):
                print("Device {:d} at address 0x{:02x}".format(i, dev_list[i]))
        i2c.unlock()
        print("End of i2c scan")
    except Exception:
        raise

lStart = True
rtc_present = None
rtc = None

temp_sensor_present = None
tmp117 = None
t0 = None
t1 = None
t2 = None

degs_sign = chr(186)  # I preferred the real degrees sign which is: chr(176)

content_sensor_idx = None
page_3_lbl_default = "The third page is fun!"
page_4_lbl_default = "The fourth page is where it's at"

online_time_present = None
aio_username = None
aio_key = None

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

# Get our username, key and desired timezone
aio_username = secrets["aio_username"]
aio_key = secrets["aio_key"]
location = secrets.get("timezone", None)

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
    active_tab_text_color=0x00AA59,
    inactive_tab_text_color=0xEEEEEE,
    inactive_tab_transparent_indexes=(0, 1),
    active_tab_transparent_indexes=(0, 1),
    tab_count=4,
)

# make 3 pages of content
page_1_group = displayio.Group()
page_2_group = displayio.Group()
page_3_group = displayio.Group()
page_4_group = displayio.Group()

# labels
page_1_lbl = Label(
    font=terminalio.FONT,
    scale=2,
    text="This is the first page!",
    anchor_point=(0, 0),
    anchored_position=(10, 10),
)
page_1_lbl2 = Label(
    font=terminalio.FONT,
    scale=2,
    text="Please wait...",
    anchor_point=(0, 0),
    anchored_position=(10, 150),
)
page_2_lbl = Label(
    font=terminalio.FONT,
    scale=2,
    text="This page is the second page!",
    anchor_point=(0, 0),
    anchored_position=(10, 10),
)
page_3_lbl = Label(
    font=terminalio.FONT,
    scale=2,
    text=page_3_lbl_default,  # Will be "Date/time:"
    anchor_point=(0, 0),
    anchored_position=(10, 10),
)
page_3_lbl2 = Label(
    font=terminalio.FONT,
    scale=2,
    text="",  # page_3_lbl2_default,   # Will be DD-MO-YYYY or Month-DD-YYYY
    anchor_point=(0, 0),
    anchored_position=(10, 40),
)
page_3_lbl3 = Label(
    font=terminalio.FONT,
    scale=2,
    text="",  # page_3_lbl3_default,  # Will be HH:MM:SS
    anchor_point=(0, 0),
    anchored_position=(10, 70),
)
page_4_lbl = Label(
    font=terminalio.FONT,
    scale=2,
    text=page_4_lbl_default,
    anchor_point=(0, 0),
    anchored_position=(10, 10),
)
page_4_lbl2 = Label(
    font=terminalio.FONT,
    scale=2,
    text="",  # Will be "Temperature"
    anchor_point=(0, 0),
    anchored_position=(10, 130),
)
page_4_lbl3 = Label(
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
page_1_group.append(square)
page_1_group.append(page_1_lbl)
page_1_group.append(page_1_lbl2)
page_2_group.append(page_2_lbl)
page_2_group.append(circle)
page_3_group.append(page_3_lbl)
page_3_group.append(page_3_lbl2)
page_3_group.append(page_3_lbl3)
page_3_group.append(triangle)
page_4_group.append(page_4_lbl)
page_4_group.append(page_4_lbl2)
page_4_group.append(page_4_lbl3)
page_4_group.append(rectangle)

pages = {0: "One", 1: "Two", 2: "Thr", 3: "For"}

# add the pages to the layout, supply your own page names
test_page_layout.add_content(page_1_group, pages[0])
test_page_layout.add_content(page_2_group, pages[1])
test_page_layout.add_content(page_3_group, pages[2])
test_page_layout.add_content(page_4_group, pages[3])

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
another_text = Label(terminalio.FONT, text="And another thing!", scale=2, color=0x00ff00, anchor_point=(0, 0),
                     anchored_position=(100, 100))
test_page_layout.showing_page_content.append(another_text)
"""
print("starting loop")

temp_update_cnt = 0
old_temp = 0.00


def get_local_timestamp(location=None):
    global online_time_present, default_dt

    # pylint: disable=line-too-long
    """Fetch and "set" the local time of this microcontroller to the local time at the location, using an internet time API.
    :param str location: Your city and country, e.g. ``"New York, US"``.
    """
    # pylint: enable=line-too-long
    api_url = None
    try:
        aio_username = secrets["aio_username"]
        aio_key = secrets["aio_key"]
    except KeyError:
        raise KeyError(
            "\n\nOur time service requires a login/password to rate-limit. Please register for a free adafruit.io account and place the user/key in your secrets file under 'aio_username' and 'aio_key'"
        )  # pylint: disable=line-too-long

    location = secrets.get("timezone", location)
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

    except KeyError:
        raise KeyError(
            "Was unable to lookup the time, try setting secrets['timezone'] according to http://worldtimeapi.org/timezones"
        )  # pylint: disable=line-too-long

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
  If reconnected this function sets the global variable temp_sensor_present
  If failed to reconnect the function clears temp_sensor_present
"""


def connect_temp_sensor():
    global temp_sensor_present, tmp117, t0, t1, t2
    t = "temperature sensor found"
    temp_sensor_present = False
    tmp117 = None

    try:
        tmp117 = adafruit_tmp117.TMP117(i2c)
    except ValueError:  # ValueError occurs if the temperature sensor is not connected
        pass

    if tmp117 is not None:
        temp_sensor_present = True

    if temp_sensor_present:
        print(t)
        print("temperature sensor connected")
        t0 = "Temperature"
        t1 = degs_sign + "C"
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
    global rtc_present, i2c, rtc, lStart, default_dt
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


"""
   Function gets a value from the external temperature sensor
   It only updates if the value has changed compared to the previous value
   If no value obtained (for instance if the sensor is disconnected) the function sets the page_4 label to a default text
"""


def get_temp(cnt):
    global temp_sensor_present, old_temp, tmp117, page_4_lbl, page_4_lbl2, page_4_lbl3, temp_shown_in_REPL
    showing_page_idx = test_page_layout.showing_page_index
    RetVal = False
    if temp_sensor_present:
        try:
            # Display temperature only after at least one time the standard page_4_lbl_default has been displayed
            # if cnt >= 3 and showing_page_idx == 3: # show temperature on most right Tab page
            # if cnt > 0 and cnt % 5 == 0:  # show temp only after from loop 6 and then every 5 loops
            temp = tmp117.temperature
            t = "{:5.2f} ".format(temp) + t1
            if my_debug and temp is not None and not temp_shown_in_REPL:
                temp_shown_in_REPL = True
                print("get_temp(): {} {}".format(t0, t))
            if showing_page_idx == 3:  # show temperature on most right Tab page
                if temp is not None:
                    if (
                        temp != old_temp
                    ):  # Only update if there is a change in temperature
                        old_temp = temp
                        t = "{:5.2f} ".format(temp) + t1
                        page_4_lbl.text = ""
                        page_4_lbl2.text = t0
                        page_4_lbl3.text = t
                        # if not my_debug:
                        # print("page_4_lbl.text = {}".format(page_4_lbl.text))
                        # time.sleep(2)
                        RetVal = True
                else:
                    t = ""
                    page_4_lbl.text = page_4_lbl_default
        except OSError:
            print("Temperature sensor has disconnected")
            t = ""
            temp_sensor_present = False
            tmp117 = None
            page_4_lbl.text = page_4_lbl_default  # clean the line  (eventually: t2)
            page_4_lbl2.text = ""
            page_4_lbl3.text = ""

    return RetVal


yy = 0
mo = 1
dd = 2
hh = 3
mm = 4
ss = 5


"""
   Function gets the date and time:
   a) if an rtc is present from the rtc;
   b) if using online NTP pool server then get the date and time from the function time.localtime
   This time.localtime has before been set with data from the NTP server.
   In both cases the date and time will be set to the page3_lbl, lbl12 and lbl3
   If no (valid) date and time has been received then a default text will be shown on the page3_lbl
"""


def get_dt():
    global rtc_present, rtc, use_txt_in_month, use_usa_notation, page_3_lbl, page_3_lbl2, page_3_lbl3, online_time_present, use_ntp, old_seconds, current_seconds, dt_refresh, sDT_old, ntp_refresh, nHH_old
    dt = None
    RetVal = False
    s = "Date/time: "
    if rtc_present:
        try:
            dt = rtc.datetime
        except OSError as exc:
            if my_debug:
                print("Error number: ", exc.args[0])
            if exc.args[0] == 5:  # Input/output error
                rtc_present = False
                print("get_dt(): OSError occurred. RTC probably is disconnected")
                page_3_lbl.text = page_3_lbl_default
                return RetVal
            raise  # Handle other errors
    elif online_time_present or use_ntp:
        dt = time.localtime()
    if dt is not None:
        sYY = str(dt[yy])
        if use_txt_in_month:
            sMO = months[dt[mo]]
        else:
            if dt[mo] < 10:
                sMO = "0" + str(dt[mo])
            else:
                sMO = str(dt[mo])
        if dt[dd] < 10:
            sDD = "0" + str(dt[dd])
        else:
            sDD = str(dt[dd])
        if dt[hh] < 10:
            sHH = "0" + str(dt[hh])
        else:
            sHH = str(dt[hh])
        if not rtc_present:
            if nHH_old != dt[hh]:
                nHH_old = dt[hh]
                ntp_refresh = True

        if dt[mm] < 10:
            sMM = "0" + str(dt[mm])
        else:
            sMM = str(dt[mm])
        if dt[ss] < 10:
            sSS = "0" + str(dt[ss])
        else:
            sSS = str(dt[ss])
        current_seconds = dt[ss]
        if use_usa_notation:
            sDT = sMO + "-" + sDD + "-" + sYY
        else:
            sDT = sYY + "-" + sMO + "-" + sDD
        if sDT_old != sDT:
            sDT_old = sDT
            dt_refresh = True  # The date has changed, set the refresh flag
        sDT2 = sHH + ":" + sMM + ":" + sSS

        if dt_refresh:  # only refresh when needed
            dt_refresh = False
            page_3_lbl.text = s
            page_3_lbl2.text = sDT

        if current_seconds != old_seconds:
            old_seconds = current_seconds
            sDT3 = s + "{} {}".format(sDT, sDT2)
            print(sDT3)

            page_3_lbl3.text = sDT2
            if my_debug:
                print("page_3_lbl.text = {}".format(page_3_lbl.text))
                print("page_3_lbl2.text = {}".format(page_3_lbl2.text))
                print("page_3_lbl3.text = {}".format(page_3_lbl3.text))
            RetVal = True

        # Return from here with a False but don't set the page_3_lbl to default.
        # It is only to say to the loop() that we did't update the datetime
    else:
        page_3_lbl.text = page_3_lbl_default
        page_3_lbl2.text = ""
        page_3_lbl3.text = ""

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

            if temp_sensor_present:
                get_temp(cnt)
            else:
                connect_temp_sensor()

            cnt += 1
            if cnt > 999:
                cnt = 0
            # change page by next page function. It will loop by default
            time.sleep(2)
            test_page_layout.next_page()
        except KeyboardInterrupt:
            print("Keyboard interrupt...exiting...")
            raise SystemExit


if __name__ == "__main__":
    main()
