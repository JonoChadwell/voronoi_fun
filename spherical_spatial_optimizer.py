import pygame
import pygame.gfxdraw
import random
import timeit
import multiprocessing
from typing import Union, Dict, List, Tuple
from functools import partial

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

def reverse_lerp(a: float, b: float, value: float) -> float:
    if a == b:
        return 0.5
    return (value - a) / (b - a)
assert(reverse_lerp(1, 5, 3) == 0.5)
assert(reverse_lerp(1, 5, 2) == 0.25)
assert(reverse_lerp(1, 6, 0) == -0.2)

def lerp(a: float, b: float, value: float) -> float:
    return a * (1 - value) + b * value
assert(lerp(1, 5, 0.5) == 3)
assert(lerp(1, 5, 0.25) == 2)

# Define a "point".
Point = Tuple[float, float]

def vector(*, origin: Point, dest: Point) -> Point:
    return (dest[0] - origin[0], dest[1] - origin[1])

# Faster than computing the actual magnitude
def magnitude_squared(point: Point) -> float:
    return point[0] * point[0] + point[1] * point[1]

def magnitude(point: Point) -> float:
    return magnitude_squared(point)**0.5

def dot_product(a: Point, b: Point) -> float:
    return a[0] * b[0] + a[1] * b[1]

def point_lerp(a: Point, b: Point, value: float) -> Point:
    return (lerp(a[0], b[0], value), lerp(a[1], b[1], value))

def scale(a: Point, scalar: float):
    return (a[0] * scalar, a[1] * scalar)

def unitize(a: Point) -> Point:
    return scale(a, 1 / magnitude(a))

# Define a Node with attributes for position and color
class Node:
    def __init__(self, pos: Point, color: Tuple[int, int, int]):
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

# Normalize to range [0,1)
def normalize(a: Union[float, Point]):
    if isinstance(a, Tuple):
        return (normalize(a[0]), normalize(a[1]))
    return (a % 1 + 1) % 1

def add_pos(a: Point, b: Point, *, normalize=False):
    result = (a[0] + b[0], a[1] + b[1])
    if (normalize):
        return normalize(result)
    return result

# Return the four midpoints of a and b in toroidal space
def midpoints(a: Node, b: Node) -> List[Point]:
    def avg(a, b):
        return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    return [normalize(avg(a.pos, add_pos(b.pos, x))) for x in TOROIDAL_OFFSETS]

# Re-orient `b` such that each instance uses the closest option to `a` in
# torioidal space.
def denormalize(a: Node, b: Union[Point, List[Point]]):
    if isinstance(b, List):
        # List comprehension to recurse for every value in b
        return [denormalize(a, value) for value in b]
    offset = lambda x : add_pos(x, (0.5 - a.x, 0.5 - a.y))
    unoffset = lambda x : add_pos(x, (a.x - 0.5, a.y - 0.5))
    return unoffset(normalize(offset(b)))

# Gemini code
def perpendicular_point(a: Point, b: Point, c: Point) -> Point:
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

def clip_polygon_2(origin: Point, polygon: List[Point], wall: Point, wall_thickness: float = 0) -> List[Point]:
    assert(origin[0] != wall[0] or origin[1] != wall[1])
    wall_vector = vector(origin=origin, dest=wall)

    # Handle wall thickness by adjusting the wall towards the clip origin
    if wall_thickness != 0:
        wall = add_pos(wall, scale(unitize(wall_vector), -wall_thickness))
        wall_vector = vector(origin=origin, dest=wall)

    wall_vec_m2 = magnitude_squared(wall_vector)

    all_in = True
    for point in polygon:
        dot_value = dot_product(wall_vector, vector(origin=origin, dest=point))
        if dot_value > wall_vec_m2:
            all_in = False
            break
    if all_in:
        return polygon

    for idx in range(len(polygon)):
        a = polygon[idx - 1]
        b = polygon[idx]

        a_dot = dot_product(wall_vector, vector(origin=origin, dest=a))
        a_in = a_dot < wall_vec_m2

        b_dot = dot_product(wall_vector, vector(origin=origin, dest=b))
        b_in = b_dot < wall_vec_m2


    result = []

    for idx in range(len(polygon)):
        a = polygon[idx - 1]
        b = polygon[idx]

        a_dot = dot_product(wall_vector, vector(origin=origin, dest=a))
        a_in = a_dot < 0 or a_dot < wall_vec_m2

        b_dot = dot_product(wall_vector, vector(origin=origin, dest=b))
        b_in = b_dot < 0 or b_dot < wall_vec_m2

        if (a_in and not b_in) or (b_in and not a_in):
            range_a = dot_product(a, wall_vector)
            range_wall = dot_product(wall, wall_vector)
            range_b = dot_product(b, wall_vector)
            result.append(point_lerp(a, b, reverse_lerp(range_a, range_b, range_wall)))

        if b_in:
            result.append(b)
    
    return result

