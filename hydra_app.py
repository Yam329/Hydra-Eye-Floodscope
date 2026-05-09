import tkinter as tk
from tkinter import messagebox, ttk
import speech_recognition as sr
import requests
import folium
import webbrowser
import re
from math import sqrt
import random
import os
import threading

# Global variable for recognized speech
stored_text = ""

# --- Tkinter GUI Functions ---
def create_gui():
    """Initialize and run the Tkinter GUI for Hydra with enhanced UI."""
    def recognize_speech():
        """Capture and recognize speech from the microphone."""
        global stored_text
        r = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                update_status("Listening... Speak now.", "#3498db")
                audio = r.listen(source, timeout=5)
                recognized_text = r.recognize_google(audio)
                update_text_box(recognized_text)
                update_status("Speech recognized!", "#2ecc71")
                stored_text = recognized_text
                print(f"Speech recognized: {recognized_text}")
        except sr.UnknownValueError:
            update_status("Could not understand audio.", "#e74c3c")
            stored_text = ""
        except sr.RequestError as e:
            update_status(f"Speech service error: {e}", "#e74c3c")
            stored_text = ""
        except sr.WaitTimeoutError:
            update_status("Listening timed out.", "#e74c3c")
            stored_text = ""
        except Exception as e:
            update_status(f"Error: {e}", "#e74c3c")
            stored_text = ""

    def update_text_box(text):
        """Update the recognized text box."""
        audio_text.config(state=tk.NORMAL)
        audio_text.delete(1.0, tk.END)
        audio_text.insert(tk.END, text)
        audio_text.config(state=tk.DISABLED)

    def update_status(text, color):
        """Update the status bar with colored text."""
        status_label.config(text=text, foreground=color)

    def update_summary(buildings, waterbodies, trees, dry_lands):
        """Update the summary text box with fetch results."""
        summary_text.config(state=tk.NORMAL)
        summary_text.delete(1.0, tk.END)
        summary_text.insert(tk.END, f"Summary:\n- Buildings: {len(buildings)}\n- Waterbodies: {len(waterbodies)}\n- Trees/Woods: {len(trees)}\n- Historical Dry Lands: {len(dry_lands)}")
        summary_text.config(state=tk.DISABLED)

    def reset_input():
        """Reset all input fields and stored text."""
        global stored_text
        text_entry.delete(0, tk.END)
        update_text_box("")
        update_summary([], [], [], [])
        update_status("Reset complete. Ready for input.", "#2ecc71")
        stored_text = ""
        progress_bar.stop()
        progress_bar["value"] = 0
        generate_button.config(state=tk.NORMAL)
        print("Input reset.")

    def set_progress(value):
        """Helper function to set progress bar value."""
        progress_bar["value"] = value

    def run_map():
        """Process input and generate map in a separate thread."""
        global stored_text
        text_to_process = stored_text or text_entry.get().strip()
        if not text_to_process:
            messagebox.showwarning("Input Error", "Please provide a location and radius.")
            return
        
        radius_match = re.search(r"radius\s*(\d+\.?\d*)\s*(m|km)", text_to_process.lower())
        if not radius_match:
            messagebox.showwarning("Input Error", "Please specify a radius (e.g., 'radius 1km' or 'radius 500m').")
            return

        generate_button.config(state=tk.DISABLED)
        progress_bar.start(10)
        update_status("Generating map...", "#3498db")

        def process_map():
            try:
                location, radius, features = parse_input(text_to_process)
                lat, lon = geocode_location(location)
                if lat is None or lon is None:
                    root.after(0, lambda: messagebox.showerror("Geocoding Error", f"Could not locate '{location}'."))
                    root.after(0, reset_input)
                else:
                    buildings = fetch_buildings(lat, lon, radius) if "buildings" in features else []
                    waterbodies = fetch_waterbodies(lat, lon, radius, location) if "waterbodies" in features else []
                    trees = fetch_trees(lat, lon, radius) if "trees" in features else []
                    dry_lands = get_historical_dry_lands(lat, lon, radius, waterbodies) if "waterbodies" in features else []

                    generate_map(lat, lon, radius, features, buildings, waterbodies, trees, dry_lands, location)
                    root.after(0, lambda: messagebox.showinfo("Success", f"Map for {location} generated!"))
                    root.after(0, lambda: update_status(f"Map ready for {location}.", "#2ecc71"))
                    root.after(0, lambda: update_summary(buildings, waterbodies, trees, dry_lands))
                    root.after(0, lambda: set_progress(100))
                    root.after(0, lambda: generate_button.config(state=tk.NORMAL))
                    root.after(0, lambda: progress_bar.stop())
            except ValueError as e:
                root.after(0, lambda: messagebox.showerror("Error", str(e)))
                root.after(0, reset_input)

        threading.Thread(target=process_map, daemon=True).start()

    def toggle_help():
        """Toggle the visibility of the help section."""
        if help_frame.winfo_viewable():
            help_frame.pack_forget()
            help_button.config(text="ℹ Help")
        else:
            help_frame.pack(fill=tk.X, pady=(0, 10))
            help_button.config(text="✖ Close Help")

    def toggle_theme():
        """Toggle between light and dark mode."""
        if theme_var.get():
            # Dark mode
            root.configure(bg="#2f3542")
            style.configure("TLabel", background="#2f3542", foreground="#dcdde1")
            style.configure("TFrame", background="#2f3542")
            audio_text.config(bg="#353b48", fg="#dcdde1")
            summary_text.config(bg="#353b48", fg="#dcdde1")
            status_frame.config(background="#353b48")
            input_frame.config(background="#353b48")
            output_frame.config(background="#353b48")
            sidebar_frame.config(background="#353b48")
        else:
            # Light mode
            root.configure(bg="#f5f6fa")
            style.configure("TLabel", background="#f5f6fa", foreground="#2f3542")
            style.configure("TFrame", background="#f5f6fa")
            audio_text.config(bg="#ffffff", fg="#2f3542")
            summary_text.config(bg="#ffffff", fg="#2f3542")
            status_frame.config(background="#dcdde1")
            input_frame.config(background="#f5f6fa")
            output_frame.config(background="#f5f6fa")
            sidebar_frame.config(background="#f5f6fa")

    # GUI Setup
    root = tk.Tk()
    root.title("Hydra")
    root.geometry("900x700")
    root.configure(bg="#f5f6fa")
    root.resizable(True, True)

    # Styling
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=8)
    style.configure("TLabel", font=("Segoe UI", 11), background="#f5f6fa", foreground="#2f3542")
    style.configure("TFrame", background="#f5f6fa")
    style.configure("TProgressbar", thickness=20, troughcolor="#dcdde1", background="#4cd137")

    # Main Container
    main_frame = ttk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

    # Sidebar (Left)
    sidebar_frame = ttk.Frame(main_frame, width=220, relief=tk.RAISED, borderwidth=2)
    sidebar_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))

    ttk.Label(sidebar_frame, text="Hydra Options", font=("Segoe UI", 14, "bold")).pack(pady=10)
    ttk.Separator(sidebar_frame, orient="horizontal").pack(fill=tk.X, pady=5)

    theme_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(sidebar_frame, text="🌙 Dark Mode", variable=theme_var, command=toggle_theme).pack(pady=10, padx=10, anchor="w")
    help_button = ttk.Button(sidebar_frame, text="ℹ Help", command=toggle_help, style="Info.TButton")
    help_button.pack(pady=10, padx=10, anchor="w")

    # Content Frame (Right)
    content_frame = ttk.Frame(main_frame)
    content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    # Header
    header_frame = ttk.Frame(content_frame)
    header_frame.pack(fill=tk.X, pady=(0, 20))
    ttk.Label(header_frame, text="Hydra", font=("Segoe UI", 20, "bold")).pack()

    # Input Frame
    input_frame = ttk.Frame(content_frame, relief=tk.GROOVE, borderwidth=2)
    input_frame.pack(fill=tk.X, pady=10)

    ttk.Label(input_frame, text="Enter or speak a location and radius (e.g., 'Durgam Cheruvu radius 500m')").pack(pady=(10, 5))
    global text_entry
    text_entry = ttk.Entry(input_frame, width=65, font=("Segoe UI", 11))
    text_entry.pack(pady=5)
    text_entry.insert(0, "e.g., 'Hyderabad radius 1km'")
    text_entry.config(foreground="grey")
    def on_entry_click(event):
        if text_entry.get() == "e.g., 'Hyderabad radius 1km'":
            text_entry.delete(0, tk.END)
            text_entry.config(foreground="black")
    def on_focusout(event):
        if not text_entry.get():
            text_entry.insert(0, "e.g., 'Hyderabad radius 1km'")
            text_entry.config(foreground="grey")
    text_entry.bind("<FocusIn>", on_entry_click)
    text_entry.bind("<FocusOut>", on_focusout)

    button_frame = ttk.Frame(input_frame)
    button_frame.pack(pady=10)
    ttk.Button(button_frame, text="🎤 Speech", command=recognize_speech, style="Accent.TButton").grid(row=0, column=0, padx=10)
    global generate_button
    generate_button = ttk.Button(button_frame, text="🗺️ Generate", command=run_map, style="Success.TButton")
    generate_button.grid(row=0, column=1, padx=10)
    ttk.Button(button_frame, text="🔄 Reset", command=reset_input, style="Danger.TButton").grid(row=0, column=2, padx=10)

    global progress_bar
    progress_bar = ttk.Progressbar(input_frame, mode="determinate", maximum=100)
    progress_bar.pack(fill=tk.X, pady=10, padx=20)

    # Output Frame
    output_frame = ttk.Frame(content_frame, relief=tk.GROOVE, borderwidth=2)
    output_frame.pack(fill=tk.BOTH, expand=True, pady=10)

    ttk.Label(output_frame, text="Recognized Input:").pack(pady=(5, 0))
    global audio_text
    audio_text = tk.Text(output_frame, height=5, width=70, font=("Segoe UI", 11), bg="#ffffff", relief=tk.FLAT, wrap=tk.WORD, borderwidth=1)
    audio_text.pack(pady=5, padx=5)

    ttk.Label(output_frame, text="Data Summary:").pack(pady=(5, 0))
    global summary_text
    summary_text = tk.Text(output_frame, height=5, width=70, font=("Segoe UI", 11), bg="#ffffff", relief=tk.FLAT, wrap=tk.WORD, borderwidth=1)
    summary_text.pack(pady=5, padx=5)
    update_summary([], [], [], [])  # Initial empty summary

    # Help Frame (Collapsible)
    global help_frame
    help_frame = ttk.Frame(content_frame)
    ttk.Label(help_frame, text="Help: Use format 'location radius X' (e.g., 'Durgam Cheruvu radius 500m').\nSupported features: 'buildings', 'waterbodies', 'trees'.", 
              wraplength=600, font=("Segoe UI", 10, "italic")).pack(pady=5)

    # Status Bar
    status_frame = ttk.Frame(content_frame, relief=tk.SUNKEN, borderwidth=1, style="Status.TFrame")
    status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))
    global status_label
    status_label = ttk.Label(status_frame, text="Welcome to Hydra! Ready for input.", foreground="#2ecc71", font=("Segoe UI", 10))
    status_label.pack(pady=5)

    # Custom Styles
    style.configure("Accent.TButton", background="#3498db", foreground="white")
    style.map("Accent.TButton", background=[("active", "#2980b9")])
    style.configure("Success.TButton", background="#2ecc71", foreground="white")
    style.map("Success.TButton", background=[("active", "#27ae60")])
    style.configure("Danger.TButton", background="#e74c3c", foreground="white")
    style.map("Danger.TButton", background=[("active", "#c0392b")])
    style.configure("Info.TButton", background="#f1c40f", foreground="white")
    style.map("Info.TButton", background=[("active", "#e1b80c")])
    style.configure("Status.TFrame", background="#dcdde1")

    # Run the GUI
    root.mainloop()

