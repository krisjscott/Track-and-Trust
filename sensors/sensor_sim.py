# sensors/sensor_sim.py
import random

def get_sensor_data():
    """
    Simulate live sensor data for hazardous chemicals.
    Returns a dictionary with humidity, temperature, and smoke levels.
    """
    return {
        "humidity": round(random.uniform(20, 80), 2),
        "temperature": round(random.uniform(20, 40), 2),
        "smoke": round(random.uniform(0, 10), 2)
    }

def check_alerts(data):
    """
    Check the sensor data and return alerts if any parameter crosses threshold.
    Thresholds:
        - Humidity > 70
        - Temperature > 37
        - Smoke > 5
    """
    alerts = []
    if data["humidity"] > 70:
        alerts.append(f"Humidity ALERT! Value: {data['humidity']:.2f}")
    if data["temperature"] > 37:
        alerts.append(f"Temperature ALERT! Value: {data['temperature']:.2f}")
    if data["smoke"] > 5:
        alerts.append(f"Smoke ALERT! Value: {data['smoke']:.2f}")
    return alerts

# Optional: Standalone test
if __name__ == "__main__":
    data = get_sensor_data()
    print("Sensor Data:", data)
    alerts = check_alerts(data)
    if alerts:
        print("Alerts:")
        for a in alerts:
            print("-", a)
    else:
        print("No alerts")
