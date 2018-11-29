#!/usr/bin/env python3

import argparse
import json
import os
import random
import sys
import time
import pprint
import configparser
import logging.config
from collections import defaultdict

from Mastermind._mm_server import MastermindServerTCP
from src.action import Action
from src.blueprint import Blueprint
from src.calendar import Calendar
from src.command import Command
from src.furniture import Furniture, FurnitureManager
from src.item import Container, Item
from src.options import Options
from src.character import Character
from src.position import Position
from src.recipe import Recipe, RecipeManager
from src.terrain import Terrain
from src.profession import ProfessionManager, Profession
from src.monster import MonsterManager
from src.worldmap import Plane
from src.passhash import makeSalt


class Server(MastermindServerTCP):
    def __init__(self, config, logger=None):
        MastermindServerTCP.__init__(self, 0.5, 0.5, 300.0)
        self._config = config
        if logger == None:
            logging.basicConfig()
            self._log = logging.getLogger("root")
            self._log.warn(
                "Basic logging configuration fallback used because no logger defined."
            )

        else:
            self._log = logger

        # all the characters() that exist in the world whether connected or not.
        self.characters = dict()

        self.localmaps = dict()  # the localmaps for each character.
        self.overmaps = dict()  # the dict of all overmaps by character.name
        # self.options = Options()
        self.calendar = Calendar(0, 0, 0, 0, 0, 0)  # all zeros is the epoch
        # self.options.save()
        # create this many chunks in x and y (z is always 1 (level 0) for genning the world. we will build off that for caverns and ant stuff and z level buildings.
        self.planes = dict()

        # load the plane from the directory in the name.
        _planes_list = ['Overworld', 'Gaea', 'Lythander', 'Mostrai',
                        'Gnarg', 'Ruggilli', 'Valriel', 'Ixalovh', 'Devourers']
        for plane in _planes_list:
            self.planes[plane] = Plane(plane)

    def get_connections(self):
        return self._mm_connections

    # normally we will want to consider impassable terrain in movement calculations. Creatures that can walk or break through walls don't need to though.
    def calculate_route(self, pos0, pos1, consider_impassable=True):
        reachable = [pos0]
        explored = []

        while len(reachable) > 0:
            position = random.choice(
                reachable
            )  # get a random reachable position #TODO: be a little more intelligent about picking the best reachable position.

            # If we just got to the goal node. return the path.
            if position == pos1:
                path = []
                while position != pos0:
                    path.append(position)
                    position = position.previous
                ret_path = []
                for step in path:
                    ret_path.insert(0, step)
                return ret_path

            # Don't repeat ourselves.
            reachable.remove(position)
            explored.append(position)

            new_reachable = self.plane.get_adjacent_positions_non_impassable(
                position
            )
            for adjacent in new_reachable:
                if abs(adjacent.x - pos0.x) > 10 or abs(adjacent.y - pos0.y) > 10:
                    continue
                if adjacent not in reachable and adjacent not in explored:
                    adjacent.previous = position  # Remember how we got there.
                    reachable.append(adjacent)

        return None

    def find_spawn_point_for_new_character(self):
        _tiles = self.plane.get_all_tiles()
        random.shuffle(_tiles)  # so we all don't spawn in one corner.
        for tile in _tiles:
            if tile["terrain"].impassable:
                continue
            if tile["creature"] is not None:
                continue
            if tile["terrain"].ident == "t_open_air":
                continue

            return tile["position"]

    def handle_new_character(self, ident):
        self.characters[ident] = Character(ident)

        self.characters[ident].position = self.find_spawn_point_for_new_character()
        self.plane.put_object_at_position(
            self.characters[ident], self.characters[ident].position
        )
        self.localmaps[ident] = self.plane.get_chunks_near_position(
            self.characters[ident].position
        )

        # give the character their starting items by referencing the ProfessionManager.
        for key, value in self.ProfessionManager.PROFESSIONS[
            str(self.characters[ident].profession)
        ].items():
            # TODO: load the items into the character equipment slots as well as future things like CBMs and flags
            if key == "equipped_items":
                for equip_location, item_ident in value.items():
                    for bodypart in self.characters[ident].body_parts:
                        if bodypart.ident.split("_")[0] == equip_location:
                            if bodypart.slot0 is None:
                                if (
                                    "container_type"
                                    in self.ItemManager.ITEM_TYPES[item_ident]
                                ):
                                    bodypart.slot0 = Container(
                                        item_ident,
                                        self.ItemManager.ITEM_TYPES[item_ident],
                                    )  # need to pass the reference to load the item with data.
                                else:
                                    bodypart.slot0 = Item(
                                        item_ident,
                                        self.ItemManager.ITEM_TYPES[item_ident],
                                    )  # need to pass the reference to load the item with data.
                                break
                            elif bodypart.slot1 is None:
                                if (
                                    "container_type"
                                    in self.ItemManager.ITEM_TYPES[item_ident]
                                ):
                                    bodypart.slot1 = Container(
                                        item_ident,
                                        self.ItemManager.ITEM_TYPES[item_ident],
                                    )  # need to pass the reference to load the item with data.
                                else:
                                    bodypart.slot1 = Item(
                                        item_ident,
                                        self.ItemManager.ITEM_TYPES[item_ident],
                                    )  # need to pass the reference to load the item with data.
                                break
                    else:
                        self._log.warn(
                            "character needed an item but no free slots found"
                        )
            elif (
                key == "items_in_containers"
            ):  # load the items_in_containers into their containers we just created.
                for location_ident, item_ident in value.items():
                    # first find the location_ident so we can load a new item into it.
                    for bodypart in self.characters[ident].body_parts:
                        if bodypart.slot0 is not None:
                            if (
                                isinstance(bodypart.slot0, Container)
                                and bodypart.slot0.ident == location_ident
                            ):  # uses the first one it finds, maybe check if it's full?
                                bodypart.slot0.add_item(
                                    Item(
                                        item_ident,
                                        self.ItemManager.ITEM_TYPES[item_ident],
                                    )
                                )
                            if (
                                isinstance(bodypart.slot1, Container)
                                and bodypart.slot1.ident == location_ident
                            ):  # uses the first one it finds, maybe check if it's full?
                                bodypart.slot1.add_item(
                                    Item(
                                        item_ident,
                                        self.ItemManager.ITEM_TYPES[item_ident],
                                    )
                                )

        self._log.info(
            "New character added to world: {}".format(
                self.characters[ident].name)
        )

    def callback_client_handle(self, connection_object, data):
        self._log.debug(
            "Server: Recieved data {} from client {}.".format(
                data, connection_object.address
            )
        )

        try:
            _command = Command(data["ident"], data["command"], data["args"])
        except:
            self._log.debug(
                "Server: invalid data {} from client {}.".format(
                    data, connection_object.address
                )
            )
            return

        # we recieved a valid command. process it.
        if isinstance(_command, Command):
            if _command["command"] == "login":
                # check whether this username has an account.
                print("checking validity of account.")
                _path = "./accounts/" + _command["ident"] + "/"
                # try:
                if os.path.isdir("./accounts/" + _command["ident"]):
                    print("username already exists.")
                    with open(str(_path + "SALT")) as f:
                        # send the user their salt.
                        _salt = f.read()
                        self.callback_client_send(
                            connection_object, str(_salt))
                else:
                    print("username doesn't have an account. let's set one up.")

                    try:
                        os.mkdir(_path)
                    except OSError:
                        print("Creation of the directory %s failed" % _path)
                    else:
                        print("Successfully created the directory %s " % _path)

                    # create salt file
                    _salt = makeSalt()
                    with open(str(_path + "SALT"), "w") as f:
                        f.write(str(_salt))

                    # send the user their salt.
                    self.callback_client_send(connection_object, str(_salt))

                    _path = "./accounts/" + _command["ident"] + "/characters/"
                    try:
                        os.mkdir(_path)
                    except OSError:
                        print("Creation of the directory %s failed" % _path)
                    else:
                        print("Successfully created the directory %s " % _path)

            if _command["command"] == "hashed_password":
                print("checking hashed_password")
                _path = "./accounts/" + _command["ident"] + "/"
                if not os.path.isfile(str(_path + "HASHED_PASSWORD")):
                    # recieved hashedPW from user, save it and send them a list of characters. (presumaably zero if this is a new user. maybe give options to take over NPCs?)
                    print("storing password for " + str(_command["ident"]))
                    with open(str(_path + "HASHED_PASSWORD"), "w") as f:
                        f.write(str(_command["args"][0]))
                else:
                    print("password exists")

                with open(str(_path + "HASHED_PASSWORD")) as f:
                    _checkPW = f.read()
                    if _checkPW == _command["args"][0]:
                        print("password accepted for " +
                              str(_command["ident"]))
                        # get a list of the Character(s) the username 'owns' and send it to them. it's okay to send an empty list.
                        _tmp_list = list()
                        # if there are no characters to add the list remains empty.

                        for root, _, files in os.walk(
                            "./accounts/" + _command["ident"] + "/characters/"
                        ):
                            for file_data in files:
                                if file_data.endswith(".character"):
                                    with open(
                                        root + "/ " + file_data, encoding="utf-8"
                                    ) as data_file:
                                        data = json.load(data_file)
                                        _tmp_list.append(data)

                        self.callback_client_send(connection_object, _tmp_list)
                    else:
                        print("password not accepted.")
                        connection_object.disconnect()

            if _command["command"] == "create_new_character":
                if not data["ident"] in self.characters:
                    # this character doesn't exist in the world yet.
                    self.handle_new_character(data["ident"])
                    self._log.debug(
                        "Server: character created: {} From client {}.".format(
                            data["ident"], connection_object.address
                        )
                    )
                    self.callback_client_send(
                        connection_object, "character added sucessfully."
                    )
                else:
                    self._log.debug(
                        "Server: character NOT created. Already Exists.: {} From client {}.".format(
                            data["ident"], connection_object.address
                        )
                    )

            if _command["command"] == "request_character_update":
                self.callback_client_send(
                    connection_object, self.characters[data["ident"]]
                )

            if _command["command"] == "request_localmap_update":
                self.localmaps[data["ident"]] = self.plane.get_chunks_near_position(
                    self.characters[data["ident"]].position
                )
                self.callback_client_send(
                    connection_object, self.localmaps[data["ident"]]
                )

            # all the commands that are actions need to be put into the command_queue then we will loop through the queue each turn and process the actions.
            if _command["command"] == "ping":
                self.callback_client_send(connection_object, "pong")

            if _command["command"] == "move":
                self.characters[data["ident"]].command_queue.append(
                    Action(self.characters[data["ident"]],
                           "move", [data.args[0]])
                )

            if _command["command"] == "bash":
                self.characters[data["ident"]].command_queue.append(
                    Action(self.characters[data["ident"]],
                           "bash", [data.args[0]])
                )

            if _command["command"] == "create_blueprint":  # [result, direction])
                # args 0 is ident args 1 is direction.
                print(
                    "creating blueprint "
                    + str(data.args[0])
                    + " for character "
                    + str(self.characters[data["ident"]])
                )
                self._log.info(
                    "creating blueprint {} for character {}".format(
                        str(data.args[0]), str(self.characters[data["ident"]])
                    )
                )
                # blueprint rules
                # * there should be blueprints for terrain, furniture, items, and anything else that takes a slot up in the Plane.
                # * they act as placeholders and then 'transform' into the type they are once completed.
                # Blueprint(type, recipe)
                position_to_create_at = None
                if data.args[1] == "south":
                    position_to_create_at = Position(
                        self.characters[data["ident"]].position.x,
                        self.characters[data["ident"]].position.y + 1,
                        self.characters[data["ident"]].position.z,
                    )
                elif data.args[1] == "north":
                    position_to_create_at = Position(
                        self.characters[data["ident"]].position.x,
                        self.characters[data["ident"]].position.y - 1,
                        self.characters[data["ident"]].position.z,
                    )
                elif data.args[1] == "east":
                    position_to_create_at = Position(
                        self.characters[data["ident"]].position.x + 1,
                        self.characters[data["ident"]].position.y,
                        self.characters[data["ident"]].position.z,
                    )
                elif data.args[1] == "west":
                    position_to_create_at = Position(
                        self.characters[data["ident"]].position.x - 1,
                        self.characters[data["ident"]].position.y,
                        self.characters[data["ident"]].position.z,
                    )

                _recipe = server.RecipeManager.RECIPE_TYPES[data.args[0]]
                type_of = _recipe["type_of"]
                bp_to_create = Blueprint(type_of, _recipe)

                self.plane.put_object_at_position(
                    bp_to_create, position_to_create_at
                )

            if _command["command"] == "calculated_move":
                self._log.debug(
                    "Recieved calculated_move action. Building a path for {}".format(
                        str(data["ident"])
                    )
                )

                _position = Position(data.args[0], data.args[1], data.args[2])
                _route = self.calculate_route(
                    self.characters[data["ident"]].position, _position
                )  # returns a route from point 0 to point 1 as a series of Position(s)
                print(_route)
                self._log.debug(
                    "Calculated route for Character {}: {}".format(
                        self.characters[data["ident"]], _route
                    )
                )

                # fill the queue with move commands to reach the tile.
                _x = self.characters[data["ident"]].position.x
                _y = self.characters[data["ident"]].position.y
                _z = self.characters[data["ident"]].position.z
                action = None
                if _route is None:
                    self._log.debug("No _route possible.")
                    return
                for step in _route:
                    _next_x = step.x
                    _next_y = step.y
                    _next_z = step.z
                    if _x > _next_x:
                        action = Action(
                            self.characters[data["ident"]], "move", ["west"]
                        )
                    elif _x < _next_x:
                        action = Action(
                            self.characters[data["ident"]], "move", ["east"]
                        )
                    elif _y > _next_y:
                        action = Action(
                            self.characters[data["ident"]], "move", ["north"]
                        )
                    elif _y < _next_y:
                        action = Action(
                            self.characters[data["ident"]], "move", ["south"]
                        )
                    elif _z < _next_z:
                        action = Action(
                            self.characters[data["ident"]], "move", ["up"])
                    elif _z > _next_z:
                        action = Action(
                            self.characters[data["ident"]], "move", ["down"]
                        )
                    self.characters[data["ident"]].command_queue.append(action)
                    # pretend as if we are in the next position.
                    _x = _next_x
                    _y = _next_y
                    _z = _next_z

            if _command["command"] == "move_item_to_character_storage":
                print("RECIEVED: move_item_to_character_storage", str(data))
                _character = self.characters[data["ident"]]
                _from_pos = Position(data.args[0], data.args[1], data.args[2])
                _item_ident = data.args[3]
                _from_item = None
                _open_containers = []
                print(_character, _from_pos, _item_ident)
                # find the item that the character is requesting.
                for item in self.plane.get_tile_by_position(_from_pos)["items"]:
                    if item.ident == _item_ident:
                        # this is the item or at least the first one that matches the same ident.
                        _from_item = item  # save a reference to it to use.
                        break

                # we didn't find one, character sent bad information (possible hack?)
                if _from_item == None:
                    print("!!! _from_item not found. this is unusual.")
                    return

                # make a list of open_containers the character has to see if they can pick it up.
                for bodyPart in _character.body_parts:
                    if (
                        bodyPart.slot0 is not None
                        and isinstance(bodyPart.slot0, Container)
                        and bodyPart.slot0.opened == "yes"
                    ):
                        _open_containers.append(bodyPart.slot0)
                    if (
                        bodyPart.slot1 is not None
                        and isinstance(bodyPart.slot1, Container)
                        and bodyPart.slot1.opened == "yes"
                    ):
                        _open_containers.append(bodyPart.slot1)

                if len(_open_containers) <= 0:
                    print("no open containers found.")
                    return  # no open containers.

                # check if the character can carry that item.
                for container in _open_containers:
                    # then find a spot for it to go (open_containers)
                    if container.add_item(item):  # if it added it sucessfully.
                        print(
                            "added item correctly. trying to remove it from the world."
                        )
                        # remove it from the world.
                        for item in self.plane.get_tile_by_position(_from_pos)[
                            "items"
                        ][
                            :
                        ]:  # iterate a copy to remove properly.
                            if item.ident == _item_ident:
                                self.plane.get_tile_by_position(_from_pos)[
                                    "items"
                                ].remove(item)
                                print("removed item from the world successfully.")
                                break
                        return
                    else:
                        print("could not add item to character inventory.")
                    # then send the character the updated version of themselves so they can refresh.

            if _command["command"] == "move_item":
                # client sends 'hey server. can you move this item from this to that?'
                _character_requesting = self.characters[data["ident"]]
                _item = data.args[0]  # the item we are moving.
                _from_type = data.args[
                    1
                ]  # creature.held_item, creature.held_item.container, bodypart.equipped, bodypart.equipped.container, position, blueprint
                _from_list = (
                    []
                )  # the object list that contains the item. parse the type and fill this properly.
                _to_list = data.args[
                    2
                ]  # the list the item will end up. passed from command.
                _position = Position(
                    data.args[3], data.args[4], data.args[5]
                )  # pass the position even if we may not need it.

                # need to parse where it's coming from and where it's going.
                if _from_type == "bodypart.equipped":
                    for bodypart in _character_requesting.body_parts[
                        :
                    ]:  # iterate a copy to remove properly.
                        if _item in bodypart.equipped:
                            _from_list = bodypart.equipped
                            _from_list.remove(_item)
                            _to_list.append(_item)
                            print("moved correctly.")
                            return
                elif _from_type == "bodypart.equipped.container":
                    for bodypart in _character_requesting.body_parts[
                        :
                    ]:  # iterate a copy to remove properly.
                        for item in bodypart.equipped:  # could be a container or not.
                            # if it's a container.
                            if isinstance(item, Container):
                                for item2 in item.contained_items[
                                    :
                                ]:  # check every item in the container.
                                    if item2 is _item:
                                        _from_list = item.contained_items
                                        _from_list.remove(_item)
                                        _to_list.append(_item)
                                        print("moved correctly.")
                                        return
                elif _from_type == "position":
                    _from_list = self.plane.get_tile_by_position(_position)[
                        "items"]
                    if _item in _from_list:
                        _from_list.remove(_item)
                        _to_list.append(_item)
                        print("moved correctly.")
                        return
                elif (
                    _from_type == "blueprint"
                ):  # a blueprint is a type of container but can't be moved from it's world position.
                    for item in self.plane.get_tile_by_position(_position)["items"]:
                        if (
                            isinstance(item) == Blueprint
                        ):  # only one blueprint allowed per space.
                            _from_list = item.contained_items
                            _from_list.remove(_item)
                            _to_list.append(_item)
                            print("moved correctly.")
                            return

                ### possible move types ###
                # creature(held) to creature(held) (give to another character)
                # creature(held) to position(ground) (drop)
                # creature(held) to bodypart (equip)
                # bodypart to creature(held) (unequip)
                # bodypart to position (drop)

                # position to creature(held) (pick up from ground)
                # position to bodypart (equip from ground)
                # position to position (move from here to there)

                # creature to blueprint (fill blueprint)

                # blueprint to position (empty blueprint on ground)
                # blueprint to creature (grab from blueprint)

        return super(Server, self).callback_client_handle(connection_object, data)

    def callback_client_send(self, connection_object, data, compression=True):
        # print("Server: Sending data \""+str(data)+"\" to client \""+str(connection_object.address)+"\" with compression \""+str(compression)+"\"!")
        return super(Server, self).callback_client_send(
            connection_object, data, compression
        )

    def callback_connect_client(self, connection_object):
        self._log.info(
            "Server: Client from {} connected.".format(
                connection_object.address)
        )
        return super(Server, self).callback_connect_client(connection_object)

    def callback_disconnect_client(self, connection_object):
        self._log.info(
            "Server: Client from {} disconnected.".format(
                connection_object.address)
        )
        return super(Server, self).callback_disconnect_client(connection_object)

    def process_creature_command_queue(self, creature):
        actions_to_take = creature.actions_per_turn
        for action in creature.command_queue[:]:
            if actions_to_take == 0:
                return  # this creature is out of action points.

            if (
                creature.next_action_available > 0
            ):  # this creature can't act until x turns from now.
                creature.next_action_available = creature.next_action_available - 1
                return

            # if we get here we can process a single action
            if action.action_type == "move":
                actions_to_take = actions_to_take - 
                if action.args[0] == "south":
                    if self.plane.move_object_from_position_to_position(
                        self.characters[creature.name],
                        self.characters[creature.name].position,
                        Position(
                            self.characters[creature.name].position.x,
                            self.characters[creature.name].position.y + 1
                        ),
                    ):
                        self.characters[creature.name].position = Position(
                            self.characters[creature.name].position.x,
                            self.characters[creature.name].position.y + 1
                        )
                    creature.command_queue.remove(
                        action
                    )  # remove the action after we process it.
                if action.args[0] == "north":
                    if self.plane.move_object_from_position_to_position(
                        self.characters[creature.name],
                        self.characters[creature.name].position,
                        Position(
                            self.characters[creature.name].position.x,
                            self.characters[creature.name].position.y - 1
                        ),
                    ):
                        self.characters[creature.name].position = Position(
                            self.characters[creature.name].position.x,
                            self.characters[creature.name].position.y - 1
                        )
                    creature.command_queue.remove(
                        action
                    )  # remove the action after we process it.
                if action.args[0] == "east":
                    if self.plane.move_object_from_position_to_position(
                        self.characters[creature.name],
                        self.characters[creature.name].position,
                        Position(
                            self.characters[creature.name].position.x + 1,
                            self.characters[creature.name].position.y
                        ),
                    ):
                        self.characters[creature.name].position = Position(
                            self.characters[creature.name].position.x + 1,
                            self.characters[creature.name].position.y
                        )
                    creature.command_queue.remove(
                        action
                    )  # remove the action after we process it.
                if action.args[0] == "west":
                    if self.plane.move_object_from_position_to_position(
                        self.characters[creature.name],
                        self.characters[creature.name].position,
                        Position(
                            self.characters[creature.name].position.x - 1,
                            self.characters[creature.name].position.y
                        ),
                    ):
                        self.characters[creature.name].position = Position(
                            self.characters[creature.name].position.x - 1,
                            self.characters[creature.name].position.y
                        )
                    creature.command_queue.remove(
                        action
                    )  # remove the action after we process it.
                if action.args[0] == "up":
                    if self.plane.move_object_from_position_to_position(
                        self.characters[creature.name],
                        self.characters[creature.name].position,
                        Position(
                            self.characters[creature.name].position.x,
                            self.characters[creature.name].position.y
                        ),
                    ):
                        self.characters[creature.name].position = Position(
                            self.characters[creature.name].position.x,
                            self.characters[creature.name].position.y
                        )
                    creature.command_queue.remove(
                        action
                    )  # remove the action after we process it.
                if action.args[0] == "down":
                    if self.plane.move_object_from_position_to_position(
                        self.characters[creature.name],
                        self.characters[creature.name].position,
                        Position(
                            self.characters[creature.name].position.x,
                            self.characters[creature.name].position.y
                        ),
                    ):
                        self.characters[creature.name].position = Position(
                            self.characters[creature.name].position.x,
                            self.characters[creature.name].position.y
                        )
                    creature.command_queue.remove(
                        action
                    )  # remove the action after we process it.
           

    # this function handles overseeing all creature movement, attacks, and interactions
    def compute_turn(self):
        # init a list for all our found lights around characters.
        for _, chunks in self.localmaps.items():
            for chunk in chunks:  # characters typically get 9 chunks
                for tile in chunk.tiles:
                    tile["lumens"] = 0  # reset light levels.

        for _, chunks in self.localmaps.items():
            for chunk in chunks:  # characters typically get 9 chunks
                for tile in chunk.tiles:
                    for item in tile["items"]:
                        if isinstance(item, Blueprint):
                            continue
                        for flag in self.ItemManager.ITEM_TYPES[item.ident]["flags"]:
                            if (
                                flag.split("_")[0] == "LIGHT"
                            ):  # this item produces light.
                                for (
                                    tile,
                                    distance,
                                ) in self.plane.get_tiles_near_position(
                                    tile["position"], int(flag.split("_")[1])
                                ):
                                    tile["lumens"] = tile["lumens"] + int(
                                        int(flag.split("_")[1]) - distance
                                    )
                    if tile["furniture"] is not None:
                        for key in self.FurnitureManager.FURNITURE_TYPES[
                            tile["furniture"].ident
                        ]:
                            if key == "flags":
                                for flag in self.FurnitureManager.FURNITURE_TYPES[
                                    tile["furniture"].ident
                                ]["flags"]:
                                    if (
                                        flag.split("_")[0] == "LIGHT"
                                    ):  # this furniture produces light.
                                        for (
                                            tile,
                                            distance,
                                        ) in self.plane.get_tiles_near_position(
                                            tile["position"], int(
                                                flag.split("_")[1])
                                        ):
                                            tile["lumens"] = tile["lumens"] + int(
                                                int(flag.split("_")
                                                    [1]) - distance
                                            )
                                        break
        # we want a list that contains all the non-duplicate creatures on all localmaps around characters.
        creatures_to_process = list()
        for _, chunks in self.localmaps.items():
            for chunk in chunks:  # characters typically get 9 chunks
                for tile in chunk.tiles:
                    if (
                        tile["creature"] is not None
                        and tile["creature"] not in creatures_to_process
                    ):
                        creatures_to_process.append(tile["creature"])

        for creature in creatures_to_process:
            # as long as there at least one we'll pass it on and let the function handle how many actions they can take.
            if len(creature.command_queue) > 0:
                print("doing actions for: " + str(creature.name))
                self.process_creature_command_queue(creature)

        # now that we've processed what everything wants to do we can return.



