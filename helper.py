def segments(char):
    bindict = {
        " ": 0b00000000,
        "_": 0b00000100,
        "-": 0b00000001,
        "/": 0b00010011,
        "^": 0b01110000,
        "0": 0b01111110,
        "1": 0b00011000,
        "2": 0b00110111,
        "3": 0b00111101,
        "4": 0b01011001,
        "5": 0b01101101,
        "6": 0b01101111,
        "7": 0b00111000,
        "8": 0b01111111,
        "9": 0b01111101,
        "a": 0b01111011,
        "b": 0b01001111,
        "c": 0b01100110,
        "d": 0b00011111,
        "e": 0b01100111,
        "f": 0b01100011,
        "g": 0b01101110,
        "h": 0b01011011,
        "i": 0b00011000,
        "j": 0b00011110,
        "k": 0b01101011,
        "l": 0b01000110,
        "m": 0b00101010,
        "n": 0b00001011,
        "o": 0b01111110,
        "p": 0b01110011,
        "q": 0b01111001,
        "r": 0b00000011,
        "s": 0b01101101,
        "t": 0b01000111,
        "u": 0b01011110,
        "v": 0b01010001,
        "w": 0b01010100,
        "x": 0b01001001,
        "y": 0b01011101,
        "z": 0b00110111,
    }
    if char.lower() in bindict:
        return [d == "1" for d in str(bin(bindict[char.lower()]))[2:].zfill(8)]
    else:
        return [False] * 8


def lerp(a, b, f):
    return a + (b - a) * f


def lerp_angle(a, b, f):
    a %= 360
    b %= 360
    d_p = (b - a) % 360
    d_n = d_p - 360
    if d_p < -d_n:
        return (a + d_p * f) % 360
    else:
        return (a + d_n * f) % 360


def rgb_conv(r, g, b):
    return (int(r * 255), int(g * 255), int(b * 255))


def rgb(h, s, v):
    h = (h / 360.0) % 1
    s /= 100.0
    v /= 100.0
    v *= v

    if s == 0.0:
        return rgb_conv(v, v, v)
    i = int(h * 6.0)
    f = (h * 6.0) - i
    p, q, t = v * (1.0 - s), v * (1.0 - s * f), v * (1.0 - s * (1.0 - f))
    i %= 6
    if i == 0:
        return rgb_conv(v, t, p)
    if i == 1:
        return rgb_conv(q, v, p)
    if i == 2:
        return rgb_conv(p, v, t)
    if i == 3:
        return rgb_conv(p, q, v)
    if i == 4:
        return rgb_conv(t, p, v)
    if i == 5:
        return rgb_conv(v, p, q)
