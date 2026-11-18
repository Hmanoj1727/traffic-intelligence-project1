import streamlit as st
import pandas as pd
import joblib
import os
import numpy as np
from zoneinfo import ZoneInfo
from datetime import datetime, timezone, timedelta
import requests



# Automatic Location and Weather Functions

@st.cache_data(ttl=86400)
def get_coordinates_for_app(area, city, state):

    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": f"{area}, {city}, {state}, India",
        "format": "jsonv2",
        "limit": 1
    }

    headers = {
        "User-Agent": "TrafficPredictionMCAProject/1.0"
    }

    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=15
    )

    response.raise_for_status()
    results = response.json()

    if not results:
        return None

    return {
        "latitude": float(results[0]["lat"]),
        "longitude": float(results[0]["lon"]),
        "display_name": results[0]["display_name"]
    }


@st.cache_data(ttl=1800)
def get_7timer_forecast(latitude, longitude):

    url = "https://www.7timer.info/bin/api.pl"

    params = {
        "lon": longitude,
        "lat": latitude,
        "product": "meteo",
        "output": "json"
    }

    response = requests.get(
        url,
        params=params,
        timeout=15
    )

    response.raise_for_status()

    return response.json()




def get_location_traffic_profile(area, city):

    area_text = area.lower()
    city_text = city.lower()

    # Different simulated location types
    if any(word in area_text for word in [
        "mvp", "colony", "residential", "housing"
    ]):
        profile = "Residential"

    elif any(word in area_text for word in [
        "madhapur", "hitech", "it park", "technology"
    ]):
        profile = "IT / Technology"

    elif any(word in area_text for word in [
        "market", "bazaar", "shopping"
    ]):
        profile = "Market"

    elif any(word in area_text for word in [
        "highway", "expressway", "national highway"
    ]):
        profile = "Highway"

    else:
        profile = "Commercial"

    # Illustrative hourly traffic multipliers
    profiles = {
        "Residential": {
            0: 0.25, 1: 0.18, 2: 0.15, 3: 0.12,
            4: 0.15, 5: 0.30, 6: 0.55, 7: 0.85,
            8: 1.00, 9: 0.80, 10: 0.60, 11: 0.55,
            12: 0.60, 13: 0.55, 14: 0.50, 15: 0.55,
            16: 0.70, 17: 0.90, 18: 1.00, 19: 0.85,
            20: 0.65, 21: 0.50, 22: 0.40, 23: 0.30
        },

        "IT / Technology": {
            0: 0.15, 1: 0.12, 2: 0.10, 3: 0.10,
            4: 0.12, 5: 0.20, 6: 0.40, 7: 0.75,
            8: 1.00, 9: 0.95, 10: 0.75, 11: 0.65,
            12: 0.60, 13: 0.65, 14: 0.70, 15: 0.75,
            16: 0.85, 17: 1.00, 18: 0.95, 19: 0.75,
            20: 0.50, 21: 0.35, 22: 0.25, 23: 0.20
        },

        "Market": {
            0: 0.15, 1: 0.10, 2: 0.08, 3: 0.08,
            4: 0.10, 5: 0.20, 6: 0.35, 7: 0.50,
            8: 0.60, 9: 0.70, 10: 0.85, 11: 0.90,
            12: 0.95, 13: 0.85, 14: 0.80, 15: 0.85,
            16: 0.95, 17: 1.00, 18: 1.00, 19: 0.95,
            20: 0.80, 21: 0.60, 22: 0.35, 23: 0.20
        },

        "Highway": {
            hour: (
                1.05 if hour == 17 else 1.00 if hour in [8, 9, 18]
                else 0.65 if hour in [7, 10, 16, 19]
                else 0.40 if 5 <= hour <= 22
                else 0.20
            )
            for hour in range(24)
        },

        "Commercial": {
            hour: 0.85 if hour in [8, 9, 17, 18, 19]
            else 0.50 if 7 <= hour <= 21
            else 0.20
            for hour in range(24)
        }
    }

    return profile, profiles[profile]


# Page configuration
st.set_page_config(
    page_title="Traffic Intelligence",
    page_icon="🚦",
    layout="wide"
)

