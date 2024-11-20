import pygame as pg
import sys, time
from bird import Bird
from pipe import Pipe
import pymongo
from pymongo import MongoClient

pg.init()

class Game:
    def __init__(self):
        # Setting window config
        self.width = 600
        self.height = 768
        self.scale_factor = 1.5
        self.win = pg.display.set_mode((self.width, self.height))
        self.clock = pg.time.Clock()
        self.move_speed = 250
        self.bird = Bird(self.scale_factor)

        self.is_enter_pressed = False
        self.pipes = []
        self.pipe_generate_counter = 71
        self.score = 0
        self.setUpBgAndGround()
        self.loadSounds()  # Load sounds

        self.game_over = False
        self.player_name = ""

        # MongoDB connection
        self.connect_to_db()

        self.getPlayerName()
        self.startScreen()

    def loadSounds(self):
        # Load sound effects
        self.flap_sound = pg.mixer.Sound('assets/sfx/flap.mp3')
        self.score_sound = pg.mixer.Sound('assets/sfx/score.mp3')
        self.game_over_sound = pg.mixer.Sound('assets/sfx/dead.mp3')

        # Load background music
        pg.mixer.music.load('assets/sfx/background.mp3')

        pg.mixer.music.set_volume(0.3)

        # Play background music
        pg.mixer.music.play(-1)  # -1 means play indefinitely

    def getPlayerName(self):
        self.win.fill((0, 0, 0))
        font = pg.font.Font(None, 74)
        text = font.render("Enter Your Name:", True, (255, 255, 255))
        text_rect = text.get_rect(center=(self.width / 2, self.height / 2 - 50))
        self.win.blit(text, text_rect)
        pg.display.update()

        name = ""
        entering_name = True
        while entering_name:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    pg.quit()
                    sys.exit()
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_RETURN:
                        if name != "":
                            entering_name = False
                            self.player_name = name
                    elif event.key == pg.K_BACKSPACE:
                        name = name[:-1]
                    else:
                        name += event.unicode

                if event.type == pg.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if name != "":
                            entering_name = False
                            self.player_name = name

            self.win.fill((0, 0, 0), (text_rect.left, text_rect.bottom + 10, 500, 50))
            name_text = font.render(name, True, (255, 255, 255))
            name_rect = name_text.get_rect(center=(self.width / 2, self.height / 2 + 10))
            self.win.blit(name_text, name_rect)
            pg.display.update()

    def startScreen(self):
        self.win.fill((0, 0, 0))
        font = pg.font.Font(None, 74)
        start_text = font.render("Enter to Begin", True, (255, 255, 255))
        start_rect = start_text.get_rect(center=(self.width / 2, self.height / 2))
        self.win.blit(start_text, start_rect)

        leaderboard_text = font.render("Leaderboard", True, (255, 255, 255))
        leaderboard_rect = leaderboard_text.get_rect(center=(self.width / 2, self.height / 2 + 100))
        self.win.blit(leaderboard_text, leaderboard_rect)

        pg.display.update()
        self.waitForKeyPress()

        mouse_pos = pg.mouse.get_pos()
        if leaderboard_rect.collidepoint(mouse_pos):
            self.show_leaderboard()
        else:
            self.resetGame()
            self.gameLoop()

    def waitForKeyPress(self):
        waiting = True
        while waiting:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    pg.quit()
                    sys.exit()
                if event.type == pg.KEYDOWN or event.type == pg.MOUSEBUTTONDOWN:
                    waiting = False

    def resetGame(self):
        self.bird = Bird(self.scale_factor)
        self.is_enter_pressed = False
        self.pipes = []
        self.pipe_generate_counter = 71
        self.score = 0
        self.game_over = False

    def gameLoop(self):
        last_time = time.time()
        while True:
            # Calculating delta time
            new_time = time.time()
            dt = new_time - last_time
            last_time = new_time

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    pg.quit()
                    sys.exit()
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_RETURN and not self.game_over:
                        self.is_enter_pressed = True
                        self.bird.update_on = True
                        self.flap_sound.play()  # Play flap sound
                    if event.key == pg.K_SPACE and self.is_enter_pressed:
                        self.bird.flap(dt)
                        self.flap_sound.play()  # Play flap sound
                if event.type == pg.MOUSEBUTTONDOWN:
                    if not self.game_over:
                        self.is_enter_pressed = True
                        self.bird.update_on = True
                        self.bird.flap(dt)
                        self.flap_sound.play()  # Play flap sound

            if self.game_over:
                self.displayGameOver()
                pg.display.update()
                self.waitForKeyPress()
                self.startScreen()

            self.updateEverything(dt)
            self.checkCollisions()
            self.drawEverything()
            pg.display.update()
            self.clock.tick(60)

    def checkCollisions(self):
        if len(self.pipes):
            if self.bird.rect.bottom > 568:
                self.bird.update_on = False
                self.is_enter_pressed = False
                self.game_over = True
                self.game_over_sound.play()  # Play game over sound
                self.save_score_to_db()  # Save score to database
            if (self.bird.rect.colliderect(self.pipes[0].rect_down) or
                self.bird.rect.colliderect(self.pipes[0].rect_up)):
                self.is_enter_pressed = False
                self.game_over = True
                self.game_over_sound.play()  # Play game over sound
                self.save_score_to_db()  # Save score to database
            # Check if bird passed the pipes
            if self.pipes[0].rect_down.right < self.bird.rect.left:
                self.pipes.pop(0)
                self.score += 10
                self.score_sound.play()  # Play score sound

    def updateEverything(self, dt):
        if self.is_enter_pressed and not self.game_over:
            # Moving the ground
            self.ground1_rect.x -= int(self.move_speed * dt)
            self.ground2_rect.x -= int(self.move_speed * dt)

            if self.ground1_rect.right < 0:
                self.ground1_rect.x = self.ground2_rect.right
            if self.ground2_rect.right < 0:
                self.ground2_rect.x = self.ground1_rect.right

            # Generating pipes
            if self.pipe_generate_counter > 70:
                self.pipes.append(Pipe(self.scale_factor, self.move_speed))
                self.pipe_generate_counter = 0
                
            self.pipe_generate_counter += 1

            # Moving the pipes
            for pipe in self.pipes:
                pipe.update(dt)
            
            # Removing pipes if out of screen
            if len(self.pipes) != 0:
                if self.pipes[0].rect_up.right < 0:
                    self.pipes.pop(0)
                    
        # Moving the bird
        self.bird.update(dt)

    def drawEverything(self):
        self.win.blit(self.bg_img, (0, -300))
        for pipe in self.pipes:
            pipe.drawPipe(self.win)
        self.win.blit(self.ground1_img, self.ground1_rect)
        self.win.blit(self.ground2_img, self.ground2_rect)
        self.win.blit(self.bird.image, self.bird.rect)
        self.drawScore()

    def drawScore(self):
        font = pg.font.Font(None, 36)
        text = font.render(f"Score: {self.score}", True, (0, 0, 0))
        self.win.blit(text, (10, 10))

    def setUpBgAndGround(self):
        # Loading images for bg and ground
        self.bg_img = pg.transform.scale_by(pg.image.load("assets/bg.png").convert(), self.scale_factor)
        self.ground1_img = pg.transform.scale_by(pg.image.load("assets/ground.png").convert(), self.scale_factor)
        self.ground2_img = pg.transform.scale_by(pg.image.load("assets/ground.png").convert(), self.scale_factor)
        
        self.ground1_rect = self.ground1_img.get_rect()
        self.ground2_rect = self.ground2_img.get_rect()

        self.ground1_rect.x = 0
        self.ground2_rect.x = self.ground1_rect.right
        self.ground1_rect.y = 568
        self.ground2_rect.y = 568

    def displayGameOver(self):
        font = pg.font.Font(None, 74)
        text = font.render("Game Over", True, (0, 0, 0))
        text_rect = text.get_rect(center=(self.width / 2, self.height / 2 - 100))
        self.win.blit(text, text_rect)

        score_text = font.render(f"Score: {self.score}", True, (0, 0, 0))
        score_rect = score_text.get_rect(center=(self.width / 2, self.height / 2))
        self.win.blit(score_text, score_rect)

        name_text = font.render(f"Player: {self.player_name}", True, (0, 0, 0))
        name_rect = name_text.get_rect(center=(self.width / 2, self.height / 2 + 100))
        self.win.blit(name_text, name_rect)

        # Display highest score
        highest_score = self.getHighestScore()
        highest_score_text = font.render(f"Highest Score: {highest_score}", True, (0, 0, 0))
        highest_score_rect = highest_score_text.get_rect(center=(self.width / 2, self.height / 2 + 200))
        self.win.blit(highest_score_text, highest_score_rect)

    def getHighestScore(self):
        # Query the database to retrieve the highest score
        highest_score_record = self.collection.find_one(sort=[("score", pymongo.DESCENDING)])
        if highest_score_record:
            return highest_score_record["score"]
        else:
            return 0  # If no record found, return 0

    # MongoDB connection method
    def connect_to_db(self):
        # Replace with your MongoDB Atlas connection string
        self.client = MongoClient("mongodb+srv://prajeetapatil5500:ra958k2ubh@cluster1.fafgqvs.mongodb.net/flappybirdscores?retryWrites=true&w=majority&appName=Cluster1")
        self.db = self.client["flappybirdscores"]
        self.collection = self.db["score"]

    # Method to save score to the database
    def save_score_to_db(self):
        score_data = {
            "player_name": self.player_name,
            "score": self.score,
            "timestamp": time.time()
        }
        # Insert the current score data into the database
        self.collection.insert_one(score_data)

    def get_top_scores(self, limit=10):
        # Retrieve the top 'limit' scores from MongoDB, sorted by score in descending order
        top_scores = self.collection.find().sort("score", pymongo.DESCENDING).limit(limit)
        return list(top_scores)
        
    def show_leaderboard(self):
        top_scores = self.get_top_scores()

        self.win.fill((0, 0, 0))
        font = pg.font.Font(None, 74)
        title_text = font.render("Leaderboard", True, (255, 255, 255))
        title_rect = title_text.get_rect(center=(self.width / 2, 100))
        self.win.blit(title_text, title_rect)

        score_font = pg.font.Font(None, 36)
        y_offset = 200
        for idx, score_data in enumerate(top_scores):
            player_name = score_data["player_name"]
            score = score_data["score"]
            score_text = score_font.render(f"{idx + 1}. {player_name}: {score}", True, (255, 255, 255))
            score_rect = score_text.get_rect(center=(self.width / 2, y_offset))
            self.win.blit(score_text, score_rect)
            y_offset += 50

        pg.display.update()
        self.waitForKeyPress()
        self.startScreen()

game = Game()
