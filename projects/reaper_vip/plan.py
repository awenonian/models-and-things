"""Floor plan of Steel Jackhammer's penthouse, traced from the Cy_Borg starter map.

All coordinates here are *map coordinates*: millimetres measured on the
827 x 845 px map image at 1 px = 1 mm, with x to the right and y DOWN the
page (north at the top). `M()` converts to model coordinates (Y up the page).

At 1 px = 1 mm the dining room is ~270 mm across and the WC ~37 mm, which
suits 30-40 mm bases. The whole flat is about 815 x 720 mm.
"""

from __future__ import annotations

from dataclasses import dataclass, field

CX, CY = 415.0, 410.0       # map point that becomes the model origin


def M(x: float, y: float) -> tuple[float, float]:
    """Map (px, y down) -> model (mm, Y up), centred on the flat."""
    return (x - CX, CY - y)


T_EXT = 7.0                 # outside walls
T_INT = 5.0                 # inside walls


@dataclass
class Wall:
    name: str
    pts: list[tuple[float, float]]
    t: float = T_INT
    kind: str = "solid"      # solid | glass (window wall) | partition (glass) | rail (balcony)
    curve: bool = False      # smooth the polyline (Catmull-Rom)


@dataclass
class Door:
    x: float
    y: float
    w: float
    jambs: bool = True


@dataclass
class Room:
    name: str
    poly: list[tuple[float, float]]
    floor: str               # planks | tiles | small_tiles | rubber | slats | plate | quilt | stone | none
    pitch: float = 0.0
    angle: float = 0.0       # pattern rotation (deg)


# ---------------------------------------------------------------------------
# Walls (centre lines)
# ---------------------------------------------------------------------------

BEDROOM_CURVE = [(10, 500), (11, 540), (18, 580), (32, 618), (54, 652), (85, 680)]
DINING_CURVE = [(603, 600), (588, 618), (560, 640), (520, 662), (480, 679), (420, 694), (328, 702)]
OUTER_CURVE = [(797, 470), (795, 512), (784, 556), (764, 600), (737, 638), (710, 662),
               (680, 682), (630, 706), (570, 730), (500, 750), (430, 762), (380, 767), (328, 770)]
HOLO_DIAG = [(603, 600), (712, 662)]

# Round piers where several walls end at one point: the holo space's diagonal
# wall meets the dining glass and the holo wall at its inner end, and the holo
# window and the balcony rail at its outer end. A tile seam crossing such a
# junction at an angle would leave slivers; a solid pier owned by one tile
# doesn't. (x, y, radius)
PIERS = [(604.0, 602.0, 5.0), (711.0, 663.0, 6.0)]