# --- Input Parsing ---
def parse_input(text):
    text_lower = text.lower()
    radius_match = re.search(r"radius\s*(\d+\.?\d*)\s*(m|km)", text_lower)
    if not radius_match:
        raise ValueError("Radius not specified in input.")
    radius = float(radius_match.group(1)) * (1000 if radius_match.group(2) == "km" else 1)

    features = []
    if "buildings" in text_lower:
        features.append("buildings")
    if "waterbodies" in text_lower:
        features.append("waterbodies")
    if "trees" in text_lower:
        features.append("trees")
    if not features:
        features = ["buildings", "waterbodies", "trees"]

    location = text_lower
    location = re.sub(r"show me the (buildings|waterbodies|trees)", "", location)
    location = re.sub(r"with\s*radius\s*\d+\.?\d*\s*(m|km).*", "", location)
    location = re.sub(r"within\s*radius\s*\d+\.?\d*\s*(m|km)|radius\s*\d+\.?\d*\s*(m|km)|within", "", location)

    if "near" in location:
        location = location.split("near")[1].strip()
    else:
        location = location.strip()

    location = " ".join(location.split())
    if not location:
        raise ValueError("No valid location found in input.")
    
    print(f"Parsed Location: {location}, Radius (meters): {radius}, Features: {features}")
    return location, radius, features

