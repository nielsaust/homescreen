from time import sleep
import pygame
import math

# Initialize Pygame
pygame.init()

# Set up your display
screen = pygame.display.set_mode((200, 200))
pygame.display.set_caption("Circular Progress Bar")

# Colors
black = (0, 0, 0)
white = (255, 255, 255)
blue = (0, 0, 255)

# Main loop
running = True
progress = 0
total_steps = 100

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill(black)

    # Calculate the angle for the progress
    angle = (progress / total_steps) * 360
    pygame.draw.arc(screen, blue, (50, 50, 100, 100), math.radians(-90), math.radians(-90 + angle), 15)

    pygame.display.update()
    progress += 1
    if progress > total_steps:
        progress = 0

    sleep(1)

# Quit Pygame
pygame.quit()
