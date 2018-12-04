
class Terrain:
    def __init__(self, bg, fg=None, impassable=False):
        self.bg = bg
        self.fg = fg
        self.impassable = impassable

    def __str__(self):
        return str(self.bg)