# --- Geocoding ---
def geocode_location(location):
    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": "Hydra/1.0"}
    
    if "durgam cheruvu" in location.lower() or "durgam ceruvu" in location.lower():
        lat, lon = 17.4308, 78.3897
        print(f"Hardcoded 'Durgam Cheruvu' to Lat: {lat}, Lon: {lon}")
        return lat, lon
    if "nallacheruvu kukatpally" in location.lower() or "nalla cheruvu" in location.lower():
        lat, lon = 17.4875, 78.4185
        print(f"Hardcoded 'Nallacheruvu, Kukatpally' to Lat: {lat}, Lon: {lon}")
        return lat, lon

    location_attempts = [
        location,
        f"{location}, Kukatpally, Hyderabad",
        f"{location}, Hyderabad",
        f"{location}, Telangana",
        f"{location}, India",
        location.split()[-1]
    ]

    for attempt in location_attempts:
        params = {"q": attempt, "format": "json", "limit": 1}
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200 and response.json():
                data = response.json()[0]
                lat, lon = float(data["lat"]), float(data["lon"])
                print(f"Geocoded '{attempt}' to Lat: {lat}, Lon: {lon}")
                return lat, lon
        except requests.RequestException as e:
            print(f"Geocoding request failed for '{attempt}': {e}")
    
    print(f"Could not geocode '{location}' or any fallback.")
    return None, None

