from machine import Pin, bitstream

class PixelLED():
    def __init__(self, pin, leds, bpp=4):
        self.pin = Pin(pin, Pin.OUT)
        self.leds = leds
        self.bpp = bpp  # Bytes per Pixel
        self.pixels = [[0,0,0,0]] * leds
        self.buf = bytearray(leds * self.bpp)
        self.timing = (400, 850, 800, 450)
        self.order = (1, 0, 2, 3)   # RGBW to GRBW
        self.brightness = 255

    def set_pixel(self, pos, rgbw, brightness=None):
        if brightness is None:
            brightness = self.brightness
        if len(rgbw) == 3:
            rgbw.append(0)
        rgbw = [round(byte / 255 * brightness) for byte in rgbw]
        self.pixels[pos] = rgbw

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
            self.set_pixel(led, rgbw, brightness)

    def clear(self):
        for led in range(self.leds):
            self.set_pixel(led, [0, 0, 0, 0])

    def set_brightness(self, brightness):
        if brightness <= 1:
            self.brightness = 1
        if brightness >= 255:
            self.brightness = 255
        else:
            self.brightness = brightness

    def get_pixel(self, pixel):
        return self.pixels[pixel]

    def show(self):
        self.buf = bytearray([sublist[index] for sublist in self.pixels for index in self.order[:self.bpp]])
        bitstream(self.pin, 0, self.timing, self.buf)

class LightStripe(PixelLED):
    def __init__(self, pin, leds, bpp=4):
        super().__init__(pin, leds, bpp)
        self.section_map = {}
        self.section_count = 0

    def clear_section_map(self):
        self.section_map = {}
        self.section_count = 0

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
            self.pixels.insert(0, [0,0,0,0])

    def shift_left(self, steps=1):
        for _ in range(steps):
            self.pixels.pop(0)
            self.pixels.append([0,0,0,0])

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
            section.insert(0, [0,0,0,0])
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
            section.append([0, 0, 0, 0])
        if len(section) > len(self.pixels[:hi]):
            for _ in range(steps):
                section.pop(0)
            self.pixels[lo:hi] = section
        else:
            self.pixels[lo-steps:hi] = section

class LightMatrix(PixelLED):
    def __init__(self, pin, leds, leds_height, leds_width, bpp=3):
        super().__init__(pin, leds, bpp)
        self.leds_height = leds_height
        self.leds_width = leds_width

    def flip(self):
        pass

    def build_line_in_x(self, line_nr):
        leds = [line_nr]
        for i in range(1, int(self.leds_width + 1)):
            leds.append(line_nr + i * 2 * self.leds_height - 1 - line_nr * 2)
            leds.append(line_nr + i * 2 * self.leds_height)
        return leds

    def set_pixel_line(self, pos_ax, pos_ay, length, rgbw, brightness=None):
        leds = self.build_line_in_x(pos_ay)
        for led in leds[pos_ax:length+pos_ax]:
            self.set_pixel(led, rgbw, brightness)

    def set_pixel_line_gradient(self, pos_ax, pos_ay, length, rgbw1, rgbw2, brightness=None):
        leds = self.build_line_in_x(pos_ay)
        rgbw_steps = self.build_gradient(rgbw1, rgbw2, length)
        count = 0
        for led in leds[pos_ax:length+pos_ax]:
            self.set_pixel(led, rgbw_steps[count], brightness)
            count += 1

    def set_pixel_rectangle(self, start_x, start_y, end_x, end_y, rgbw, brightness=None):
        hi_x, low_x = max(start_x, end_x), min(start_x, end_x)
        hi_y, low_y = max(start_y, end_y), min(start_y, end_y)
        height = hi_y - low_y + 1
        length = hi_x - low_x + 1
        for line in range(height):
            self.set_pixel_line(low_x, low_y + line, length, rgbw, brightness)

    def rotate_right(self, steps=1):
        for _ in range(steps):
            for _ in range(self.leds_height * 2):
                for _ in range(self.bpp):
                    self.pixels.insert(0, self.pixels.pop())

    def rotate_left(self):
        pass

    def set_char(self):
        pass

    def set_text(self):
        pass


