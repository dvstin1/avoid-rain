"""
Manages the global game state and coordinates engine components.
"""
from constants import (
    PLAYER_START_X, PLAYER_START_Y, DUMMY_X, DUMMY_Y,
    DUMMY_WIDTH, DUMMY_HEIGHT, DAMAGE_NUMBER_LIFETIME, DAMAGE_NUMBER_SPEED,
    SWORD_DAMAGE, COLOR_YELLOW, RECOVERY_TIME, STAGGER_OUTLINE_TIME
)
from engine.player import Player, PlayerStateEnum
from engine.world import World
from engine.combat import get_sword_hitbox
from engine.physics import check_aabb_collision

class GameState:
    """Master state object for the game engine."""
    def __init__(self):
        self.world = World()
        self.player = Player(PLAYER_START_X, PLAYER_START_Y)

        # Dummy Entity State
        self.dummy_rect = (DUMMY_X, DUMMY_Y, DUMMY_WIDTH, DUMMY_HEIGHT)
        self.dummy_stagger_timer = 0.0
        self.dummy_outline_timer = 0.0

        self.damage_numbers = []

    def update(self, dt, actions):
        """Update all game logic."""
        move_dir = actions.get('move', (0, 0))
        attack_pressed = actions.get('attack', False)

        # 1. Update Player
        player_rect = (self.player.x, self.player.y, self.player.width, self.player.height)
        walls = self.world.get_nearby_walls(player_rect)
        self.player.update(dt, move_dir, walls, attack_pressed)

        # 2. Check for Sword Hits
        if self.player.state == PlayerStateEnum.ATTACKING:
            hitbox = get_sword_hitbox(self.player.get_center(), self.player.facing)
            if check_aabb_collision(hitbox, self.dummy_rect):
                if self.dummy_stagger_timer <= 0: # Only hit if not recovering
                    self.trigger_dummy_hit(SWORD_DAMAGE, COLOR_YELLOW)
                    self.dummy_stagger_timer = RECOVERY_TIME
                    self.dummy_outline_timer = STAGGER_OUTLINE_TIME

        # 3. Update Timers
        if self.dummy_stagger_timer > 0:
            self.dummy_stagger_timer -= dt
        if self.dummy_outline_timer > 0:
            self.dummy_outline_timer -= dt

        self.update_damage_numbers(dt)

    def update_damage_numbers(self, dt):
        """Handle fading and movement of damage numbers."""
        for num in self.damage_numbers[:]:
            num['time'] -= dt
            x, y = num['pos']
            num['pos'] = (x, y - DAMAGE_NUMBER_SPEED * dt)
            if num['time'] <= 0:
                self.damage_numbers.remove(num)

    def trigger_dummy_hit(self, damage, color):
        """Simulation of hitting the dummy."""
        self.damage_numbers.append({
            'val': damage,
            'pos': (self.dummy_rect[0] + 10, self.dummy_rect[1] - 20),
            'time': DAMAGE_NUMBER_LIFETIME,
            'color': color
        })
