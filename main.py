import pixelled
from time import sleep

red = [255, 0, 0]
blue = [0, 0, 255]

pix = pixelled.LightMatrix(0, 512, 8, 32, 3)
pix.set_brightness(10)

pix.set_pixel_line_gradient(0,0,6,red, blue)
pix.show()

sleep(1)
pix.rotate_right()
pix.show()
sleep(5)
pix.clear()
pix.show()
