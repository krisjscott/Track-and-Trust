import random

def get_sensor_data():
    return {
        "humidity": random.uniform(20, 80),
        "temperature": random.uniform(25, 40),
        "smoke": random.uniform(0, 10)
    }

def check_alerts(data):
    alerts = []
    if data["humidity"] > 70:
        alerts.append(f"Humidity ALERT! Value: {data['humidity']:.2f} exceeds threshold 70.0")
    if data["temperature"] > 37:
        alerts.append(f"Temperature ALERT! Value: {data['temperature']:.2f} exceeds threshold 37.0")
    if data["smoke"] > 5:
        alerts.append(f"Smoke ALERT! Value: {data['smoke']:.2f} exceeds threshold 5.0")
    return alerts
