"""
        distanceX, distanceY = mousePosition[0] - self.rect.x, mousePosition[1] - self.rect.y
        angle = (180 / math.pi) * -math.atan2(distanceY, distanceX)

        self.surface = pygame.transform.rotate(self.originalImage, int(angle))
        self.rect = self.surface.get_rect(center=self.rect.center)
        """

        #rotation = mousePosition - self.rect