# --- Overpass API Queries ---
def fetch_waterbodies(lat, lon, radius, location):
    url = "https://overpass-api.de/api/interpreter"
    query = f"""
[out:json];
(
  way(around:{radius},{lat},{lon})["natural"~"water|lake"];
);
out geom;
    """
    try:
        print(f"Fetching waterbodies with query:\n{query}")
        response = requests.post(url, data=query, headers={"User-Agent": "Hydra/1.0"}, timeout=20)
        if response.status_code == 200:
            elements = response.json().get("elements", [])
            valid_waterbodies = [
                elem for elem in elements 
                if elem.get("type") == "way" 
                and "geometry" in elem 
                and isinstance(elem["geometry"], list) 
                and len(elem["geometry"]) > 0
                and all("lat" in node and "lon" in node for node in elem["geometry"])
            ]
            print(f"Total waterbodies fetched: {len(elements)}, Valid with geometry: {len(valid_waterbodies)}")
            return valid_waterbodies
        else:
            print(f"API error: Status code {response.status_code}")
            return []
    except requests.RequestException as e:
        print(f"Error fetching waterbodies: {e}")
        return []

def fetch_buildings(lat, lon, radius):
    url = "http://overpass-api.de/api/interpreter"
    query = f"""
[out:json];
(
  way(around:{radius},{lat},{lon})["building"];
  >;
);
out geom;
    """
    try:
        response = requests.post(url, data=query, headers={"User-Agent": "Hydra/1.0"}, timeout=20)
        if response.status_code == 200 and response.json().get("elements"):
            print(f"Found {len(response.json()['elements'])} buildings.")
            return response.json()["elements"]
        print("No buildings found.")
        return []
    except requests.RequestException as e:
        print(f"Error fetching buildings: {e}")
        return []

