class Circle:
    def __init__(self, radius):
        self.radius = radius
        self.pi = 3.14

    def get_area(self):
        return self.pi * (self.radius ** 2)

    def get_circumference(self):
        return 2 * self.pi * self.radius
    
    def print_circle_info(self):
        area = self.get_area()
        circumference = self.get_circumference()
        print(f"Circle with radius {self.radius} has an area of {area} and a circumference of {circumference}.")


circle1 = Circle(5)
circle1.print_circle_info()

circle2 = Circle(10)
circle2.print_circle_info()

circle3 = Circle(15)
circle3.print_circle_info()