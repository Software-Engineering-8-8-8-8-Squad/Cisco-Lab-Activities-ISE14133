import requests
import urllib.parse
import json
import os
from datetime import timedelta

# API configuration
API_KEY = "cd1bb4ac-2bdb-4437-8d21-8ab1ea18b06c"  # Using provided key
GEOCODE_URL = "https://graphhopper.com/api/1/geocode?"
ROUTE_URL = "https://graphhopper.com/api/1/route?"

# Create data directory if it doesn't exist
os.makedirs("data", exist_ok=True)

def display_separator(char="=", length=49):
    """Display a separator line with specified character and length."""
    print(char * length)

def display_header(message, char="+", length=49):
    """Display a header with specified message, character, and length."""
    display_separator(char, length)
    print(message)
    display_separator(char, length)

def format_time(seconds):
    """Convert seconds to HH:MM:SS format."""
    return str(timedelta(seconds=seconds)).zfill(8)

def format_distance(meters):
    """Format distance in km and miles."""
    km = meters / 1000.0
    miles = km * 0.621371
    return f"{miles:.1f} miles / {km:.1f} km"

def geocode_location(location, key=API_KEY):
    """
    Geocode a location to get its coordinates.
    
    Args:
        location (str): The location to geocode
        key (str): API key for GraphHopper
        
    Returns:
        tuple: (status_code, latitude, longitude, display_name) or (status_code, None, None, None)
    """
    if not location:
        return 0, None, None, None
    
    url = GEOCODE_URL + urllib.parse.urlencode({"q": location, "limit": "1", "key": key})
    
    try:
        response = requests.get(url)
        status_code = response.status_code
        
        if status_code == 200:
            json_data = response.json()
            
            # Save the json data to data folder for debugging/reference
            clean_name = location.replace(",", "_").replace(" ", "_")
            with open(f"data/geocode_{clean_name}.json", "w") as f:
                json.dump(json_data, f, indent=4)
            
            # Extract location information
            if json_data.get("hits") and len(json_data["hits"]) > 0:
                hit = json_data["hits"][0]
                lat = hit["point"]["lat"]
                lng = hit["point"]["lng"]
                display_name = hit.get("name", location)
                location_type = hit.get("osm_value", "")
                country = hit.get("country", "")
                
                # Build a more complete display name
                full_display_name = display_name
                if country:
                    full_display_name += f", {country}"
                
                print(f"Geocoding API URL for {full_display_name} (Location Type: {location_type})")
                print(url)
                
                return status_code, lat, lng, full_display_name
            else:
                print(f"No geocoding results found for {location}")
                return status_code, None, None, None
        else:
            print(f"Geocoding API error: Status code {status_code}")
            return status_code, None, None, None
    
    except Exception as e:
        print(f"Error during geocoding: {e}")
        return 0, None, None, None

def get_directions(start_loc, end_loc, vehicle="car", key=API_KEY):
    """
    Get directions between two locations.
    
    Args:
        start_loc (tuple): (lat, lng) of starting location
        end_loc (tuple): (lat, lng) of ending location
        vehicle (str): Vehicle profile (car, bike, foot)
        key (str): API key for GraphHopper
        
    Returns:
        tuple: (status_code, route_data)
    """
    start_lat, start_lng = start_loc
    end_lat, end_lng = end_loc
    
    params = {
        "key": key,
        "vehicle": vehicle,
        "point": [f"{start_lat},{start_lng}", f"{end_lat},{end_lng}"]
    }
    
    # Construct URL with multiple point parameters
    url_parts = []
    url_parts.append(f"key={key}")
    url_parts.append(f"vehicle={vehicle}")
    for point in params["point"]:
        url_parts.append(f"point={urllib.parse.quote(point)}")
    
    url = ROUTE_URL + "&".join(url_parts)
    
    try:
        response = requests.get(url)
        status_code = response.status_code
        
        print("=================================================")
        print(f"Routing API Status: {status_code}")
        print(f"Routing API URL:\n{url}")
        print("=================================================")
        
        if status_code == 200:
            return status_code, response.json()
        else:
            return status_code, response.json() if hasattr(response, 'json') else None
    
    except Exception as e:
        print(f"Error during routing: {e}")
        return 0, None

def display_route(route_data, start_name, end_name, vehicle):
    """Display the route information and directions."""
    if not route_data or "paths" not in route_data or not route_data["paths"]:
        print(f"Directions from {start_name} to {end_name} by {vehicle}")
        print("=================================================")
        print("Error: No route data available")
        return
    
    path = route_data["paths"][0]
    
    # Extract route information
    distance = path.get("distance", 0)  # in meters
    time_value = path.get("time", 0)    # in milliseconds
    
    # Convert time from milliseconds to seconds
    time_seconds = time_value / 1000
    
    print(f"Directions from {start_name} to {end_name} by {vehicle}")
    print("=================================================")
    print(f"Distance Traveled: {format_distance(distance)}")
    print(f"Trip Duration: {format_time(time_seconds)}")
    print("=================================================")
    
    # Display instructions
    if "instructions" in path:
        for instruction in path["instructions"]:
            text = instruction.get("text", "Continue")
            distance_inst = instruction.get("distance", 0)
            
            # Format distance for each instruction
            km = distance_inst / 1000.0
            miles = km * 0.621371
            
            print(f"{text} ( {km:.1f} km / {miles:.1f} miles )")
    
    print("=================================================")

def get_available_profiles():
    """Return a list of available vehicle profiles."""
    # These are the standard profiles supported by GraphHopper
    return ["car", "bike", "foot"]

def main():
    """Main function to run the application."""
    try:
        while True:
            # Display available vehicle profiles
            profiles = get_available_profiles()
            display_header("Vehicle profiles available on Graphhopper:", "+")
            print(", ".join(profiles))
            display_header("", "+")
            
            # Get vehicle profile
            vehicle = input("Enter a vehicle profile from the list above: ").strip().lower()
            
            if vehicle == "q":
                print("Exiting program.")
                break
            
            if vehicle not in profiles:
                print("No valid vehicle profile was entered. Using the car profile.")
                vehicle = "car"
            
            # Get starting location
            start_location = input("Starting Location: ").strip()
            while not start_location:
                start_location = input("Enter location again: ").strip()
            
            # Geocode starting location
            start_status, start_lat, start_lng, start_name = geocode_location(start_location)
            
            if start_status != 200 or start_lat is None:
                print(f"Could not geocode starting location: {start_location}")
                continue
            
            # Get destination
            end_location = input("Destination: ").strip()
            while not end_location:
                end_location = input("Enter destination again: ").strip()
            
            # Geocode destination
            end_status, end_lat, end_lng, end_name = geocode_location(end_location)
            
            if end_status != 200 or end_lat is None:
                print(f"Could not geocode destination: {end_location}")
                continue
            
            # Get directions
            route_status, route_data = get_directions(
                (start_lat, start_lng),
                (end_lat, end_lng),
                vehicle
            )
            
            # Display directions
            if route_status == 200 and route_data:
                display_route(route_data, start_name, end_name, vehicle)
            else:
                error_msg = "Unknown error"
                if route_data and "message" in route_data:
                    error_msg = route_data["message"]
                
                print(f"Directions from {start_name} to {end_name} by {vehicle}")
                print("=================================================")
                print(f"Error message: {error_msg}")
                print("*************************************************")
    
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()