# Custom CSS
st.html("""
<style>

/* Main dashboard background */
.stApp {
    background: #0B1220 !important;
    color: #F1F5F9 !important;
}

/* Main content area */
[data-testid="stAppViewContainer"] {
    background: #0B1220 !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #14213A !important;
}

/* Headings and labels */
h1, h2, h3, p, label, span {
    color: #F1F5F9;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: #192A43 !important;
    padding: 18px !important;
    border-radius: 12px !important;
    border: 1px solid #30445F !important;
}

/* Text and number inputs */
div[data-baseweb="input"],
div[data-baseweb="textarea"] {
    background: #1E304A !important;
    border: 1px solid #49617E !important;
    border-radius: 8px !important;
}

div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea {
    color: #FFFFFF !important;
    background: transparent !important;
}

/* Dropdowns */
div[data-baseweb="select"] > div {
    background: #1E304A !important;
    color: #FFFFFF !important;
    border-color: #49617E !important;
}

/* Date and time fields */
[data-testid="stDateInput"] input,
[data-testid="stTimeInput"] input {
    background: #1E304A !important;
    color: #FFFFFF !important;
}

/* File uploader */
[data-testid="stFileUploader"] section {
    background: #192A43 !important;
    border: 1px dashed #6080A5 !important;
    border-radius: 12px !important;
}

/* Buttons */
.stButton > button {
    background: #2563EB !important;
    color: #FFFFFF !important;
    border-radius: 8px !important;
    border: none !important;
    padding: 10px 20px !important;
    font-weight: 600 !important;
}

.stButton > button:hover {
    background: #1D4ED8 !important;
}

/* Forms */
[data-testid="stForm"] {
    background: #14213A !important;
    padding: 20px !important;
    border-radius: 12px !important;
    border: 1px solid #30445F !important;
}

</style>
""")

# Load model from Hugging Face
@st.cache_resource
def load_model():
    from huggingface_hub import hf_hub_download

    model_path = hf_hub_download(
        repo_id="manojHanumanthu/traffic-prediction-random-forest",
        filename="random_forest_traffic_model (1).pkl"
    )
    return joblib.load(model_path)

try:
    model = load_model()
    model_status = "Model loaded successfully"
except Exception as e:
    model = None
    model_status = f"Model loading failed: {e}"

# Sidebar
st.sidebar.title("🚦 Traffic Intelligence")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Traffic Prediction",
        "Traffic Analytics",
        "About Project"
    ]
)

# Dashboard
if page == "Dashboard":

    st.title("🚦 Traffic Intelligence Dashboard")

    st.write(
        "Large-Scale Traffic Data Analytics "
        "for Intelligent Traffic Prediction"
    )

    if model:
        st.success(model_status)
    else:
        st.error(model_status)

    col1, col2, col3 = st.columns(3)

    col1.metric("Historical Records", "48,187")
    col2.metric("Selected ML Model", "Random Forest")
    col3.metric("ML Models Compared", "5")

    st.divider()

    st.subheader("Project Overview")

    st.write("""
    This project uses Machine Learning techniques to
    analyze historical traffic patterns and predict
    traffic volume based on weather, time, and
    historical traffic information.
    """)





# Traffic Prediction

