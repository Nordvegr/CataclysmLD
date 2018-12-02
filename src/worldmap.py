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
        # the plane the exit is on.
        self.plane = plane
        # the position on the plane this leads to.
        self.position = position
        

class Chunk:
    # x, y relate to it's position on the plane
    def __init__(self, x, y, chunk_size=25):
        self.tiles = []
        self.weather = "WEATHER_NONE"  # weather is per chunk.
        self.bigmap_tile = "open_air"  # the tile represented on the players big map
        # set this to true to have the changes updated on the disk, default is True so worldgen writes it to disk
        self.is_dirty = (True)
        # start = time.time()
        for i in range(chunk_size):  # 0-25
            for j in range(chunk_size):  # 0-25
                tiledict = {}
                tiledict["position"] = Position(
                    i + int(x * chunk_size), j + int(y * chunk_size))
                # this position is on the plane. no position is ever repeated on a plane. each chunk tile gets its own position.
                tiledict["terrain"] = Terrain("t_dirt")  # make the earth
                # Creature() # one creature per tile
                tiledict["creature"] = None
                tiledict["items"] = list()  # can be more then one item in a tile.
                tiledict["trap"] = None  # one per tile
                # used in lightmap calculations, use 1 for base so we never have total darkness.
                tiledict["lumens"] = 1
                # exits lead to other planes or instances.
                # create two-way exits by default.
                # one exit per tile
                tiledict["exit"] = None 
                # flags are special things that the tile does.
                # dict so we can pass kwargs
                tiledict["flags"] = dict()
                self.tiles.append(tiledict)
        # end = time.time()
        # duration = end - start
        # print('chunk generation took: ' + str(duration) + ' seconds.')


