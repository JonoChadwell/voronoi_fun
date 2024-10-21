import pygame
import pygame.gfxdraw
import random
import timeit
from typing import Union, Dict, List, Tuple

# Pastel color palette
PASTEL_COLORS = [
    (255, 204, 204),  # Light Red
    (255, 229, 204),  # Light Orange
    (255, 255, 204),  # Light Yellow
    (204, 255, 204),  # Light Green
    (204, 255, 229),  # Light Teal
    (204, 255, 255),  # Light Blue
    (204, 204, 255),  # Light Purple
    (229, 204, 255)   # Light Magenta
]

TOROIDAL_OFFSETS=[
    (0,0),
    (0,1),
    (1,1),
    (1,0)
]

RENDER_TOROIDAL_OFFSETS=[
    (0,0),
    (0,1),
    (0,-1),
    (1,0),
    (-1,0),
    (1,1),
    (1,-1),
    (-1,1),
    (-1,-1),
]

# Define a Node with attributes for position and color
class Node:
    def __init__(self, pos: Tuple[float, float], color: Tuple[int, int, int]):
        self.pos = pos
        self.color = color
    
    @property
    def x(self):
        return self.pos[0]
    
    @x.setter
    def x(self, value):
        self.pos[0] = value
    
    @property
    def y(self):
        return self.pos[1]
    
    @y.setter
    def y(self, value):
        self.pos[1] = value

NUM_POINTS=5
points = []
# Fill in random x/y points in the range (0, 1)
for i in range(NUM_POINTS):
    x = random.uniform(0, 1)
    y = random.uniform(0, 1)
    color = random.choice(PASTEL_COLORS)
    node = Node((x,y), color)
    node.motion = (random.uniform(-0.01, 0.01), random.uniform(-0.01, 0.01))
    points.append(node)

# Normalize to range [0,1)
def normalize(a: Union[float, Tuple[float, float]]):
    if isinstance(a, Tuple):
        return (normalize(a[0]), normalize(a[1]))
    return (a % 1 + 1) % 1

def add_pos(a: Tuple[float, float], b: Tuple[float, float], *, normalize=False):
    result = (a[0] + b[0], a[1] + b[1])
    if (normalize):
        return normalize(result)
    return result

# Return the four midpoints of a and b in toroidal space
def midpoints(a: Node, b: Node) -> List[Tuple[float, float]]:
    def avg(a, b):
        return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    return [normalize(avg(a.pos, add_pos(b.pos, x))) for x in TOROIDAL_OFFSETS]

# Re-orient `b` such that each instance uses the closest option to `a` in
# torioidal space.
def denormalize(a: Node, b: Union[Tuple[float, float], List[Tuple[float, float]]]):
    if isinstance(b, List):
        # List comprehension to recurse for every value in b
        return [denormalize(a, value) for value in b]
    offset = lambda x : add_pos(x, (0.5 - a.x, 0.5 - a.y))
    unoffset = lambda x : add_pos(x, (a.x - 0.5, a.y - 0.5))
    return unoffset(normalize(offset(b)))