WALLS: list[Wall] = [
    # --- building corridor, lift and stairs (common area) ---------------------
    Wall("corr_n", [(66.5, 195), (307.5, 195)], T_EXT),
    Wall("corr_s", [(70, 260), (310, 260)]),
    Wall("lifts_w", [(70, 260), (70, 500)], T_EXT),
    Wall("lifts_s", [(70, 345), (232, 345)], T_EXT),
    Wall("lift_e", [(148, 260), (148, 345)]),
    # --- gym -----------------------------------------------------------------
    Wall("gym_w", [(310, 100), (310, 260)]),      # stops on the corridor wall's centre line
    Wall("gym_glass", [(310, 100), (355, 53), (430, 53), (478, 100)], T_EXT, "glass"),
    Wall("gym_s", [(312.5, 260), (475.5, 260)], 3.0, "partition"),
    Wall("gym_e", [(478, 100), (478, 343)]),
    # --- shower, hot tub, sauna ------------------------------------------------
    Wall("spa_n", [(478, 100), (650, 100)], T_EXT),
    Wall("shower_s", [(480.5, 202), (542.5, 202)], 3.0, "partition"),
    Wall("tub_w", [(545, 100), (545, 202)]),
    Wall("tub_e", [(650, 100), (650, 205), (690, 205)]),
    Wall("sauna_glass", [(690, 205), (750, 263)], 3.0, "partition"),
    Wall("sauna_w", [(750, 263), (750, 343)]),
    Wall("sauna_n", [(650, 100), (690, 128), (745, 128), (818, 205), (818, 343)], T_EXT),
    Wall("spa_s", [(478, 343), (818, 343)]),
    # --- hallway, guest room, kitchen ------------------------------------------
    Wall("guest_e", [(232, 260), (232, 540)]),
    Wall("kitchen_stub", [(265, 412), (303, 367)]),
    Wall("kitchen_n", [(303, 367), (518, 367)]),
    Wall("kitchen_e", [(518, 343), (518, 484)]),
    Wall("kitchen_s", [(232, 484), (518, 484)]),
    # --- passage, WC, baths, sensory deprivation ------------------------------
    Wall("wc_w", [(580, 343), (580, 457.5)]),
    Wall("wc_s", [(580, 400), (622, 400)]),
    Wall("wc_e", [(622, 343), (622, 400)]),
    Wall("sdc_w", [(652, 343), (652, 455)]),
    Wall("holo_n", [(580, 455), (797, 455)]),
    Wall("sdc_e", [(797, 344), (797, 470)], T_EXT),     # its end cap stays inside spa_s
    # --- master bedroom, bath, closet, storage ---------------------------------
    Wall("bed_n", [(10, 500), (232, 500)], T_EXT),
    Wall("bed_glass", BEDROOM_CURVE + [(185, 680)], T_EXT, "glass", curve=True),
    Wall("bed_s", [(185, 680), (242.5, 683)], T_EXT),      # ends on the seam
    Wall("bath_s", [(232, 538), (328, 538)]),
    Wall("storage_n", [(245, 612), (328, 612)]),
    Wall("storage_w", [(245, 612), (245, 683)]),
    Wall("storage_curve", [(245.5, 683), (255, 715), (278, 742), (305, 760), (330, 770)], T_EXT,
         curve=True),
    # --- dining room, holo space, balcony --------------------------------------
    Wall("dining_w", [(328, 484), (328, 770)]),
    Wall("holo_w", [(603, 455), (603, 600)]),
    Wall("dining_glass", DINING_CURVE, T_INT, "glass", curve=True),
    Wall("holo_diag", HOLO_DIAG, 6.0),
    Wall("holo_glass", OUTER_CURVE[:6], T_EXT, "glass", curve=True),
    Wall("balcony_rail", OUTER_CURVE[5:], 4.0, "rail", curve=True),
]

DOORS: list[Door] = [
    Door(111, 260, 52),          # lift doors
    Door(190, 260, 52),          # stairwell
    Door(271, 260, 42),          # front door of the flat
    Door(400, 260, 44, False),   # gym glass doors
    Door(478, 228, 38),          # gym -> spa
    Door(478, 302, 40),          # hallway -> spa
    Door(512, 202, 36, False),   # shower screen
    Door(720, 234, 38, False),   # sauna glass door
    Door(547, 343, 36),          # spa -> passage
    Door(601, 343, 34),          # spa -> WC
    Door(580, 427, 40),          # passage -> bath
    Door(652, 421, 36),          # bath -> sensory deprivation
    Door(603, 528, 44),          # dining -> holo space
    Door(518, 403, 40),          # kitchen -> passage
    Door(454, 484, 72, False),   # kitchen opens into the dining room
    Door(232, 375, 40),          # guest room
    Door(258, 538, 38),          # bath -> closet
    Door(328, 574, 44),          # closet -> dining room
    Door(287, 612, 38),          # storage
    Door(543, 649, 46, False),   # sliding doors to the balcony
]

# ---------------------------------------------------------------------------
# Rooms: floor finish (rough outlines; walls are added over the top)
# ---------------------------------------------------------------------------

