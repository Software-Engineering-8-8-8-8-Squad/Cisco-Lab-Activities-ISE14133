class Location:
    def __init__(self, name, country):
        """
        This constructor initializes the Location object with a name and country.
        """
        self.name = name
        self.country = country

    def myLocation(self):
        """
        This method returns a string that describes the location.
        """
        print(f"Hi there! My name is {self.name} and I live in {self.country}.")

location1= Location("Tomas", "Portugal")
location1.myLocation()

location2 = Location("Ying", "China")
location2.myLocation()

location3 = Location("Amare", "Kenya")
location3.myLocation()

my_location = Location("Abdulloh", "Uzbekistan")
my_location.myLocation()