class Plane:
    # let's make the plane map and fill it with chunks!

    # size in chunks along one axis.
    def __init__(self, name, total_chunks=900):
        self.name = name
        self.total_chunks = total_chunks
        self.chunk_dist_xy = int(math.sqrt(total_chunks))
        self._log = logging.getLogger("plane_" + str(name))
        self.PLANE = defaultdict(dict)  # dict of dicts for chunks
        start = time.time()
        # TODO: only need to load the chunks where there are actual Characters present in memory after generation.
        self._log.debug("creating/loading plane chunks")
        for i in range(self.chunk_dist_xy):
            for j in range(self.chunk_dist_xy):
                path = str(
                    "./planes/"
                    + self.name
                    + "/"
                    + str(i)
                    + "_"
                    + str(j)
                    + ".chunk"
                )
                # load it.
                if os.path.isfile(path):
                    with open(path, "rb") as fp:
                        self.PLANE[i][j] = pickle.load(fp)
                        self.PLANE[i][j].was_loaded = "yes"
                else:
                    self.PLANE[i][j] = Chunk(i, j)
                    with open(path, "wb") as fp:
                        pickle.dump(self.PLANE[i][j], fp)

        end = time.time()
        duration = end - start
        self._log.debug("---------------------------------------------")
        self._log.debug("World generation took: {} seconds".format(duration))

    def get_chunk_by_position(self, position):
        tile = self.get_tile_by_position(
            position
        )  # check and see if it exists if not create it.
        x_count = 0  #
        x = position.x
        # print(position)
        while x >= self.chunk_size:
            x = x - self.chunk_size
            x_count = x_count + 1

        y_count = 0  #
        y = position.y
        # plane[x][y].tiles
        while y >= self.chunk_size:
            y = y - self.chunk_size
            y_count = y_count + 1

        z = position.z

        # self._log.debug('getting chunk {} {}'.format(x_count, y_count))
        return self.PLANE[x_count][y_count][z]

    def get_all_tiles(self):
        ret = []
        self._log.debug("getting all tiles")
        for i, dictionary_x in self.PLANE.items():
            for j, dictionary_y in dictionary_x.items():
                for k, chunk in dictionary_y.items():
                    for tile in chunk.tiles:
                        ret.append(tile)
        self._log.debug("all tiles: {}".format(len(ret)))
        return ret  # expensive function. use sparingly.

    def get_tile_by_position(self, position):
        x_count = 0  # these two little loop gets us the right chunk FAST
        x = position.x
        while x >= self.chunk_size:
            x = x - self.chunk_size
            x_count = x_count + 1

        y_count = 0  #
        y = position.y
        while y >= self.chunk_size:
            y = y - self.chunk_size
            y_count = y_count + 1

        z = position.z

        try:
            for tile in self.PLANE[x_count][y_count][z].tiles:
                if tile["position"] == position:
                    return tile
            else:
                raise Exception("FATAL ERROR: couldn't find chunk for tile")
        except Exception:
            # if it doesn't exist yet (exception) we need to create it and return it.
            self.PLANE[x_count][y_count][z] = Chunk(
                x_count, y_count, self.chunk_size
            )
            path = str(
                "./planes/default/"
                + str(x_count)
                + "_"
                + str(y_count)
                + "_"
                + str(z)
                + ".chunk"
            )
            with open(path, "wb") as fp:
                pickle.dump(self.PLANE[x_count][y_count][z], fp)
                for tile in self.PLANE[x_count][y_count][z].tiles:
                    if tile["position"] == position:
                        return tile
                else:
                    raise Exception(
                        "ERROR: Could not find tile or create it. (this should never happen)"
                    )

    def get_chunks_near_position(self, position):  # a localmap
        chunks = []
        # we should only need the 9 chunks around the chunk position
        x = position.x
        y = position.y
        z = position.z

        north_east_chunk = self.get_chunk_by_position(
            Position(x + self.chunk_size, y + self.chunk_size)
        )
        chunks.append(north_east_chunk)
        north_chunk = self.get_chunk_by_position(
            Position(x + self.chunk_size, y))
        chunks.append(north_chunk)
        north_west_chunk = self.get_chunk_by_position(
            Position(x + self.chunk_size, y - self.chunk_size)
        )
        chunks.append(north_west_chunk)
        west_chunk = self.get_chunk_by_position(
            Position(x, y - self.chunk_size))
        chunks.append(west_chunk)
        mid_chunk = self.get_chunk_by_position(Position(x, y))
        chunks.append(mid_chunk)
        east_chunk = self.get_chunk_by_position(
            Position(x, y + self.chunk_size))
        chunks.append(east_chunk)
        south_west_chunk = self.get_chunk_by_position(
            Position(x - self.chunk_size, y - self.chunk_size)
        )
        chunks.append(south_west_chunk)
        south_chunk = self.get_chunk_by_position(
            Position(x - self.chunk_size, y))
        chunks.append(south_chunk)
        south_east_chunk = self.get_chunk_by_position(
            Position(x - self.chunk_size, y + self.chunk_size)
        )
        chunks.append(south_east_chunk)

        # up_chunk = self.get_chunk_by_position(Position(x, y+1))
        # chunks.append(up_chunk)

        # down_chunk = self.get_chunk_by_position(Position(x, y-1))
        # chunks.append(down_chunk)

        return chunks

    def get_character(self, ident):
        # print('ident:' + str(ident))
        for tile in self.get_all_tiles():
            if tile["creature"] is not None and tile["creature"].name == ident:
                print("found player:" + tile["creature"].name)
                return tile["creature"]
        else:
            return None

    def put_object_at_position(
        self, obj, position
    ):  # attempts to take any object (creature, item, furniture) and put it in the right spot in the PLANE
        # TODO: check if something is already there. right now it just replaces it
        tile = self.get_tile_by_position(position)
        # print(tile)
        self.get_chunk_by_position(position).is_dirty = True
        if isinstance(obj, (Creature, Character, Monster)):
            tile["creature"] = obj
            return
        elif isinstance(obj, Terrain):
            tile["terrain"] = obj
            # tile = self.get_tile_by_position(position)
            # print(tile['terrain'])
            return
        elif isinstance(obj, Item):
            items = tile["items"]  # which is []
            items.append(obj)
            return
        elif isinstance(obj, Furniture):
            tile["furniture"] = obj
            return
        elif isinstance(
            obj, Blueprint
        ):  # a blueprint takes up the slot that the final object is. e.g Terrain blueprint takes up the Terrain slot in the world map.
            # print('isinstance blueprint')
            # print(obj.type_of)
            # print(str(obj.type_of))
            if obj.type_of == "Terrain":
                tile["terrain"] = obj
                return
            elif obj.type_of == "Item":
                items = tile["items"]  # which is []
                items.append(obj)
                self._log.debug("added blueprint for an Item.")
                return
            elif obj.type_of == "Furniture":
                tile["furniture"] = obj
                return

        # TODO: the rest of the types.

    def build_json_building_at_position(
        self, filename, position
    ):  # applys the json file to world coordinates. can be done over multiple chunks.
        self._log.debug("building: {} at {}".format(filename, position))
        start = time.time()
        # TODO: fill the chunk overmap tile with this om_terrain
        with open(filename) as json_file:
            data = json.load(json_file)
        # print(data)
        # group = data['group']
        # overmap_terrain = data['overmap_terrain']
        floors = data["floors"]
        # print(floors)
        terrain = data["terrain"]  # list
        furniture = data["furniture"]  # list
        fill_terrain = data["fill_terrain"]  # string

        impassable_tiles = ["t_wall"]  # TODO: make this global
        for k, floor in floors.items():
            # print(k)
            i, j = 0, 0
            for row in floor:
                i = 0
                for char in row:
                    # print(char)
                    # print(terrain)
                    impassable = False
                    t_position = Position(position.x + i, position.y + j)
                    self.put_object_at_position(
                        Terrain(fill_terrain, impassable), t_position
                    )  # use fill_terrain if unrecognized.
                    if char in terrain:
                        # print('char in terrain')
                        if terrain[char] in impassable_tiles:
                            impassable = True
                        # print('placing: ' + str(terrain[char]))
                        self.put_object_at_position(
                            Terrain(terrain[char], impassable), t_position
                        )
                    elif char in furniture:
                        # print('placing: ' + str(furniture[char]))
                        self.put_object_at_position(
                            Furniture(furniture[char]), t_position
                        )
                    else:
                        # print('placed : ' + str(fill_terrain))
                        pass
                    i = i + 1
                j = j + 1
        end = time.time()
        duration = end - start
        self._log.debug(
            "Building {} took: {} seconds.".format(filename, duration))

    def move_object_from_position_to_position(self, obj, from_position, to_position):
        from_tile = self.get_tile_by_position(from_position)
        to_tile = self.get_tile_by_position(to_position)
        if to_tile is None or from_tile is None:
            self._log.error(
                "tile doesn't exist. This should NEVER get called. get_tile_by_position creates a new chunk and tiles if we need it."
            )
            return False
        if from_position.z != to_position.z:  # check for stairs.
            if from_position.z < to_position.z:
                if from_tile["terrain"].ident != "t_stairs_up":
                    print("no up stairs there")
                    return False
            elif from_position.z > to_position.z:
                if from_tile["terrain"].ident != "t_stairs_down":
                    print("no down stairs there")
                    return False
        # print(self.get_chunk_by_position(to_position).is_dirty)
        self.get_chunk_by_position(from_position).is_dirty = True
        self.get_chunk_by_position(to_position).is_dirty = True
        # print(self.get_chunk_by_position(to_position).is_dirty)
        if isinstance(obj, (Creature, Character, Monster)):
            self._log.debug(
                "moving {} from {} to {}.".format(
                    obj, from_position, to_position)
            )
            if to_tile["terrain"].impassable:
                self._log.debug("tile is impassable")
                return False
            if (
                to_tile["creature"] is not None
            ):  # don't replace creatures in the tile if we move over them.
                self._log.debug("creature is impassable")
                return False
            to_tile["creature"] = obj
            from_tile["creature"] = None
            return True
        if isinstance(obj, Terrain):
            to_tile["terrain"] = obj
            return True
        if obj is Item:
            print(
                "Moving "
                + str(obj)
                + " from "
                + str(from_tile["position"])
                + " to "
                + str(to_tile["position"])
            )
            # iterate a copy to remove properly.
            if obj in from_tile["items"][:]:
                # items = tile['item'] # which is []
                from_tile["items"].remove(obj)
                to_tile["items"].append(obj)
            else:
                pass
            return True
        if obj is Furniture:
            if to_tile["furniture"] is not None:
                self._log.debug("already furniture there.")
                return False
            to_tile["furniture"] = obj
            from_tile["furniture"] = None
            return True
        # TODO: the rest of the types.

    def bash(
        self, object, position
    ):  # catch-all for bash/smash (can probably use this for vehicle collisions aswell) object is object that is doing the bashing
        # since we bash in a direction we need to check what's in the tile and go from there.
        # both furniture and terrain can be bashed but we should assume that the player wants to bash the furniture first then terrain we will go in that order.
        tile = self.get_tile_by_position(position)
        terrain = tile["terrain"]
        # strength = creature strength.
        if tile["furniture"] is not None:
            furniture_type = self.FurnitureManager.FURNITURE_TYPES[
                tile["furniture"].ident
            ]
            # print(tile['furniture'])
            for item in furniture_type["bash"]["items"]:
                print(item)
                print(str(self.ItemManager.ITEM_TYPES[str(item["item"])]))
                self.put_object_at_position(
                    Item(
                        self.ItemManager.ITEM_TYPES[str(
                            item["item"])]["ident"],
                        self.ItemManager.ITEM_TYPES[str(item["item"])],
                    ),
                    position,
                )  # need to pass the reference to load the item with data.
            tile["furniture"] = None
            # get the 'bash' dict for this object from furniture.json
            # get 'str_min'
            # if player can break it then delete the furniture and add the bash items from it to the tile.
            return
        if terrain is not None:
            # pprint(terrain['bash'])
            # get the 'bash' dict for this object from terrain.json if any
            # if dict is not None:
            # get 'str_min'
            # if player can break it then delete the terrain and add the bash terrain from it to the tile.
            return
        return

    # the object doing the opening.
    def furniture_open(self, object, position):
        tile = self.get_tile_by_position(position)
        furniture = tile["furniture"]
        if furniture is not None:
            if "open" in furniture:  #
                # replace this furniture with the open version.
                # make sure to copy any items in it to the new one.
                pass
        else:
            return False
        return

    # the object doing the opening.
    def furniture_close(self, object, position):
        tile = self.get_tile_by_position(position)
        furniture = tile["furniture"]
        if furniture is not None:
            if "close" in furniture:  #
                # replace this furniture with the closed version.
                # make sure to copy any items in it to the new one.
                pass
        else:
            return False
        return

    def get_tiles_near_position(self, position, radius):
        # figure out a way to get all tile positions near a position so we can get_tile_by_position on them.
        ret_tiles = []
        for i in range(position.x - radius, position.x + radius + 1):
            for j in range(position.y - radius, position.y + radius + 1):
                dx = position.x - i
                dy = position.y - j
                distance = max(abs(dx), abs(dy))
                # distance = int(abs(position.x) + abs(i)) - int(abs(position.y) + abs(j)) # 1,2 to 2,4 would be distance 2. we'll see how this looks
                # print(distance)
                ret_tiles.append(
                    (self.get_tile_by_position(Position(i, j)), distance)
                )
        return ret_tiles

    # we use this in pathfinding.
    def get_adjacent_positions_non_impassable(self, position):
        ret_tiles = []
        tile0 = self.get_tile_by_position(
            Position(position.x + 1, position.y)
        )
        tile1 = self.get_tile_by_position(
            Position(position.x - 1, position.y)
        )
        tile2 = self.get_tile_by_position(
            Position(position.x, position.y + 1)
        )
        tile3 = self.get_tile_by_position(
            Position(position.x, position.y - 1)
        )

        if not tile0["terrain"].impassable:
            ret_tiles.append(tile0["position"])
        if not tile1["terrain"].impassable:
            ret_tiles.append(tile1["position"])
        if not tile2["terrain"].impassable:
            ret_tiles.append(tile2["position"])
        if not tile3["terrain"].impassable:
            ret_tiles.append(tile3["position"])

        return ret_tiles
