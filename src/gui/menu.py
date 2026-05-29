from util.constants import *
from gui.object import Object
from gui.input_box import InputBox
from gui.button import TriangleButton, EllipseButton
from gui.text import Text
from pygame_core.asset_path import ImagePath

class Menu():

	def __init__(self, game) -> None:

		super().__init__()

		self.game = game

		self.tabs = {

			"mainMenu" : pygame.sprite.Group(),
			"playerMenu" : pygame.sprite.Group(),
			"gameTypeMenu" : pygame.sprite.Group(),
			"createRoomMenu" : pygame.sprite.Group(),
			"connectMenu" : pygame.sprite.Group(),
			"roomMenu" : pygame.sprite.Group()

		}

		self.panel = Object(("CENTER", "CENTER"), size=(400, 500))

		self.title = Text(("CENTER", self.panel.rect.y-80), WINDOW_TITLE, 60, color=Red)
		self.player_count_text = Text(("CENTER", self.panel.rect.bottom+30), "You are playing in offline mode !", 24, background_color=Black, color=Red)		

		self.selected_character = 0
		self.character_texts = []
		self.characters = []

		for character_name in CHARACTER_LIST:

			self.characters.append(Object(("CENTER", 195), CHARACTER_SIZE, ImagePath("idle", "characters/"+character_name), parent_rect=self.panel.screen_rect))

			words = character_name.split("_")
			character_name = ""

			for text in words:

				if not character_name == "":

					character_name += " "

				character_name += text.capitalize()
		
			self.character_texts.append(Text(("CENTER", 145), character_name, 40, parent_rect=self.panel.screen_rect))

		#region Create gui objects
			
		# Main menu
		self.settings_button = EllipseButton(("CENTER", "CENTER"), (300, 60), Red, Blue, sprite_groups=self.tabs["mainMenu"], parent_rect=self.panel.screen_rect, text="SETTINGS", text_size=40, is_active=False)
		self.play_button = EllipseButton(("CENTER", self.settings_button.rect.y - 140), (300, 60), Red, Blue, sprite_groups=self.tabs["mainMenu"], parent_rect=self.panel.screen_rect, text="PLAY", text_size=40)
		self.achievments_button = EllipseButton(("CENTER", self.settings_button.rect.y - 70), (300, 60), Red, Blue, sprite_groups=self.tabs["mainMenu"], parent_rect=self.panel.screen_rect, text="ACHIEVMENTS", text_size=40, is_active=False)
		self.credits_button = EllipseButton(("CENTER", self.settings_button.rect.y + 70), (300, 60), Red, Blue, sprite_groups=self.tabs["mainMenu"], parent_rect=self.panel.screen_rect, text="CREDITS", text_size=40, is_active=False)
		self.exit_button = EllipseButton(("CENTER", self.settings_button.rect.y + 140), (300, 60), Red, Blue, sprite_groups=self.tabs["mainMenu"], parent_rect=self.panel.screen_rect, text="EXIT", text_size=40)

		# Player menu
		self.player_name_text = Text(("CENTER", 40), "PLAYER NAME", 40, sprite_groups=self.tabs["playerMenu"], parent_rect=self.panel.screen_rect)
		self.player_name_entry = InputBox(("CENTER", 90), (300, 40), '', 'Please enter a player name...', self.tabs["playerMenu"], self.panel.screen_rect)
		self.previous = TriangleButton((75, 185), (50, 50), Blue, Red, sprite_groups=self.tabs["playerMenu"], parent_rect=self.panel.screen_rect, rotation="LEFT")
		self.next = TriangleButton((275, 185), (50, 50), Blue, Red, sprite_groups=self.tabs["playerMenu"], parent_rect=self.panel.screen_rect)
		self.confirm_button = EllipseButton(("CENTER", self.credits_button.rect.y), (300, 60), Red, Blue, sprite_groups=[self.tabs["playerMenu"]], parent_rect=self.panel.screen_rect, text="CONFIRM", text_size=40)
		self.back_button = EllipseButton(("CENTER", self.exit_button.rect.y), (300, 60), Red, Blue, sprite_groups=[self.tabs["playerMenu"]], parent_rect=self.panel.screen_rect, text="BACK", text_size=40)

		# Game type menu
		self.create_room_button = EllipseButton(("CENTER", "CENTER"), (300, 60), Red, Blue, sprite_groups=self.tabs["gameTypeMenu"], parent_rect=self.panel.screen_rect, text="CREATE ROOM", text_size=40)
		self.new_game_button = EllipseButton(("CENTER", self.settings_button.rect.y - 140), (300, 60), Red, Blue, sprite_groups=self.tabs["gameTypeMenu"], parent_rect=self.panel.screen_rect, text="NEW GAME", text_size=40)
		self.continue_button = EllipseButton(("CENTER", self.settings_button.rect.y - 70), (300, 60), Red, Blue, sprite_groups=self.tabs["gameTypeMenu"], parent_rect=self.panel.screen_rect, text="CONTINUE", text_size=40, is_active=False)	
		self.connect_button = EllipseButton(("CENTER", self.settings_button.rect.y + 70), (300, 60), Red, Blue, sprite_groups=self.tabs["gameTypeMenu"], parent_rect=self.panel.screen_rect, text="CONNECT", text_size=40)
		self.back_button2 = EllipseButton(("CENTER", self.settings_button.rect.y + 140), (300, 60), Red, Blue, sprite_groups=self.tabs["gameTypeMenu"], parent_rect=self.panel.screen_rect, text="BACK", text_size=40)

		# Create room menu
		self.create_button = EllipseButton(("CENTER", self.settings_button.rect.y + 70), (300, 60), Red, Blue, sprite_groups=self.tabs["createRoomMenu"], parent_rect=self.panel.screen_rect, text="CREATE", text_size=40)
		self.back_button3 = EllipseButton(("CENTER", self.settings_button.rect.y + 140), (300, 60), Red, Blue, sprite_groups=self.tabs["createRoomMenu"], parent_rect=self.panel.screen_rect, text="BACK", text_size=40)

		# Join room menu
		self.join_room_text = Text(("CENTER", 100), "JOIN A ROOM", 40, sprite_groups=self.tabs["connectMenu"], parent_rect=self.panel.screen_rect)
		self.room_id_entry = InputBox(("CENTER", 150), (300, 40), '', 'Please enter a room id...', self.tabs["connectMenu"], self.panel.screen_rect)
		self.join_button = EllipseButton(("CENTER", 250), (300, 60), Red, Blue, sprite_groups=self.tabs["connectMenu"], parent_rect=self.panel.screen_rect, text="JOIN", text_size=40)
		self.back_button4 = EllipseButton(("CENTER", 320), (300, 60), Red, Blue, sprite_groups=self.tabs["connectMenu"], parent_rect=self.panel.screen_rect, text="BACK", text_size=40)

		# Room menu
		self.room_text = Text(("CENTER", 20), "ROOM 0", 40, sprite_groups=self.tabs["roomMenu"], parent_rect=self.panel.screen_rect)
		self.leave_room = EllipseButton(("CENTER", self.panel.rect.height-200), (300, 60), Blue, Red, sprite_groups=self.tabs["roomMenu"], parent_rect=self.panel.screen_rect, text="LEAVE ROOM", text_size=40)

		#endregion

	def open_tab(self, tab: str) -> None:
	
		if not self.game.client.is_connected:

			self.create_room_button.disable()
			self.connect_button.disable()

		else:

			self.create_room_button.enable()
			self.connect_button.enable()
		
		for sprite in self.tabs[tab]:
			
			if hasattr(self.game, "mouse_position") and hasattr(sprite, "update_color"):

				sprite.update_color(self.game.mouse_position)
				sprite.rerender()

		self.tab = tab

	def update_players_in_room(self, players):

		self.player_texts = []
		are_all_ready = True

		for i, player in enumerate(players):
			
			if player.is_ruler:

				color = Red
				text = player.name + " (Ruler)"

			elif player.is_ready:

				color = Green
				text = player.name + " (Ready)"

			else:

				color = White
				text = player.name
				are_all_ready = False

			self.player_texts.append(Text(("CENTER", (i+1)*60 + 23), text, 25, color=color, parent_rect=self.panel.screen_rect))

		# firstly remove the existing button to update with new one
		if hasattr(self, 'start_game'):

			self.start_game.kill()

		if hasattr(self, 'ready'):

				self.ready.kill()

		if hasattr(self, 'unready'):

				self.unready.kill()

		# if the client is ruler of the room it should have start button else ready button
		if self.game.player_info.is_ruler:

			self.start_game = EllipseButton(("CENTER", self.panel.rect.height-115), (300, 60), Green, Red, sprite_groups=self.tabs["roomMenu"], parent_rect=self.panel.screen_rect, text="START GAME", text_size=40)

			if not are_all_ready: # disable start button if others arent ready 

				self.start_game.disable()
		
		else:
	
			if self.game.player_info.is_ready:

				self.unready = EllipseButton(("CENTER", self.panel.rect.height-115), (300, 60), Red, Blue, sprite_groups=self.tabs["roomMenu"], parent_rect=self.panel.screen_rect, text="UNREADY", text_size=40)

			else:

				self.ready = EllipseButton(("CENTER", self.panel.rect.height-115), (300, 60), Green, Red, sprite_groups=self.tabs["roomMenu"], parent_rect=self.panel.screen_rect, text="READY", text_size=40)
			
	def handle_events(self, event, mouse_position, keys):

		for sprite in self.tabs[self.tab]:

			if hasattr(sprite, "handle_events"):

				sprite.handle_events(event, mouse_position, keys)

		if self.tab == "mainMenu":
				
			if self.play_button.is_mouse_click(event, mouse_position):

				self.open_tab("playerMenu")

			elif self.exit_button.is_mouse_click(event, mouse_position):

				self.game.exit()

		elif self.tab == "playerMenu":
			
			if self.previous.is_mouse_click(event, mouse_position):

				if self.selected_character > 0:

					self.selected_character -= 1

			elif self.next.is_mouse_click(event, mouse_position):

				if self.selected_character+1 < len(self.characters):

					self.selected_character += 1

			elif self.confirm_button.is_mouse_click(event, mouse_position):

				self.game.set_player(self.player_name_entry.text, CHARACTER_LIST[self.selected_character])
				self.open_tab("gameTypeMenu")

			elif self.back_button.is_mouse_click(event, mouse_position):

				self.open_tab("mainMenu")

		elif self.tab == "gameTypeMenu":

			if self.new_game_button.is_mouse_click(event, mouse_position):
				
				self.game.mode = "offline"
				self.open_tab("createRoomMenu")

			elif self.create_room_button.is_mouse_click(event, mouse_position):
		
				self.game.mode = "online"
				self.open_tab("createRoomMenu")

			elif self.connect_button.is_mouse_click(event, mouse_position):
		
				self.game.mode = "online"
				self.open_tab("connectMenu")

			elif self.back_button2.is_mouse_click(event, mouse_position):

				self.open_tab("playerMenu")

		elif self.tab == "createRoomMenu":

			if self.create_button.is_mouse_click(event, mouse_position):
				
				map_name = "level2"
				self.game.create_room(map_name)

			elif self.back_button3.is_mouse_click(event, mouse_position):

				self.open_tab("gameTypeMenu")

		elif self.tab == "connectMenu":
			
			if self.join_button.is_mouse_click(event, mouse_position):

				room_id = int(self.room_id_entry.text) if self.room_id_entry.text.isnumeric() else 0
				self.game.join_room(room_id)

			elif self.back_button4.is_mouse_click(event, mouse_position):

				self.open_tab("gameTypeMenu")

		elif self.tab == "roomMenu":

			if self.game.player_info.is_ruler:

				if self.start_game.is_mouse_click(event, mouse_position):
					
					self.game.client.send_data("!START_GAME")

			else:

				if self.game.player_info.is_ready:

					if self.unready.is_mouse_click(event, mouse_position):

						self.game.client.send_data("!GET_UNREADY")

				else:

					if self.ready.is_mouse_click(event, mouse_position):

						self.game.client.send_data("!GET_READY")

			if self.leave_room.is_mouse_click(event, mouse_position):

				self.game.client.send_data("!LEAVE_ROOM")

	def update(self):

		pass

	def draw(self, image):
		
		image.fill(BACKGROUND_COLORS["menu"])

		self.title.draw(image)
		self.player_count_text.draw(image)

		self.panel.rerender()
		self.panel.image.fill((*Gray, 100))
		
		self.tabs[self.tab].draw(self.panel.image)

		if self.tab == "playerMenu":
			
			self.characters[self.selected_character].draw(self.panel.image)
			self.character_texts[self.selected_character].draw(self.panel.image)

		elif self.tab == "roomMenu":
	
			for i in range(6):

				pygame.draw.line(self.panel.image, White, (0, (i+1)*60), (self.panel.rect.width, (i+1)*60))

			pygame.draw.line(self.panel.image, White, (0, 0), (0, self.panel.rect.height))
			pygame.draw.line(self.panel.image, White, (self.panel.rect.width, 0), (self.panel.rect.width, self.panel.rect.height))

			for player_text in self.player_texts:

				player_text.draw(self.panel.image)
		
		self.panel.draw(image)
