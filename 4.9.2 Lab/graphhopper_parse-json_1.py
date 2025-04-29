import requests
import urllib.parse
import json
import sys
import time
import os
from datetime import timedelta
import re
import textwrap
import base64

# API configuration
GRAPHHOPPER_API_KEY = "cd1bb4ac-2bdb-4437-8d21-8ab1ea18b06c"
GEOCODE_URL = "https://graphhopper.com/api/1/geocode?"
ROUTE_URL = "https://graphhopper.com/api/1/route?"

# LLM API Keys (Replace with your actual keys)
HUGGINGFACE_API_KEY = "hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
GOOGLE_API_KEY = "AIza-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Create data directory if it doesn't exist
os.makedirs("data", exist_ok=True)

# LLM selection
DEFAULT_LLM = "ollama"  # alternatives: "huggingface", "gemini"

def display_separator(char="=", length=70):
    """Display a separator line with specified character and length."""
    print(char * length)

def display_header(message, char="+", length=70):
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

def call_ollama_api(prompt, model="llama3.2"):
    """
    Call the Ollama API (local) with a prompt.
    
    Args:
        prompt (str): The prompt to send to the model
        model (str): The model to use (llama3.2, mistral, phi, etc.)
        
    Returns:
        str: The response from the model or error message
    """
    url = "http://localhost:11434/api/generate"
    
    data = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            return response.json().get("response", "No response generated")
        else:
            return f"Error {response.status_code}: {response.text}"
    except Exception as e:
        return f"Ollama API call failed: {e}. Make sure Ollama is running locally with 'ollama serve'"

def call_huggingface_api(prompt, model="mistralai/Mistral-7B-Instruct-v0.2"):
    """
    Call the Hugging Face Inference API with a prompt.
    
    Args:
        prompt (str): The prompt to send to the model
        model (str): The model to use
        
    Returns:
        str: The response from the model or error message
    """
    api_url = f"https://api-inference.huggingface.co/models/{model}"
    
    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 512,
            "temperature": 0.7,
            "return_full_text": False
        }
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0].get("generated_text", "No text generated")
            return str(result)
        else:
            return f"Error {response.status_code}: {response.text}"
    except Exception as e:
        return f"Hugging Face API call failed: {e}"

