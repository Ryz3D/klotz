import os, math, time, threading, importlib, json, atexit
from helper import lerp, lerp_angle, rgb, segments
from rpi_ws281x import PixelStrip, Color
from aiohttp import web

"""
TODO:
    - kill process with only one Ctrl+C
    - (startup) animations
        - fade
        - buildup
    - chaser color (bright spot at moving x)
    - blinking option
    - color correction new/old led
    - hue changes in homekit (low brightness)
    - notifications?
    - reload after network crash
"""

settings = {
    "digits": 4,
    "fade_speed": 0.05,
    "offset_delay": 0.5,
    "seg_width": 8,
    "seg_height": 3,
    "time_zone": 1,
    "timer_blinks": 4,
}

if os.path.isfile("settings.json"):
    with open("settings.json") as settings_file:
        settings.update(json.loads(settings_file.read()))

run_loop = True

w = settings["seg_width"]
h = settings["seg_height"]
module_size = w * 3 + h * 4
module_count = settings["digits"] * module_size

new_hsv = (0.0, 0.0, 0.0)
set_hsv = (0.0, 0.0, 0.0)
powered = False

seg_indices = []
for i in range(7):
    seg_indices.extend([h, w, h, h, w, h, w][i] * [i + 1])
seg_positions = []
seg_positions.extend(map(lambda v: (0, v), range(h + 2, h * 2 + 2)))
seg_positions.extend(map(lambda v: (v, 8), range(1, w + 1)))
seg_positions.extend(map(lambda v: (9, v), range(h * 2 + 1, h + 1, -1)))
seg_positions.extend(map(lambda v: (9, v), range(h, 0, -1)))
seg_positions.extend(map(lambda v: (v, 0), range(w, 0, -1)))
seg_positions.extend(map(lambda v: (0, v), range(1, h + 1)))
seg_positions.extend(map(lambda v: (v, 4), range(1, w + 1)))

available_cmodes = []
available_dmodes = []
current_cmode = 0
current_dmode = 0
color_mode = lambda **kwargs: (0, 0, 0)
data_mode = lambda **kwargs: "0000"
data_override = ""

timer_start = 0
timer_length = 0

if os.path.isfile("last_data.json"):
    with open("last_data.json") as save_file:
        d = json.loads(save_file.read())
        new_hsv = tuple(map(lambda s: float(s), d["color"].split(" ")))
        powered = d["powered"] == 1
        current_cmode = d["cmode"]
        current_dmode = d["dmode"]


led = PixelStrip(module_count, 18, 400000, 10, True, 255, 0)
led.begin()

for i in range(module_count):
    led.setPixelColor(i, Color(0, 0, 0))
led.show()


def timer_to_str(include_dots=False):
    global timer_length

    delta = timer_length - time.time() + timer_start
    if delta >= 60:
        mm = math.floor(delta / 60)
        ss = math.floor(delta - mm * 60)
        return str(mm).zfill(2) + (":" if include_dots else "") + str(ss).zfill(2)
    elif delta > 0:
        ss = math.floor(delta)
        ms = math.floor((delta - ss) * 100.0) / 100.0
        if ms != 0:
            return (
                str(ss).zfill(2)
                + ("." if include_dots else "")
                + str(ms)[2:].ljust(2, "0")
            )
        else:
            return str(ss).zfill(2) + ("." if include_dots else "") + "00"
    else:
        for rep in range(settings["timer_blinks"]):
            for i in range(module_count):
                led.setPixelColor(i, Color(255, 255, 255))
            led.show()
            led.show()
            time.sleep(0.5)
            for i in range(module_count):
                led.setPixelColor(i, Color(0, 0, 0))
            led.show()
            led.show()
            time.sleep(0.4)
        timer_length = 0
        set_hsv = (0, 0, 0)
        return ""


def loop():
    global set_hsv
    global new_hsv

    data_offset = 0
    last_offset = 0

    while run_loop:
        loop_time = time.time() + settings["time_zone"] * 3600

        fade_to = new_hsv if powered else (set_hsv[0], set_hsv[1], 0)
        set_hsv = (
            lerp_angle(set_hsv[0], fade_to, settings["fade_speed"]),
            lerp(set_hsv[1], fade_to, settings["fade_speed"]),
            lerp(set_hsv[2], fade_to, settings["fade_speed"]),
        )
        timer_str = "" if timer_length == 0 else timer_to_str()
        data = (
            data_override
            or timer_str
            or data_mode(
                time=loop_time,
            )
        )
        if data_override:
            pass
        elif timer_str:
            data = data[:2]
        else:
            if loop_time % 4 < 2:
                data = data[:2]
            else:
                data = data[2:]
        if len(data) <= settings["digits"]:
            data_offset = 0
            last_offset = loop_time
        elif loop_time - last_offset > settings["offset_delay"]:
            data_offset += 1
            if data_offset > len(data) + settings["digits"]:
                data_offset = 0
            last_offset = loop_time

        for digit in range(settings["digits"]):
            if digit + data_offset < 0 or digit + data_offset >= len(data):
                seg_powered = segments(" ")
            else:
                seg_powered = segments(data[digit + data_offset])
            for seg in range(module_size):
                index = digit * module_size + seg
                if seg_powered[seg_indices[seg]]:
                    digit_x = seg_positions[seg][0] / (w + 1)
                    global_pos = (
                        (digit_x + digit * 1.3) / (settings["digits"] * 1.3 - 0.3),
                        seg_positions[seg][1] / (h * 2 + 2),
                    )
                    mod = seg / module_size
                    raw_color = color_mode(
                        base=set_hsv,  # base color
                        settings=settings,  # entire settings dict
                        time=loop_time,  # unix time
                        module=mod,  # 0 to 1, position of module in strip
                        segment=seg_indices[seg],  # current segment
                        d_x=digit_x,  # 0 to 1, to left side of current digit
                        x=global_pos[0],  # 0 to 1, to left side
                        y=global_pos[1],  # 0 to 1, to bottom
                    )
                    color = rgb(360 - (raw_color[0] % 360), raw_color[1], raw_color[2])
                    led.setPixelColor(index, Color(*color))
                else:
                    led.setPixelColor(index, Color(0, 0, 0))
        led.show()
        led.show()
        time.sleep(0.01)


