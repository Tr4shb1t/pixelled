from machine import Pin, bitstream

class PixelLED():
    def __init__(self, pin, leds, bpp=3):
        self.pin = Pin(pin, Pin.OUT)
        self.leds = leds
        self.bpp = bpp  # Bytes per Pixel
        self.pixels = [[0,0,0,0,None]] * leds
        self.buf = bytearray(leds * self.bpp)
        self.timing = (400, 850, 800, 450)
        self.order = (1, 0, 2, 3)   # RGBW to GRBW
        self.default_brightness = 255

    def set_pixel_in_serial(self, pos, rgbw, brightness=None):
        rgbw_copy = rgbw.copy()
        if sum(rgbw_copy[:self.bpp]) is 0:
            brightness = None
        elif brightness is None:
            brightness = self.default_brightness
        while len(rgbw_copy) < 4:
            rgbw_copy.append(0)
        if brightness is not None:
            rgbw_copy = [round(byte / 255 * brightness) for byte in rgbw_copy]
        rgbw_copy.append(brightness)
        self.pixels[pos] = rgbw_copy

    def build_gradient(self, rgbw1, rgbw2, steps):
        rgbw_steps = []
        for leds in range(steps):
            rgbw = []
            for byte in range(self.bpp):
                step = (rgbw1[byte] - rgbw2[byte]) / (steps - 1)
                rgbw.append(int(rgbw1[byte] - step * leds))
            rgbw_steps.append(rgbw)
        return rgbw_steps

    def fill(self, rgbw, brightness=None):
        for led in range(self.leds):
            self.set_pixel_in_serial(led, rgbw, brightness)

    def clear(self):
        for led in range(self.leds):
            self.pixels[led] = [0, 0, 0, 0, None]

    def set_default_brightness(self, brightness):
        if brightness < 1:
            self.default_brightness = 1
        elif brightness > 255:
            self.default_brightness = 255
        else:
            self.default_brightness = brightness

    def set_pixel_brightness_in_serial(self, pos, brightness):
        if brightness < 1:
            brightness = 1
        elif brightness > 255:
            brightness = 255
        self.pixels[pos] = [round(byte / self.pixels[pos][-1] * brightness) for byte in self.pixels[pos][:-1]]
        self.pixels[pos].append(brightness)

    def set_brightness(self, brightness):
        for led in range(self.leds):
            self.set_pixel_brightness_in_serial(led, brightness)

    def get_pixel_in_serial(self, pos):
        color = self.pixels[pos][:self.bpp]
        brightness = self.pixels[pos][-1]
        return color, brightness

    def show(self):
        self.buf = bytearray([sublist[index] for sublist in self.pixels for index in self.order[:self.bpp]])
        bitstream(self.pin, 0, self.timing, self.buf)

