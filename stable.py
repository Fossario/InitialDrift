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
WIDTH, HEIGHT = 800, 600
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

class GameState(Enum):
    MENU = 0
    CAR_SELECT = 1
    NAME_INPUT = 2
    PLAYING = 3
    GAME_OVER = 4
    PAUSED = 5
    LEADERBOARD = 6

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
                    # Собираем использованные имена
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
        # Сортируем по очкам (по убыванию)
        self.entries.sort(key=lambda x: x['score'], reverse=True)
        # Оставляем только топ-50 записей
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
    """Класс для создания CRT эффектов"""
    def __init__(self, screen):
        self.screen = screen
        self.scanlines = self.create_scanlines()
        self.vignette = self.create_vignette()

    def create_scanlines(self):
        scanline_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for y in range(0, HEIGHT, 3):
            pygame.draw.line(scanline_surface, (0, 0, 0, 60), (0, y), (WIDTH, y), 1)
        return scanline_surface

    def create_vignette(self):
        vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        center_x, center_y = WIDTH // 2, HEIGHT // 2
        max_radius = math.sqrt(center_x**2 + center_y**2)

        for y in range(HEIGHT):
            for x in range(WIDTH):
                dist = math.sqrt((x - center_x)**2 + (y - center_y)**2)
                alpha = min(150, int(200 * (dist / max_radius)))
                vignette.set_at((x, y), (0, 0, 0, alpha))
        return vignette

    def draw(self, surface=None):
        target = surface if surface else self.screen
        target.blit(self.scanlines, (0, 0))
        target.blit(self.vignette, (0, 0))

