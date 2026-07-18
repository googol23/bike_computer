from .widget import Widget

class TextWidget(Widget):
    VALID_ALIGNMENTS = {"left", "center", "right"}
    
    def __init__(self, name, x, y, w, h, text="None", font_size=30, align="left", padding=4):
        super().__init__(name, x, y, w, h)
        
        if align not in self.VALID_ALIGNMENTS:
            raise ValueError(
                f"Invalid alignment: {align}. "
                f"Expected one of {self.VALID_ALIGNMENTS}"
            )

        self.text = text
        self.font_size = font_size
        self.align = align
        self.padding = max(0, padding)

    # def render(self, display):
    #     display.text(
    #         self.x + self.padding,
    #         self.y + self.padding,
    #         self.w - 2*self.padding,
    #         self.h - 2*self.padding,
    #         self.text,
    #         0xFFFF,
    #         font_size=self.font_size,
    #     )
    #     self.dirty = False

    def set_text(self, text:str):
        self.text = text
        self.dirty = True

    def set_align(self, align):
        if align not in self.VALID_ALIGNMENTS:
            raise ValueError(
                f"Invalid alignment: {align}. "
                f"Expected one of {self.VALID_ALIGNMENTS}"
            )
        self.align = align
        self.dirty = True

    def render(self, display):
            inner_x = self.x + self.padding
            inner_y = self.y + self.padding
            inner_w = max(0, self.w - (2 * self.padding))
            inner_h = max(0, self.h - (2 * self.padding))
    
            text_width = display.text_width(
                self.text,
                font_size=self.font_size,
            )
    
            if self.align == "center":
                text_x = inner_x + max(0, (inner_w - text_width) // 2)
            elif self.align == "right":
                text_x = inner_x + max(0, inner_w - text_width)
            else:
                text_x = inner_x
    
            display.text(
                text_x,
                inner_y,
                max(0, inner_x + inner_w - text_x),
                inner_h,
                self.text,
                0xFFFF,
                font_size=self.font_size,
            )
    
            self.dirty = False