def fetch_trees(lat, lon, radius):
    url = "http://overpass-api.de/api/interpreter"
    query = f"""
[out:json];
(
  node(around:{radius},{lat},{lon})["natural"="tree"];
  way(around:{radius},{lat},{lon})["natural"~"wood|forest"];
  >;
);
out center;
    """
    try:
        response = requests.post(url, data=query, headers={"User-Agent": "Hydra/1.0"}, timeout=20)
        if response.status_code == 200 and response.json().get("elements"):
            print(f"Found {len(response.json()['elements'])} tree/wood features.")
            return response.json()["elements"]
        print("No trees found.")
        return []
    except requests.RequestException as e:
        print(f"Error fetching trees: {e}")
        return []

# --- Historical Dry Lands Simulation ---
def get_historical_dry_lands(lat, lon, radius, waterbodies):
    dry_lands = []
    if not lat or not lon:
        return dry_lands

    base_dry_count = min(len(waterbodies) + 1, 3)
    num_dry_lands = random.randint(0, base_dry_count)

    for _ in range(num_dry_lands):
        attempts = 0
        while attempts < 10:
            lat_offset = random.uniform(-2 * radius / 111320, 2 * radius / 111320)
            lon_offset = random.uniform(-2 * radius / (111320 * abs(lat)), 2 * radius / (111320 * abs(lat)))
            dry_lat = lat + lat_offset
            dry_lon = lon + lon_offset
            dist = sqrt((lat - dry_lat)**2 + (lon - dry_lon)**2) * 111320

            outside_water = True
            for wb in waterbodies:
                if "geometry" in wb:
                    coords = [(node["lat"], node["lon"]) for node in wb["geometry"]]
                    min_lat = min(c[0] for c in coords)
                    max_lat = max(c[0] for c in coords)
                    min_lon = min(c[1] for c in coords)
                    max_lon = max(c[1] for c in coords)
                    if min_lat <= dry_lat <= max_lat and min_lon <= dry_lon <= max_lon:
                        outside_water = False
                        break
            
            if dist <= radius and outside_water:
                dry_lands.append({
                    "coords": (dry_lat, dry_lon),
                    "note": f"Historical dry land (simulated, ~{random.randint(1800, 2020)})"
                })
                print(f"Simulated dry land at ({dry_lat}, {dry_lon})")
                break
            attempts += 1
    
    return dry_lands

# --- Expand Geometry for FTL and Buffer Zone ---
def expand_geometry(coords, distance_meters):
    expanded_coords = []
    distance_degrees = distance_meters / 111320
    for lat, lon in coords:
        expanded_coords.append((lat - distance_degrees, lon - distance_degrees))
        expanded_coords.append((lat + distance_degrees, lon + distance_degrees))
        expanded_coords.append((lat - distance_degrees, lon + distance_degrees))
        expanded_coords.append((lat + distance_degrees, lon - distance_degrees))
    min_lat = min(c[0] for c in expanded_coords)
    max_lat = max(c[0] for c in expanded_coords)
    min_lon = min(c[1] for c in expanded_coords)
    max_lon = max(c[1] for c in expanded_coords)
    return [
        (min_lat, min_lon), (min_lat, max_lon),
        (max_lat, max_lon), (max_lat, min_lon),
        (min_lat, min_lon)
    ]