# Gemini code
def perpendicular_point(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> Tuple[float, float]:
    """
    Finds the intersection point of two lines perpendicular to AB and AC, respectively, passing through points B and C.

    Returns:
        The coordinates of the intersection point.
    """

    xa, ya = a
    xb, yb = b
    xc, yc = c

    # Calculate slopes of AB and AC
    slope_ab = (yb - ya) / (xb - xa)
    slope_ac = (yc - ya) / (xc - xa)

    # Calculate slopes of perpendicular lines
    slope_perp_b = -1 / slope_ab
    slope_perp_c = -1 / slope_ac

    # Find equations of perpendicular lines
    line_b_eq = yb - slope_perp_b * xb
    line_c_eq = yc - slope_perp_c * xc

    # Solve the system of equations
    x = (line_c_eq - line_b_eq) / (slope_perp_b - slope_perp_c)
    y = slope_perp_b * x + line_b_eq

    return x, y

# Compute the region closest to the given point. Output will be a convex hull. 
def compute_dominated_region(points: List[Dict], index: int) -> List[Tuple[int, int]]:
    dominated_region = []
    key_point = points[index]
    midpoints = []
    for i, point in enumerate(points):
        if i == index:
            continue
        midpoints.append(((point.x + key_point.x) / 2, (point.y + key_point.y) / 2))
       

    return dominated_region

pygame.init()
screen = pygame.display.set_mode((1200, 1200))
running = True

def distance(a: Union[Tuple[float, float], Node], b: Union[Tuple[float, float], Node]):
    if isinstance(a, Node):
        a = a.pos
    if isinstance(b, Node):
        b = b.pos

    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    real_dx = min(dx, 1 - dx)
    real_dy = min(dy, 1 - dy)
    return (real_dx**2 + real_dy**2)**0.5

def simulate(time):
    for point in points:
        point.pos = (normalize(point.x + point.motion[0] * time), normalize(point.y + point.motion[1] * time))

def reverse_lerp(a: float, b: float, value: float) -> float:
    if a == b:
        return 0.5
    return (value - a) / (b - a)
assert(reverse_lerp(1, 5, 3) == 0.5)
assert(reverse_lerp(1, 5, 2) == 0.25)


def lerp(a: float, b: float, value: float) -> float:
    return a * (1 - value) + b * value
assert(lerp(1, 5, 0.5) == 3)
assert(lerp(1, 5, 0.25) == 2)

def clip_polygon(polygon: List[Tuple[float, float]]) -> List[Tuple[float, float]]:

    # Clip to x >= 0
    in_bounds = lambda p : 0 <= p[0]
    project = lambda p_a, p_b : (0, lerp(p_a[1], p_b[1], reverse_lerp(p_a[0], p_b[0], 0)))
    result = []
    for idx in range(len(polygon)):
        a = polygon[idx - 1]
        b = polygon[idx]

        a_in = in_bounds(a)
        b_in = in_bounds(b)
        if (a_in and not b_in) or (b_in and not a_in):
            result.append(project(a, b))

        if in_bounds(b):
            result.append(b)
    polygon = result

    # Clip to x <= 1
    in_bounds = lambda p : p[0] <= 1
    project = lambda p_a, p_b : (1, lerp(p_a[1], p_b[1], reverse_lerp(p_a[0], p_b[0], 1)))
    result = []
    for idx in range(len(polygon)):
        a = polygon[idx - 1]
        b = polygon[idx]

        a_in = in_bounds(a)
        b_in = in_bounds(b)
        if (a_in and not b_in) or (b_in and not a_in):
            result.append(project(a, b))

        if in_bounds(b):
            result.append(b)
    polygon = result

    # Clip to y >= 0
    in_bounds = lambda p : 0 <= p[1]
    project = lambda p_a, p_b : (lerp(p_a[0], p_b[0], reverse_lerp(p_a[1], p_b[1], 0)), 0)
    result = []
    for idx in range(len(polygon)):
        a = polygon[idx - 1]
        b = polygon[idx]

        a_in = in_bounds(a)
        b_in = in_bounds(b)
        if (a_in and not b_in) or (b_in and not a_in):
            result.append(project(a, b))

        if in_bounds(b):
            result.append(b)
    polygon = result

    # Clip to y <= 1
    in_bounds = lambda p : p[0] <= 1
    project = lambda p_a, p_b : (lerp(p_a[0], p_b[0], reverse_lerp(p_a[1], p_b[1], 1)), 1)
    result = []
    for idx in range(len(polygon)):
        a = polygon[idx - 1]
        b = polygon[idx]

        a_in = in_bounds(a)
        b_in = in_bounds(b)
        if (a_in and not b_in) or (b_in and not a_in):
            result.append(project(a, b))

        if in_bounds(b):
            result.append(b)
    polygon = result

    return polygon

simtoggle = True
# Main render function
def render(surface):
    size = min(surface.get_width(), surface.get_height())
    surface.fill((40, 40, 40))

    def surface_pos(a):
        if isinstance(a, Node):
            return (a.x * size, a.y * size)
        return (a[0] * size, a[1] * size)

    first_midpoints = midpoints(points[0], points[1])

    make_perpendicular = lambda node, a, b : perpendicular_point(node.pos, denormalize(node, a), denormalize(node, b))
    perpendiculars = [
        make_perpendicular(points[0], first_midpoints[0], first_midpoints[1]),
        make_perpendicular(points[0], first_midpoints[1], first_midpoints[2]),
        make_perpendicular(points[0], first_midpoints[2], first_midpoints[3]),
        make_perpendicular(points[0], first_midpoints[3], first_midpoints[0]),
    ]

    # Render polygons
    for offset in RENDER_TOROIDAL_OFFSETS:
        polygon = clip_polygon([add_pos(point, offset) for point in perpendiculars])
        if 3 <= len(polygon):
            pygame.gfxdraw.filled_polygon(surface, [surface_pos(point) for point in polygon], points[0].color)

    # # Color to the nearest point for each pixel
    # for x in range(1, size, 5):
    #     for y in range(1, size, 5):
    #         test_location = (x/size,y/size)
    #         nearest = points[0]
    #         for point in points[1::]:
    #             if distance(test_location, point) < distance(test_location, nearest):
    #                 nearest = point
    #         pygame.draw.rect(surface, nearest.color, (x, y, 4, 4))
    
    # Draw lines from point 0 to midpoints
    for end_point in denormalize(points[0], first_midpoints):
        for offset in RENDER_TOROIDAL_OFFSETS:
            pygame.draw.line(surface, (255, 255, 255), surface_pos(add_pos(points[0].pos, offset)), surface_pos(add_pos(end_point, offset)), 2)

    # Draw points to surface
    for point in points:    
        pygame.draw.circle(surface, (0,0,0), surface_pos(point), 10)
        pygame.draw.circle(surface, point.color, surface_pos(point), 6)
    
    # # Draw midpoints between points[0] and points[1]
    # for midpoint in first_midpoints:
    #     pygame.draw.circle(surface, (255, 255, 255), surface_pos(midpoint), 4)

    pygame.display.flip()

last_auto_tick = pygame.time.get_ticks()
simtoggle = True
revsersetoggle = False
quadtoggle = False
while running:

    for event in pygame.event.get():
        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = pygame.mouse.get_pos()
    
        # Check if the user is initiating a drag by moving the cursor more than 5 pixels away from the drag start point
        if event.type == pygame.MOUSEMOTION:
            pos = pygame.mouse.get_pos()

        # Check if the user has finished dragging an item
        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                pass

        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            # Flip simtoggle if the user presses spacebar
            if event.key == pygame.K_SPACE:
                simtoggle = not simtoggle
            if event.key == pygame.K_0:
                quadtoggle = not quadtoggle
            if event.key == pygame.K_1:
                revsersetoggle = not revsersetoggle
            if event.key == pygame.K_ESCAPE:
                running = False
        
        # Quit if we lost focus
        if event.type == pygame.ACTIVEEVENT:
            if event.state & 1 == 1 and event.gain == 0:
                running = False

    if simtoggle:        
        if last_auto_tick + 20 < pygame.time.get_ticks():
            last_auto_tick = pygame.time.get_ticks()
            if revsersetoggle: 
                simulate(-0.5)
            else:
                simulate(0.5)

    if quadtoggle:
        size = min(screen.get_width(), screen.get_height()) / 2
        draw_plane = pygame.Surface((size, size))
        render(draw_plane)
        # Draw 4 copies of surface to screen
        screen.fill((40, 40, 40))
        screen.blit(draw_plane, (0, 0))
        screen.blit(draw_plane, (size + 1, 0))
        screen.blit(draw_plane, (0, size + 1))
        screen.blit(draw_plane, (size + 1, size + 1))
    else:
        render(screen)
    pygame.display.flip()
    

    

pygame.quit()