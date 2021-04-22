"Zoom a window to maximum height."
import re
import sys
import tkinter


class WmInfoGatheringError(Exception):
    pass


class ZoomHeight:
    _max_height_and_y_coords = {}

    def __init__(self, editwin):
        self.editwin = editwin
        self.top = self.editwin.top

    def zoom_height_event(self, event=None):
        zoomed = self.zoom_height()
        if zoomed is None:
            self.top.bell()
        else:
            menu_status = "Restore" if zoomed else "Zoom"
            self.editwin.update_menu_label(
                menu="options", index="* Height", label=f"{menu_status} Height"
            )
        return "break"

    def zoom_height(self):
        top = self.top
        (width, height, x, y) = get_window_geometry(top)
        if top.wm_state() != "normal":
            return None
        try:
            (maxheight, maxy) = self.get_max_height_and_y_coord()
        except WmInfoGatheringError:
            return None
        if height != maxheight:
            set_window_geometry(top, (width, maxheight, x, maxy))
            return True
        else:
            top.wm_geometry("")
            return False

    def get_max_height_and_y_coord(self):
        top = self.top
        screen_dimensions = (top.winfo_screenwidth(), top.winfo_screenheight())
        if screen_dimensions not in self._max_height_and_y_coords:
            orig_state = top.wm_state()
            try:
                top.wm_state("zoomed")
            except tkinter.TclError:
                raise WmInfoGatheringError(
                    (
                        "Failed getting geometry of maximized windows, because "
                        + 'the "zoomed" window state is unavailable.'
                    )
                )
            top.update()
            (maxwidth, maxheight, maxx, maxy) = get_window_geometry(top)
            if sys.platform == "win32":
                maxy = 0
            maxrooty = top.winfo_rooty()
            top.wm_state("normal")
            top.update()
            orig_geom = get_window_geometry(top)
            max_y_geom = orig_geom[:3] + (maxy,)
            set_window_geometry(top, max_y_geom)
            top.update()
            max_y_geom_rooty = top.winfo_rooty()
            maxheight += maxrooty - max_y_geom_rooty
            self._max_height_and_y_coords[screen_dimensions] = (maxheight, maxy)
            set_window_geometry(top, orig_geom)
            top.wm_state(orig_state)
        return self._max_height_and_y_coords[screen_dimensions]


def get_window_geometry(top):
    geom = top.wm_geometry()
    m = re.match("(\\d+)x(\\d+)\\+(-?\\d+)\\+(-?\\d+)", geom)
    return tuple(map(int, m.groups()))


def set_window_geometry(top, geometry):
    top.wm_geometry("{:d}x{:d}+{:d}+{:d}".format(*geometry))


if __name__ == "__main__":
    from unittest import main

    main("idlelib.idle_test.test_zoomheight", verbosity=2, exit=False)
