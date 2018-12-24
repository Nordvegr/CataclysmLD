import json
import os
import pickle
import pprint
import random
import time
import logging
import math
from collections import defaultdict

from src.blueprint import Blueprint
from src.creature import Creature
from src.furniture import Furniture, FurnitureManager
from src.item import Item, ItemManager
from src.lighting import Lighting
from src.monster import Monster
from src.character import Character
from src.position import Position
from src.terrain import Terrain

# weather_types = [clear, rain, fog, storm]


class Exit:
    def __init__(self, plane, position):
        # the plane the exit leads too.
        self.plane = plane
        # the position on the plane this leads to.
        self.position = position


class Chunk:
    # x, y relate to it's position on the plane
    def __init__(self, x, y, chunk_size=25):
        self.tiles = []
        self.weather = None  # weather is per chunk.
        self.bigmap_tile = "open_air"  # the tile represented on the players big map
        # set this to true to have the changes updated on the disk, default is True so worldgen writes it to disk
        self.is_dirty = (True)
        for i in range(chunk_size):  # 0-25
            for j in range(chunk_size):  # 0-25
                tiledict = {}
                tiledict["position"] = Position(
                    i + int(x * chunk_size), j + int(y * chunk_size))
                # this position is on the plane. no position is ever repeated on a plane. each chunk tile gets its own position.
                tiledict["terrain"] = Terrain("t_grass")  # make the earth
                # Creature() # one creature per tile
                tiledict["creature"] = None
                # can be more then one item in a tile.
                tiledict["items"] = list()
                # used in lightmap calculations, use 1 for base so we never have total darkness.
                tiledict["lumens"] = 1
                # exits lead to other planes or instances.
                # create two-way exits by default.
                # one exit per tile
                tiledict["exit"] = None
                # flags are special things that the tile does.
                # dict so we can pass kwargs
                # traps now go in flags (trap:electric)
                tiledict["flags"] = dict()
                self.tiles.append(tiledict)


class Plane:
    def __init__(self, name):
        self.name = name
        if(self.name == 'Overmap'):
            self.size = 25
        else:
            self.size = 1
        # size in chunks along one axis.
        self.chunks = dict()  # dict of chunks

    def create(self):
        for i in range(self.size):
            for j in range(self.size):
                self.chunks[str(i)+'_'+str(j)] = Chunk(i, j)
    
    def load_chunk_into_memory(self, x, y):
        path = "./planes/" + str(self.name) + "/" + str(i) + "_" + str(j) + ".chunk"
        if os.path.isfile(path):
            with open(path, "rb") as fp:
                self.chunks[str(i)+'_'+str(j)] = pickle.load(fp)
        else:
            raise FileNotFoundError
    
    def unload_chunk_from_memory(self, x, y):
        self.chunks[str(i)+'_'+str(j)] = None
    
    def save_chunk_to_file(self, x, y):
        if(not os.path.isdir('./planes/' + str(self.name))):
            os.mkdir('./planes/' + str(self.name))
        _path = './planes/' + str(self.name) + '/' + str(x)+'_'+str(y) + '.chunk'
        with open(_path, "wb") as fp:
            pickle.dump(self.chunks[str(x)+'_'+str(y)], fp)

    def load_all(self):
        for i in range(self.size):
            for j in range(self.size):
                path = "./planes/" + str(self.name) + "/" + str(i) + "_" + str(j) + ".chunk"
                if os.path.isfile(path):
                    with open(path, "rb") as fp:
                        self.chunks[str(i)+'_'+str(j)] = pickle.load(fp)
                else:
                    raise FileNotFoundError

    def save_all(self):
        if(not os.path.isdir('./planes/' + str(self.name))):
            os.mkdir('./planes/' + str(self.name))

        for key, chunk in self.chunks.items():
            print(key, chunk)
            _path = './planes/' + str(self.name) + '/' + key + '.chunk'
            with open(_path, "wb") as fp:
                pickle.dump(chunk, fp)
  