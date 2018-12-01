import json
import pygame
import sys


class TileManager:  # holds all the tile types from tile_config.json as well as terrain.json information because terrain can have a fg and bg
    def __init__(self):
        self.tilemapPx = 64
        self.tilemapPy = 32
        pygame.init()
        screen = pygame.display.set_mode((100, 100))
        pygame.display.set_caption('RipTiles')

        self.TILE_MAP = self.load_tile_table(
            str(sys.argv[1]), self.tilemapPx, self.tilemapPy)

    def load_tile_table(self, filename, width, height):
        print('loading tile table: ' + str(filename))
        # print(width)
        # print(height)
        image = pygame.image.load(filename).convert_alpha()
        image_width, image_height = image.get_size()
        # print(str(image_width))
        # print(str(image_height))

        for tile_y in range(0, int(image_height/height)):
            for tile_x in range(0, int(image_width/width)):
                rect = (tile_x*width, tile_y*height, width, height)
                print('writing', tile_x, tile_y)
                # for saving the tilemap to individual files
                pygame.image.save(image.subsurface(
                    rect), './' + str(tile_x) + '_' + str(tile_y) + '.png')


tm = TileManager()
