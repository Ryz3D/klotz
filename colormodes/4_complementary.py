# base color in the top left and its complementary bottom right


def color(base, x, y, **kwargs):
    if y < 1.25 * (x - 0.1):
        return (base[0] + 180, base[1], base[2])
    else:
        return base
