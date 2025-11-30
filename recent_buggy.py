# main.py
import pygame
import random
import math
import sys
import os
import json
from datetime import datetime
from enum import Enum

# Инициализация Pygame
pygame.init()
pygame.mixer.init()

# Константы
INITIAL_WIDTH, INITIAL_HEIGHT = 800, 600
FPS = 60
ROAD_WIDTH = 400
PLAYER_SPEED = 5
MAX_ENEMY_SPEED = 7
MIN_ENEMY_SPEED = 3

# Цвета в ретро-стиле
BLACK = (0, 0, 0)
DARK_GRAY = (20, 20, 20)
RED = (255, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
BLUE = (0, 100, 255)
GRAY = (100, 100, 100)
GREEN = (0, 255, 0)
PURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)
CYAN = (0, 255, 255)
PINK = (255, 105, 180)

class GameState(Enum):
    MENU = 0
    CAR_SELECT = 1
    NAME_INPUT = 2
    PLAYING = 3
    GAME_OVER = 4
    PAUSED = 5
    LEADERBOARD = 6
    SETTINGS = 7
    RACE_MODE = 8

class CarType(Enum):
    AE86 = {"name": "AE86 Trueno", "color": WHITE, "handling": 1.2, "drift": 1.5, "acceleration": 1.1, "max_speed": 11, "drift_slowdown": 0.98}
    RX7 = {"name": "Mazda RX-7", "color": RED, "handling": 1.0, "drift": 1.3, "acceleration": 1.3, "max_speed": 12, "drift_slowdown": 0.985}
    GTR = {"name": "Nissan GTR", "color": BLUE, "handling": 0.8, "drift": 1.0, "acceleration": 1.4, "max_speed": 13, "drift_slowdown": 0.975}
    EVO = {"name": "Lancer Evo", "color": GRAY, "handling": 1.1, "drift": 1.2, "acceleration": 1.2, "max_speed": 12, "drift_slowdown": 0.98}
    SUPRA = {"name": "Toyota Supra", "color": PURPLE, "handling": 0.9, "drift": 1.1, "acceleration": 1.5, "max_speed": 14, "drift_slowdown": 0.97}

class TurnDirection(Enum):
    STRAIGHT = 0
    LEFT = 1
    RIGHT = 2

class Leaderboard:
    def __init__(self, filename="leaderboard.json"):
        self.filename = filename
        self.entries = []
        self.used_names = set()
        self.load()

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    data = json.load(f)
                    self.entries = data.get('entries', [])
                    self.used_names = {entry['name'] for entry in self.entries}
            except:
                self.entries = []
                self.used_names = set()
        else:
            self.entries = []
            self.used_names = set()

    def save(self):
        data = {'entries': self.entries}
        with open(self.filename, 'w') as f:
            json.dump(data, f, indent=2)

    def is_name_used(self, name):
        return name in self.used_names

    def add_entry(self, name, score, drift_score, car_type, date=None):
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d %H:%M")

        entry = {
            'name': name,
            'score': score,
            'drift_score': drift_score,
            'car_type': car_type,
            'date': date
        }

        self.entries.append(entry)
        self.used_names.add(name)
        self.entries.sort(key=lambda x: x['score'], reverse=True)
        self.entries = self.entries[:50]
        self.save()

    def get_entries(self, car_filter=None):
        entries = self.entries
        if car_filter:
            entries = [entry for entry in entries if entry['car_type'] == car_filter]
        return entries

    def get_top_entries(self, count=10, car_filter=None):
        entries = self.get_entries(car_filter)
        return entries[:count]

class CRT:
    def __init__(self, screen):
        self.screen = screen
        self.scanlines = None
        self.vignette = None
        self.update_effects(screen.get_size())

    def update_effects(self, size):
        width, height = size
        self.scanlines = self.create_scanlines(width, height)
        self.vignette = self.create_vignette(width, height)

    def create_scanlines(self, width, height):
        scanline_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        for y in range(0, height, 3):
            pygame.draw.line(scanline_surface, (0, 0, 0, 60), (0, y), (width, y), 1)
        return scanline_surface

    def create_vignette(self, width, height):
        vignette = pygame.Surface((width, height), pygame.SRCALPHA)
        center_x, center_y = width // 2, height // 2
        max_radius = math.sqrt(center_x**2 + center_y**2)

        for y in range(height):
            for x in range(width):
                dist = math.sqrt((x - center_x)**2 + (y - center_y)**2)
                alpha = min(150, int(200 * (dist / max_radius)))
                vignette.set_at((x, y), (0, 0, 0, alpha))
        return vignette

    def draw(self, surface=None):
        target = surface if surface else self.screen
        target.blit(self.scanlines, (0, 0))
        target.blit(self.vignette, (0, 0))

