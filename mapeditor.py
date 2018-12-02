#!/usr/bin/env python3

from src.worldmap import Plane
from src.tileManager import TileManager
from src.recipe import Recipe, RecipeManager
from src.position import Position
from src.item import Item, ItemManager
from src.command import Command
from src.blueprint import Blueprint
from src.action import Action
from Mastermind._mm_client import MastermindClientTCP
import argparse
import json
import math
import os
import sys
import time
from collections import defaultdict

import pyglet
import glooey
from pyglet.window import key as KEY
from pyglet import clock
from src.passhash import hashPassword
from src.character import Character

# load all the resources we can use and index them.

for folder in [
    # load tileset resources
    "tiles/grassland/bg",
    "tiles/grassland/fg",
    "tiles/grassland/objects",
    "tiles/items",
    "tiles/containers"
    "tiles/monsters",
    "tiles/terrain",

    # load UI graphicss
    "gfx/inputbox",
    "gfx/background",
    "gfx/scrollbox/vbar/backward",
    "gfx/scrollbox/vbar/forward",
    "gfx/scrollbox/vbar/decoration",
    "gfx/scrollbox/vbar/grip",
    "gfx/scrollbox/frame/decoration",
]:
    pyglet.resource.path.append(folder)
    print("Loaded resource folder", folder)

pyglet.resource.reindex()

class CustomInputBox(glooey.Form):
    custom_alignment = "center"
    custom_height_hint = 12

    class Label(glooey.EditableLabel):
        custom_font_size = 10
        custom_color = "#b9ad86"
        custom_alignment = "center"
        custom_horz_padding = 4
        custom_top_padding = 2
        custom_width_hint = 200
        custom_height_hint = 12
        # TODO: import string; def format_alpha(entered_string): return "".join(char for char in entered_string if char in string.ascii_letters) # only allow valid non-space asicii

    class Base(glooey.Background):
        custom_center = pyglet.resource.texture("form_center.png")
        custom_left = pyglet.resource.image("form_left.png")
        custom_right = pyglet.resource.image("form_right.png")


class CustomScrollBox(glooey.ScrollBox):
    # custom_alignment = 'center'
    custom_size_hint = 300, 200
    custom_height_hint = 200

    class Frame(glooey.Frame):
        class Decoration(glooey.Background):
            custom_center = pyglet.resource.texture("scrollbox_center.png")

        class Box(glooey.Bin):
            custom_horz_padding = 2

    class VBar(glooey.VScrollBar):
        class Decoration(glooey.Background):
            custom_top = pyglet.resource.image("bar_top.png")
            custom_center = pyglet.resource.texture("bar_vert.png")
            custom_bottom = pyglet.resource.image("bar_bottom.png")

        class Forward(glooey.Button):
            class Base(glooey.Image):
                custom_image = pyglet.resource.image("forward_base.png")

            class Over(glooey.Image):
                custom_image = pyglet.resource.image("forward_over.png")

            class Down(glooey.Image):
                custom_image = pyglet.resource.image("forward_down.png")

        class Backward(glooey.Button):
            class Base(glooey.Image):
                custom_image = pyglet.resource.image("backward_base.png")

            class Over(glooey.Image):
                custom_image = pyglet.resource.image("backward_over.png")

            class Down(glooey.Image):
                custom_image = pyglet.resource.image("backward_down.png")

        class Grip(glooey.ButtonScrollGrip):
            class Base(glooey.Background):
                custom_top = pyglet.resource.image("grip_top_base.png")
                custom_center = pyglet.resource.texture("grip_vert_base.png")
                custom_bottom = pyglet.resource.image("grip_bottom_base.png")

            class Over(glooey.Background):
                custom_top = pyglet.resource.image("grip_top_over.png")
                custom_center = pyglet.resource.texture("grip_vert_over.png")
                custom_bottom = pyglet.resource.image("grip_bottom_over.png")

            class Down(glooey.Background):
                custom_top = pyglet.resource.image("grip_top_down.png")
                custom_center = pyglet.resource.texture("grip_vert_down.png")
                custom_bottom = pyglet.resource.image("grip_bottom_down.png")

class MapTile(glooey.Label):
    custom_height_hint = 16
    custom_width_hint = 32

    # custom_alignment = 'fill'
    # because they way they stack make height and width

    def __init__(self, x, y):
        super().__init__(str(x) + '_' + str(y)) #pyglet.resource.image("t_grass.png"))
        self.x = x
        self.y = y

        @self.event
        def on_mouse_release(x, y, button, modifiers):
            # did we click a tile? then select it. if not ignore. 
            print(self.x, self.y)
            self.get_parent().selected_tile = self
            print(self.get_parent().selected_tile)

       
        
        
# maps are loaded as planes
# on load load the whole map directory.
# move chunk postions with wasd
class mainWindow(glooey.containers.Board):
    def __init__(self):
        super().__init__()
        self.selected_tile = None
        self.tile_half_width, self.tile_half_height = 32, 16

        self.chunk_size = (25, 25)  # the only tuple you'll see I swear.

        # chunk_size + tilemap size
        self.map_grid = glooey.Board() # self.chunk_size[0], self.chunk_size[1], 32, 64)

        for i in range(self.chunk_size[0]):
            for j in range(self.chunk_size[1]):
                # before update we need to init the map with grass.
                # 0,0 = tile_half_width, tile_half_height
                # 2,1 = 64, 16 
                
                x = 786 - self.tile_half_width + ((i * self.tile_half_width) - (j * self.tile_half_width))
                y = 786 - self.tile_half_height - ((i * self.tile_half_height) + (j * self.tile_half_height))
                # print('trying',x,y)
                mp = MapTile(i, j)
               
                self.map_grid.add(widget=mp,rect=glooey.Rect(x, y, 32, 16))

        bg = glooey.Background()
        bg.set_appearance(
            center=pyglet.resource.texture("center.png"),
            top=pyglet.resource.texture("top.png"),
            bottom=pyglet.resource.texture("bottom.png"),
            left=pyglet.resource.texture("left.png"),
            right=pyglet.resource.texture("right.png"),
            top_left=pyglet.resource.texture("top_left.png"),
            top_right=pyglet.resource.texture("top_right.png"),
            bottom_left=pyglet.resource.texture("bottom_left.png"),
            bottom_right=pyglet.resource.texture("bottom_right.png"),
        )

        self.add(widget=bg,rect=glooey.Rect(0, 0, 1800, 1000))
        self.add(widget=self.map_grid,rect=glooey.Rect(0, 0, 1600, 800))
    
        
        


class MapEditor:  # extends MastermindClientTCP
    def __init__(self):
        self.window = pyglet.window.Window(1800, 1000)

        pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
        pyglet.gl.glBlendFunc(pyglet.gl.GL_SRC_ALPHA,
                              pyglet.gl.GL_ONE_MINUS_SRC_ALPHA)

        self.gui = glooey.Gui(self.window)

        self.gui.add(mainWindow())


#
#   if we start a client directly
#
if __name__ == "__main__":
     

    mapeditor = MapEditor()

    pyglet.app.event_loop.run()  # main event loop starts here.
