import pixelled
from time import sleep
import random

red = [255, 0, 0, 255]
green = [0, 255, 0]
blue = [0, 0, 255]
purple = [120, 0, 255]
yellow = [120, 120,0]
colors= [[255,0,0], [0,255,0], [0,0,255]]
white = [255,255,255]
orange = [255, 120, 0]
black = [0,0,0]
sky = [orange, blue, purple, yellow]

pix = pixelled.LightMatrix(0, 512, 8, 32)

while True:
    for _ in range(200):
        pix.set_pixel(random.randint(0,511),sky[random.randint(0,3)],random.randint(1,10))
        pix.set_pixel(random.randint(0,511),black)
        pix.show()
        # sleep(3)