assert(clip_polygon_2((0.0, 0.0), [(0.0, 0.0), (2.0, 2.0), (2.0, 0.0)], (1,0,0.0)) == [(1.0, 0.0), (0.0, 0.0), (1.0, 1.0)])
assert(clip_polygon_2((5,5), [(3,3),(3,7),(7,7),(7,3)], (6,6)) == [(3,3),(3,7),(5,7),(7,5),(7,3)])
assert(clip_polygon_2((.5,.5), [(.3,.3),(.3,.7),(.7,.7),(.7,.3)], (.6,.6)) == [(.3,.3),(.3,.7),(.5,.7),(.7,.5),(.7,.3)])

# Compute the region closest to the given point. Output will be a convex hull. 
def compute_dominated_region(nodes: List[Node], index: int, *, wall_thickness=0.0) -> List[Point]:
    node = nodes[index]
    # polygon = [add_pos(node.pos, x) for x in [(1,1), (1,-1), (-1,-1), (-1,1)]]
    polygon = [add_pos(node.pos, x) for x in [(.5,.5), (.5,-.5), (-0.5,-0.5), (-0.5,0.5)]]

    all_midpoints = []
    for other in nodes:
        if node == other:
            continue
        all_midpoints += denormalize(node, midpoints(node, other))

    for point in all_midpoints:
        new_polygon = clip_polygon_2(node.pos, polygon, point, wall_thickness)
        polygon = new_polygon

    return polygon

def distance(a: Union[Point, Node], b: Union[Point, Node]):
    if isinstance(a, Node):
        a = a.pos
    if isinstance(b, Node):
        b = b.pos

    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    real_dx = min(dx, 1 - dx)
    real_dy = min(dy, 1 - dy)
    return (real_dx**2 + real_dy**2)**0.5

def clip_polygon(polygon: List[Point]) -> List[Point]:

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

# Main render function
g_processing_pool = None

def compute_one_region(idx: int, render_points):
    return compute_dominated_region(render_points, idx, wall_thickness=0.002)

def compute_regions_parallel(render_points):
    regions = g_processing_pool.map(partial(compute_one_region, render_points=render_points), range(len(render_points)), chunksize=10)
    return regions

g_regions = []    
def render(surface, render_points):
    size = min(surface.get_width(), surface.get_height())
    surface.fill((40, 40, 40))

    def surface_pos(a):
        if isinstance(a, Node):
            return (a.x * size, a.y * size)
        return (a[0] * size, a[1] * size)
        
    def compute():
        global g_regions        
        # g_regions = [compute_one_region(idx, render_points) for idx in range(len(render_points))]
        g_regions = compute_regions_parallel(render_points)
    
    def do_render():
        global g_regions
        # Render polygons
        for idx in range(len(render_points)):
            for offset in RENDER_TOROIDAL_OFFSETS:
                polygon = clip_polygon([add_pos(point, offset) for point in g_regions[idx]])
                if 3 <= len(polygon):
                    pygame.gfxdraw.filled_polygon(surface, [surface_pos(point) for point in polygon], render_points[idx].color)

    compute_time = timeit.timeit(compute, number=1)
    render_time = timeit.timeit(do_render, number=1)

    # Draw points to surface
    for point in render_points:    
        pygame.draw.circle(surface, (0,0,0), surface_pos(point), 10)
        pygame.draw.circle(surface, point.color, surface_pos(point), 6)
    
    # # Draw midpoints between render_points[0] and render_points[1]
    # for midpoint in first_midpoints:
    #     pygame.draw.circle(surface, (255, 255, 255), surface_pos(midpoint), 4)

def simulate(render_points):
    SPEED = 0.25
    for point in render_points:
        point.pos = (normalize(point.x + point.motion[0] * SPEED), normalize(point.y + point.motion[1] * SPEED))

def main():
    global g_processing_pool
    g_processing_pool = multiprocessing.Pool(processes=8)

    
    NUM_POINTS=80
    render_points = []
    # Fill in random x/y points in the range (0, 1)
    for i in range(NUM_POINTS):
        x = random.uniform(0, 1)
        y = random.uniform(0, 1)
        color = random.choice(PASTEL_COLORS)
        node = Node((x,y), color)
        node.motion = (random.uniform(-0.01, 0.01), random.uniform(-0.01, 0.01))
        render_points.append(node)


    pygame.init()
    screen = pygame.display.set_mode((1200, 1200))
    last_auto_tick = pygame.time.get_ticks()

    running = True
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
            
            # # Quit if we lost focus
            # if event.type == pygame.ACTIVEEVENT:
            #     if event.state & 1 == 1 and event.gain == 0:
            #         running = False

        if simtoggle:        
            if last_auto_tick + 20 < pygame.time.get_ticks():
                last_auto_tick = pygame.time.get_ticks()
                simulate(render_points)

        if quadtoggle:
            size = min(screen.get_width(), screen.get_height()) / 2
            draw_plane = pygame.Surface((size, size))
            render(draw_plane, render_points)
            # Draw 4 copies of surface to screen
            screen.fill((40, 40, 40))
            screen.blit(draw_plane, (0, 0))
            screen.blit(draw_plane, (size + 1, 0))
            screen.blit(draw_plane, (0, size + 1))
            screen.blit(draw_plane, (size + 1, size + 1))
        else:
            render(screen, render_points)
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()