# --- Map Generation ---
def generate_map(lat, lon, radius, features, buildings, waterbodies, trees, dry_lands, location):
    m = folium.Map(location=[lat, lon], zoom_start=15)

    folium.Marker(
        location=[lat, lon],
        popup=f"Center: {location}",
        icon=folium.Icon(color="red")
    ).add_to(m)

    folium.Circle(
        radius=radius,
        location=[lat, lon],
        color="black",
        fill=False,
        weight=2,
        tooltip=f"Radius: {radius}m"
    ).add_to(m)

    overlaps = []

    if "waterbodies" in features:
        for waterbody in waterbodies:
            if "geometry" in waterbody and isinstance(waterbody["geometry"], list) and len(waterbody["geometry"]) > 0:
                coords = [(node["lat"], node["lon"]) for node in waterbody["geometry"]]
                tooltip = waterbody.get("tags", {}).get("name", "Waterbody")
                
                folium.Polygon(
                    locations=coords,
                    color="blue",
                    fill=True,
                    fill_opacity=0.6,
                    weight=3,
                    tooltip=f"{tooltip} (Current)"
                ).add_to(m)

                ftl_coords = expand_geometry(coords, 10)
                folium.Polygon(
                    locations=ftl_coords,
                    color="lightblue",
                    fill=True,
                    fill_opacity=0.3,
                    weight=2,
                    tooltip=f"{tooltip} (Full Tank Level - Simulated)"
                ).add_to(m)

                buffer_coords = expand_geometry(coords, 30)
                folium.Polygon(
                    locations=buffer_coords,
                    color="yellow",
                    fill=True,
                    fill_opacity=0.2,
                    weight=2,
                    tooltip=f"{tooltip} (Buffer Zone - 30m, No Construction)"
                ).add_to(m)

        for dry_land in dry_lands:
            folium.Marker(
                location=dry_land["coords"],
                popup=f"Potential Dried River/Waterbody: {dry_land['note']} - Risk of Flooding",
                icon=folium.Icon(color="orange", icon="exclamation-triangle")
            ).add_to(m)

    if "buildings" in features:
        for building in buildings:
            if "geometry" in building:
                coords = [(node["lat"], node["lon"]) for node in building["geometry"]]
                overlap = False
                for wb in waterbodies + dry_lands:
                    if "geometry" in wb:
                        wb_coords = [(node["lat"], node["lon"]) for node in wb["geometry"]]
                        wb_min_lat = min(c[0] for c in wb_coords)
                        wb_max_lat = max(c[0] for c in wb_coords)
                        wb_min_lon = min(c[1] for c in wb_coords)
                        wb_max_lon = max(c[1] for c in wb_coords)
                        bldg_min_lat = min(c[0] for c in coords)
                        bldg_max_lat = max(c[0] for c in coords)
                        bldg_min_lon = min(c[1] for c in coords)
                        bldg_max_lon = max(c[1] for c in coords)
                        if (bldg_min_lat <= wb_max_lat and bldg_max_lat >= wb_min_lat and 
                            bldg_min_lon <= wb_max_lon and bldg_max_lon >= wb_min_lon):
                            overlap = True
                            break
                color = "purple" if overlap else "red"
                tooltip = "Building - Risky (Near Water/Dry Land)" if overlap else "Building"
                folium.Polygon(
                    locations=coords,
                    color=color,
                    fill=True,
                    fill_opacity=0.5,
                    weight=3,
                    tooltip=tooltip
                ).add_to(m)
                if overlap:
                    overlaps.append(coords)

    if "trees" in features:
        for tree in trees:
            if "lat" in tree:
                coords = [tree["lat"], tree["lon"]]
            elif "center" in tree:
                coords = [tree["center"]["lat"], tree["center"]["lon"]]
            else:
                continue
            folium.CircleMarker(
                location=coords,
                radius=5,
                color="green",
                fill=True,
                fill_opacity=0.7,
                tooltip="Tree/Wood"
            ).add_to(m)

    if overlaps:
        folium.Marker(
            location=[lat, lon],
            popup=f"WARNING: {len(overlaps)} building(s) overlap with waterbodies or dry lands - High Risk!",
            icon=folium.Icon(color="black", icon="info-sign")
        ).add_to(m)

    map_path = os.path.abspath("flood_risk_map.html")
    m.save(map_path)
    if os.path.exists(map_path):
        print(f"Map saved to {map_path}")
        webbrowser.open(map_path)
    else:
        print("Error: Map file was not saved.")

# --- Main Execution ---
if __name__ == "__main__":
    print("Starting Hydra...")
    create_gui()