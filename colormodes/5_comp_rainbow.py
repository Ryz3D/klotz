# rainbow color in the top left and its complementary bottom right


def color(base, time, x, y, **kwargs):
    comp_base = base[0] + time * 10 + x * 40 + y * 10
    if y < 1.25 * (x - 0.1):
        return (comp_base + 180, base[1], base[2])
    else:
        return (comp_base, base[1], base[2])