class PlayerCar:
    def __init__(self, car_type):
        self.car_type = car_type
        self.stats = car_type.value
        self.width = 40
        self.height = 70
        self.x = WIDTH // 2
        self.y = HEIGHT - 100
        self.speed = 0
        self.max_speed = self.stats["max_speed"]
        self.acceleration = 0.2 * self.stats["acceleration"]
        self.deceleration = 0.1
        self.handling = 4 * self.stats["handling"]
        self.lane = 1  # 0: left, 1: center, 2: right
        self.lanes_x = [WIDTH//2 - ROAD_WIDTH//3, WIDTH//2, WIDTH//2 + ROAD_WIDTH//3]
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

    def update(self, keys, turn_direction, turn_intensity):
        # Управление скоростью
        if keys[pygame.K_UP]:
            self.speed = min(self.speed + self.acceleration, self.max_speed)
        elif keys[pygame.K_DOWN]:
            self.speed = max(self.speed - self.deceleration * 2, 0)
        else:
            self.speed = max(self.speed - self.deceleration, 0)

        # Смена полосы с учетом поворота - теперь 3 полосы: 0 (левая), 1 (центр), 2 (правая)
        if keys[pygame.K_LEFT] and self.lane > 0:
            self.lane -= 1
            self.target_x = self.lanes_x[self.lane]
        if keys[pygame.K_RIGHT] and self.lane < 2:
            self.lane += 1
            self.target_x = self.lanes_x[self.lane]

        # Автоматическое смещение на поворотах
        if turn_direction != TurnDirection.STRAIGHT:
            turn_factor = turn_intensity * 0.5
            if turn_direction == TurnDirection.LEFT:
                self.target_x += turn_factor
            else:  # RIGHT
                self.target_x -= turn_factor

            # Ограничение, чтобы не выехать за дорогу
            self.target_x = max(self.lanes_x[0], min(self.lanes_x[2], self.target_x))

        # Дрифт
        self.is_drifting = keys[pygame.K_z] and abs(self.speed) > 3
        if self.is_drifting:
            # Увеличиваем мощность дрифта
            self.drift_power = min(self.drift_power + 0.5, 100)

            # Угол дрифта зависит от мощности и типа машины
            max_drift_angle = 25 * self.stats["drift"]
            drift_direction = 1 if keys[pygame.K_LEFT] else -1 if keys[pygame.K_RIGHT] else 0
            if drift_direction == 0:
                # Автоматический дрифт на поворотах
                if turn_direction == TurnDirection.LEFT:
                    drift_direction = 1
                elif turn_direction == TurnDirection.RIGHT:
                    drift_direction = -1

            self.drift_angle = drift_direction * (max_drift_angle * (self.drift_power / 100))

            # Добавляем очки за дрифт ТОЛЬКО в поворотах (уменьшенные значения)
            if turn_direction != TurnDirection.STRAIGHT:
                current_time = pygame.time.get_ticks()
                if current_time - self.last_drift_time > 150:  # Увеличили интервал для меньшего заработка
                    # Бонус за интенсивность поворота (уменьшенный)
                    turn_bonus = 0.5 + turn_intensity * 0.5  # Уменьшенный множитель
                    drift_points = int(self.drift_power * 0.05 * (1 + self.drift_combo * 0.05) * turn_bonus)  # Уменьшенные значения
                    self.drift_score += drift_points
                    self.score += drift_points
                    self.last_drift_time = current_time
                    self.drift_combo += 1
                    self.drift_bonus_active = True
            else:
                self.drift_bonus_active = False

            # Замедление скорости во время дрифта
            self.speed *= self.drift_slowdown
        else:
            # Плавный выход из дрифта
            self.drift_angle *= 0.8
            self.drift_power *= 0.9
            if self.drift_power < 5:
                self.drift_power = 0
                if self.drift_combo > 0 and self.drift_bonus_active:
                    # Бонус за завершение дрифта в повороте (уменьшенный)
                    combo_bonus = self.drift_combo * 10  # Уменьшенный бонус
                    self.score += combo_bonus
                    self.drift_score += combo_bonus
                self.drift_combo = 0
                self.drift_bonus_active = False

        # Нитро
        if keys[pygame.K_x] and self.nitro > 0 and self.speed > 0:
            self.speed = min(self.speed + 0.5, self.max_speed * 1.3)
            self.nitro -= 1

        # Плавное движение к целевой позиции
        move_speed = self.handling * (0.8 if self.is_drifting else 1.0)  # Меньше контроля в дрифте
        self.x += (self.target_x - self.x) * 0.1 * move_speed

        # Восстановление нитро
        if self.nitro < 100 and not keys[pygame.K_x]:
            self.nitro += 0.1

        # Обновление комбо (уменьшенный заработок за обгоны)
        if pygame.time.get_ticks() - self.last_overtake > 2000:
            self.combo = max(0, self.combo - 1)

    def draw(self, screen, turn_direction, turn_intensity):
        # Корпус автомобиля
        car_color = self.stats["color"]
        car_rect = pygame.Rect(0, 0, self.width, self.height)
        car_rect.center = (self.x, self.y)

        # Рисуем автомобиль с учетом дрифта и поворота
        car_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

        # Основной цвет автомобиля
        pygame.draw.rect(car_surface, car_color, (0, 0, self.width, self.height))
        pygame.draw.rect(car_surface, BLACK, (0, 0, self.width, self.height), 2)

        # Фары и детали
        pygame.draw.rect(car_surface, YELLOW, (5, 5, 8, 5))  # левая фара
        pygame.draw.rect(car_surface, YELLOW, (self.width-13, 5, 8, 5))  # правая фара
        pygame.draw.rect(car_surface, RED, (5, self.height-10, 8, 5))  # левый стоп-сигнал
        pygame.draw.rect(car_surface, RED, (self.width-13, self.height-10, 8, 5))  # правый стоп-сигнал

        # Наклейка Initial D для AE86
        if self.car_type == CarType.AE86:
            font = pygame.font.SysFont('Arial', 10, bold=True)
            text = font.render("INITIAL D", True, RED)
            car_surface.blit(text, (self.width//2 - text.get_width()//2, self.height//2 - 5))

        # Поворачиваем автомобиль при дрифте
        total_angle = self.drift_angle
        if turn_direction != TurnDirection.STRAIGHT:
            turn_angle = turn_intensity * 5 * (1 if turn_direction == TurnDirection.LEFT else -1)
            total_angle += turn_angle * (0.5 if self.is_drifting else 0.2)  # Больше наклон в дрифте

        rotated_car = pygame.transform.rotate(car_surface, total_angle)
        rotated_rect = rotated_car.get_rect(center=car_rect.center)
        screen.blit(rotated_car, rotated_rect)

        # Эффект дыма при дрифте
        if self.drift_power > 10 and self.speed > 5:
            smoke_intensity = int(self.drift_power / 5)
            for i in range(smoke_intensity):
                side = -1 if self.drift_angle > 0 else 1
                smoke_x = self.x + side * random.randint(15, 30)
                smoke_y = self.y + random.randint(20, 40)
                smoke_size = random.randint(10, 25)
                alpha = random.randint(50, 150)
                smoke_surface = pygame.Surface((smoke_size, smoke_size), pygame.SRCALPHA)
                pygame.draw.circle(smoke_surface, (200, 200, 200, alpha),
                                 (smoke_size//2, smoke_size//2), smoke_size//2)
                screen.blit(smoke_surface, (smoke_x - smoke_size//2, smoke_y - smoke_size//2))

class EnemyCar:
    def __init__(self, player_speed, turn_direction, turn_intensity):
        self.type = random.choice(list(CarType))
        self.stats = self.type.value
        self.width = 40
        self.height = 70
        self.lane = random.randint(0, 2)  # 3 полосы: 0, 1, 2
        self.lanes_x = [WIDTH//2 - ROAD_WIDTH//3, WIDTH//2, WIDTH//2 + ROAD_WIDTH//3]
        self.x = self.lanes_x[self.lane]
        self.y = -100
        self.speed = random.uniform(MIN_ENEMY_SPEED, MAX_ENEMY_SPEED) + player_speed * 0.3
        self.passed = False
        self.turn_offset = 0

    def update(self, player_speed, turn_direction, turn_intensity):
        self.y += self.speed

        # Смещение на поворотах
        if turn_direction != TurnDirection.STRAIGHT:
            turn_factor = turn_intensity * 0.3
            if turn_direction == TurnDirection.LEFT:
                self.turn_offset += turn_factor
            else:  # RIGHT
                self.turn_offset -= turn_factor

        self.x = self.lanes_x[self.lane] + self.turn_offset

        return self.y > HEIGHT + 100

    def draw(self, screen, turn_direction, turn_intensity):
        color = self.stats["color"]
        car_rect = pygame.Rect(0, 0, self.width, self.height)
        car_rect.center = (self.x, self.y)

        car_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pygame.draw.rect(car_surface, color, (0, 0, self.width, self.height))
        pygame.draw.rect(car_surface, BLACK, (0, 0, self.width, self.height), 2)

        # Детали автомобиля
        pygame.draw.rect(car_surface, YELLOW, (5, 5, 8, 5))
        pygame.draw.rect(car_surface, YELLOW, (self.width-13, 5, 8, 5))

        # Наклон на поворотах
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
    def __init__(self):
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
        self.turn_progress = 0  # Прогресс поворота (0-100)

        # Инициализация позиций линий разметки
        for y in range(-self.line_height, HEIGHT + self.line_height, self.line_spacing):
            self.line_positions.append(y)

    def update(self, speed):
        self.speed = speed

        # Смена поворотов
        self.curve_change_timer += 1
        if self.curve_change_timer > 180:  # Меняем поворот каждые 3 секунды при 60 FPS
            self.curve_change_timer = 0
            if random.random() < 0.7:  # 70% шанс на поворот
                self.current_turn = random.choice([TurnDirection.LEFT, TurnDirection.RIGHT])
                self.turn_intensity = random.uniform(0.3, 1.0)
                self.curve_target = self.turn_intensity * 100 * (1 if self.current_turn == TurnDirection.LEFT else -1)
                self.turn_progress = 0
            else:
                self.current_turn = TurnDirection.STRAIGHT
                self.turn_intensity = 0
                self.curve_target = 0
                self.turn_progress = 0

        # Плавное изменение кривизны
        self.curve += (self.curve_target - self.curve) * 0.05

        # Обновляем прогресс поворота
        if self.current_turn != TurnDirection.STRAIGHT:
            self.turn_progress = min(100, self.turn_progress + 0.5)

        # Двигаем линии разметки
        for i in range(len(self.line_positions)):
            self.line_positions[i] += speed
            if self.line_positions[i] > HEIGHT + self.line_height:
                self.line_positions[i] = -self.line_height

    def draw(self, screen):
        # Рисуем дорогу
        road_rect = pygame.Rect(WIDTH//2 - ROAD_WIDTH//2, 0, ROAD_WIDTH, HEIGHT)
        pygame.draw.rect(screen, DARK_GRAY, road_rect)

        # Рисуем линии разметки с учетом поворота
        for y in self.line_positions:
            curve_offset = self.curve * (y / HEIGHT) * 0.5
            line_rect = pygame.Rect(WIDTH//2 - self.line_width//2 + curve_offset, y,
                                  self.line_width, self.line_height)
            pygame.draw.rect(screen, YELLOW, line_rect)

        # Бордюры дороги с учетом поворота
        for y in range(0, HEIGHT, 20):
            curve_offset = self.curve * (y / HEIGHT) * 0.5
            left_border = WIDTH//2 - ROAD_WIDTH//2 - 20 + curve_offset
            right_border = WIDTH//2 + ROAD_WIDTH//2 + curve_offset

            pygame.draw.rect(screen, GRAY, (left_border, y, 20, 10))
            pygame.draw.rect(screen, GRAY, (right_border, y, 20, 10))

        # Отображаем предупреждение о повороте
        if self.current_turn != TurnDirection.STRAIGHT and self.turn_intensity > 0.5:
            warning_font = pygame.font.SysFont('courier', 24, bold=True)
            if self.current_turn == TurnDirection.LEFT:
                warning_text = warning_font.render("← LEFT TURN", True, YELLOW)
            else:
                warning_text = warning_font.render("RIGHT TURN →", True, YELLOW)

            screen.blit(warning_text, (WIDTH//2 - warning_text.get_width()//2, 50))

            # Индикатор прогресса поворота
            progress_width = 200
            pygame.draw.rect(screen, DARK_GRAY, (WIDTH//2 - progress_width//2, 90, progress_width, 10))
            pygame.draw.rect(screen, GREEN, (WIDTH//2 - progress_width//2, 90, progress_width * (self.turn_progress / 100), 10))

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
        screen.fill(BLACK)

        title = self.font_large.render("ENTER YOUR NAME", True, YELLOW)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))

        # Отображение выбранной машины
        car = car_type.value
        car_text = self.font_medium.render(f"Selected: {car['name']}", True, car["color"])
        screen.blit(car_text, (WIDTH//2 - car_text.get_width()//2, 160))

        # Поле ввода имени
        input_rect = pygame.Rect(WIDTH//2 - 150, 220, 300, 50)
        pygame.draw.rect(screen, DARK_GRAY, input_rect)
        pygame.draw.rect(screen, WHITE, input_rect, 2)

        name_text = self.font_medium.render(self.name, True, WHITE)
        screen.blit(name_text, (input_rect.x + 10, input_rect.y + 10))

        # Курсор
        if self.active and pygame.time.get_ticks() % 1000 < 500:
            cursor_x = input_rect.x + 10 + name_text.get_width()
            pygame.draw.line(screen, WHITE, (cursor_x, input_rect.y + 10),
                           (cursor_x, input_rect.y + 40), 2)

        # Сообщение об ошибке
        if self.error_message:
            error_text = self.font_small.render(self.error_message, True, RED)
            screen.blit(error_text, (WIDTH//2 - error_text.get_width()//2, 290))

        # Подсказки
        hint1 = self.font_small.render("Press ENTER to start racing", True, GREEN)
        hint2 = self.font_small.render("Press ESC to go back", True, GRAY)

        screen.blit(hint1, (WIDTH//2 - hint1.get_width()//2, 330))
        screen.blit(hint2, (WIDTH//2 - hint2.get_width()//2, 360))

        crt.draw()
        pygame.display.flip()

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if self.name.strip():
                    # Проверяем, не используется ли имя
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
                # Добавляем символ, если это буква или цифра и имя не слишком длинное
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
        screen.fill(BLACK)

        title = self.font_large.render("LEADERBOARD", True, YELLOW)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))

        # Фильтры
        filter_text = self.font_medium.render("FILTER:", True, WHITE)
        screen.blit(filter_text, (50, 110))

        for i, filter_name in enumerate(self.filters):
            color = YELLOW if i == self.selected_filter else WHITE
            filter_btn = self.font_small.render(filter_name, True, color)
            screen.blit(filter_btn, (150 + i * 80, 110))

        # Заголовки таблицы
        headers = ["RANK", "NAME", "SCORE", "DRIFT", "CAR", "DATE"]
        header_x = [50, 120, 250, 350, 450, 550]

        for i, header in enumerate(headers):
            header_text = self.font_small.render(header, True, GREEN)
            screen.blit(header_text, (header_x[i], 150))

        # Получаем записи с учетом фильтра
        car_filter = None
        if self.selected_filter > 0:
            car_filter = list(CarType)[self.selected_filter - 1].name

        entries = self.leaderboard.get_top_entries(50, car_filter)

        # Отображаем записи
        y_pos = 180
        for i in range(self.start_index, min(self.start_index + self.entries_per_page, len(entries))):
            entry = entries[i]

            # Ранг
            rank_text = self.font_small.render(f"{i+1}.", True, WHITE)
            screen.blit(rank_text, (header_x[0], y_pos))

            # Имя (обрезаем если слишком длинное)
            name = entry['name'][:10] + "..." if len(entry['name']) > 10 else entry['name']
            name_text = self.font_small.render(name, True, WHITE)
            screen.blit(name_text, (header_x[1], y_pos))

            # Очки
            score_text = self.font_small.render(str(entry['score']), True, YELLOW)
            screen.blit(score_text, (header_x[2], y_pos))

            # Очки дрифта
            drift_text = self.font_small.render(str(entry['drift_score']), True, GREEN)
            screen.blit(drift_text, (header_x[3], y_pos))

            # Машина
            car_text = self.font_small.render(entry['car_type'], True, getattr(self, 'get_car_color')(entry['car_type']))
            screen.blit(car_text, (header_x[4], y_pos))

            # Дата
            date = entry['date'].split()[0]  # Берем только дату
            date_text = self.font_small.render(date, True, GRAY)
            screen.blit(date_text, (header_x[5], y_pos))

            y_pos += 30

        # Навигация по страницам
        if len(entries) > self.entries_per_page:
            page_info = f"PAGE {self.start_index // self.entries_per_page + 1}/{(len(entries) - 1) // self.entries_per_page + 1}"
            page_text = self.font_small.render(page_info, True, WHITE)
            screen.blit(page_text, (WIDTH//2 - page_text.get_width()//2, HEIGHT - 80))

        # Управление
        controls = [
            "←→: Change Filter",
            "↑↓: Scroll",
            "ESC: Back to Menu"
        ]

        for i, control in enumerate(controls):
            control_text = self.font_small.render(control, True, GRAY)
            screen.blit(control_text, (WIDTH//2 - control_text.get_width()//2, HEIGHT - 40 + i * 20))

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

class Menu:
    def __init__(self):
        self.selected_option = 0
        self.options = ["START GAME", "CAR SELECT", "LEADERBOARD", "QUIT"]
        self.font_large = pygame.font.SysFont('courier', 48, bold=True)
        self.font_medium = pygame.font.SysFont('courier', 36, bold=True)
        self.font_small = pygame.font.SysFont('courier', 24)

    def draw(self, screen, crt):
        screen.fill(BLACK)

        # Заголовок
        title = self.font_large.render("INITIAL D", True, RED)
        subtitle = self.font_medium.render("RETRO ARCADE", True, WHITE)

        screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))
        screen.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, 160))

        # Опции меню
        for i, option in enumerate(self.options):
            color = YELLOW if i == self.selected_option else WHITE
            text = self.font_medium.render(option, True, color)
            screen.blit(text, (WIDTH//2 - text.get_width()//2, 280 + i * 60))

        # Управление
        controls = [
            "↑↓: Navigate",
            "ENTER: Select",
            "ESC: Quit"
        ]

        for i, control in enumerate(controls):
            text = self.font_small.render(control, True, GRAY)
            screen.blit(text, (WIDTH//2 - text.get_width()//2, 500 + i * 30))

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
        screen.fill(BLACK)

        title = self.font_large.render("SELECT YOUR CAR", True, YELLOW)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))

        # Отображение машин
        for i, car_type in enumerate(self.cars):
            car = car_type.value
            color = YELLOW if i == self.selected_car else WHITE

            # Название машины
            name_text = self.font_medium.render(car["name"], True, color)
            screen.blit(name_text, (WIDTH//2 - name_text.get_width()//2, 150 + i * 100))

            # Характеристики
            stats_text = self.font_small.render(
                f"Speed: {car['max_speed']} | Handling: {car['handling']} | Drift: {car['drift']}",
                True, car["color"]
            )
            screen.blit(stats_text, (WIDTH//2 - stats_text.get_width()//2, 180 + i * 100))

            # Отображение машины
            car_rect = pygame.Rect(WIDTH//2 - 20, 210 + i * 100, 40, 70)
            pygame.draw.rect(screen, car["color"], car_rect)
            pygame.draw.rect(screen, BLACK, car_rect, 2)

            # Детали
            pygame.draw.rect(screen, YELLOW, (WIDTH//2 - 15, 215 + i * 100, 8, 5))
            pygame.draw.rect(screen, YELLOW, (WIDTH//2 + 7, 215 + i * 100, 8, 5))
            pygame.draw.rect(screen, RED, (WIDTH//2 - 15, 265 + i * 100, 8, 5))
            pygame.draw.rect(screen, RED, (WIDTH//2 + 7, 265 + i * 100, 8, 5))

        # Управление
        controls = [
            "↑↓: Select Car",
            "ENTER: Confirm",
            "ESC: Back to Menu"
        ]

        for i, control in enumerate(controls):
            text = self.font_small.render(control, True, GRAY)
            screen.blit(text, (WIDTH//2 - text.get_width()//2, 500 + i * 25))

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
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
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
        self.selected_car = CarType.AE86
        self.player_name = ""
        self.reset_game()

    def reset_game(self):
        self.player = PlayerCar(self.selected_car)
        self.road = Road()
        self.enemies = []
        self.particles = []
        self.spawn_timer = 0
        self.game_over = False

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if self.state == GameState.MENU:
                result = self.menu.handle_input(event)
                if result is not None:
                    if result == 0:  # START GAME
                        self.state = GameState.CAR_SELECT
                    elif result == 1:  # CAR SELECT
                        self.state = GameState.CAR_SELECT
                    elif result == 2:  # LEADERBOARD
                        self.state = GameState.LEADERBOARD
                    elif result == 3:  # QUIT
                        return False

            elif self.state == GameState.CAR_SELECT:
                result = self.car_selection.handle_input(event)
                if result == "BACK":
                    self.state = GameState.MENU
                elif result is not None and isinstance(result, CarType):
                    self.selected_car = result
                    self.state = GameState.NAME_INPUT
                    self.name_input.name = ""  # Сбрасываем имя
                    self.name_input.error_message = ""  # Сбрасываем ошибку

            elif self.state == GameState.NAME_INPUT:
                result = self.name_input.handle_input(event)
                if result == "BACK":
                    self.state = GameState.CAR_SELECT
                elif result is not None:
                    self.player_name = result
                    self.state = GameState.PLAYING
                    self.reset_game()

            elif self.state == GameState.PLAYING:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.state = GameState.PAUSED
                    if event.key == pygame.K_r and self.game_over:
                        self.reset_game()

            elif self.state == GameState.PAUSED:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        self.state = GameState.PLAYING
                    elif event.key == pygame.K_ESCAPE:
                        self.state = GameState.MENU

            elif self.state == GameState.GAME_OVER:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        # Сохраняем результат перед рестартом
                        self.leaderboard.add_entry(
                            self.player_name,
                            self.player.score,
                            self.player.drift_score,
                            self.selected_car.value["name"]
                        )
                        self.reset_game()
                        self.state = GameState.PLAYING
                    elif event.key == pygame.K_ESCAPE:
                        # Сохраняем результат и возвращаемся в меню
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

        return True

    def update(self):
        if self.state != GameState.PLAYING or self.game_over:
            return

        keys = pygame.key.get_pressed()
        self.player.update(keys, self.road.current_turn, self.road.turn_intensity)

        # Обновление дороги
        self.road.update(self.player.speed)

        # Спавн вражеских автомобилей
        self.spawn_timer += 1
        if self.spawn_timer > 60 - min(50, self.player.score // 100):
            self.spawn_timer = 0
            if len(self.enemies) < 5 + self.player.score // 500:
                self.enemies.append(EnemyCar(self.player.speed, self.road.current_turn, self.road.turn_intensity))

        # Обновление вражеских автомобилей и проверка столкновений
        for enemy in self.enemies[:]:
            if enemy.update(self.player.speed, self.road.current_turn, self.road.turn_intensity):
                self.enemies.remove(enemy)
            elif enemy.check_collision(self.player):
                self.create_explosion(self.player.x, self.player.y)
                self.game_over = True
                self.state = GameState.GAME_OVER
            elif not enemy.passed and enemy.y > self.player.y:
                enemy.passed = True
                # Уменьшенный заработок за обгоны
                self.player.score += 5 * (1 + self.player.combo // 5)  # Уменьшено с 10 до 5
                self.player.combo += 1
                self.player.last_overtake = pygame.time.get_ticks()
                self.player.nitro = min(100, self.player.nitro + 5)

        # Обновление частиц
        for particle in self.particles[:]:
            particle.update()
            if particle.is_dead():
                self.particles.remove(particle)

        # Увеличиваем счет за скорость (уменьшенный)
        self.player.score += int(self.player.speed * 0.05)  # Уменьшено с 0.1 до 0.05

    def create_explosion(self, x, y):
        for _ in range(30):
            color = random.choice([RED, YELLOW, (255, 100, 0)])
            self.particles.append(Particle(x, y, color))

    def draw_hud(self):
        # Имя игрока
        name_text = self.font_small.render(f"DRIVER: {self.player_name}", True, WHITE)
        self.screen.blit(name_text, (20, 20))

        # Спидометр
        speed_text = self.font_medium.render(f"SPEED: {int(self.player.speed * 20)} km/h", True, WHITE)
        self.screen.blit(speed_text, (20, 50))

        # Счет
        score_text = self.font_medium.render(f"SCORE: {self.player.score}", True, WHITE)
        self.screen.blit(score_text, (20, 80))

        # Комбо
        if self.player.combo > 1:
            combo_text = self.font_medium.render(f"COMBO: x{self.player.combo}", True, YELLOW)
            self.screen.blit(combo_text, (20, 110))

        # Очки дрифта
        if self.player.drift_power > 10:
            drift_color = GREEN if self.player.drift_bonus_active else GRAY
            drift_text = self.font_small.render(f"DRIFT: {self.player.drift_score} (x{self.player.drift_combo})", True, drift_color)
            self.screen.blit(drift_text, (20, 140))

            # Подсказка для дрифта
            if not self.player.drift_bonus_active and self.player.is_drifting:
                hint_text = self.font_small.render("DRIFT IN TURNS FOR BONUS!", True, YELLOW)
                self.screen.blit(hint_text, (WIDTH//2 - hint_text.get_width()//2, 160))

        # Нитро
        nitro_text = self.font_small.render("NITRO", True, WHITE)
        self.screen.blit(nitro_text, (WIDTH - 100, 20))
        pygame.draw.rect(self.screen, DARK_GRAY, (WIDTH - 100, 45, 80, 15))
        pygame.draw.rect(self.screen, BLUE, (WIDTH - 100, 45, 80 * (self.player.nitro / 100), 15))

        # Управление
        controls_text = [
            "↑↓: Gas/Brake",
            "←→: Change Lane",
            "Z: Drift",
            "X: Nitro",
            "ESC: Pause"
        ]

        for i, text in enumerate(controls_text):
            control_surf = self.font_small.render(text, True, GRAY)
            self.screen.blit(control_surf, (WIDTH - 150, HEIGHT - 120 + i * 20))

    def draw_playing(self):
        # Очистка экрана
        self.screen.fill(BLACK)

        # Рисуем дорогу
        self.road.draw(self.screen)

        # Рисуем вражеские автомобили
        for enemy in self.enemies:
            enemy.draw(self.screen, self.road.current_turn, self.road.turn_intensity)

        # Рисуем частицы
        for particle in self.particles:
            particle.draw(self.screen)

        # Рисуем игрока
        self.player.draw(self.screen, self.road.current_turn, self.road.turn_intensity)

        # HUD
        self.draw_hud()

        # Game Over экран
        if self.game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (0, 0))

            game_over_text = self.font_large.render("GAME OVER", True, RED)
            name_text = self.font_medium.render(f"Driver: {self.player_name}", True, WHITE)
            score_text = self.font_medium.render(f"Final Score: {self.player.score}", True, WHITE)
            drift_text = self.font_medium.render(f"Drift Score: {self.player.drift_score}", True, GREEN)
            restart_text = self.font_medium.render("Press R to Restart", True, YELLOW)
            menu_text = self.font_medium.render("Press ESC for Menu", True, YELLOW)

            self.screen.blit(game_over_text, (WIDTH//2 - game_over_text.get_width()//2, HEIGHT//2 - 120))
            self.screen.blit(name_text, (WIDTH//2 - name_text.get_width()//2, HEIGHT//2 - 60))
            self.screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, HEIGHT//2 - 20))
            self.screen.blit(drift_text, (WIDTH//2 - drift_text.get_width()//2, HEIGHT//2 + 20))
            self.screen.blit(restart_text, (WIDTH//2 - restart_text.get_width()//2, HEIGHT//2 + 80))
            self.screen.blit(menu_text, (WIDTH//2 - menu_text.get_width()//2, HEIGHT//2 + 120))

        # Экран паузы
        if self.state == GameState.PAUSED:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.screen.blit(overlay, (0, 0))

            pause_text = self.font_large.render("PAUSED", True, YELLOW)
            continue_text = self.font_medium.render("Press ENTER to Continue", True, WHITE)
            menu_text = self.font_medium.render("Press ESC for Menu", True, WHITE)

            self.screen.blit(pause_text, (WIDTH//2 - pause_text.get_width()//2, HEIGHT//2 - 60))
            self.screen.blit(continue_text, (WIDTH//2 - continue_text.get_width()//2, HEIGHT//2))
            self.screen.blit(menu_text, (WIDTH//2 - menu_text.get_width()//2, HEIGHT//2 + 40))

        # CRT эффекты
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
        elif self.state == GameState.PLAYING or self.state == GameState.PAUSED or self.state == GameState.GAME_OVER:
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
