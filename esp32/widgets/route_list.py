
from .widget import Widget
from .buttom import Buttom
from .text import TextWidget
from .route_preview import RoutePreviewWidget
from gpx.route_cache import RouteEntry, read_route_metadata, ensure_route_cache

from events import EventType
import os

class RouteListWidget(Widget):
    def __init__(
        self,
        name,
        x,
        y,
        w,
        h,
        routes_folder="routes",
        on_route_selected=None,
    ):
        super().__init__(name, x, y, w, h)

        self.routes_folder = routes_folder
        self.on_route_selected = on_route_selected

        self.visible = False
        self.routes: list[RouteEntry] = []

        self.selected_index = None
        self.current_page = 0

        self.background_color = 0x0000
        self.text_color = 0xFFFF

        self.font_size = 30
        self.padding = 5
        self.row_height = self.font_size + 2 * self.padding

        button_w = 16
        button_h = 32

        # Split the widget into list and preview panels.
        self.list_panel_w = (
            self.w - 3 * self.padding
        ) // 2

        self.list_panel_h = self.h

        preview_panel_x = (
            self.x
            + 2 * self.padding
            + self.list_panel_w
        )

        preview_panel_y = self.y

        preview_panel_w = (
            self.w
            - self.list_panel_w
            - 3 * self.padding
        )

        preview_panel_h = self.h

        self.route_preview = RoutePreviewWidget(
            "Route preview",
            preview_panel_x,
            preview_panel_y,
            preview_panel_w,
            preview_panel_h,
        )

        self.reload_routes()
        self.dirty = True

        self.button_prev = Buttom(
            "ButtonPrevious",
            self.x + self.padding,
            self.y + self.h - self.padding - button_h,
            button_w,
            button_h,
            on_push=self.previous_page,
        )

        self.button_next = Buttom(
            "ButtonNext",
            self.list_panel_w - self.padding - button_w,
            self.y + self.h - self.padding - button_h,
            button_w,
            button_h,
            on_push=self.next_page,
        )

        self.page_index = TextWidget(
            "PageIndex",
            self.x + self.padding + button_w,
            self.y + self.h - self.padding - button_h,
            (self.list_panel_w - self.padding - button_w) - (self.x + self.padding + button_w),
            button_h,
            f"{self.current_page+1}/{self.page_count()}",
            font_size=16,
            align="center",
        )
        
        self.widgets = [
            self.button_prev,
            self.button_next,
            self.page_index,
            self.route_preview,
        ]

    def routes_per_page(self):
        button_area_height = (
            self.button_prev.h
            + 2 * self.padding
        )

        available_height = (
            self.list_panel_h
            - button_area_height
            - self.padding
        )

        return max(
            1,
            available_height // self.row_height,
        )

    def page_count(self):
        rows = self.routes_per_page()

        if not self.routes:
            return 0

        return (
            len(self.routes) + rows - 1
        ) // rows

    def get_item_at_point(self, point):
        if point is None:
            return None

        px, py = point

        # Touch must be inside the list panel.
        if not (
            self.x <= px < self.x + self.list_panel_w
            and self.y <= py < self.button_prev.y
        ):
            return None

        local_y = py - self.y - self.padding

        if local_y < 0:
            return None

        row = local_y // self.row_height
        rows_per_page = self.routes_per_page()

        if row < 0 or row >= rows_per_page:
            return None

        index = (
            self.current_page * rows_per_page
            + row
        )

        if index < 0 or index >= len(self.routes):
            return None

        return index

    def select_route(self, index):
        route = self.routes[index]
    
        print(
            "RouteListWidget: selected route",
            index,
            route.name,
        )
    
        if route.metadata is None:
            route.metadata = ensure_route_cache(
                route
            )
    
        if route.metadata is None:
            print(
                "Could not load route:",
                route.name,
            )
            return
    
        self.route_preview.set_route(
            route_name=route.name,
            route_info=route.metadata,
            cache_path=route.cache_path,
        )
        
    def handle_touch(self, point, event_type):
        if not self.visible:
            return

        # Paging buttons have priority.
        self.button_prev.handle_touch(point, event_type)
        self.button_next.handle_touch(point, event_type)

        if event_type == EventType.SINGLE_TAP:
            selected_index = self.get_item_at_point(
                point
            )
    
            if selected_index is None:
                return
    
            self.selected_index = selected_index
            route_name = self.routes[selected_index].name
    
            print(
                "RouteListWidget: selected route",
                selected_index,
                route_name,
            )
    
            self.select_route(self.selected_index)
    
            self._mark_all_dirty()

        elif event_type == EventType.DOUBLE_TAP and self.selected_index:
            route = self.routes[self.selected_index]
        
            if self.on_route_selected is not None:
                self.on_route_selected(route)

    def next_page(self):
        page_count = self.page_count()

        if page_count == 0:
            print(
                "RouteListWidget: no pages available"
            )
            return

        self.current_page = (
            self.current_page + 1
        ) % page_count

        self.selected_index = None
        self.route_preview.clear()


        self.dirty = True
        self.route_preview.dirty = True

        self.page_index.set_text(f"{self.current_page+1}/{self.page_count()}")

        print(
            "RouteListWidget: page",
            self.current_page + 1,
            "of",
            page_count,
        )

    def previous_page(self):
        page_count = self.page_count()

        if page_count == 0:
            print(
                "RouteListWidget: no pages available"
            )
            return

        self.current_page = (
            self.current_page - 1
        ) % page_count

        self.selected_index = None
        self.route_preview.clear()

        self.dirty = True
        self.route_preview.dirty = True

        self.page_index.set_text(f"{self.current_page+1}/{self.page_count()}")
        
        print(
            "RouteListWidget: page",
            self.current_page + 1,
            "of",
            page_count,
        )

    def load_routes(self):
        self.routes = []
    
        try:
            filenames = os.listdir("routes")
        except Exception as e:
            print("Failed to list routes:", e)
            self.routes_loaded = True
            return
    
        for filename in filenames:
            if not filename.endswith(".gpx"):
                continue
    
            route_name = filename[:-4]
    
            route = RouteEntry(
                name=route_name,
                gpx_path="/routes/" + filename,
                cache_path="/cache/routes/" + route_name + ".bin"
            )
    
            route.metadata = read_route_metadata(
                route.cache_path,
                route.name,
            )
    
            self.routes.append(route)
    
        self.routes.sort(
            key=lambda route: route.name.lower()
        )
    
        self.routes_loaded = True
        self.dirty = True
            
    def reload_routes(self):
        self.routes.clear()
        self.load_routes()

    def open(self):
        if not self.routes_loaded:
            self.load_routes()
    
        self.visible = True
        
        self._mark_all_dirty()

    def refresh_routes(self):
        self.routes = []
        self.routes_loaded = False
        self.selected_index = None
    
        self.load_routes()
    
        self.dirty = True

    def close(self):
        self.visible = False
        self.dirty = False

    def toggle(self):
        if self.visible:
            self.close()
        else:
            self.open()

    def render(self, display):
        if not self.visible or not self.dirty:
            return

        display.fill_rect(
            self.x,
            self.y,
            self.w,
            self.h,
            self.background_color,
        )

        route_count = len(self.routes)

        if route_count == 0:
            print(
                "RouteListWidget: no routes found in",
                self.routes_folder,
            )

            display.text(
                self.x + self.padding,
                self.y + self.padding,
                self.list_panel_w
                - 2 * self.padding,
                self.row_height,
                "No routes found",
                self.text_color,
                bg=self.background_color,
                font_size=self.font_size,
            )

            super().render(display)
            self.dirty = False
            return

        rows_per_page = self.routes_per_page()
        page_count = self.page_count()

        if self.current_page >= page_count:
            self.current_page = page_count - 1

        start_index = (
            self.current_page
            * rows_per_page
        )

        end_index = min(
            start_index + rows_per_page,
            route_count,
        )

        print(
            "RouteListWidget: rendering page",
            self.current_page + 1,
            "of",
            page_count,
            "routes",
            start_index,
            "to",
            end_index - 1,
        )

        y = self.y + self.padding

        for index in range(
            start_index,
            end_index,
        ):
            display.text(
                self.x + self.padding,
                y,
                self.list_panel_w
                - 2 * self.padding,
                self.row_height,
                self.routes[index].name,
                self.text_color,
                bg=self.background_color,
                font_size=self.font_size,
            )

            y += self.row_height

        # Buttons and preview render after the list.
        self.button_prev.dirty = True
        self.button_next.dirty = True

        super().render(display)

        self.dirty = False