class LightStripe(PixelLED):
    def __init__(self, pin, leds, bpp=3):
        super().__init__(pin, leds, bpp)
        self.section_map = {}
        self.section_count = 0

    def get_pixel(self, pos):
        return super().get_pixel_in_serial(pos)
    
    def set_pixel_brightness(self, pos, brightness):
        super().set_pixel_brightness_in_serial(pos, brightness)

    def set_pixel(self, pos, rgbw, brightness=None):
        super().set_pixel_in_serial(pos, rgbw, brightness)

    def set_pixel_line(self, pos_a, pos_b, rgbw, brightness=None):
        if pos_a < pos_b:
            for led in range(pos_a, pos_b + 1):
                self.set_pixel(led, rgbw, brightness)
        if pos_a > pos_b:
            for led in range(pos_b, pos_a + 1):
                self.set_pixel(led, rgbw, brightness)
        else:
            self.set_pixel(pos_a, rgbw, brightness)

    def set_pixel_line_gradient(self, pos_a, pos_b, rgbw1, rgbw2, brightness=None):
        hi = max(pos_a, pos_b)
        lo = min(pos_a, pos_b)
        steps = hi - lo + 1
        pixel_steps = self.build_gradient(rgbw1, rgbw2, steps)
        for led in range(len(pixel_steps)):
            if pos_a < pos_b:
                self.set_pixel(lo + led, pixel_steps[led], brightness)
            else:
                self.set_pixel(hi - led, pixel_steps[led], brightness)

    def rotate_right(self, steps=1):
        for _ in range(steps):
            self.pixels.insert(0, self.pixels.pop())

    def rotate_left(self, steps=1):
        for _ in range(steps):
            self.pixels.append(self.pixels.pop(0))

    def shift_right(self, steps=1):
        for _ in range(steps):
            self.pixels.pop()
            self.pixels.insert(0, [0, 0, 0, 0, None])

    def shift_left(self, steps=1):
        for _ in range(steps):
            self.pixels.pop(0)
            self.pixels.append([0, 0, 0, 0, None])

    def clear_section_map(self):
        self.section_map = {}
        self.section_count = 0

    def set_section(self, pos_a, pos_b, section_id=None):
        if section_id is None:
            section_id = self.section_count
            self.section_count += 1
        self.section_map[f"section_{section_id}"] = {
            "pos_a": min(pos_a, pos_b),
            "pos_b": max(pos_a, pos_b) + 1
        }
        return section_id

    def unset_section(self, section_id=None):
        if section_id is None:
            self.section_count -= 1
            section_id = self.section_count
        self.section_map.pop(f"section_{section_id}")

    def shift_section_right(self, pos_a, pos_b=None, steps=1):
        if pos_b is None:
            hi = self.section_map[f"section_{pos_a}"]["pos_b"]
            lo = self.section_map[f"section_{pos_a}"]["pos_a"]
            self.section_map[f"section_{pos_a}"]["pos_a"] += steps
            self.section_map[f"section_{pos_a}"]["pos_b"] += steps
        else:
            hi = max(pos_a, pos_b)
            lo = min(pos_a, pos_b)
        section = self.pixels[lo:hi]
        for _ in range(steps):
            section.insert(0, [0, 0, 0, 0, None])
        for pixel in range(len(section)):
            if lo + pixel > len(self.pixels) - 1:
                break
            else:
                self.pixels[lo + pixel] = section[pixel]

    def shift_section_left(self, pos_a, pos_b=None, steps=1):
        if pos_b is None:
            hi = self.section_map[f"section_{pos_a}"]["pos_b"]
            lo = self.section_map[f"section_{pos_a}"]["pos_a"]
            self.section_map[f"section_{pos_a}"]["pos_a"] -= steps
            if self.section_map[f"section_{pos_a}"]["pos_a"] < 0:
                self.section_map[f"section_{pos_a}"]["pos_a"] = 0
            self.section_map[f"section_{pos_a}"]["pos_b"] -= steps
            if self.section_map[f"section_{pos_a}"]["pos_b"] < 0:
                self.section_map[f"section_{pos_a}"]["pos_b"] = 0
        else:
            hi = max(pos_a, pos_b)
            lo = min(pos_a, pos_b)
        section = self.pixels[lo:hi]
        for _ in range(steps):
            section.append([0, 0, 0, 0, None])
        if len(section) > len(self.pixels[:hi]):
            for _ in range(steps):
                section.pop(0)
            self.pixels[lo:hi] = section
        else:
            self.pixels[lo-steps:hi] = section

