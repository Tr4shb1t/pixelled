import pixelled
from time import sleep
from random import randint

red = [255, 0, 0, 255]
green = [0, 255, 0]
blue = [0, 0, 255]
purple = [120, 0, 180]
yellow = [120, 75,0]
colors= [[255,0,0], [0,255,0], [0,0,255]]
white = [255,255,255]
orange = [180, 20, 0]
off = [0,0,0]
sky = [orange, blue, purple, yellow]

pix = pixelled.LightMatrix(0, 8, 64, 3)

while True:
    pix.set_pixel_in_serial(randint(0,pix.leds-1), sky[randint(0,3)], randint(1,10))
    pix.set_pixel_in_serial(randint(0,pix.leds-1), off)
    pix.show()
    # sleep(3)