class DriftEffect:
    def __init__(self):
        self.particles = []
        self.trails = []
        self.lightning_timer = 0
        self.combo_flash = 0

    def add_particle(self, x, y, drift_power, drift_combo):
        if drift_combo >= 10:
            for _ in range(3):
                color = random.choice([CYAN, PINK, YELLOW, WHITE])
                size = random.randint(3, 8)
                speed = random.uniform(1, 3)
                angle = random.uniform(0, 2 * math.pi)
                life = random.randint(20, 40)
                self.particles.append({
                    'x': x, 'y': y, 'color': color, 'size': size,
                    'vx': math.cos(angle) * speed, 'vy': math.sin(angle) * speed,
                    'life': life, 'max_life': life
                })
        elif drift_combo >= 5:
            for _ in range(2):
                color = random.choice([YELLOW, WHITE, ORANGE])
                size = random.randint(2, 6)
                speed = random.uniform(0.5, 2)
                angle = random.uniform(0, 2 * math.pi)
                life = random.randint(15, 30)
                self.particles.append({
                    'x': x, 'y': y, 'color': color, 'size': size,
                    'vx': math.cos(angle) * speed, 'vy': math.sin(angle) * speed,
                    'life': life, 'max_life': life
                })
        else:
            color = (200, 200, 200, random.randint(100, 200))
            size = random.randint(10, 25)
            self.particles.append({
                'x': x, 'y': y, 'color': color, 'size': size,
                'vx': random.uniform(-1, 1), 'vy': random.uniform(-2, 0),
                'life': 30, 'max_life': 30
            })

    def add_trail(self, x, y, drift_angle, drift_power):
        intensity = min(255, 100 + int(drift_power * 1.5))
        color = (255, 255, 0, intensity)

        if drift_power > 80:
            color = (255, 0, 0, intensity)
        elif drift_power > 60:
            color = (255, 165, 0, intensity)

        self.trails.append({
            'x': x, 'y': y, 'color': color,
            'width': int(10 + drift_power * 0.2),
            'life': 20
        })

    def update(self):
        for particle in self.particles[:]:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['life'] -= 1
            particle['vy'] += 0.1

            if particle['life'] <= 0:
                self.particles.remove(particle)

        for trail in self.trails[:]:
            trail['life'] -= 1
            if trail['life'] <= 0:
                self.trails.remove(trail)

        self.lightning_timer = max(0, self.lightning_timer - 1)
        self.combo_flash = max(0, self.combo_flash - 1)

    def draw(self, screen):
        for trail in self.trails:
            alpha = int(trail['color'][3] * (trail['life'] / 20))
            trail_color = (*trail['color'][:3], alpha)
            trail_surface = pygame.Surface((trail['width'], trail['width']), pygame.SRCALPHA)
            pygame.draw.circle(trail_surface, trail_color,
                             (trail['width']//2, trail['width']//2), trail['width']//2)
            screen.blit(trail_surface, (trail['x'] - trail['width']//2, trail['y'] - trail['width']//2))

        for particle in self.particles:
            alpha = int(255 * (particle['life'] / particle['max_life']))
            if len(particle['color']) == 3:
                color_with_alpha = (*particle['color'], alpha)
            else:
                color_with_alpha = particle['color']

            surf = pygame.Surface((particle['size'], particle['size']), pygame.SRCALPHA)
            pygame.draw.circle(surf, color_with_alpha,
                             (particle['size']//2, particle['size']//2), particle['size']//2)
            screen.blit(surf, (int(particle['x']), int(particle['y'])))

        if self.combo_flash > 0:
            flash_alpha = int(100 * (self.combo_flash / 10))
            flash_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            flash_surface.fill((255, 255, 255, flash_alpha))
            screen.blit(flash_surface, (0, 0))

    def trigger_combo_flash(self):
        self.combo_flash = 10

class PlayerCar:
    def __init__(self, car_type, screen_width, screen_height, num_lanes=3, insane_mode=False):
        self.car_type = car_type
        self.stats = car_type.value
        self.width = 40
        self.height = 70
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.num_lanes = num_lanes
        self.insane_mode = insane_mode

        # Fixed lane positioning to prevent overlap
        if num_lanes == 4:
            self.lanes_x = [
                screen_width//2 - ROAD_WIDTH//2 + ROAD_WIDTH//8,
                screen_width//2 - ROAD_WIDTH//4 + ROAD_WIDTH//8,
                screen_width//2 + ROAD_WIDTH//8,
                screen_width//2 + ROAD_WIDTH//4 + ROAD_WIDTH//8
            ]
            self.lane = 1
        elif num_lanes == 3:
            # Better spaced lanes for 3-lane mode
            lane_spacing = ROAD_WIDTH // 3
            self.lanes_x = [
                screen_width//2 - ROAD_WIDTH//2 + lane_spacing//2,
                screen_width//2,
                screen_width//2 + ROAD_WIDTH//2 - lane_spacing//2
            ]
            self.lane = 1
        else:
            self.lanes_x = [
                screen_width//2 - ROAD_WIDTH//4,
                screen_width//2 + ROAD_WIDTH//4
            ]
            self.lane = 0

        self.x = self.lanes_x[self.lane]
        self.y = screen_height - 100
        self.speed = 0

        speed_multiplier = 1.5 if insane_mode else 1.0
        self.max_speed = self.stats["max_speed"] * speed_multiplier
        self.acceleration = 0.2 * self.stats["acceleration"] * speed_multiplier
        self.deceleration = 0.1
        self.handling = 4 * self.stats["handling"]
        self.target_x = self.lanes_x[self.lane]
        self.drift_angle = 0
        self.drift_power = 0
        self.nitro = 100
        self.score = 0
        self.combo = 0
        self.last_overtake = 0
        self.drift_score = 0
        self.drift_combo = 0
        self.last_drift_time = 0
        self.is_drifting = False
        self.drift_bonus_active = False
        self.drift_slowdown = self.stats["drift_slowdown"]
        self.drift_effect = DriftEffect()
        self.max_drift_combo = 0

    def update_size(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Update lane positions with proper spacing
        if self.num_lanes == 4:
            self.lanes_x = [
                screen_width//2 - ROAD_WIDTH//2 + ROAD_WIDTH//8,
                screen_width//2 - ROAD_WIDTH//4 + ROAD_WIDTH//8,
                screen_width//2 + ROAD_WIDTH//8,
                screen_width//2 + ROAD_WIDTH//4 + ROAD_WIDTH//8
            ]
        elif self.num_lanes == 3:
            lane_spacing = ROAD_WIDTH // 3
            self.lanes_x = [
                screen_width//2 - ROAD_WIDTH//2 + lane_spacing//2,
                screen_width//2,
                screen_width//2 + ROAD_WIDTH//2 - lane_spacing//2
            ]
        else:
            self.lanes_x = [
                screen_width//2 - ROAD_WIDTH//4,
                screen_width//2 + ROAD_WIDTH//4
            ]

        # FIX: Ensure lane index is within bounds after resize
        if self.lane >= len(self.lanes_x):
            self.lane = len(self.lanes_x) - 1
            
        self.x = self.lanes_x[self.lane]
        self.target_x = self.lanes_x[self.lane]
        self.y = screen_height - 100

    def update(self, keys, turn_direction, turn_intensity):
        if keys[pygame.K_UP]:
            self.speed = min(self.speed + self.acceleration, self.max_speed)
        elif keys[pygame.K_DOWN]:
            self.speed = max(self.speed - self.deceleration * 2, 0)
        else:
            self.speed = max(self.speed - self.deceleration, 0)

        move_speed = self.handling * (0.8 if self.is_drifting else 1.0)
        self.x += (self.target_x - self.x) * 0.1 * move_speed

        if turn_direction != TurnDirection.STRAIGHT:
            turn_factor = turn_intensity * 0.5
            if turn_direction == TurnDirection.LEFT:
                self.target_x += turn_factor
            else:
                self.target_x -= turn_factor

            self.target_x = max(self.lanes_x[0], min(self.lanes_x[-1], self.target_x))

        self.is_drifting = keys[pygame.K_z] and abs(self.speed) > 3
        if self.is_drifting:
            self.drift_power = min(self.drift_power + 0.5, 100)

            max_drift_angle = 25 * self.stats["drift"]
            drift_direction = 1 if keys[pygame.K_LEFT] else -1 if keys[pygame.K_RIGHT] else 0
            if drift_direction == 0:
                if turn_direction == TurnDirection.LEFT:
                    drift_direction = 1
                elif turn_direction == TurnDirection.RIGHT:
                    drift_direction = -1

            self.drift_angle = drift_direction * (max_drift_angle * (self.drift_power / 100))

            if turn_direction != TurnDirection.STRAIGHT:
                current_time = pygame.time.get_ticks()
                if current_time - self.last_drift_time > 150:
                    turn_bonus = 0.5 + turn_intensity * 0.5
                    combo_multiplier = 1 + (self.drift_combo ** 1.2) * 0.1
                    drift_points = int(self.drift_power * 0.1 * combo_multiplier * turn_bonus)
                    self.drift_score += drift_points
                    self.score += drift_points
                    self.last_drift_time = current_time
                    self.drift_combo += 1
                    self.drift_bonus_active = True

                    if self.drift_combo > self.max_drift_combo:
                        self.max_drift_combo = self.drift_combo

                    if self.drift_combo in [5, 10, 15, 20, 25, 30]:
                        self.drift_effect.trigger_combo_flash()
            else:
                self.drift_bonus_active = False

            self.speed *= self.drift_slowdown

            side = -1 if self.drift_angle > 0 else 1
            effect_x = self.x + side * random.randint(20, 40)
            effect_y = self.y + random.randint(10, 30)
            self.drift_effect.add_particle(effect_x, effect_y, self.drift_power, self.drift_combo)
            self.drift_effect.add_trail(effect_x, effect_y, self.drift_angle, self.drift_power)
        else:
            self.drift_angle *= 0.8
            self.drift_power *= 0.9
            if self.drift_power < 5:
                self.drift_power = 0
                if self.drift_combo > 0 and self.drift_bonus_active:
                    combo_bonus = self.drift_combo * 20
                    self.score += combo_bonus
                    self.drift_score += combo_bonus
                self.drift_combo = 0
                self.drift_bonus_active = False

        if keys[pygame.K_x] and self.nitro > 0 and self.speed > 0:
            self.speed = min(self.speed + 0.5, self.max_speed * 1.3)
            self.nitro -= 1

        if self.nitro < 100 and not keys[pygame.K_x]:
            self.nitro += 0.1

        if pygame.time.get_ticks() - self.last_overtake > 2000:
            self.combo = max(0, self.combo - 1)

        self.drift_effect.update()

    def draw(self, screen, turn_direction, turn_intensity):
        self.drift_effect.draw(screen)

        car_color = self.stats["color"]
        car_rect = pygame.Rect(0, 0, self.width, self.height)
        car_rect.center = (self.x, self.y)

        car_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

        pygame.draw.rect(car_surface, car_color, (0, 0, self.width, self.height))
        pygame.draw.rect(car_surface, BLACK, (0, 0, self.width, self.height), 2)

        pygame.draw.rect(car_surface, YELLOW, (5, 5, 8, 5))
        pygame.draw.rect(car_surface, YELLOW, (self.width-13, 5, 8, 5))
        pygame.draw.rect(car_surface, RED, (5, self.height-10, 8, 5))
        pygame.draw.rect(car_surface, RED, (self.width-13, self.height-10, 8, 5))

        if self.car_type == CarType.AE86:
            font = pygame.font.SysFont('Arial', 10, bold=True)
            text = font.render("INITIAL D", True, RED)
            car_surface.blit(text, (self.width//2 - text.get_width()//2, self.height//2 - 5))

        total_angle = self.drift_angle
        if turn_direction != TurnDirection.STRAIGHT:
            turn_angle = turn_intensity * 5 * (1 if turn_direction == TurnDirection.LEFT else -1)
            total_angle += turn_angle * (0.5 if self.is_drifting else 0.2)

        rotated_car = pygame.transform.rotate(car_surface, total_angle)
        rotated_rect = rotated_car.get_rect(center=car_rect.center)
        screen.blit(rotated_car, rotated_rect)

class EnemyCar:
    def __init__(self, player_speed, turn_direction, turn_intensity, screen_width, screen_height, num_lanes=3, insane_mode=False):
        self.type = random.choice(list(CarType))
        self.stats = self.type.value
        self.width = 40
        self.height = 70
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.num_lanes = num_lanes

        # Use the same lane positioning as PlayerCar
        if num_lanes == 4:
            self.lanes_x = [
                screen_width//2 - ROAD_WIDTH//2 + ROAD_WIDTH//8,
                screen_width//2 - ROAD_WIDTH//4 + ROAD_WIDTH//8,
                screen_width//2 + ROAD_WIDTH//8,
                screen_width//2 + ROAD_WIDTH//4 + ROAD_WIDTH//8
            ]
        elif num_lanes == 3:
            lane_spacing = ROAD_WIDTH // 3
            self.lanes_x = [
                screen_width//2 - ROAD_WIDTH//2 + lane_spacing//2,
                screen_width//2,
                screen_width//2 + ROAD_WIDTH//2 - lane_spacing//2
            ]
        else:
            self.lanes_x = [
                screen_width//2 - ROAD_WIDTH//4,
                screen_width//2 + ROAD_WIDTH//4
            ]

        self.lane = random.randint(0, self.num_lanes - 1)
        self.x = self.lanes_x[self.lane]
        self.y = -100

        speed_multiplier = 1.5 if insane_mode else 1.0
        self.speed = random.uniform(MIN_ENEMY_SPEED, MAX_ENEMY_SPEED) * speed_multiplier + player_speed * 0.3
        self.passed = False
        self.turn_offset = 0

    def update_size(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height

        if self.num_lanes == 4:
            self.lanes_x = [
                screen_width//2 - ROAD_WIDTH//2 + ROAD_WIDTH//8,
                screen_width//2 - ROAD_WIDTH//4 + ROAD_WIDTH//8,
                screen_width//2 + ROAD_WIDTH//8,
                screen_width//2 + ROAD_WIDTH//4 + ROAD_WIDTH//8
            ]
        elif self.num_lanes == 3:
            lane_spacing = ROAD_WIDTH // 3
            self.lanes_x = [
                screen_width//2 - ROAD_WIDTH//2 + lane_spacing//2,
                screen_width//2,
                screen_width//2 + ROAD_WIDTH//2 - lane_spacing//2
            ]
        else:
            self.lanes_x = [
                screen_width//2 - ROAD_WIDTH//4,
                screen_width//2 + ROAD_WIDTH//4
            ]

        # FIX: Ensure lane index is within bounds after resize
        if self.lane >= len(self.lanes_x):
            self.lane = len(self.lanes_x) - 1
            
        self.x = self.lanes_x[self.lane]

    def update(self, player_speed, turn_direction, turn_intensity):
        self.y += self.speed

        if turn_direction != TurnDirection.STRAIGHT:
            turn_factor = turn_intensity * 0.3
            if turn_direction == TurnDirection.LEFT:
                self.turn_offset += turn_factor
            else:
                self.turn_offset -= turn_factor

        self.x = self.lanes_x[self.lane] + self.turn_offset

        return self.y > self.screen_height + 100

    def draw(self, screen, turn_direction, turn_intensity):
        color = self.stats["color"]
        car_rect = pygame.Rect(0, 0, self.width, self.height)
        car_rect.center = (self.x, self.y)

        car_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pygame.draw.rect(car_surface, color, (0, 0, self.width, self.height))
        pygame.draw.rect(car_surface, BLACK, (0, 0, self.width, self.height), 2)

        pygame.draw.rect(car_surface, YELLOW, (5, 5, 8, 5))
        pygame.draw.rect(car_surface, YELLOW, (self.width-13, 5, 8, 5))

        turn_angle = 0
        if turn_direction != TurnDirection.STRAIGHT:
            turn_angle = turn_intensity * 3 * (1 if turn_direction == TurnDirection.LEFT else -1)

        rotated_car = pygame.transform.rotate(car_surface, turn_angle)
        rotated_rect = rotated_car.get_rect(center=car_rect.center)
        screen.blit(rotated_car, rotated_rect)

    def check_collision(self, player):
        player_rect = pygame.Rect(player.x - player.width//2, player.y - player.height//2,
                                player.width, player.height)
        enemy_rect = pygame.Rect(self.x - self.width//2, self.y - self.height//2,
                               self.width, self.height)
        return player_rect.colliderect(enemy_rect)

class Road:
    def __init__(self, screen_width, screen_height, num_lanes=3):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.num_lanes = num_lanes
        self.line_height = 40
        self.line_width = 10
        self.line_spacing = 60
        self.line_positions = []
        self.speed = 0
        self.curve = 0
        self.curve_target = 0
        self.curve_change_timer = 0
        self.current_turn = TurnDirection.STRAIGHT
        self.turn_intensity = 0
        self.turn_progress = 0

        for y in range(-self.line_height, screen_height + self.line_height, self.line_spacing):
            self.line_positions.append(y)

    def update_size(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height

        self.line_positions = []
        for y in range(-self.line_height, screen_height + self.line_height, self.line_spacing):
            self.line_positions.append(y)

    def update(self, speed):
        self.speed = speed

        self.curve_change_timer += 1
        if self.curve_change_timer > 180:
            self.curve_change_timer = 0
            if random.random() < 0.7:
                self.current_turn = random.choice([TurnDirection.LEFT, TurnDirection.RIGHT])
                self.turn_intensity = random.uniform(0.3, 1.0)
                self.curve_target = self.turn_intensity * 100 * (1 if self.current_turn == TurnDirection.LEFT else -1)
                self.turn_progress = 0
            else:
                self.current_turn = TurnDirection.STRAIGHT
                self.turn_intensity = 0
                self.curve_target = 0
                self.turn_progress = 0

        self.curve += (self.curve_target - self.curve) * 0.05

        if self.current_turn != TurnDirection.STRAIGHT:
            self.turn_progress = min(100, self.turn_progress + 0.5)

        for i in range(len(self.line_positions)):
            self.line_positions[i] += speed
            if self.line_positions[i] > self.screen_height + self.line_height:
                self.line_positions[i] = -self.line_height

    def draw(self, screen):
        road_rect = pygame.Rect(self.screen_width//2 - ROAD_WIDTH//2, 0, ROAD_WIDTH, self.screen_height)
        pygame.draw.rect(screen, DARK_GRAY, road_rect)

        for y in self.line_positions:
            curve_offset = self.curve * (y / self.screen_height) * 0.5
            line_rect = pygame.Rect(self.screen_width//2 - self.line_width//2 + curve_offset, y,
                                  self.line_width, self.line_height)
            pygame.draw.rect(screen, YELLOW, line_rect)

        for y in range(0, self.screen_height, 20):
            curve_offset = self.curve * (y / self.screen_height) * 0.5
            left_border = self.screen_width//2 - ROAD_WIDTH//2 - 20 + curve_offset
            right_border = self.screen_width//2 + ROAD_WIDTH//2 + curve_offset

            pygame.draw.rect(screen, GRAY, (left_border, y, 20, 10))
            pygame.draw.rect(screen, GRAY, (right_border, y, 20, 10))

        for y in range(0, self.screen_height, 40):
            curve_offset = self.curve * (y / self.screen_height) * 0.5

            if self.num_lanes == 4:
                for i in range(1, 4):
                    divider_x = self.screen_width//2 - ROAD_WIDTH//2 + (ROAD_WIDTH * i) // 4 + curve_offset
                    pygame.draw.rect(screen, (150, 150, 150, 100), (divider_x - 1, y, 2, 20))
            elif self.num_lanes == 3:
                for i in range(1, 3):
                    divider_x = self.screen_width//2 - ROAD_WIDTH//2 + (ROAD_WIDTH * i) // 3 + curve_offset
                    pygame.draw.rect(screen, (150, 150, 150, 100), (divider_x - 1, y, 2, 20))
            else:
                divider_x = self.screen_width//2 + curve_offset
                pygame.draw.rect(screen, (150, 150, 150, 100), (divider_x - 1, y, 2, 20))

        if self.current_turn != TurnDirection.STRAIGHT and self.turn_intensity > 0.5:
            warning_font = pygame.font.SysFont('courier', 24, bold=True)
            if self.current_turn == TurnDirection.LEFT:
                warning_text = warning_font.render("← LEFT TURN", True, YELLOW)
            else:
                warning_text = warning_font.render("RIGHT TURN →", True, YELLOW)

            screen.blit(warning_text, (self.screen_width//2 - warning_text.get_width()//2, 50))

            progress_width = 200
            pygame.draw.rect(screen, DARK_GRAY, (self.screen_width//2 - progress_width//2, 90, progress_width, 10))
            pygame.draw.rect(screen, GREEN, (self.screen_width//2 - progress_width//2, 90, progress_width * (self.turn_progress / 100), 10))

    # Add this method to fix the error
    def get_race_progress(self):
        return 0  # Regular road doesn't have race progress

class RaceRoad(Road):
    def __init__(self, screen_width, screen_height, num_lanes=3):
        super().__init__(screen_width, screen_height, num_lanes)
        self.turn_sequence = []
        self.current_turn_index = 0
        self.turn_progress = 0
        self.race_distance = 0
        self.generate_turn_sequence()

    def generate_turn_sequence(self):
        turns = [
            (TurnDirection.LEFT, 0.8, 120),
            (TurnDirection.STRAIGHT, 0, 60),
            (TurnDirection.RIGHT, 0.9, 100),
            (TurnDirection.STRAIGHT, 0, 40),
            (TurnDirection.LEFT, 0.7, 80),
            (TurnDirection.RIGHT, 0.6, 70),
            (TurnDirection.STRAIGHT, 0, 50),
            (TurnDirection.LEFT, 1.0, 150),
            (TurnDirection.RIGHT, 0.8, 90),
            (TurnDirection.STRAIGHT, 0, 30),
            (TurnDirection.LEFT, 0.9, 110),
            (TurnDirection.RIGHT, 0.7, 85),
            (TurnDirection.STRAIGHT, 0, 60),
            (TurnDirection.LEFT, 0.6, 75),
            (TurnDirection.RIGHT, 1.0, 140),
        ]
        self.turn_sequence = turns

    def update(self, speed):
        self.speed = speed
        self.race_distance += speed

        if self.current_turn_index < len(self.turn_sequence):
            current_turn = self.turn_sequence[self.current_turn_index]
            self.current_turn = current_turn[0]
            self.turn_intensity = current_turn[1]

            self.turn_progress += speed
            if self.turn_progress >= current_turn[2]:
                self.turn_progress = 0
                self.current_turn_index += 1
                if self.current_turn_index >= len(self.turn_sequence):
                    self.current_turn_index = 0
        else:
            self.current_turn = TurnDirection.STRAIGHT
            self.turn_intensity = 0

        if self.current_turn == TurnDirection.LEFT:
            self.curve_target = self.turn_intensity * 150
        elif self.current_turn == TurnDirection.RIGHT:
            self.curve_target = -self.turn_intensity * 150
        else:
            self.curve_target = 0

        self.curve += (self.curve_target - self.curve) * 0.03

        for i in range(len(self.line_positions)):
            self.line_positions[i] += speed
            if self.line_positions[i] > self.screen_height + self.line_height:
                self.line_positions[i] = -self.line_height

    def get_race_progress(self):
        total_distance = sum(turn[2] for turn in self.turn_sequence)
        return min(100, (self.race_distance / total_distance) * 100)

class RaceBot:
    def __init__(self, car_type, screen_width, screen_height, num_lanes=3):
        self.car_type = car_type
        self.stats = car_type.value
        self.width = 40
        self.height = 70
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.num_lanes = num_lanes

        # Use the same lane positioning as PlayerCar
        if num_lanes == 4:
            self.lanes_x = [
                screen_width//2 - ROAD_WIDTH//2 + ROAD_WIDTH//8,
                screen_width//2 - ROAD_WIDTH//4 + ROAD_WIDTH//8,
                screen_width//2 + ROAD_WIDTH//8,
                screen_width//2 + ROAD_WIDTH//4 + ROAD_WIDTH//8
            ]
            self.lane = 2
        elif num_lanes == 3:
            lane_spacing = ROAD_WIDTH // 3
            self.lanes_x = [
                screen_width//2 - ROAD_WIDTH//2 + lane_spacing//2,
                screen_width//2,
                screen_width//2 + ROAD_WIDTH//2 - lane_spacing//2
            ]
            self.lane = 2
        else:
            self.lanes_x = [
                screen_width//2 - ROAD_WIDTH//4,
                screen_width//2 + ROAD_WIDTH//4
            ]
            self.lane = 1

        self.x = self.lanes_x[self.lane]
        self.y = screen_height - 200
        self.speed = 8
        self.target_x = self.lanes_x[self.lane]
        self.drift_angle = 0
        self.reaction_time = random.uniform(0.1, 0.3)
        self.last_lane_change = 0

    def update(self, turn_direction, turn_intensity, player_x, player_speed):
        target_speed = player_speed * 1.1
        self.speed += (target_speed - self.speed) * 0.05

        self.x += (self.target_x - self.x) * 0.1

        current_time = pygame.time.get_ticks()
        if current_time - self.last_lane_change > 2000:
            if random.random() < 0.02:
                if self.lane > 0 and random.random() < 0.5:
                    self.lane -= 1
                elif self.lane < self.num_lanes - 1:
                    self.lane += 1
                self.target_x = self.lanes_x[self.lane]
                self.last_lane_change = current_time

        if turn_direction != TurnDirection.STRAIGHT:
            turn_factor = turn_intensity * 0.4
            if turn_direction == TurnDirection.LEFT:
                self.target_x += turn_factor
            else:
                self.target_x -= turn_factor

            self.target_x = max(self.lanes_x[0], min(self.lanes_x[-1], self.target_x))

        if turn_direction != TurnDirection.STRAIGHT and turn_intensity > 0.5:
            max_drift_angle = 15 * self.stats["drift"]
            drift_direction = 1 if turn_direction == TurnDirection.LEFT else -1
            self.drift_angle = drift_direction * (max_drift_angle * turn_intensity)
        else:
            self.drift_angle *= 0.8

    def draw(self, screen, turn_direction, turn_intensity):
        color = self.stats["color"]
        car_rect = pygame.Rect(0, 0, self.width, self.height)
        car_rect.center = (self.x, self.y)

        car_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pygame.draw.rect(car_surface, color, (0, 0, self.width, self.height))
        pygame.draw.rect(car_surface, BLACK, (0, 0, self.width, self.height), 2)

        pygame.draw.rect(car_surface, YELLOW, (5, 5, 8, 5))
        pygame.draw.rect(car_surface, YELLOW, (self.width-13, 5, 8, 5))

        turn_angle = 0
        if turn_direction != TurnDirection.STRAIGHT:
            turn_angle = turn_intensity * 3 * (1 if turn_direction == TurnDirection.LEFT else -1)

        total_angle = self.drift_angle + turn_angle

        rotated_car = pygame.transform.rotate(car_surface, total_angle)
        rotated_rect = rotated_car.get_rect(center=car_rect.center)
        screen.blit(rotated_car, rotated_rect)

    def check_collision(self, player):
        player_rect = pygame.Rect(player.x - player.width//2, player.y - player.height//2,
                                player.width, player.height)
        bot_rect = pygame.Rect(self.x - self.width//2, self.y - self.height//2,
                             self.width, self.height)
        return player_rect.colliderect(bot_rect)

class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-2, 0)
        self.life = 30
        self.color = color
        self.size = random.randint(2, 6)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        self.vy += 0.1

    def draw(self, screen):
        alpha = int(255 * (self.life / 30))
        color_with_alpha = (*self.color, alpha)
        surf = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        pygame.draw.circle(surf, color_with_alpha, (self.size//2, self.size//2), self.size//2)
        screen.blit(surf, (int(self.x), int(self.y)))

    def is_dead(self):
        return self.life <= 0

class NameInput:
    def __init__(self, leaderboard):
        self.name = ""
        self.active = True
        self.leaderboard = leaderboard
        self.error_message = ""
        self.font_large = pygame.font.SysFont('courier', 36, bold=True)
        self.font_medium = pygame.font.SysFont('courier', 24, bold=True)
        self.font_small = pygame.font.SysFont('courier', 18)

    def draw(self, screen, crt, car_type):
        screen_width, screen_height = screen.get_size()
        screen.fill(BLACK)

        title = self.font_large.render("ENTER YOUR NAME", True, YELLOW)
        screen.blit(title, (screen_width//2 - title.get_width()//2, 100))

        car = car_type.value
        car_text = self.font_medium.render(f"Selected: {car['name']}", True, car["color"])
        screen.blit(car_text, (screen_width//2 - car_text.get_width()//2, 160))

        input_rect = pygame.Rect(screen_width//2 - 150, 220, 300, 50)
        pygame.draw.rect(screen, DARK_GRAY, input_rect)
        pygame.draw.rect(screen, WHITE, input_rect, 2)

        name_text = self.font_medium.render(self.name, True, WHITE)
        screen.blit(name_text, (input_rect.x + 10, input_rect.y + 10))

        if self.active and pygame.time.get_ticks() % 1000 < 500:
            cursor_x = input_rect.x + 10 + name_text.get_width()
            pygame.draw.line(screen, WHITE, (cursor_x, input_rect.y + 10),
                           (cursor_x, input_rect.y + 40), 2)

        if self.error_message:
            error_text = self.font_small.render(self.error_message, True, RED)
            screen.blit(error_text, (screen_width//2 - error_text.get_width()//2, 290))

        hint1 = self.font_small.render("Press ENTER to start racing", True, GREEN)
        hint2 = self.font_small.render("Press ESC to go back", True, GRAY)

        screen.blit(hint1, (screen_width//2 - hint1.get_width()//2, 330))
        screen.blit(hint2, (screen_width//2 - hint2.get_width()//2, 360))

        crt.draw()
        pygame.display.flip()

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if self.name.strip():
                    if self.leaderboard.is_name_used(self.name.strip()):
                        self.error_message = "This name is already used! Choose another one."
                        return None
                    else:
                        return self.name.strip()
                else:
                    self.error_message = "Please enter a name!"
            elif event.key == pygame.K_ESCAPE:
                self.error_message = ""
                return "BACK"
            elif event.key == pygame.K_BACKSPACE:
                self.name = self.name[:-1]
                self.error_message = ""
            else:
                if event.unicode.isprintable() and len(self.name) < 15:
                    self.name += event.unicode
                    self.error_message = ""
        return None

class LeaderboardScreen:
    def __init__(self, leaderboard):
        self.leaderboard = leaderboard
        self.selected_filter = 0
        self.filters = ["ALL CARS", "AE86", "RX-7", "GTR", "EVO", "SUPRA"]
        self.font_large = pygame.font.SysFont('courier', 36, bold=True)
        self.font_medium = pygame.font.SysFont('courier', 24, bold=True)
        self.font_small = pygame.font.SysFont('courier', 18)
        self.start_index = 0
        self.entries_per_page = 8

    def draw(self, screen, crt):
        screen_width, screen_height = screen.get_size()
        screen.fill(BLACK)

        title = self.font_large.render("LEADERBOARD", True, YELLOW)
        screen.blit(title, (screen_width//2 - title.get_width()//2, 50))

        filter_text = self.font_medium.render("FILTER:", True, WHITE)
        screen.blit(filter_text, (50, 110))

        for i, filter_name in enumerate(self.filters):
            color = YELLOW if i == self.selected_filter else WHITE
            filter_btn = self.font_small.render(filter_name, True, color)
            screen.blit(filter_btn, (150 + i * 80, 110))

        headers = ["RANK", "NAME", "SCORE", "DRIFT", "CAR", "DATE"]
        header_x = [50, 120, 250, 350, 450, 550]

        for i, header in enumerate(headers):
            header_text = self.font_small.render(header, True, GREEN)
            screen.blit(header_text, (header_x[i], 150))

        car_filter = None
        if self.selected_filter > 0:
            car_filter = list(CarType)[self.selected_filter - 1].name

        entries = self.leaderboard.get_top_entries(50, car_filter)

        y_pos = 180
        for i in range(self.start_index, min(self.start_index + self.entries_per_page, len(entries))):
            entry = entries[i]

            rank_text = self.font_small.render(f"{i+1}.", True, WHITE)
            screen.blit(rank_text, (header_x[0], y_pos))

            name = entry['name'][:10] + "..." if len(entry['name']) > 10 else entry['name']
            name_text = self.font_small.render(name, True, WHITE)
            screen.blit(name_text, (header_x[1], y_pos))

            score_text = self.font_small.render(str(entry['score']), True, YELLOW)
            screen.blit(score_text, (header_x[2], y_pos))

            drift_text = self.font_small.render(str(entry['drift_score']), True, GREEN)
            screen.blit(drift_text, (header_x[3], y_pos))

            car_text = self.font_small.render(entry['car_type'], True, self.get_car_color(entry['car_type']))
            screen.blit(car_text, (header_x[4], y_pos))

            date = entry['date'].split()[0]
            date_text = self.font_small.render(date, True, GRAY)
            screen.blit(date_text, (header_x[5], y_pos))

            y_pos += 30

        if len(entries) > self.entries_per_page:
            page_info = f"PAGE {self.start_index // self.entries_per_page + 1}/{(len(entries) - 1) // self.entries_per_page + 1}"
            page_text = self.font_small.render(page_info, True, WHITE)
            screen.blit(page_text, (screen_width//2 - page_text.get_width()//2, screen_height - 80))

        controls = [
            "←→: Change Filter",
            "↑↓: Scroll",
            "ESC: Back to Menu"
        ]

        for i, control in enumerate(controls):
            control_text = self.font_small.render(control, True, GRAY)
            screen.blit(control_text, (screen_width//2 - control_text.get_width()//2, screen_height - 40 + i * 20))

        crt.draw()
        pygame.display.flip()

    def get_car_color(self, car_name):
        for car_type in CarType:
            if car_type.value["name"] == car_name:
                return car_type.value["color"]
        return WHITE

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "BACK"
            elif event.key == pygame.K_LEFT:
                self.selected_filter = (self.selected_filter - 1) % len(self.filters)
                self.start_index = 0
            elif event.key == pygame.K_RIGHT:
                self.selected_filter = (self.selected_filter + 1) % len(self.filters)
                self.start_index = 0
            elif event.key == pygame.K_UP:
                self.start_index = max(0, self.start_index - 1)
            elif event.key == pygame.K_DOWN:
                entries = self.leaderboard.get_top_entries(50)
                self.start_index = min(len(entries) - self.entries_per_page, self.start_index + 1)
        return None

class SettingsScreen:
    def __init__(self):
        self.selected_option = 0
        self.options = ["2 LANES", "3 LANES", "4 LANES", "INSANE MODE: OFF", "RACE MODE: OFF", "BACK"]
        self.font_large = pygame.font.SysFont('courier', 36, bold=True)
        self.font_medium = pygame.font.SysFont('courier', 24, bold=True)
        self.font_small = pygame.font.SysFont('courier', 18)

    def draw(self, screen, crt, current_lanes, insane_mode, race_mode):
        screen_width, screen_height = screen.get_size()
        screen.fill(BLACK)

        title = self.font_large.render("SETTINGS", True, YELLOW)
        screen.blit(title, (screen_width//2 - title.get_width()//2, 100))

        lanes_text = self.font_medium.render(f"Current: {current_lanes} LANES", True, GREEN)
        screen.blit(lanes_text, (screen_width//2 - lanes_text.get_width()//2, 160))

        insane_text = self.font_medium.render(f"Insane Mode: {'ON' if insane_mode else 'OFF'}",
                                            True, RED if insane_mode else GREEN)
        screen.blit(insane_text, (screen_width//2 - insane_text.get_width()//2, 190))

        race_text = self.font_medium.render(f"Race Mode: {'ON' if race_mode else 'OFF'}",
                                          True, CYAN if race_mode else GRAY)
        screen.blit(race_text, (screen_width//2 - race_text.get_width()//2, 220))

        for i, option in enumerate(self.options):
            color = YELLOW if i == self.selected_option else WHITE

            if i == 3:
                option = "INSANE MODE: ON" if insane_mode else "INSANE MODE: OFF"
            elif i == 4:
                option = "RACE MODE: ON" if race_mode else "RACE MODE: OFF"

            text = self.font_medium.render(option, True, color)
            screen.blit(text, (screen_width//2 - text.get_width()//2, 280 + i * 50))

        controls = [
            "↑↓: Navigate",
            "ENTER: Select/Toggle",
            "ESC: Back to Menu"
        ]

        for i, control in enumerate(controls):
            text = self.font_small.render(control, True, GRAY)
            screen.blit(text, (screen_width//2 - text.get_width()//2, screen_height - 100 + i * 30))

        crt.draw()
        pygame.display.flip()

    def handle_input(self, event, current_lanes, insane_mode, race_mode):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected_option = (self.selected_option - 1) % len(self.options)
            elif event.key == pygame.K_DOWN:
                self.selected_option = (self.selected_option + 1) % len(self.options)
            elif event.key == pygame.K_RETURN:
                if self.selected_option == 0:
                    return 2, insane_mode, race_mode
                elif self.selected_option == 1:
                    return 3, insane_mode, race_mode
                elif self.selected_option == 2:
                    return 4, insane_mode, race_mode
                elif self.selected_option == 3:
                    return current_lanes, not insane_mode, race_mode
                elif self.selected_option == 4:
                    return current_lanes, insane_mode, not race_mode
                elif self.selected_option == 5:
                    return "BACK", insane_mode, race_mode
        return current_lanes, insane_mode, race_mode

class Menu:
    def __init__(self):
        self.selected_option = 0
        self.options = ["START GAME", "CAR SELECT", "LEADERBOARD", "SETTINGS", "QUIT"]
        self.font_large = pygame.font.SysFont('courier', 48, bold=True)
        self.font_medium = pygame.font.SysFont('courier', 36, bold=True)
        self.font_small = pygame.font.SysFont('courier', 24)

    def draw(self, screen, crt):
        screen_width, screen_height = screen.get_size()
        screen.fill(BLACK)

        title = self.font_large.render("INITIAL D", True, RED)
        subtitle = self.font_medium.render("RETRO ARCADE", True, WHITE)

        screen.blit(title, (screen_width//2 - title.get_width()//2, 100))
        screen.blit(subtitle, (screen_width//2 - subtitle.get_width()//2, 160))

        for i, option in enumerate(self.options):
            color = YELLOW if i == self.selected_option else WHITE
            text = self.font_medium.render(option, True, color)
            screen.blit(text, (screen_width//2 - text.get_width()//2, 250 + i * 60))

        controls = [
            "↑↓: Navigate",
            "ENTER: Select",
            "ESC: Quit"
        ]

        for i, control in enumerate(controls):
            text = self.font_small.render(control, True, GRAY)
            screen.blit(text, (screen_width//2 - text.get_width()//2, screen_height - 100 + i * 30))

        crt.draw()
        pygame.display.flip()

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected_option = (self.selected_option - 1) % len(self.options)
            elif event.key == pygame.K_DOWN:
                self.selected_option = (self.selected_option + 1) % len(self.options)
            elif event.key == pygame.K_RETURN:
                return self.selected_option
        return None

class CarSelection:
    def __init__(self):
        self.selected_car = 0
        self.cars = list(CarType)
        self.font_large = pygame.font.SysFont('courier', 36, bold=True)
        self.font_medium = pygame.font.SysFont('courier', 24, bold=True)
        self.font_small = pygame.font.SysFont('courier', 18)

    def draw(self, screen, crt):
        screen_width, screen_height = screen.get_size()
        screen.fill(BLACK)

        title = self.font_large.render("SELECT YOUR CAR", True, YELLOW)
        screen.blit(title, (screen_width//2 - title.get_width()//2, 50))

        for i, car_type in enumerate(self.cars):
            car = car_type.value
            color = YELLOW if i == self.selected_car else WHITE

            name_text = self.font_medium.render(car["name"], True, color)
            screen.blit(name_text, (screen_width//2 - name_text.get_width()//2, 150 + i * 100))

            stats_text = self.font_small.render(
                f"Speed: {car['max_speed']} | Handling: {car['handling']} | Drift: {car['drift']}",
                True, car["color"]
            )
            screen.blit(stats_text, (screen_width//2 - stats_text.get_width()//2, 180 + i * 100))

            car_rect = pygame.Rect(screen_width//2 - 20, 210 + i * 100, 40, 70)
            pygame.draw.rect(screen, car["color"], car_rect)
            pygame.draw.rect(screen, BLACK, car_rect, 2)

            pygame.draw.rect(screen, YELLOW, (screen_width//2 - 15, 215 + i * 100, 8, 5))
            pygame.draw.rect(screen, YELLOW, (screen_width//2 + 7, 215 + i * 100, 8, 5))
            pygame.draw.rect(screen, RED, (screen_width//2 - 15, 265 + i * 100, 8, 5))
            pygame.draw.rect(screen, RED, (screen_width//2 + 7, 265 + i * 100, 8, 5))

        controls = [
            "↑↓: Select Car",
            "ENTER: Confirm",
            "ESC: Back to Menu"
        ]

        for i, control in enumerate(controls):
            text = self.font_small.render(control, True, GRAY)
            screen.blit(text, (screen_width//2 - text.get_width()//2, screen_height - 100 + i * 25))

        crt.draw()
        pygame.display.flip()

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected_car = (self.selected_car - 1) % len(self.cars)
            elif event.key == pygame.K_DOWN:
                self.selected_car = (self.selected_car + 1) % len(self.cars)
            elif event.key == pygame.K_RETURN:
                return self.cars[self.selected_car]
            elif event.key == pygame.K_ESCAPE:
                return "BACK"
        return None

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((INITIAL_WIDTH, INITIAL_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("Initial D: Retro Arcade")
        self.clock = pygame.time.Clock()
        self.crt = CRT(self.screen)
        self.font_large = pygame.font.SysFont('courier', 36, bold=True)
        self.font_medium = pygame.font.SysFont('courier', 24, bold=True)
        self.font_small = pygame.font.SysFont('courier', 18)
        self.leaderboard = Leaderboard()
        self.state = GameState.MENU
        self.menu = Menu()
        self.car_selection = CarSelection()
        self.name_input = NameInput(self.leaderboard)
        self.leaderboard_screen = LeaderboardScreen(self.leaderboard)
        self.settings_screen = SettingsScreen()
        self.selected_car = CarType.AE86
        self.player_name = ""
        self.num_lanes = 3
        self.insane_mode = False
        self.race_mode = False
        self.music_playing = False
        self.load_music()
        self.reset_game()

    def load_music(self):
        try:
            # Create a simple music file if it doesn't exist
            if not os.path.exists("initial_d.mp3"):
                print("Music file not found. Game will run without music.")
            else:
                pygame.mixer.music.load("initial_d.mp3")
                pygame.mixer.music.set_volume(0.7)
                pygame.mixer.music.play(-1)
                self.music_playing = True
        except:
            print("Music not available. Game will run without music.")
            self.music_playing = False

    def reset_game(self):
        screen_width, screen_height = self.screen.get_size()
        if self.race_mode:
            self.player = PlayerCar(self.selected_car, screen_width, screen_height, self.num_lanes, self.insane_mode)
            self.road = RaceRoad(screen_width, screen_height, self.num_lanes)
            self.bot = RaceBot(random.choice(list(CarType)), screen_width, screen_height, self.num_lanes)
            self.enemies = []
            self.race_finished = False
            self.race_time = 0
            self.bot_finished = False
        else:
            self.player = PlayerCar(self.selected_car, screen_width, screen_height, self.num_lanes, self.insane_mode)
            self.road = Road(screen_width, screen_height, self.num_lanes)
            self.enemies = []

        self.particles = []
        self.spawn_timer = 0
        self.game_over = False

    def update_sizes(self):
        screen_width, screen_height = self.screen.get_size()
        self.crt.update_effects((screen_width, screen_height))

        if hasattr(self, 'player'):
            self.player.update_size(screen_width, screen_height)
            self.road.update_size(screen_width, screen_height)

            for enemy in self.enemies:
                enemy.update_size(screen_width, screen_height)

            if self.race_mode and hasattr(self, 'bot'):
                self.bot.screen_width = screen_width
                self.bot.screen_height = screen_height

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.VIDEORESIZE:
                self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                self.update_sizes()

            if self.state == GameState.MENU:
                result = self.menu.handle_input(event)
                if result is not None:
                    if result == 0:
                        if self.race_mode:
                            self.state = GameState.RACE_MODE
                        else:
                            self.state = GameState.CAR_SELECT
                    elif result == 1:
                        self.state = GameState.CAR_SELECT
                    elif result == 2:
                        self.state = GameState.LEADERBOARD
                    elif result == 3:
                        self.state = GameState.SETTINGS
                    elif result == 4:
                        return False

            elif self.state == GameState.CAR_SELECT:
                result = self.car_selection.handle_input(event)
                if result == "BACK":
                    self.state = GameState.MENU
                elif result is not None and isinstance(result, CarType):
                    self.selected_car = result
                    self.state = GameState.NAME_INPUT
                    self.name_input.name = ""
                    self.name_input.error_message = ""

            elif self.state == GameState.NAME_INPUT:
                result = self.name_input.handle_input(event)
                if result == "BACK":
                    self.state = GameState.CAR_SELECT
                elif result is not None:
                    self.player_name = result
                    if self.race_mode:
                        self.state = GameState.RACE_MODE
                    else:
                        self.state = GameState.PLAYING
                    self.reset_game()

            elif self.state == GameState.PLAYING or self.state == GameState.RACE_MODE:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        if self.player.lane > 0:
                            self.player.lane -= 1
                            self.player.target_x = self.player.lanes_x[self.player.lane]
                    elif event.key == pygame.K_RIGHT:
                        if self.player.lane < self.player.num_lanes - 1:
                            self.player.lane += 1
                            self.player.target_x = self.player.lanes_x[self.player.lane]
                    elif event.key == pygame.K_ESCAPE:
                        self.state = GameState.PAUSED
                    elif event.key == pygame.K_r and self.game_over:
                        self.reset_game()

            elif self.state == GameState.PAUSED:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        if self.race_mode:
                            self.state = GameState.RACE_MODE
                        else:
                            self.state = GameState.PLAYING
                    elif event.key == pygame.K_ESCAPE:
                        self.state = GameState.MENU

            elif self.state == GameState.GAME_OVER:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.leaderboard.add_entry(
                            self.player_name,
                            self.player.score,
                            self.player.drift_score,
                            self.selected_car.value["name"]
                        )
                        self.reset_game()
                        if self.race_mode:
                            self.state = GameState.RACE_MODE
                        else:
                            self.state = GameState.PLAYING
                    elif event.key == pygame.K_ESCAPE:
                        self.leaderboard.add_entry(
                            self.player_name,
                            self.player.score,
                            self.player.drift_score,
                            self.selected_car.value["name"]
                        )
                        self.state = GameState.MENU

            elif self.state == GameState.LEADERBOARD:
                result = self.leaderboard_screen.handle_input(event)
                if result == "BACK":
                    self.state = GameState.MENU

            elif self.state == GameState.SETTINGS:
                result = self.settings_screen.handle_input(event, self.num_lanes, self.insane_mode, self.race_mode)
                if result is not None:
                    new_lanes, new_insane, new_race = result
                    if new_lanes == "BACK":
                        self.state = GameState.MENU
                    else:
                        self.num_lanes = new_lanes
                        self.insane_mode = new_insane
                        self.race_mode = new_race

        return True

    def update(self):
        if (self.state != GameState.PLAYING and self.state != GameState.RACE_MODE) or self.game_over:
            return

        keys = pygame.key.get_pressed()
        continuous_keys = {
            pygame.K_UP: keys[pygame.K_UP],
            pygame.K_DOWN: keys[pygame.K_DOWN],
            pygame.K_z: keys[pygame.K_z],
            pygame.K_x: keys[pygame.K_x],
            pygame.K_LEFT: keys[pygame.K_LEFT],
            pygame.K_RIGHT: keys[pygame.K_RIGHT]
        }

        self.player.update(continuous_keys, self.road.current_turn, self.road.turn_intensity)
        self.road.update(self.player.speed)

        if self.race_mode and hasattr(self, 'bot'):
            self.bot.update(self.road.current_turn, self.road.turn_intensity, self.player.x, self.player.speed)

            if not self.race_finished and self.road.get_race_progress() >= 100:
                self.race_finished = True
                self.race_time = pygame.time.get_ticks() // 1000

            if not self.bot_finished and random.random() < 0.001:
                self.bot_finished = True

        if not self.race_mode:
            self.spawn_timer += 1
            if self.spawn_timer > 60 - min(50, self.player.score // 100):
                self.spawn_timer = 0
                screen_width, screen_height = self.screen.get_size()
                if len(self.enemies) < 5 + self.player.score // 500:
                    self.enemies.append(EnemyCar(self.player.speed, self.road.current_turn, self.road.turn_intensity,
                                               screen_width, screen_height, self.num_lanes, self.insane_mode))

        for enemy in self.enemies[:]:
            if enemy.update(self.player.speed, self.road.current_turn, self.road.turn_intensity):
                self.enemies.remove(enemy)
            elif enemy.check_collision(self.player):
                self.create_explosion(self.player.x, self.player.y)
                self.game_over = True
                self.state = GameState.GAME_OVER
            elif not enemy.passed and enemy.y > self.player.y:
                enemy.passed = True
                self.player.score += 5 * (1 + self.player.combo // 5)
                self.player.combo += 1
                self.player.last_overtake = pygame.time.get_ticks()
                self.player.nitro = min(100, self.player.nitro + 5)

        if self.race_mode and hasattr(self, 'bot') and self.bot.check_collision(self.player):
            self.create_explosion(self.player.x, self.player.y)
            self.game_over = True
            self.state = GameState.GAME_OVER

        for particle in self.particles[:]:
            particle.update()
            if particle.is_dead():
                self.particles.remove(particle)

        if not self.race_mode:
            self.player.score += int(self.player.speed * 0.05)

    def create_explosion(self, x, y):
        for _ in range(30):
            color = random.choice([RED, YELLOW, (255, 100, 0)])
            self.particles.append(Particle(x, y, color))

    def draw_hud(self):
        screen_width, screen_height = self.screen.get_size()

        name_text = self.font_small.render(f"DRIVER: {self.player_name}", True, WHITE)
        self.screen.blit(name_text, (20, 20))

        speed_text = self.font_medium.render(f"SPEED: {int(self.player.speed * 20)} km/h", True, WHITE)
        self.screen.blit(speed_text, (20, 50))

        if self.race_mode:
            time_text = self.font_medium.render(f"TIME: {pygame.time.get_ticks() // 1000}s", True, CYAN)
            self.screen.blit(time_text, (20, 80))

            # FIXED: Now all road types have get_race_progress method
            progress = self.road.get_race_progress()
            progress_text = self.font_medium.render(f"RACE: {progress:.1f}%", True, GREEN)
            self.screen.blit(progress_text, (20, 110))

            if hasattr(self, 'bot'):
                if self.player.y < self.bot.y:
                    position_text = self.font_medium.render("POSITION: 1st", True, YELLOW)
                else:
                    position_text = self.font_medium.render("POSITION: 2nd", True, ORANGE)
                self.screen.blit(position_text, (20, 140))
        else:
            score_text = self.font_medium.render(f"SCORE: {self.player.score}", True, WHITE)
            self.screen.blit(score_text, (20, 80))

        if self.player.combo > 1:
            combo_text = self.font_medium.render(f"COMBO: x{self.player.combo}", True, YELLOW)
            self.screen.blit(combo_text, (20, 110))

        if self.player.drift_power > 10 or self.player.drift_combo > 0:
            drift_color = GREEN if self.player.drift_bonus_active else GRAY
            drift_text = self.font_small.render(f"DRIFT: {self.player.drift_score}", True, drift_color)
            self.screen.blit(drift_text, (20, 140))

            if self.player.drift_combo > 0:
                combo_text = self.font_small.render(f"DRIFT COMBO: x{self.player.drift_combo}", True, YELLOW)
                self.screen.blit(combo_text, (20, 160))

                if self.player.max_drift_combo > 5:
                    max_combo_text = self.font_small.render(f"MAX COMBO: {self.player.max_drift_combo}", True, PINK)
                    self.screen.blit(max_combo_text, (20, 180))

            if not self.player.drift_bonus_active and self.player.is_drifting:
                hint_text = self.font_small.render("DRIFT IN TURNS FOR BONUS!", True, YELLOW)
                self.screen.blit(hint_text, (screen_width//2 - hint_text.get_width()//2, 160))

        if self.num_lanes == 4:
            lane_names = ["FAR LEFT", "LEFT", "RIGHT", "FAR RIGHT"]
        elif self.num_lanes == 3:
            lane_names = ["LEFT", "CENTER", "RIGHT"]
        else:
            lane_names = ["LEFT", "RIGHT"]

        # FIXED: Added bounds checking for player lane
        if self.player.lane < 0:
            self.player.lane = 0
        elif self.player.lane >= len(lane_names):
            self.player.lane = len(lane_names) - 1

        lane_text = self.font_small.render(f"LANE: {lane_names[self.player.lane]}", True, GREEN)
        self.screen.blit(lane_text, (screen_width - 150, 80))

        if self.insane_mode:
            insane_text = self.font_small.render("INSANE MODE!", True, RED)
            self.screen.blit(insane_text, (screen_width - 150, 110))

        if self.race_mode:
            race_text = self.font_small.render("RACE MODE!", True, CYAN)
            self.screen.blit(race_text, (screen_width - 150, 140))

        nitro_text = self.font_small.render("NITRO", True, WHITE)
        self.screen.blit(nitro_text, (screen_width - 100, 20))
        pygame.draw.rect(self.screen, DARK_GRAY, (screen_width - 100, 45, 80, 15))
        pygame.draw.rect(self.screen, BLUE, (screen_width - 100, 45, 80 * (self.player.nitro / 100), 15))

        controls_text = [
            "↑↓: Gas/Brake",
            "←→: Change Lane",
            "Z: Drift",
            "X: Nitro",
            "ESC: Pause"
        ]

        for i, text in enumerate(controls_text):
            control_surf = self.font_small.render(text, True, GRAY)
            self.screen.blit(control_surf, (screen_width - 150, screen_height - 120 + i * 20))

    def draw_playing(self):
        self.screen.fill(BLACK)
        self.road.draw(self.screen)

        for enemy in self.enemies:
            enemy.draw(self.screen, self.road.current_turn, self.road.turn_intensity)

        if self.race_mode and hasattr(self, 'bot'):
            self.bot.draw(self.screen, self.road.current_turn, self.road.turn_intensity)

        for particle in self.particles:
            particle.draw(self.screen)

        self.player.draw(self.screen, self.road.current_turn, self.road.turn_intensity)
        self.draw_hud()

        if self.game_over:
            screen_width, screen_height = self.screen.get_size()
            overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (0, 0))

            game_over_text = self.font_large.render("GAME OVER", True, RED)
            name_text = self.font_medium.render(f"Driver: {self.player_name}", True, WHITE)
            restart_text = self.font_medium.render("Press R to Restart", True, YELLOW)
            menu_text = self.font_medium.render("Press ESC for Menu", True, YELLOW)

            self.screen.blit(game_over_text, (screen_width//2 - game_over_text.get_width()//2, screen_height//2 - 120))
            self.screen.blit(name_text, (screen_width//2 - name_text.get_width()//2, screen_height//2 - 60))

            if self.race_mode:
                if self.race_finished:
                    result_text = self.font_medium.render("RACE FINISHED!", True, GREEN)
                    time_text = self.font_medium.render(f"Your Time: {self.race_time}s", True, CYAN)
                    self.screen.blit(result_text, (screen_width//2 - result_text.get_width()//2, screen_height//2 - 20))
                    self.screen.blit(time_text, (screen_width//2 - time_text.get_width()//2, screen_height//2 + 20))
                else:
                    result_text = self.font_medium.render("RACE FAILED!", True, RED)
                    self.screen.blit(result_text, (screen_width//2 - result_text.get_width()//2, screen_height//2 - 20))
            else:
                score_text = self.font_medium.render(f"Final Score: {self.player.score}", True, WHITE)
                drift_text = self.font_medium.render(f"Drift Score: {self.player.drift_score}", True, GREEN)
                self.screen.blit(score_text, (screen_width//2 - score_text.get_width()//2, screen_height//2 - 20))
                self.screen.blit(drift_text, (screen_width//2 - drift_text.get_width()//2, screen_height//2 + 20))

            self.screen.blit(restart_text, (screen_width//2 - restart_text.get_width()//2, screen_height//2 + 80))
            self.screen.blit(menu_text, (screen_width//2 - menu_text.get_width()//2, screen_height//2 + 120))

        if self.state == GameState.PAUSED:
            screen_width, screen_height = self.screen.get_size()
            overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.screen.blit(overlay, (0, 0))

            pause_text = self.font_large.render("PAUSED", True, YELLOW)
            continue_text = self.font_medium.render("Press ENTER to Continue", True, WHITE)
            menu_text = self.font_medium.render("Press ESC for Menu", True, WHITE)

            self.screen.blit(pause_text, (screen_width//2 - pause_text.get_width()//2, screen_height//2 - 60))
            self.screen.blit(continue_text, (screen_width//2 - continue_text.get_width()//2, screen_height//2))
            self.screen.blit(menu_text, (screen_width//2 - menu_text.get_width()//2, screen_height//2 + 40))

        self.crt.draw()
        pygame.display.flip()

    def draw(self):
        if self.state == GameState.MENU:
            self.menu.draw(self.screen, self.crt)
        elif self.state == GameState.CAR_SELECT:
            self.car_selection.draw(self.screen, self.crt)
        elif self.state == GameState.NAME_INPUT:
            self.name_input.draw(self.screen, self.crt, self.selected_car)
        elif self.state == GameState.LEADERBOARD:
            self.leaderboard_screen.draw(self.screen, self.crt)
        elif self.state == GameState.SETTINGS:
            self.settings_screen.draw(self.screen, self.crt, self.num_lanes, self.insane_mode, self.race_mode)
        elif self.state == GameState.PLAYING or self.state == GameState.PAUSED or self.state == GameState.GAME_OVER or self.state == GameState.RACE_MODE:
            self.draw_playing()

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()