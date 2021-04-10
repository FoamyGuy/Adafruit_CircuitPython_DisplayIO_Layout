# SPDX-FileCopyrightText: Copyright (c) 2021 Tim Cocks
#
# SPDX-License-Identifier: MIT
"""
`foamyguy_displayio_inflater.linear_layout`
================================================================================

Consumes JSON layout code creates a LinearLayout that positions elements within
it in a line vertically or horizontally.


* Author(s): Tim Cocks
"""

from adafruit_displayio_layout.widgets.widget import Widget


class LinearLayout(Widget):
    VERTICAL_ORIENTATION = 1
    HORIZONTAL_ORIENTATION = 2

    def __init__(
        self,
        x,
        y,
        width,
        height,
        orientation=VERTICAL_ORIENTATION,
        padding=0,
        max_size=None,
    ):

        super().__init__(x=x, y=y, width=width, height=height, max_size=max_size)

        self.x = x
        self.y = y
        self.padding = padding
        self._width = width
        self._height = height
        if orientation not in [self.VERTICAL_ORIENTATION, self.HORIZONTAL_ORIENTATION]:
            raise ValueError(
                "Orientation must be either LinearLayout.VERTICAL_ORIENTATION or LinearLayout.HORIZONTAL_ORIENTATION"
            )

        self.orientation = orientation
        self._content_list = []
        self._prev_content_end = 0

    def add_content(self, content):
        """Add a child to the linear layout.

        :param content: the content to add to the linear layout e.g. label, button, etc...
         Group subclasses that have width and height properties can be used.

        :return: None"""

        self._content_list.append(content)
        self.append(content)
        self._layout()

    def _layout(self):
        self._prev_content_end = 0

        for index, content in enumerate(self._content_list):
            if not hasattr(content, "anchor_point"):
                if self.orientation == self.VERTICAL_ORIENTATION:
                    content.y = self._prev_content_end
                    try:
                        self._prev_content_end = (
                            self._prev_content_end + content.height + self.padding
                        )
                    except AttributeError as e:
                        print(e)
                        try:
                            self._prev_content_end = (
                                self._prev_content_end + content._height + self.padding
                            )
                        except AttributeError as e:
                            print(e)

                else:
                    content.x = self._prev_content_end
                    self._prev_content_end = content.x + content.width
            else:  # use anchor point
                content.anchor_point = (0, 0)
                if self.orientation == self.VERTICAL_ORIENTATION:
                    print("before {}".format(self._prev_content_end))

                    # print("y before {}".format(content.y))

                    print("setting y to: {}".format(self._prev_content_end + 0))
                    content.anchored_position = (0, self._prev_content_end)
                    # self._prev_content_end = content.y + content.height
                    if not hasattr(content, "bounding_box"):
                        self._prev_content_end = (
                            self._prev_content_end + content.height + self.padding
                        )
                    else:
                        self._prev_content_end = (
                            self._prev_content_end
                            + (content.bounding_box[3] * content.scale)
                            + self.padding
                        )
                    print("after {}".format(self._prev_content_end))
                else:
                    content.anchored_position = (self._prev_content_end, 0)
                    if not hasattr(content, "bounding_box"):
                        self._prev_content_end = (
                            self._prev_content_end + content.width + self.padding
                        )
                    else:
                        self._prev_content_end = (
                            self._prev_content_end
                            + (content.bounding_box[2] * content.scale)
                            + self.padding
                        )

        print("-----------------")