ROOMS: list[Room] = [
    Room("corridor", [(66, 195), (310, 195), (310, 260), (66, 260)], "tiles", 20),
    Room("lift", [(70, 260), (148, 260), (148, 345), (70, 345)], "plate", 6),
    Room("stairs", [(148, 260), (232, 260), (232, 345), (148, 345)], "none"),
    Room("gym", [(310, 53), (478, 53), (478, 260), (310, 260)], "rubber", 24),
    Room("shower", [(478, 100), (545, 100), (545, 202), (478, 202)], "small_tiles", 6),
    Room("spa", [(478, 202), (750, 202), (750, 343), (478, 343)], "stone", 18),
    Room("sauna", [(650, 100), (818, 100), (818, 343), (650, 343)], "slats", 5, 90),
    Room("hallway", [(232, 260), (518, 260), (518, 367), (232, 367)], "planks", 9),
    Room("guest", [(70, 345), (232, 345), (232, 500), (70, 500)], "planks", 9, 90),
    Room("kitchen", [(232, 367), (518, 367), (518, 484), (232, 484)], "tiles", 14, 45),
    Room("passage", [(518, 343), (580, 343), (580, 484), (518, 484)], "planks", 9, 90),
    Room("wc", [(580, 343), (652, 343), (652, 455), (580, 455)], "small_tiles", 6),
    Room("sdc", [(652, 343), (797, 343), (797, 455), (652, 455)], "quilt", 10),
    Room("bath", [(232, 484), (328, 484), (328, 538), (232, 538)], "small_tiles", 6),
    Room("closet", [(232, 538), (328, 538), (328, 612), (232, 612)], "planks", 9, 90),
    Room("storage", [(245, 612), (328, 612), (328, 770), (245, 770)], "plate", 10),
    Room("bedroom", [(0, 500), (245, 500), (245, 690), (0, 690)], "planks", 9),
    Room("dining", [(328, 484), (603, 484), (603, 704), (328, 704)], "planks", 9),
    Room("holo", [(603, 455), (800, 455), (800, 670), (712, 662), (603, 600)], "hex", 16),
    Room("balcony", [(328, 600), (720, 600), (720, 775), (328, 775)], "deck", 12, -18),
]

# ---------------------------------------------------------------------------
# Outline of the floor slab (outer wall centre lines, clockwise on the map)
# ---------------------------------------------------------------------------

OUTLINE_STRAIGHT_N = [(66.5, 195), (310, 195), (310, 100), (355, 53), (430, 53), (478, 100),
                      (650, 100), (690, 128), (745, 128), (818, 205), (818, 343), (797, 343)]
# ...then (797, 470) and OUTER_CURVE to (328, 770), the storage curve back to
# its start, along the bedroom's south wall and up its curve to (10, 500).

# ---------------------------------------------------------------------------
# Print tiles: the plan is cut into bed-sized tiles. Seams run along wall
# faces wherever possible so a whole wall stays on one tile. Each zone is a
# list of rectangles (x0, y0, x1, y1) in map coords, claimed in this order:
# a later zone never takes area an earlier one already has. Where both faces of
# a wall carry details (the chamber's padding and its lock button), the seam
# runs down the middle of the wall instead, so each half keeps its own face.
# ---------------------------------------------------------------------------

BIG = 2000.0
ZONES: list[tuple[str, list]] = [
    ("gym", [(307.5, -BIG, 480.5, 262.5), (290.0, -BIG, 307.5, 191.5),
             (480.5, 199.5, 494.2, 204.5)]),     # the shower screen's stub, on the gym wall
    ("hot_tub", [(480.5, -BIG, 652.5, 340.5)]),
    ("sauna", [(652.5, -BIG, BIG, 340.5)]),
    ("corridor", [(-BIG, -BIG, 307.5, 348.5)]),
    ("kitchen", [(307.5, 262.5, 480.5, 486.5), (480.5, 340.5, 520.5, 486.5)]),
    ("bedroom", [(-BIG, 496.5, 235.5, BIG), (-BIG, 400.0, 66.4, BIG), (-BIG, 609.5, 242.5, BIG),
                 (-BIG, 534.0, 239.2, 542.0)]),     # the bath wall's stub beside the door
    ("guest_room", [(-BIG, 348.5, 307.5, 486.5), (-BIG, 486.5, 235.5, 496.5)]),
    ("passage", [(520.5, 340.5, 652.0, 457.5), (520.5, 457.5, 605.5, 486.5)]),
    ("sensory", [(652.0, 340.5, BIG, 457.5)]),
    ("storage_cage", [(242.5, 617.0, 485.0, BIG), (242.5, 609.5, 325.5, BIG)]),
    ("bath_closet", [(235.5, 486.5, 405.0, 617.0)]),
    ("holo", "holo"),            # special: north-east of the diagonal wall
    ("dining", "dining"),        # special: inside the dining room's glass curve
    ("balcony", [(-BIG, -BIG, BIG, BIG)]),
]
