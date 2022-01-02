# rainbow


def color(base, time, x, y, **kwargs):
    return (base[0] + time * 10 + x * 40 + y * 10, base[1], base[2])
