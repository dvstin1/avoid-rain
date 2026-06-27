# pylint: disable=too-many-arguments,too-many-positional-arguments,unused-argument,too-few-public-methods,too-many-instance-attributes
"""
Tests for Slug and Bat spatial sound effects, movement loop logic,
and attack sound channel concurrency limits.
"""

import math
from unittest.mock import MagicMock, patch
from engine.audio import AudioManager
from constants import SFX_FULL_VOLUME_DIST, SFX_MIN_VOLUME_DIST, SFX_MIN_VOLUME

class MockPlayer:
    """Mock Player class with essential attributes for audio testing."""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 40
        self.height = 40

    def get_center(self):
        """Returns the player center coordinates."""
        return (self.x + self.width / 2, self.y + self.height / 2)

class MockEnemy:
    """Mock Enemy class containing positional, HP and velocity attributes."""
    def __init__(self, name, x, y, hp=40, vx=0.0, vy=0.0, stagger_timer=0.0):
        self.name = name
        self.x = x
        self.y = y
        self.width = 32
        self.height = 32
        self.hp = hp
        self.vx = vx
        self.vy = vy
        self.stagger_timer = stagger_timer

    def get_center(self):
        """Returns the enemy center coordinates."""
        return (self.x + self.width / 2, self.y + self.height / 2)

class MockGameState:
    """Mock GameState class containing the player and active enemies."""
    def __init__(self, player, enemies):
        self.player = player
        self.enemies = enemies

@patch("pygame.mixer.init")
@patch("pygame.mixer.set_num_channels")
def test_spatial_volume_calculation(mock_set_channels, mock_mixer_init):
    """Verify spatial volume calculations at boundaries and linear interpolation."""
    audio = AudioManager()

    # Test full volume boundary (<= 120)
    assert audio.calculate_spatial_volume(0) == 1.0
    assert audio.calculate_spatial_volume(SFX_FULL_VOLUME_DIST) == 1.0

    # Test min volume boundary (>= 1280)
    assert audio.calculate_spatial_volume(SFX_MIN_VOLUME_DIST) == SFX_MIN_VOLUME
    assert audio.calculate_spatial_volume(1500) == SFX_MIN_VOLUME

    # Test intermediate values
    vol_mid = audio.calculate_spatial_volume(700)
    expected_mid = 1.0 - ((700 - SFX_FULL_VOLUME_DIST) / (SFX_MIN_VOLUME_DIST - SFX_FULL_VOLUME_DIST)) * 0.95
    assert math.isclose(vol_mid, expected_mid)

@patch("pygame.mixer.init")
@patch("pygame.mixer.set_num_channels")
@patch("pygame.mixer.Sound")
def test_movement_sound_limits_and_selection(mock_sound_class, mock_set_channels, mock_mixer_init):
    """Verify that only the closest 2 moving enemies of a type have active move sounds."""
    mock_sound_instance = MagicMock()
    mock_sound_class.return_value = mock_sound_instance
    mock_channel = MagicMock()
    mock_sound_instance.play.return_value = mock_channel
    mock_channel.get_busy.return_value = True

    audio = AudioManager()
    player = MockPlayer(0, 0)

    # Slugs at varying distances: closest two should play
    slugs = [
        MockEnemy("Slug", 100, 0, vx=10.0),
        MockEnemy("Slug", 200, 0, vx=10.0),
        MockEnemy("Slug", 300, 0, vx=10.0),
        MockEnemy("Slug", 400, 0, vx=10.0),
    ]

    state = MockGameState(player, slugs)

    with patch("os.path.exists", return_value=True):
        audio.update_enemy_sounds(state)

    assert len(audio.active_move_sounds) == 2

    assert id(slugs[0]) in audio.active_move_sounds
    assert id(slugs[1]) in audio.active_move_sounds
    assert id(slugs[2]) not in audio.active_move_sounds
    assert id(slugs[3]) not in audio.active_move_sounds

@patch("pygame.mixer.init")
@patch("pygame.mixer.set_num_channels")
@patch("pygame.mixer.Sound")
def test_attack_sound_limits(mock_sound_class, mock_set_channels, mock_mixer_init):
    """Verify concurrency limits on attack sounds (max 4 concurrent playbacks)."""
    mock_sound_instance = MagicMock()
    mock_sound_class.return_value = mock_sound_instance
    mock_channel = MagicMock()
    mock_sound_instance.play.return_value = mock_channel

    audio = AudioManager()

    # Under 4 sounds playing: play succeeds
    mock_sound_instance.get_num_channels.return_value = 2
    with patch("os.path.exists", return_value=True):
        audio.play_sfx("slug_attack.ogg")
        mock_sound_instance.play.assert_called_once()

    # 4 sounds playing: play call is skipped
    mock_sound_instance.play.reset_mock()
    mock_sound_instance.get_num_channels.return_value = 4
    with patch("os.path.exists", return_value=True):
        audio.play_sfx("slug_attack.ogg")
        mock_sound_instance.play.assert_not_called()