# do this if the server was started up directly.
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Cataclysm LD Server")
    parser.add_argument("--host", metavar="Host",
                        help="Server host", default="0.0.0.0")
    parser.add_argument(
        "--port", metavar="Port", type=int, help="Server port", default=6317
    )
    parser.add_argument(
        "--config", metavar="Config", help="Configuration file", default="server.cfg"
    )
    args = parser.parse_args()

    # Configuration Parser - configured values override command line
    configParser = configparser.ConfigParser()
    configParser.read(args.config)

    # Grab the values within the configuration file's DEFAULT scope and
    # make them available as configuration values
    defaultConfig = configParser["DEFAULT"]
    ip = defaultConfig.get("listen_address", args.host)
    port = int(defaultConfig.get("listen_port", args.port))

    # Enable logging - It uses its own configparser for the same file
    logging.config.fileConfig(args.config)
    log = logging.getLogger("root")
    log.info("Server is start at {}:{}".format(ip, port))

    server = Server(logger=log, config=defaultConfig)
    server.connect(ip, port)
    server.accepting_allow()

    dont_break = True
    time_offset = float(
        defaultConfig.get("time_offset", 1.0)
    )  # 0.5 is twice as fast, 2.0 is twice as slow
    last_turn_time = time.time()
    citySize = int(defaultConfig.get("city_size", 1))
    log.info("City size: {}".format(citySize))
    server.generate_and_apply_city_layout(citySize)

    time_per_turn = int(defaultConfig.get("time_per_turn", 1))
    log.info("time_per_turn: {}".format(time_per_turn))
    spin_delay_ms = float(defaultConfig.get("time_per_turn", 0.001))
    log.info("spin_delay_ms: {}".format(spin_delay_ms))
    log.info("Started up Cataclysm: Looming Darkness Server.")
    while dont_break:
        try:
            while (
                time.time() - last_turn_time < time_offset
            ):  # try to keep up with the time offset but never go faster than it.
                time.sleep(spin_delay_ms)
            server.calendar.advance_time_by_x_seconds(
                time_per_turn
            )  # a turn is one second.
            # where all queued creature actions get taken care of, as well as physics engine stuff.
            server.compute_turn()
            # print('turn: ' + str(server.calendar.get_turn()))
            # if the plane in memory changed update it on the hard drive.
            server.plane.update_chunks_on_disk()
            # TODO: unload from memory chunks that have no updates required. (such as no monsters, Characters, or fires)
            last_turn_time = time.time()  # based off of system clock.
        except KeyboardInterrupt:
            log.info("cleaning up before exiting.")
            server.accepting_disallow()
            server.disconnect_clients()
            server.disconnect()
            # if the plane in memory changed update it on the hard drive.
            server.plane.update_chunks_on_disk()
            dont_break = False
            log.info("done cleaning up.")
        """except Exception as e:
            print('!! Emergency Exit due to Server Exception. !!')
            print(e)
            print()
            server.accepting_disallow()
            server.disconnect_clients()
            server.disconnect()
            server.plane.update_chunks_on_disk() # if the plane in memory changed update it on the hard drive.
            dont_break = False
            sys.exit()"""