def call_google_gemini_api(prompt, model="gemini-1.0-pro"):
    """
    Call the Google Gemini API with a prompt.
    
    Args:
        prompt (str): The prompt to send to Gemini
        model (str): The Gemini model to use
        
    Returns:
        str: The response from Gemini or error message
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    params = {
        "key": GOOGLE_API_KEY
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, params=params)
        if response.status_code == 200:
            result = response.json()
            if "candidates" in result and len(result["candidates"]) > 0:
                parts = result["candidates"][0]["content"]["parts"]
                return parts[0]["text"] if parts else "No text generated"
            return "No valid response from Gemini"
        else:
            return f"Error {response.status_code}: {response.text}"
    except Exception as e:
        return f"Google Gemini API call failed: {e}"

def call_lm_api(prompt, provider=DEFAULT_LLM):
    """
    Generic function to call different LLM APIs based on the provider.
    
    Args:
        prompt (str): The prompt to send to the LLM
        provider (str): The LLM provider to use
        
    Returns:
        str: The response from the LLM or error message
    """
    providers = {
        "ollama": {"func": call_ollama_api, "model": "llama2"},
        "huggingface": {"func": call_huggingface_api, "model": "mistralai/Mistral-7B-Instruct-v0.2"},
        "gemini": {"func": call_google_gemini_api, "model": "gemini-1.0-pro"}
    }
    
    if provider not in providers:
        print(f"Warning: Unknown provider '{provider}'. Using default: {DEFAULT_LLM}")
        provider = DEFAULT_LLM
    
    provider_info = providers[provider]
    return provider_info["func"](prompt, provider_info["model"])

def parse_natural_language_query(query, provider=DEFAULT_LLM):
    """
    Use an LLM to parse a natural language query into structured location data.
    
    Args:
        query (str): Natural language query about directions
        provider (str): The LLM provider to use
        
    Returns:
        dict: Structured data with start_location, end_location, and vehicle_preference
    """
    prompt = f"""
    Parse the following direction query into structured data:
    
    "{query}"
    
    Please identify:
    1. Starting location
    2. Destination
    3. Preferred mode of transport (car, bike, foot, or none specified)
    
    Return ONLY a JSON object with these three fields:
    {{
        "start_location": "extracted starting location",
        "end_location": "extracted destination",
        "vehicle_preference": "extracted transport mode or 'not specified'"
    }}
    """
    
    response = call_lm_api(prompt, provider)
    
    try:
        # Clean up response to extract only the JSON part
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            parsed_json = json.loads(json_match.group(0))
            return parsed_json
        else:
            return {
                "start_location": "",
                "end_location": "",
                "vehicle_preference": "not specified"
            }
    except Exception as e:
        print(f"Error parsing LLM response: {e}")
        return {
            "start_location": "",
            "end_location": "",
            "vehicle_preference": "not specified"
        }

def generate_route_summary(route_data, start_name, end_name, vehicle, provider=DEFAULT_LLM):
    """
    Use an LLM to generate a natural language summary of the route.
    
    Args:
        route_data (dict): Route data from GraphHopper API
        start_name (str): Name of starting location
        end_name (str): Name of destination
        vehicle (str): Vehicle profile used
        provider (str): The LLM provider to use
        
    Returns:
        str: Natural language summary of the route
    """
    if not route_data or "paths" not in route_data or not route_data["paths"]:
        return "I couldn't find a route between these locations."
    
    path = route_data["paths"][0]
    
    # Extract key information
    distance = path.get("distance", 0)  # in meters
    time_value = path.get("time", 0)    # in milliseconds
    time_seconds = time_value / 1000
    
    # Get major instructions (limit to avoid token issues)
    instructions = []
    if "instructions" in path:
        for i, instruction in enumerate(path["instructions"]):
            if i < 10:  # Only include first 10 instructions to keep prompt size reasonable
                instructions.append(instruction.get("text", "Continue"))
    
    # Create prompt for LLM
    prompt = f"""
    Create a natural, conversational summary of this route:
    
    From: {start_name}
    To: {end_name}
    Mode: {vehicle}
    Distance: {format_distance(distance)}
    Duration: {format_time(time_seconds)}
    
    Key directions:
    - {" ".join(instructions[:3])}
    
    Include:
    1. A friendly introduction
    2. Any notable aspects of the journey (distance, duration)
    3. Brief mention of major roads or landmarks if apparent
    4. A couple of tips for the traveler based on the mode of transport
    
    Keep it concise (max 150 words) and conversational, as if you're a helpful local.
    """
    
    summary = call_lm_api(prompt, provider)
    return summary

def suggest_points_of_interest(start_name, end_name, vehicle, route_data, provider=DEFAULT_LLM):
    """
    Use an LLM to suggest points of interest along the route.
    
    Args:
        start_name (str): Name of starting location
        end_name (str): Name of destination
        vehicle (str): Vehicle profile used
        route_data (dict): Route data from GraphHopper API
        provider (str): The LLM provider to use
        
    Returns:
        str: Suggestions for points of interest
    """
    if not route_data or "paths" not in route_data:
        return "I couldn't generate points of interest suggestions without a valid route."
    
    path = route_data["paths"][0]
    distance = path.get("distance", 0)  # in meters
    
    prompt = f"""
    Suggest 3-5 interesting places or attractions that might be worth visiting along or near a route:
    
    From: {start_name}
    To: {end_name}
    Mode of transport: {vehicle}
    Total distance: {format_distance(distance)}
    
    Please provide realistic suggestions based on the locations mentioned. 
    For each suggestion, include:
    1. Name of the place
    2. A brief one-sentence description
    3. Why it might be worth stopping there
    
    Format as a bulleted list. Be conversational and helpful.
    If the locations are very generic or you don't have specific knowledge about attractions between them,
    provide general categories of places that travelers might find interesting along such a route.
    """
    
    poi_suggestions = call_lm_api(prompt, provider)
    return poi_suggestions

def answer_travel_question(question, start_name, end_name, vehicle, route_data, provider=DEFAULT_LLM):
    """
    Use an LLM to answer a specific question about the trip.
    
    Args:
        question (str): User's question about the trip
        start_name (str): Name of starting location
        end_name (str): Name of destination
        vehicle (str): Vehicle profile used
        route_data (dict): Route data from GraphHopper API
        provider (str): The LLM provider to use
        
    Returns:
        str: Answer to the question
    """
    if not route_data or "paths" not in route_data:
        return "I need a valid route to answer questions about your trip."
    
    path = route_data["paths"][0]
    distance = path.get("distance", 0)  # in meters
    time_value = path.get("time", 0)    # in milliseconds
    time_seconds = time_value / 1000
    
    prompt = f"""
    Answer the following question about a trip:
    
    Question: "{question}"
    
    Trip details:
    - From: {start_name}
    - To: {end_name}
    - Mode of transport: {vehicle}
    - Distance: {format_distance(distance)}
    - Duration: {format_time(time_seconds)}
    
    Answer the question directly and conversationally, as if you're a helpful travel assistant.
    Keep your answer concise and focused on the question asked.
    """
    
    answer = call_lm_api(prompt, provider)
    return answer

def geocode_location(location, key=GRAPHHOPPER_API_KEY):
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

def get_directions(start_loc, end_loc, vehicle="car", key=GRAPHHOPPER_API_KEY):
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

def get_available_llm_providers():
    """Return a list of available LLM providers."""
    return ["ollama", "huggingface", "gemini"]

def show_llm_features_menu():
    """Display available LLM-enhanced features."""
    print("\nLLM Features:")
    print("1. Natural language route query")
    print("2. Get route summary")
    print("3. Suggest points of interest")
    print("4. Ask a question about your trip")
    print("5. Change LLM provider")
    print("6. Return to main menu")
    
    choice = input("\nSelect an option (1-6): ").strip()
    return choice

def print_wrapped_text(text, width=70):
    """Print text with word wrapping for better readability."""
    wrapped_text = textwrap.fill(text, width=width)
    print(wrapped_text)
    print()

def main():
    """Main function to run the application."""
    current_route_data = None
    current_start_name = None
    current_end_name = None
    current_vehicle = None
    current_llm_provider = DEFAULT_LLM
    
    try:
        display_header("GraphHopper Navigation Assistant with LLM Integration", "=")
        print("Welcome to the enhanced navigation system! This application combines")
        print("GraphHopper's routing capabilities with LLM natural language processing.")
        print("You can get directions, summaries, points of interest, and more.")
        print(f"\nCurrent LLM provider: {current_llm_provider}")
        
        while True:
            print("\nMain Menu:")
            print("1. Plan a route")
            print("2. LLM-enhanced features" + (" (route required first)" if not current_route_data else ""))
            print("3. Exit")
            
            choice = input("\nSelect an option (1-3): ").strip()
            
            if choice == "1":
                # Plan a route - similar to original functionality
                # Display available vehicle profiles
                profiles = get_available_profiles()
                display_header("Vehicle profiles available on Graphhopper:", "+")
                print(", ".join(profiles))
                display_header("", "+")
                
                # Get vehicle profile
                vehicle = input("Enter a vehicle profile from the list above: ").strip().lower()
                
                if vehicle == "q":
                    print("Returning to main menu.")
                    continue
                
                if vehicle not in profiles:
                    print(f"No valid vehicle profile was entered. Using the car profile.")
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
                    # Store the current route data for LLM features
                    current_route_data = route_data
                    current_start_name = start_name
                    current_end_name = end_name
                    current_vehicle = vehicle
                else:
                    error_msg = "Unknown error"
                    if route_data and "message" in route_data:
                        error_msg = route_data["message"]
                    
                    print(f"Directions from {start_name} to {end_name} by {vehicle}")
                    print("=================================================")
                    print(f"Error message: {error_msg}")
                    print("*************************************************")
            
            elif choice == "2":
                # LLM-enhanced features
                if not current_route_data:
                    print("Please plan a route first before using LLM features.")
                    continue
                
                llm_choice = show_llm_features_menu()
                
                if llm_choice == "1":
                    # Natural language route query
                    query = input("\nDescribe your journey (e.g., 'I want to go from Boston to New York by bike'): ")
                    print(f"\nProcessing your query using {current_llm_provider}...")
                    
                    parsed_query = parse_natural_language_query(query, current_llm_provider)
                    
                    print("\nI understood your query as:")
                    print(f"Starting point: {parsed_query['start_location']}")
                    print(f"Destination: {parsed_query['end_location']}")
                    print(f"Transport mode: {parsed_query['vehicle_preference']}")
                    
                    use_parsed = input("\nWould you like to plan this route? (y/n): ").strip().lower()
                    
                    if use_parsed == 'y':
                        # Set up for a new route with the parsed information
                        start_location = parsed_query['start_location']
                        end_location = parsed_query['end_location']
                        vehicle = parsed_query['vehicle_preference']
                        
                        if vehicle == "not specified" or vehicle not in get_available_profiles():
                            vehicle = "car"
                            print(f"Using default vehicle profile: {vehicle}")
                        
                        # Continue with geocoding and route planning
                        start_status, start_lat, start_lng, start_name = geocode_location(start_location)
                        if start_status != 200 or start_lat is None:
                            print(f"Could not geocode starting location: {start_location}")
                            continue
                        
                        end_status, end_lat, end_lng, end_name = geocode_location(end_location)
                        if end_status != 200 or end_lat is None:
                            print(f"Could not geocode destination: {end_location}")
                            continue
                        
                        route_status, route_data = get_directions(
                            (start_lat, start_lng),
                            (end_lat, end_lng),
                            vehicle
                        )
                        
                        if route_status == 200 and route_data:
                            display_route(route_data, start_name, end_name, vehicle)
                            # Update current route data
                            current_route_data = route_data
                            current_start_name = start_name
                            current_end_name = end_name
                            current_vehicle = vehicle
                        else:
                            error_msg = "Unknown error"
                            if route_data and "message" in route_data:
                                error_msg = route_data["message"]
                            
                            print(f"Directions from {start_name} to {end_name} by {vehicle}")
                            print("=================================================")
                            print(f"Error message: {error_msg}")
                            print("*************************************************")
                
                elif llm_choice == "2":
                    # Get route summary
                    print(f"\nGenerating a conversational summary of your route using {current_llm_provider}...")
                    summary = generate_route_summary(
                        current_route_data,
                        current_start_name,
                        current_end_name,
                        current_vehicle,
                        current_llm_provider
                    )
                    display_header("Route Summary", "~")
                    print_wrapped_text(summary)
                
                elif llm_choice == "3":
                    # Suggest points of interest
                    print(f"\nFinding interesting places along your route using {current_llm_provider}...")
                    poi_suggestions = suggest_points_of_interest(
                        current_start_name,
                        current_end_name,
                        current_vehicle,
                        current_route_data,
                        current_llm_provider
                    )
                    display_header("Points of Interest", "~")
                    print_wrapped_text(poi_suggestions)
                
                elif llm_choice == "4":
                    # Ask a question about your trip
                    question = input("\nWhat would you like to know about your trip?: ")
                    print(f"\nThinking about your question using {current_llm_provider}...")
                    
                    answer = answer_travel_question(
                        question,
                        current_start_name,
                        current_end_name,
                        current_vehicle,
                        current_route_data,
                        current_llm_provider
                    )
                    
                    display_header("Answer", "~")
                    print_wrapped_text(answer)
                
                elif llm_choice == "5":
                    # Change LLM provider
                    providers = get_available_llm_providers()
                    display_header("Available LLM Providers", "+")
                    for i, provider in enumerate(providers, 1):
                        print(f"{i}. {provider}")
                    display_header("", "+")
                    
                    print("Provider Information:")
                    print("- ollama: Free, runs locally (requires installation)")
                    print("- huggingface: Free tier available, good quality")
                    print("- anthropic: Commercial but competitive pricing")
                    print("- gemini: Free tier available from Google")
                    print("- replicate: Pay per run, many model options")
                    
                    try:
                        provider_choice = int(input(f"\nSelect a provider (1-{len(providers)}): ").strip())
                        if 1 <= provider_choice <= len(providers):
                            current_llm_provider = providers[provider_choice-1]
                            print(f"\nSwitched to {current_llm_provider} as LLM provider")
                        else:
                            print(f"Invalid choice. Keeping {current_llm_provider} as provider.")
                    except ValueError:
                        print(f"Invalid input. Keeping {current_llm_provider} as provider.")
                
                elif llm_choice == "6":
                    # Return to main menu
                    continue
                
                else:
                    print("Invalid option. Please try again.")
            
            elif choice == "3":
                print("Thank you for using the GraphHopper Navigation Assistant. Goodbye!")
                break
            
            else:
                print("Invalid option. Please try again.")
    
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()