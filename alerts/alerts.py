# This module is currently integrated in sensors/sensor_sim.py
# So you can simply import check_alerts from there

# If you want a separate alerts module:

def check_alerts(data, thresholds=None):
    if thresholds is None:
        thresholds = {
            "humidity": 70.0,
            "temperature": 37.0,
            "smoke": 5.0
        }
    alerts = []
    for key, value in data.items():
        if key in thresholds and value > thresholds[key]:
            alerts.append(f"{key.capitalize()} ALERT! Value: {value:.2f} exceeds threshold {thresholds[key]}")
    if alerts:
        print("ALERTS:", alerts)
    return alerts