class LightMatrix(PixelLED):
    def __init__(self, pin, leds_height, leds_width, bpp=3):
        leds = leds_height * leds_width
        super().__init__(pin, leds, bpp)
        self.leds_height = leds_height
        self.leds_width = leds_width
        self.pixel_position_map = self.build_pixel_position_map()

    def build_pixel_position_line_in_x(self, line_nr):
        leds = [line_nr]
        for led in range(1, int(self.leds_width + 1)):
            leds.append(line_nr + led * 2 * self.leds_height - 1 - line_nr * 2)
            if len(leds) < self.leds_width:
                leds.append(line_nr + led * 2 * self.leds_height)
        return leds
    
    def build_pixel_position_map(self):
        pixel_position_map = [[] for _ in range(self.leds_height)]
        for line in range(self.leds_height):
            pixel_position_map[line] = self.build_pixel_position_line_in_x(line)
        return pixel_position_map
    
    def get_pixel(self, pos_x, pos_y):
        pos = self.pixel_position_map[pos_y][pos_x]
        return super().get_pixel_in_serial(pos)
    
    def set_pixel_brightness(self, pos_x, pos_y, brightness):
        pos = self.pixel_position_map[pos_y][pos_x]
        super().set_pixel_brightness_in_serial(pos, brightness)

    def set_pixel(self, pos_x, pos_y, rgbw, brightness=None):
        pos = self.pixel_position_map[pos_y][pos_x]
        super().set_pixel_in_serial(pos, rgbw, brightness)

    def set_pixel_line_horizontal(self, start_x, start_y, length, rgbw, brightness=None):
        for led in range(length):
            self.set_pixel(start_x + led, start_y, rgbw, brightness)

    def set_pixel_line_vertical(self, start_x, start_y, length, rgbw, brightness=None):
        for led in range(length):
            self.set_pixel(start_x, start_y + led, rgbw, brightness)

    def set_pixel_line_gradient_horizontal(self, start_x, start_y, length, rgbw1, rgbw2, brightness=None):
        rgbw_steps = self.build_gradient(rgbw1, rgbw2, length)
        for led in range(length):
            self.set_pixel(start_x + led, start_y, rgbw_steps[led], brightness)

    def set_pixel_line_gradient_vertical(self, start_x, start_y, length, rgbw1, rgbw2, brightness=None):
        rgbw_steps = self.build_gradient(rgbw1, rgbw2, length)
        for led in range(length):
            self.set_pixel(start_x, start_y + led, rgbw_steps[led], brightness)

    def set_pixel_rectangle(self, start_x, start_y, end_x, end_y, rgbw, fill=True, brightness=None):
        hi_x, low_x = max(start_x, end_x), min(start_x, end_x)
        hi_y, low_y = max(start_y, end_y), min(start_y, end_y)
        height = hi_y - low_y + 1
        length = hi_x - low_x + 1
        for line in range(height):
            if line is not 0 and line is not height -1 and not fill:
                self.set_pixel(low_x, low_y + line, rgbw, brightness)
                self.set_pixel(hi_x, low_y + line, rgbw, brightness)
            else:
                self.set_pixel_line_horizontal(low_x, low_y + line, length, rgbw, brightness)

    def mirror_x(self):
        self.pixels.reverse()

    def mirror_y(self):
        for i in range(0, len(self.pixels), self.leds_height):
            self.pixels[i:i+self.leds_height] = self.pixels[i:i+self.leds_height][::-1]

    def rotate_right(self, steps=1):
        for _ in range(steps):
            for _ in range(self.leds_height):
                self.pixels.insert(0, self.pixels.pop(self.leds-1))
            self.mirror_y()

    def rotate_left(self, steps=1):
        for _ in range(steps):
            for _ in range(self.leds_height):
                self.pixels.append(self.pixels.pop(0))
            self.mirror_y()

    def rotate_up(self, steps=1):
        for _ in range(steps):
            for column in range(self.leds_width):
                self.pixels.insert(self.pixel_position_map[self.leds_height - 1][column], 
                                   self.pixels.pop(self.pixel_position_map[0][column]))

    def rotate_down(self, steps=1):
        for _ in range(steps):
            for column in range(self.leds_width):
                self.pixels.insert(self.pixel_position_map[0][column], 
                                   self.pixels.pop(self.pixel_position_map[self.leds_height - 1][column]))

    def shift_right(self, steps=1):
        for _ in range(steps):
            for _ in range(self.leds_height):
                self.pixels.pop(self.leds-1)
                self.pixels.insert(0, [0, 0, 0, 0, None])
            self.mirror_y()

    def shift_left(self, steps=1):
        for _ in range(steps):
            for _ in range(self.leds_height):
                self.pixels.pop(0)
                self.pixels.append([0, 0, 0, 0, None])
            self.mirror_y()

    def shift_up(self, steps=1):
        for _ in range(steps):
            for column in range(self.leds_width):
                self.pixels.pop(self.pixel_position_map[0][column])
                self.pixels.insert(self.pixel_position_map[self.leds_height - 1][column], [0, 0, 0, 0, None])

    def shift_down(self, steps=1):
        for _ in range(steps):
            for column in range(self.leds_width):
                self.pixels.pop(self.pixel_position_map[self.leds_height - 1][column])
                self.pixels.insert(self.pixel_position_map[0][column], [0, 0, 0, 0, None])

    def set_char(self):
        pass

    def set_text(self):
        pass