def load_cmode(index, force=False):
    global current_cmode
    global color_mode
    if index == -1 or index >= len(available_cmodes):
        print("colormode {} is not available".format(index + 1))
    else:
        if force or index != current_cmode:
            print("loading colormode {}".format(available_cmodes[index]))
            current_cmode = index
            module = importlib.import_module("colormodes." + available_cmodes[index])
            color_mode = module.color
        else:
            print("current colormode is already {}".format(available_cmodes[index]))


def load_dmode(index, force=False):
    global current_dmode
    global data_mode
    if index == -1 or index >= len(available_dmodes):
        print("datamode {} is not available".format(index + 1))
    else:
        if force or index != current_dmode:
            print("loading datamode {}".format(available_dmodes[index]))
            current_dmode = index
            module = importlib.import_module("datamodes." + available_dmodes[index])
            data_mode = module.data
        else:
            print("current datamode is already {}".format(available_dmodes[index]))


async def handle_cmode_get(req: web.Request):
    return web.Response(text=str(current_cmode + 1))


async def handle_cmode_set(req: web.Request):
    load_cmode(int(await req.text()) - 1)
    return web.Response(text="OK")


async def handle_dmode_get(req: web.Request):
    return web.Response(text=str(current_dmode + 1))


async def handle_dmode_set(req: web.Request):
    load_dmode(int(await req.text()) - 1)
    return web.Response(text="OK")


async def handle_color_get(req: web.Request):
    return web.Response(text="{},{},{}".format(*map(lambda s: int(s), new_hsv)))


async def handle_color_set(req: web.Request):
    global new_hsv
    new_hsv = tuple(map(lambda s: float(s), (await req.text()).split(",")))
    return web.Response(text="OK")


async def handle_power_get(req: web.Request):
    return web.Response(text="ON" if powered else "OFF")


async def handle_power_set(req: web.Request):
    global powered
    powered = await req.text() == "ON"
    return web.Response(text="OK")


async def handle_timerstr_get(req: web.Request):
    global timer_length
    now = time.time()
    if timer_length > 0 and timer_length > now - timer_start:
        return web.Response(text=timer_to_str(True))
    else:
        timer_length = 0
        return web.Response(text="0")


async def handle_timer_get(req: web.Request):
    global timer_length
    now = time.time()
    if timer_length > 0 and timer_length > now - timer_start:
        return web.Response(text=str(timer_length - now + timer_start))
    else:
        timer_length = 0
        return web.Response(text="0")


async def handle_timer_set(req: web.Request):
    global timer_start
    global timer_length
    req_val = float(await req.text())
    if req_val == -1:
        timer_length = 0
        print("timer cleared")
    elif timer_length == 0:
        timer_length = req_val
        timer_start = time.time()
        print("timer set for {}s".format(timer_length))
    return web.Response(text="OK")


async def handle_text_get(req: web.Request):
    return web.Response(text=data_override)


async def handle_text_set(req: web.Request):
    global data_override
    data_override = await req.text()
    if data_override == "clear":
        data_override = ""
        print("text cleared")
    else:
        print("displaying '{}'".format(data_override))
    return web.Response(text="OK")


@atexit.register
def atexit():
    global run_loop

    run_loop = False
    if loop_thread.is_alive():
        loop_thread.join()

    with open("last_data.json", "w") as save_file:
        save_file.write(
            json.dumps(
                {
                    "color": "{} {} {}".format(*new_hsv),
                    "powered": 1 if powered else 0,
                    "cmode": current_cmode,
                    "dmode": current_dmode,
                }
            )
        )

    print("data saved")


def start():
    global run_loop
    global loop_thread

    loop_thread = threading.Thread(target=loop)
    loop_thread.start()

    app = web.Application()
    app.add_routes(
        [
            web.get("/", lambda req: web.Response(text="OK")),
            web.get("/cmode", handle_cmode_get),
            web.put("/cmode", handle_cmode_set),
            web.get("/dmode", handle_dmode_get),
            web.put("/dmode", handle_dmode_set),
            web.get("/color", handle_color_get),
            web.put("/color", handle_color_set),
            web.get("/power", handle_power_get),
            web.put("/power", handle_power_set),
            web.get("/timerstr", handle_timerstr_get),
            web.get("/timer", handle_timer_get),
            web.put("/timer", handle_timer_set),
            web.get("/text", handle_text_get),
            web.put("/text", handle_text_set),
        ]
    )
    web.run_app(app, port=8005)


def load_available(dir):
    return list(
        filter(
            lambda x: x != "__pycache__",
            sorted(map(lambda s: s.split(".")[0], os.listdir(dir))),
        )
    )


if __name__ == "__main__":
    available_cmodes = load_available("colormodes")
    available_dmodes = load_available("datamodes")

    print("available colormodes: [{}]".format(", ".join(available_cmodes)))
    print("available datamodes: [{}]".format(", ".join(available_dmodes)))

    if len(available_cmodes) == 0:
        current_cmode = -1
        print("WARNING: no colormode, proceeding with full white")
    else:
        load_cmode(current_cmode, force=True)

    if len(available_dmodes) == 0:
        current_dmode = -1
        print("WARNING: no datamode, proceeding with 0000")
    else:
        load_dmode(current_dmode, force=True)

    start()