elif page == "Traffic Prediction":

    st.title("🚦 Intelligent Traffic Prediction")
    st.write("Experimental traffic analysis for multiple locations.")

    st.warning(
        "Experimental demonstration: The prediction model was trained "
        "using Minnesota highway data. Results are not verified traffic "
        "predictions for the selected Indian locality or live traffic."
    )

    st.divider()

    st.subheader("📍 Location Details")

    states = [
        "Andhra Pradesh", "Telangana", "Karnataka",
        "Tamil Nadu", "Kerala", "Maharashtra",
        "Delhi", "Gujarat", "Rajasthan", "Uttar Pradesh",
        "Madhya Pradesh", "West Bengal", "Odisha",
        "Bihar", "Punjab", "Haryana", "Goa",
        "Assam", "Jharkhand", "Chhattisgarh"
    ]

    state = st.selectbox("Select State", states)

    col1, col2 = st.columns(2)

    with col1:
        city = st.text_input("Enter City / District")

    with col2:
        area = st.text_input("Enter Area / Locality")

    st.divider()

    DATA_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "historical_traffic_data.csv"
    )

    @st.cache_data
    def load_history():
        df = pd.read_csv(DATA_PATH)
        df["date_time"] = pd.to_datetime(df["date_time"])
        return df.sort_values("date_time").reset_index(drop=True)

    try:
        history = load_history()

        if model is None:
            st.error("Random Forest model is not available.")
            st.stop()

    except Exception as e:
        st.error(f"Could not load historical data: {e}")
        st.stop()

    st.subheader("🌦️ Automatic Weather Information")

    st.info(
        "Weather information will be fetched automatically using "
        "your selected locality. No manual weather entry is required."
    )

    holiday_options = (
        history["holiday"].dropna().astype(str).unique().tolist()
    )

    holiday = st.selectbox(
        "Holiday",
        ["No holiday"] + sorted(holiday_options)
    )

    st.divider()

    st.subheader("Prediction Mode")

    prediction_mode = st.radio(
        "Choose Prediction Mode",
        ["Automatic Traffic Analysis", "Manual Traffic Prediction"],
        horizontal=True
    )

    india_today = datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).date()

    selected_date = st.date_input(
        "Select Prediction Date",
        value=india_today,
        min_value=india_today,
        max_value=india_today + timedelta(days=7)
    )

    if prediction_mode == "Manual Traffic Prediction":
        selected_time = st.time_input(
            "Select Prediction Time",
            value=datetime.now(ZoneInfo("Asia/Kolkata")).time().replace(
                second=0, microsecond=0
            )
        )
    else:
        selected_time = None

    st.divider()

    if st.button("🔍 Analyse Traffic", use_container_width=True):

        if not city.strip() or not area.strip():
            st.warning("Please enter both city and area.")

        else:

            try:
                with st.spinner("Finding location and fetching weather..."):

                    location = get_coordinates_for_app(
                        area.strip(),
                        city.strip(),
                        state
                    )

                    if location is None:
                        st.error(
                            "Location not found. Please check the city "
                            "and area names."
                        )
                        st.stop()

                    forecast = get_7timer_forecast(
                        location["latitude"],
                        location["longitude"]
                    )

                    if not forecast.get("dataseries"):
                        st.error("Weather forecast is unavailable.")
                        st.stop()

                st.success(
                    f"Location found: {area}, {city}, {state}"
                )

                st.caption(location["display_name"])

                # Select the closest available weather forecast
                def get_weather_for_time(timestamp):

                    init_time = datetime.strptime(
                        forecast["init"], "%Y%m%d%H"
                    ).replace(tzinfo=timezone.utc)

                    target_time = timestamp.replace(
                        tzinfo=ZoneInfo("Asia/Kolkata")
                    ).astimezone(timezone.utc)

                    forecast_points = []

                    for item in forecast["dataseries"]:

                        point_time = init_time + timedelta(
                            hours=item["timepoint"]
                        )

                        forecast_points.append(
                            (point_time, item)
                        )

                    first_time = min(x[0] for x in forecast_points)
                    last_time = max(x[0] for x in forecast_points)

                    if target_time < first_time or target_time > last_time:
                        raise ValueError(
                            "The selected date/time is outside the "
                            "available weather forecast period."
                        )

                    nearest_time, item = min(
                        forecast_points,
                        key=lambda x: abs(
                            (x[0] - target_time).total_seconds()
                        )
                    )

                    cloud_map = {
                        1: 3, 2: 12, 3: 25, 4: 38, 5: 50,
                        6: 62, 7: 75, 8: 88, 9: 97
                    }

                    cloud_percent = cloud_map.get(
                        item["cloudcover"], 50
                    )

                    precipitation_type = item.get(
                        "prec_type", "none"
                    )

                    amount = item.get("prec_amount", 0)

                    # Approximate precipitation feature:
                    # 7Timer does not provide exact hourly rainfall.
                    rain_value = 1.0 if precipitation_type == "rain" and amount > 0 else 0.0
                    snow_value = 1.0 if precipitation_type == "snow" and amount > 0 else 0.0

                    if precipitation_type == "rain":
                        main = "Rain"
                        description = (
                            "light rain" if amount <= 2
                            else "moderate rain"
                        )

                    elif precipitation_type == "snow":
                        main = "Snow"
                        description = "snow"

                    elif item.get("lifted_index", 0) <= -6:
                        main = "Thunderstorm"
                        description = "proximity thunderstorm"

                    elif item["cloudcover"] <= 2:
                        main = "Clear"
                        description = "sky is clear"

                    else:
                        main = "Clouds"

                        if item["cloudcover"] <= 3:
                            description = "few clouds"
                        elif item["cloudcover"] <= 5:
                            description = "scattered clouds"
                        else:
                            description = "overcast clouds"

                    # Keep categories compatible with training data.
                    available_weather_main = (
                        history["weather_main"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )

                    if main not in available_weather_main:
                        main = (
                            "Clouds" if "Clouds" in available_weather_main
                            else available_weather_main[0]
                        )

                    description_options = (
                        history["weather_description"]
                        .dropna().astype(str).unique().tolist()
                    )

                    if description not in description_options:
                        description = description_options[0]

                    return {
                        "temperature": float(item["temp2m"]),
                        "clouds": cloud_percent,
                        "rain": rain_value,
                        "snow": snow_value,
                        "weather_main": main,
                        "weather_description": description,
                        "forecast_time": nearest_time
                    }

                recent_values = (
                    history["traffic_volume"]
                    .tail(24).astype(float).tolist()
                )

                previous_traffic = float(
                    history["traffic_volume"].iloc[-1]
                )

                hourly_median = (
                    history.groupby(
                        history["date_time"].dt.hour
                    )["traffic_volume"].median()
                )

                q33 = history["traffic_volume"].quantile(0.33)
                q66 = history["traffic_volume"].quantile(0.66)

                def get_congestion(value):

                    if value <= q33:
                        return "Low"
                    elif value <= q66:
                        return "Moderate"
                    else:
                        return "Heavy"

                selected_holiday = (
                    None if holiday == "No holiday" else holiday
                )

                def predict_for_time(timestamp, previous, recent):

                    weather = get_weather_for_time(timestamp)

                    hour = timestamp.hour

                    lag24 = float(
                        hourly_median.get(
                            hour,
                            history["traffic_volume"].median()
                        )
                    )

                    rolling = float(np.mean(recent[-24:]))

                    input_data = {
                        "holiday": selected_holiday,
                        "temp": weather["temperature"] + 273.15,
                        "rain_1h": weather["rain"],
                        "snow_1h": weather["snow"],
                        "clouds_all": weather["clouds"],
                        "weather_main": weather["weather_main"],
                        "weather_description": weather["weather_description"],
                        "hour": hour,
                        "day": timestamp.day,
                        "month": timestamp.month,
                        "year": timestamp.year,
                        "day_of_week": timestamp.dayofweek,
                        "is_weekend": int(timestamp.dayofweek >= 5),
                        "is_rush_hour": int(
                            hour in [7, 8, 9, 16, 17, 18]
                        ),
                        "traffic_lag_1": previous,
                        "traffic_lag_24": lag24,
                        "rolling_mean_24": rolling
                    }

                    input_df = pd.DataFrame(
                        [input_data],
                        columns=model.feature_names_in_
                    )

                    prediction = float(model.predict(input_df)[0])

                    return max(0, prediction), weather

                
                # Automatic 24-hour prediction
                if prediction_mode == "Automatic Traffic Analysis":

                    results = []

                    # Always start at 12 AM on the selected date
                    start_timestamp = pd.Timestamp(selected_date)

                    for hour in range(24):

                        timestamp = (
                            start_timestamp
                            + pd.Timedelta(hours=hour)
                        )

                        try:
                            weather = get_weather_for_time(timestamp)

                            prediction, weather = predict_for_time(
                                timestamp,
                                previous_traffic,
                                recent_values
                            )

                            temperature = weather["temperature"]
                            weather_name = weather["weather_main"]
                            cloud_coverage = weather["clouds"]

                        except ValueError:
                            # Weather unavailable for this hour
                            weather = None

                            prediction = float(
                                model.predict(
                                    pd.DataFrame([{
                                        "holiday": selected_holiday,
                                        "temp": float(history["temp"].median()),
                                        "rain_1h": 0.0,
                                        "snow_1h": 0.0,
                                        "clouds_all": float(history["clouds_all"].median()),
                                        "weather_main": "Clouds",
                                        "weather_description": "overcast clouds",
                                        "hour": timestamp.hour,
                                        "day": timestamp.day,
                                        "month": timestamp.month,
                                        "year": timestamp.year,
                                        "day_of_week": timestamp.dayofweek,
                                        "is_weekend": int(timestamp.dayofweek >= 5),
                                        "is_rush_hour": int(timestamp.hour in [7, 8, 9, 16, 17, 18]),
                                        "traffic_lag_1": previous_traffic,
                                        "traffic_lag_24": float(hourly_median.get(timestamp.hour, history["traffic_volume"].median())),
                                        "rolling_mean_24": float(np.mean(recent_values[-24:]))
                                    }], columns=model.feature_names_in_)
                                )[0]
                            )

                            temperature = None
                            weather_name = "Weather unavailable"
                            cloud_coverage = None

                        results.append({
                            "Time": timestamp.strftime("%I %p"),
                            "Estimated Traffic Volume": round(max(0, prediction)),
                            "Congestion": get_congestion(prediction),
                            "Temperature (°C)": temperature,
                            "Weather": weather_name,
                            "Cloud Coverage (%)": cloud_coverage
                        })

                        recent_values.append(prediction)
                        previous_traffic = prediction

                    result_df = pd.DataFrame(results)

                    st.subheader("🌦️ Weather for Selected Date")

                    st.write(
                        "Selected date:",
                        selected_date.strftime("%d-%m-%Y")
                    )

                    st.info(
                        "Weather is shown using the closest available "
                        "3-hour forecast. Unavailable hours are marked."
                    )

                    st.subheader("📊 24-Hour Traffic and Weather Analysis")

                    st.dataframe(
                        result_df,
                        use_container_width=True
                    )

                    st.subheader("Hourly Traffic Trend")

                    st.line_chart(
                        result_df.set_index("Time")[
                            "Estimated Traffic Volume"
                        ]
                    )

                    busiest = result_df.loc[
                        result_df["Estimated Traffic Volume"].idxmax()
                    ]

                    quietest = result_df.loc[
                        result_df["Estimated Traffic Volume"].idxmin()
                    ]

                    c1, c2 = st.columns(2)

                    c1.metric("Busiest Hour", busiest["Time"])
                    c2.metric("Least Busy Hour", quietest["Time"])

# Manual date and time prediction
                else:

                    timestamp = pd.Timestamp.combine(
                        selected_date,
                        selected_time
                    )

                    prediction, weather = predict_for_time(
                        timestamp,
                        previous_traffic,
                        recent_values
                    )

                    congestion = get_congestion(prediction)

                    st.subheader("🌦️ Weather Forecast")

                    wc1, wc2, wc3 = st.columns(3)

                    wc1.metric(
                        "Temperature",
                        f"{weather['temperature']} °C"
                    )

                    wc2.metric(
                        "Weather",
                        weather["weather_main"]
                    )

                    wc3.metric(
                        "Cloud Coverage",
                        f"{weather['clouds']}%"
                    )

                    st.subheader("📊 Traffic Prediction Result")

                    c1, c2 = st.columns(2)

                    c1.metric(
                        "Estimated Traffic Volume",
                        f"{round(prediction):,}"
                    )

                    c2.metric(
                        "Congestion Level",
                        congestion
                    )

                    st.write(
                        "Selected Date and Time:",
                        timestamp.strftime("%d-%m-%Y %I:%M %p")
                    )

                    st.caption(
                        "The displayed weather is the closest available "
                        "forecast, not an exact hourly observation."
                    )

            except Exception as e:
                st.error(f"Analysis could not be completed: {e}")

            st.caption(
                "Weather data comes from an approximate forecast. "
                "Rainfall and snowfall features are simplified proxies. "
                "Traffic predictions use historical Minnesota data and "
                "are not verified traffic counts for this Indian locality."
            )

elif page == "Traffic Analytics":

    st.title("Traffic Analytics")

    st.info(
        "Traffic analytics charts will be added in the next step."
    )

# About Project
elif page == "About Project":

    st.title("About the Project")

    st.write("""
    **Project Title:**

    Large-Scale Traffic Data Analytics for
    Intelligent Traffic Prediction

    **Algorithm:** Random Forest Regression

    **Dataset:** UCI Metro Interstate Traffic Volume Dataset

    **Technologies:** Python, Machine Learning, Pandas,
    Scikit-learn and Streamlit
    """)
