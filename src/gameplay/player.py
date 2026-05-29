from util.constants import *
from gameplay.bullet import Bullet
from gameplay.entity import Entity
from gameplay.muzzle_flash import MuzzleFlash
from random import uniform

class Player(Entity):

	def __init__(self, id, name, name_color, character, position, size, game) -> None:

		super().__init__(id, name, name_color, position, size, game.assets.image_path(f"char_{character}_gun"), (game.players, game.all_sprites), PLAYER_MAX_HP, PLAYER_MAX_HP)
		
		# Shooting
		self.is_shooting = False
		self.shoot_rate = SHOOT_RATE
		self.last_shoot_time = -1000

		self.character, self.game = character, game
		self.map, self.camera = game.map, game.camera

		# Hit rect for collisions
		self.hit_rect = PLAYER_HIT_RECT.copy()
		self.hit_rect.center = self.rect.center
		self.auto_shoot = True,

		#region Physical Variables

		# Force (Newton)
		self.force = Vec(3, 3)
		self.frictional_force = Vec(-1., -1.)
		self.net_force = Vec()

		# Acceleration (m/s**2)
		self.acceleration = Vec()
		self.max_acceleration = 5

		# Velocity / Speed (m/s*2)
		self.velocity = Vec()
		self.max_speed = 5

		# Rotation
		self.force_rotation = Vec()
		self.delta = Vec()
		self.angle = 0
		
		# Weight (Kilogram)
		self.density = 25 # d (kg/piksel**2)
		self.weight = (self.rect.width/TILE_WIDTH * self.rect.height/TILE_HEIGHT) * self.density # m = d*v

		#endregion

	def rotate_to_mouse(self):

		"""
		
		# Also this works to calculate angel

		distanceX = self.game.mouse_position[0] - self.game.camera.apply(self.rect)[0]
		distanceY = self.game.mouse_position[1] - self.game.camera.apply(self.rect)[1]

		self.angle = math.atan2(-distanceY, distanceX)
		self.angle = math.degrees(self.angle)  # Convert radians to degrees

		"""

		self.angle = (Vec(self.game.mouse_position) - Vec(self.game.camera.apply(self.rect).center)).angle_to(Vec(1,0)) # sthis calculating angle between difference vector and x apsis
		#self.rotate(self.angle)

	def move(self):

		#region Get the rotation of force

		if self.game.keys[pygame.K_LEFT] or self.game.keys[pygame.K_a]:

			self.force_rotation.x = -1

		elif self.game.keys[pygame.K_RIGHT] or self.game.keys[pygame.K_d]:
			
			self.force_rotation.x = 1

		else:

			self.force_rotation.x = 0

		if self.game.keys[pygame.K_UP] or self.game.keys[pygame.K_w]:
			
			self.force_rotation.y = -1

		elif self.game.keys[pygame.K_DOWN] or self.game.keys[pygame.K_s]:
			
			self.force_rotation.y = 1

		else:

			self.force_rotation.y = 0

		#endregion

		# Normalize force rotation
		if self.force_rotation.length() != 0:
		
			self.force_rotation.normalize()

		# Calculate net force
		self.net_force = self.force.elementwise() * self.force_rotation

		# apply frictional force
		if self.velocity.length() != 0:

			if abs(self.net_force.x) > self.frictional_force.x:

				self.net_force.x += self.frictional_force.x * self.velocity.normalize().x * self.game.delta_time

			if abs(self.net_force.y) > self.frictional_force.y:

				self.net_force.y += self.frictional_force.y * self.velocity.normalize().y * self.game.delta_time
			
		# Calculate acceleration
		self.acceleration = self.net_force / self.weight

		# Clamp acceleration
		self.acceleration.x = max(-self.max_acceleration, min(self.max_acceleration, self.acceleration.x))
		self.acceleration.y = max(-self.max_acceleration, min(self.max_acceleration, self.acceleration.y))

		# update velocity
		self.velocity += self.acceleration * self.game.delta_time

		# Limit velocity to a maximum speed
		if self.velocity.length() > self.max_speed:

			self.velocity.scale_to_length(self.max_speed)

		if abs(self.velocity.x) < 0.01:

			self.velocity.x = 0

		if abs(self.velocity.y) < 0.01:
			
			self.velocity.y = 0
		
		self.delta = (self.velocity * self.game.delta_time) + (0.5 * self.acceleration * self.game.delta_time * self.game.delta_time)

		#super().move(self.delta)

	def shoot(self):

		now = pygame.time.get_ticks()

		if now - self.last_shoot_time > self.shoot_rate:

			spread = uniform(-GUN_SPREAD, GUN_SPREAD)
			angle = self.angle + spread
			position = Vec(self.rect.center) + BARREL_OFFSET.rotate(-angle)

			Bullet(self, position, angle)
			MuzzleFlash(self.game, position, self.angle)

			self.velocity = Vec(-KICKBACK, 0).rotate(-self.angle)

			self.last_shoot_time = now
						
	def handle_events(self, event, mouse_position, keys):
		
		if self.alive():
			
			if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
			
				if self.auto_shoot:

					self.is_shooting = True

				else:

					self.game.shoot()

			if event.type == pygame.MOUSEBUTTONUP and event.button == 1:

				self.is_shooting = False

	def update(self):
		
		self.rotate(self.angle)
		super().move(self.delta)

class Players(pygame.sprite.Group):

	def __init__(self, game) -> None:
		
		super().__init__()
		self.game = game

	def add_player(self, player_info, name_color):
		
		return Player(player_info.id, player_info.name, name_color, player_info.character_name, self.game.map.spawn_points[player_info.base_number], player_info.size, self.game)

	def get_player_with_id(self, id: int) -> Player:

		for player in self.sprites():

			if player.id == id:

				return player
