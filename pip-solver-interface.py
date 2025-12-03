import pygame
import sys
from z3 import *
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Initialize Pygame
pygame.init()

# Constants
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
GRID_SIZE = 80
GRID_ROWS = 8
GRID_COLS = 8
GRID_OFFSET_X = 50
GRID_OFFSET_Y = 100

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
LIGHT_GRAY = (240, 240, 240)
DARK_GRAY = (100, 100, 100)
ACTIVE_CELL = (100, 200, 255)
SELECTED_CELL = (255, 200, 100)
REGION_COLORS = [
    (255, 150, 150), (150, 255, 150), (150, 150, 255),
    (255, 255, 150), (255, 150, 255), (150, 255, 255),
    (200, 150, 100), (150, 200, 100)
]

# Button class
class Button:
    def __init__(self, x, y, width, height, text, color, text_color=BLACK):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.text_color = text_color
        self.active = False
        
    def draw(self, screen, font):
        color = self.color if not self.active else SELECTED_CELL
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, BLACK, self.rect, 2)
        text_surface = font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)
        
    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

# Main application class
class DominoPuzzleBuilder:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Domino Puzzle Builder")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 36)
        
        # State
        self.mode = "SETUP_BOARD"  # SETUP_BOARD, ADD_DOMINOS, ADD_REGIONS, SOLVE
        self.active_cells = set()  # Cells that are part of the board
        self.cell_map = {}  # Maps grid position to cell number
        self.dominos = []  # List of (a, b) tuples
        self.regions = []  # List of (cells, op, target) tuples
        self.current_region_cells = []
        self.current_region_type = None
        
        # Input fields
        self.domino_input = {"a": "", "b": ""}
        self.region_target_input = ""
        self.active_input = None
        
        # Buttons
        self.setup_buttons()
        
    def setup_buttons(self):
        # Mode buttons
        button_y = 20
        button_width = 150
        button_height = 40
        button_spacing = 160
        
        self.mode_buttons = {
            "SETUP_BOARD": Button(50, button_y, button_width, button_height, "1. Setup Board", LIGHT_GRAY),
            "ADD_DOMINOS": Button(50 + button_spacing, button_y, button_width, button_height, "2. Add Dominos", LIGHT_GRAY),
            "ADD_REGIONS": Button(50 + button_spacing * 2, button_y, button_width, button_height, "3. Add Regions", LIGHT_GRAY),
            "SOLVE": Button(50 + button_spacing * 3, button_y, button_width, button_height, "4. Solve!", LIGHT_GRAY),
        }
        
        # Region type buttons
        self.region_buttons = {
            "sum_eq": Button(750, 150, 180, 35, "Sum Equals", LIGHT_GRAY),
            "sum_lt": Button(750, 195, 180, 35, "Sum Less Than", LIGHT_GRAY),
            "sum_gt": Button(750, 240, 180, 35, "Sum Greater Than", LIGHT_GRAY),
            "all_eq": Button(750, 285, 180, 35, "All Equal", LIGHT_GRAY),
            "all_diff": Button(750, 330, 180, 35, "All Different", LIGHT_GRAY),
        }
        
        # Action buttons
        self.finish_region_button = Button(750, 400, 180, 40, "Finish Region", (150, 255, 150))
        self.clear_region_button = Button(750, 450, 180, 40, "Clear Selection", (255, 150, 150))
        self.add_domino_button = Button(950, 150, 180, 40, "Add Domino", (150, 255, 150))
        self.clear_board_button = Button(950, 20, 120, 40, "Clear All", (255, 100, 100))
        
    def get_grid_cell(self, pos):
        """Convert mouse position to grid cell coordinates"""
        x, y = pos
        col = (x - GRID_OFFSET_X) // GRID_SIZE
        row = (y - GRID_OFFSET_Y) // GRID_SIZE
        if 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS:
            return (row, col)
        return None
    
    def draw_grid(self):
        """Draw the grid and active cells"""
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                x = GRID_OFFSET_X + col * GRID_SIZE
                y = GRID_OFFSET_Y + row * GRID_SIZE
                
                # Determine cell color
                cell = (row, col)
                if cell in self.active_cells:
                    color = ACTIVE_CELL
                    if cell in self.current_region_cells:
                        color = SELECTED_CELL
                    # Check if part of existing region
                    for i, (region_cells, _, _) in enumerate(self.regions):
                        if self.cell_map.get(cell) in region_cells:
                            color = REGION_COLORS[i % len(REGION_COLORS)]
                    pygame.draw.rect(self.screen, color, (x, y, GRID_SIZE, GRID_SIZE))
                    
                    # Draw cell number
                    if cell in self.cell_map:
                        text = self.font.render(str(self.cell_map[cell]), True, BLACK)
                        self.screen.blit(text, (x + 5, y + 5))
                else:
                    pygame.draw.rect(self.screen, LIGHT_GRAY, (x, y, GRID_SIZE, GRID_SIZE))
                
                # Draw grid lines
                pygame.draw.rect(self.screen, GRAY, (x, y, GRID_SIZE, GRID_SIZE), 1)
    
    def draw_instructions(self):
        """Draw mode-specific instructions"""
        instructions = {
            "SETUP_BOARD": "Click cells to add them to the board. They will be numbered automatically.",
            "ADD_DOMINOS": "Enter domino values (0-6) and click 'Add Domino'. Example: a=3, b=4",
            "ADD_REGIONS": "1. Select region type, 2. Click cells to add to region, 3. Enter target (if needed), 4. Finish Region",
            "SOLVE": "Click 'Solve!' to find the solution and visualize it!"
        }
        
        text = self.font.render(instructions[self.mode], True, BLACK)
        self.screen.blit(text, (50, 730))
    
    def draw_dominos_list(self):
        """Draw the list of added dominos"""
        y = 150
        text = self.font.render("Dominos:", True, BLACK)
        self.screen.blit(text, (750, y))
        y += 30
        
        for i, (a, b) in enumerate(self.dominos):
            text = self.font.render(f"{i+1}. ({a}, {b})", True, BLACK)
            self.screen.blit(text, (750, y))
            y += 25
    
    def draw_regions_list(self):
        """Draw the list of added regions"""
        y = 500
        text = self.font.render("Regions:", True, BLACK)
        self.screen.blit(text, (750, y))
        y += 30
        
        for i, (cells, op, target) in enumerate(self.regions):
            color_rect = pygame.Rect(750, y, 20, 20)
            pygame.draw.rect(self.screen, REGION_COLORS[i % len(REGION_COLORS)], color_rect)
            
            target_str = f"={target}" if target is not None else ""
            text = self.font.render(f"{cells} {op} {target_str}", True, BLACK)
            self.screen.blit(text, (775, y))
            y += 25
    
    def draw_input_fields(self):
        """Draw input fields based on current mode"""
        if self.mode == "ADD_DOMINOS":
            # Domino input fields - moved to right side
            pygame.draw.rect(self.screen, WHITE, (950, 200, 80, 30))
            pygame.draw.rect(self.screen, BLACK, (950, 200, 80, 30), 2)
            text = self.font.render("a: " + self.domino_input["a"], True, BLACK)
            self.screen.blit(text, (955, 205))
            
            pygame.draw.rect(self.screen, WHITE, (1040, 200, 80, 30))
            pygame.draw.rect(self.screen, BLACK, (1040, 200, 80, 30), 2)
            text = self.font.render("b: " + self.domino_input["b"], True, BLACK)
            self.screen.blit(text, (1045, 205))
            
            self.add_domino_button.draw(self.screen, self.font)
            
        elif self.mode == "ADD_REGIONS":
            # Region target input
            if self.current_region_type in ["sum_eq", "sum_lt", "sum_gt"]:
                text = self.font.render("Target:", True, BLACK)
                self.screen.blit(text, (750, 365))
                
                pygame.draw.rect(self.screen, WHITE, (820, 360, 100, 30))
                pygame.draw.rect(self.screen, BLACK, (820, 360, 100, 30), 2)
                text = self.font.render(self.region_target_input, True, BLACK)
                self.screen.blit(text, (825, 365))
            
            self.finish_region_button.draw(self.screen, self.font)
            self.clear_region_button.draw(self.screen, self.font)
    
    def handle_board_click(self, cell):
        """Handle clicking a cell in SETUP_BOARD mode"""
        if cell in self.active_cells:
            self.active_cells.remove(cell)
            if cell in self.cell_map:
                del self.cell_map[cell]
        else:
            self.active_cells.add(cell)
        
        # Renumber cells
        self.cell_map = {}
        for i, c in enumerate(sorted(self.active_cells)):
            self.cell_map[c] = i
    
    def handle_region_click(self, cell):
        """Handle clicking a cell in ADD_REGIONS mode"""
        if cell in self.active_cells and self.current_region_type:
            cell_num = self.cell_map[cell]
            if cell in self.current_region_cells:
                self.current_region_cells.remove(cell)
            else:
                self.current_region_cells.append(cell)
    
    def add_domino(self):
        """Add a domino from input fields"""
        try:
            a = int(self.domino_input["a"])
            b = int(self.domino_input["b"])
            if 0 <= a <= 6 and 0 <= b <= 6:
                self.dominos.append((a, b))
                self.domino_input["a"] = ""
                self.domino_input["b"] = ""
        except ValueError:
            pass
    
    def finish_region(self):
        """Finish adding a region"""
        if self.current_region_cells and self.current_region_type:
            cell_nums = [self.cell_map[cell] for cell in self.current_region_cells]
            
            target = None
            if self.current_region_type in ["sum_eq", "sum_lt", "sum_gt"]:
                try:
                    target = int(self.region_target_input)
                except ValueError:
                    return  # Invalid target
            
            self.regions.append((cell_nums, self.current_region_type, target))
            self.current_region_cells = []
            self.region_target_input = ""
            self.current_region_type = None
            
            # Deactivate region buttons
            for button in self.region_buttons.values():
                button.active = False
    
    def solve_puzzle(self):
        """Solve the domino puzzle using Z3"""
        if not self.active_cells or not self.dominos:
            print("Please set up the board and add dominos first!")
            return
        
        # Build cells and edges
        cells = list(range(len(self.active_cells)))
        map_structure = self.build_map_structure()
        edges = self.list_edges_from_grid()
        
        print(f"\n=== Puzzle Setup ===")
        print(f"Map structure (like original code):")
        for row in map_structure:
            print(f"  {row}")
        print(f"\nCells: {cells}")
        print(f"Edges: {edges}")
        print(f"Dominos: {self.dominos}")
        print(f"Regions: {self.regions}")
        print(f"\nNumber of edges: {len(edges)}, Number of dominos: {len(self.dominos)}")
        
        if len(edges) != len(self.dominos):
            print(f"\n⚠️ WARNING: You have {len(self.dominos)} dominos but {len(edges)} edges!")
            print("Each domino needs exactly one edge (pair of adjacent cells).")
        
        # Call solver
        placements = self.run_solver(cells, self.dominos, edges, self.regions)
        
        if placements:
            # Visualize
            node_pos = {}
            for cell, cell_num in self.cell_map.items():
                node_pos[cell_num] = cell
            
            self.visualize_solution(placements, self.dominos, edges, node_pos)
        else:
            print("\n❌ No solution found!")
            print("Possible reasons:")
            print("- Region constraints are too strict")
            print("- Not enough dominos for the number of cells")
            print("- Domino values don't match region requirements")
    
    def build_map_structure(self):
        """Build map structure from active cells - fill gaps with -1"""
        if not self.active_cells:
            return []
        
        # Find the bounding box of active cells
        rows = [r for r, c in self.active_cells]
        cols = [c for r, c in self.active_cells]
        min_row, max_row = min(rows), max(rows)
        min_col, max_col = min(cols), max(cols)
        
        # Build map with -1 for empty cells
        map_structure = []
        for r in range(min_row, max_row + 1):
            row = []
            for c in range(min_col, max_col + 1):
                if (r, c) in self.active_cells:
                    row.append(self.cell_map[(r, c)])
                else:
                    row.append(-1)
            map_structure.append(row)
        
        return map_structure
    
    def list_edges_from_grid(self):
        """Generate edges from map structure - matches original code"""
        map_structure = self.build_map_structure()
        edges = []
        rows = len(map_structure)
        
        for r in range(rows):
            cols = len(map_structure[r])
            # Horizontal edges within row
            for c in range(cols - 1):
                if map_structure[r][c] != -1 and map_structure[r][c + 1] != -1:
                    edges.append((map_structure[r][c], map_structure[r][c + 1]))
            
            # Vertical edges to next row
            if r < rows - 1:
                for c in range(min(cols, len(map_structure[r + 1]))):
                    if c < len(map_structure[r]) and c < len(map_structure[r + 1]):
                        if map_structure[r][c] != -1 and map_structure[r + 1][c] != -1:
                            edges.append((map_structure[r][c], map_structure[r + 1][c]))
        
        return edges
    
    def run_solver(self, cells, dominos, edges, regions):
        """Run Z3 solver"""
        solver = Solver()
        
        D = len(dominos)
        E = len(edges)
        
        # Variables
        place = {}
        for d in range(D):
            for e in range(E):
                for o in [0, 1]:
                    place[(d, e, o)] = Bool(f"place_{d}_{e}_{o}")
        
        cell_val = [Int(f"v_{c}") for c in cells]
        for c in cells:
            solver.add(And(cell_val[c] >= 0, cell_val[c] <= 6))
        
        # Each domino placed exactly once
        for d in range(D):
            choices = [place[(d, e, o)] for e in range(E) for o in [0, 1]]
            solver.add(AtLeast(*choices, 1))
            solver.add(AtMost(*choices, 1))
        
        # Build touches
        touches = {c: [] for c in cells}
        for d, (a, b) in enumerate(dominos):
            for e, (c1, c2) in enumerate(edges):
                for o in [0, 1]:
                    p = place[(d, e, o)]
                    if o == 0:
                        v1, v2 = a, b
                    else:
                        v1, v2 = b, a
                    touches[c1].append((p, v1))
                    touches[c2].append((p, v2))
        
        # Each cell touched exactly once
        for c in cells:
            bools = [p for (p, v) in touches[c]]
            solver.add(AtLeast(*bools, 1))
            solver.add(AtMost(*bools, 1))
            
            constraints = []
            for (p, v) in touches[c]:
                constraints.append(Implies(p, cell_val[c] == v))
            solver.add(And(*constraints))
        
        # Region constraints
        for cells_R, op, target in regions:
            vals = [cell_val[c] for c in cells_R]
            
            if op == "sum_eq":
                solver.add(Sum(vals) == target)
            elif op == "sum_lt":
                solver.add(Sum(vals) < target)
            elif op == "sum_gt":
                solver.add(Sum(vals) > target)
            elif op == "all_eq":
                base = vals[0]
                solver.add(And([v == base for v in vals]))
            elif op == "all_diff":
                solver.add(Distinct(vals))
        
        # Solve
        if solver.check() == sat:
            model = solver.model()
            placements = []
            for d in range(D):
                for e in range(E):
                    for o in [0, 1]:
                        if model.evaluate(place[(d, e, o)], model_completion=True):
                            placements.append((d, e, o))
            return placements
        else:
            return None
    
    def visualize_solution(self, placements, dominos, edges, node_pos):
        """Visualize the solution using matplotlib"""
        # Use actual grid dimensions (8x8 from pygame grid)
        rows = GRID_ROWS
        cols = GRID_COLS
        
        tiles = []
        for dom_idx, edge_idx, flipped in placements:
            a, b = dominos[dom_idx]
            if flipped == 1:
                a, b = b, a
            
            n1, n2 = edges[edge_idx]
            # node_pos maps cell_num -> (row, col) from original pygame grid
            c1 = node_pos[n1]
            c2 = node_pos[n2]
            
            label = f"{a}-{b}"
            tiles.append({
                "cells": [c1, c2],
                "value": label,
            })
        
        # Plot
        fig, ax = plt.subplots(figsize=(10, 10))
        ax.set_xlim(0, cols)
        ax.set_ylim(0, rows)
        ax.set_aspect("equal")
        ax.invert_yaxis()
        
        # Draw all grid cells (faded background)
        for row in range(rows):
            for col in range(cols):
                rect = patches.Rectangle(
                    (col, row), 1, 1,
                    fill=False,
                    linewidth=0.5,
                    edgecolor=(0.8, 0.8, 0.8),
                    linestyle=":"
                )
                ax.add_patch(rect)
        
        # Draw active cells
        for cell in self.active_cells:
            row, col = cell
            rect = patches.Rectangle(
                (col, row), 1, 1,
                fill=True,
                linewidth=1,
                edgecolor=(0.5, 0.5, 0.5),
                facecolor=(0.95, 0.95, 0.95),
                alpha=0.5
            )
            ax.add_patch(rect)
        
        # Draw domino tiles
        cmap = plt.cm.get_cmap("tab20")
        for i, tile in enumerate(tiles):
            cells = tile["cells"]
            color = cmap(i % 20)
            
            # cells are (row, col) tuples
            rows_ = [r for (r, c) in cells]
            cols_ = [c for (r, c) in cells]
            min_r, max_r = min(rows_), max(rows_)
            min_c, max_c = min(cols_), max(cols_)
            
            # x is column, y is row
            x, y = min_c, min_r
            w = max_c - min_c + 1
            h = max_r - min_r + 1
            
            rect = patches.Rectangle(
                (x, y), w, h,
                linewidth=3,
                edgecolor="black",
                facecolor=color,
                alpha=0.8,
            )
            ax.add_patch(rect)
            
            value = tile.get("value", "")
            cx = x + w / 2
            cy = y + h / 2
            ax.text(cx, cy, str(value), ha="center", va="center",
                    fontsize=14, weight="bold")
        
        ax.set_xticks([])
        ax.set_yticks([])
        plt.title("Domino Puzzle Solution", fontsize=16)
        plt.tight_layout()
        plt.show()
    
    def run(self):
        """Main game loop"""
        running = True
        
        while running:
            self.screen.fill(WHITE)
            
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    pos = pygame.mouse.get_pos()
                    
                    # Check mode buttons
                    for mode, button in self.mode_buttons.items():
                        if button.is_clicked(pos):
                            self.mode = mode
                    
                    # Check clear button
                    if self.clear_board_button.is_clicked(pos):
                        self.active_cells.clear()
                        self.cell_map.clear()
                        self.dominos.clear()
                        self.regions.clear()
                        self.current_region_cells.clear()
                        self.mode = "SETUP_BOARD"
                    
                    # Handle grid clicks
                    cell = self.get_grid_cell(pos)
                    if cell:
                        if self.mode == "SETUP_BOARD":
                            self.handle_board_click(cell)
                        elif self.mode == "ADD_REGIONS":
                            self.handle_region_click(cell)
                    
                    # Mode-specific buttons
                    if self.mode == "ADD_DOMINOS":
                        if self.add_domino_button.is_clicked(pos):
                            self.add_domino()
                        
                        # Check input field clicks - updated positions
                        if 950 <= pos[0] <= 1030 and 200 <= pos[1] <= 230:
                            self.active_input = "a"
                        elif 1040 <= pos[0] <= 1120 and 200 <= pos[1] <= 230:
                            self.active_input = "b"
                        else:
                            self.active_input = None
                    
                    elif self.mode == "ADD_REGIONS":
                        for region_type, button in self.region_buttons.items():
                            if button.is_clicked(pos):
                                self.current_region_type = region_type
                                # Set all buttons inactive
                                for btn in self.region_buttons.values():
                                    btn.active = False
                                button.active = True
                        
                        if self.finish_region_button.is_clicked(pos):
                            self.finish_region()
                        
                        if self.clear_region_button.is_clicked(pos):
                            self.current_region_cells.clear()
                        
                        # Check target input field
                        if 820 <= pos[0] <= 920 and 360 <= pos[1] <= 390:
                            self.active_input = "target"
                        else:
                            if not any(button.is_clicked(pos) for button in self.region_buttons.values()):
                                self.active_input = None
                    
                    elif self.mode == "SOLVE":
                        # Solve button is the mode button itself
                        pass
                
                elif event.type == pygame.KEYDOWN:
                    if self.mode == "ADD_DOMINOS" and self.active_input:
                        if event.key == pygame.K_BACKSPACE:
                            self.domino_input[self.active_input] = self.domino_input[self.active_input][:-1]
                        elif event.unicode.isdigit():
                            self.domino_input[self.active_input] += event.unicode
                    
                    elif self.mode == "ADD_REGIONS" and self.active_input == "target":
                        if event.key == pygame.K_BACKSPACE:
                            self.region_target_input = self.region_target_input[:-1]
                        elif event.unicode.isdigit():
                            self.region_target_input += event.unicode
            
            # Check if solve mode activated
            if self.mode == "SOLVE":
                self.solve_puzzle()
                self.mode = "ADD_REGIONS"  # Reset back
            
            # Draw everything
            self.draw_grid()
            
            # Draw mode buttons
            for mode, button in self.mode_buttons.items():
                button.active = (mode == self.mode)
                button.draw(self.screen, self.font)
            
            self.clear_board_button.draw(self.screen, self.font)
            
            # Draw region buttons
            if self.mode == "ADD_REGIONS":
                for button in self.region_buttons.values():
                    button.draw(self.screen, self.font)
            
            # Draw mode-specific content
            if self.mode == "ADD_DOMINOS":
                self.draw_dominos_list()
            elif self.mode == "ADD_REGIONS":
                self.draw_regions_list()
            
            self.draw_input_fields()
            self.draw_instructions()
            
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    app = DominoPuzzleBuilder()
    app.run()