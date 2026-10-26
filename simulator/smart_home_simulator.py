import time
import random
import threading
import paho.mqtt.client as mqtt

class SmartHomeSimulator:
    def __init__(self, broker_host="localhost", broker_port=1883):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, "smart_home_simulator")
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.running = False
        self.devices_state = {
            "living_room_light": {"power": False, "brightness": 50},
            "bedroom_light": {"power": False, "brightness": 70},
            "kitchen_light": {"power": False, "brightness": 60},
            "thermostat": {"current_temp": 21.0, "target_temp": 22.0, "heating": False},
            "motion_detector": {"motion": False, "battery": 95},
            "door_sensor": {"open": False, "battery": 88},
            "smart_socket": {"power": False, "consumption": 0}
        }

    def on_connect(self, client, userdata, flags, rc):
        print(f"Підключено до MQTT брокера. Код: {rc}")
        client.subscribe("smarthome/+/set")
        client.subscribe("smarthome/+/+/set")

    def on_message(self, client, userdata, msg):
        topic_parts = msg.topic.split('/')
        device = topic_parts[1]
        command = msg.payload.decode()
        print(f"Команда: {device} -> {command}")
        self.handle_command(device, command)

    def handle_command(self, device, command):
        if device in ["living_room_light", "bedroom_light", "kitchen_light"]:
            if command in ["ON", "OFF"]:
                self.devices_state[device]["power"] = (command == "ON")
                self.publish_device_state(device)
        elif device == "thermostat" and command.replace('.', '').isdigit():
            self.devices_state["thermostat"]["target_temp"] = float(command)
            self.publish_device_state("thermostat")
        elif device == "smart_socket":
            if command in ["ON", "OFF"]:
                self.devices_state[device]["power"] = (command == "ON")
                self.publish_device_state(device)

    def connect(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(self.broker_host, self.broker_port, 60)
        self.client.loop_start()
        self.running = True

    def publish_device_state(self, device):
        state = self.devices_state[device]
        if "light" in device:
            self.client.publish(f"smarthome/{device}/state", "ON" if state["power"] else "OFF")
            if state["power"]:
                self.client.publish(f"smarthome/{device}/brightness", state["brightness"])
        elif device == "thermostat":
            self.client.publish("smarthome/thermostat/current_temp", f"{state['current_temp']:.1f}")
            self.client.publish("smarthome/thermostat/target_temp", f"{state['target_temp']:.1f}")
            self.client.publish("smarthome/thermostat/heating", "ON" if state["heating"] else "OFF")
        elif device == "smart_socket":
            self.client.publish("smarthome/smart_socket/state", "ON" if state["power"] else "OFF")
            if state["power"]:
                self.client.publish("smarthome/smart_socket/power", state["consumption"])

    def lighting_simulator(self):
        while self.running:
            for device in ["living_room_light", "bedroom_light", "kitchen_light"]:
                if self.devices_state[device]["power"]:
                    current = self.devices_state[device]["brightness"]
                    change = random.randint(-5, 5)
                    self.devices_state[device]["brightness"] = max(10, min(100, current + change))
                    self.publish_device_state(device)
            time.sleep(60)

    def climate_simulator(self):
        while self.running:
            current = self.devices_state["thermostat"]["current_temp"]
            target = self.devices_state["thermostat"]["target_temp"]
            if current < target - 0.5:
                self.devices_state["thermostat"]["heating"] = True
                current += random.uniform(0.1, 0.3)
            elif current > target + 0.5:
                self.devices_state["thermostat"]["heating"] = False
                current -= random.uniform(0.1, 0.2)
            else:
                current += random.uniform(-0.1, 0.1)
            self.devices_state["thermostat"]["current_temp"] = current
            self.publish_device_state("thermostat")
            time.sleep(30)

    def sensors_simulator(self):
        while self.running:
            if random.random() < 0.1:
                self.devices_state["motion_detector"]["motion"] = True
                self.client.publish("smarthome/motion_detector/state", "ON")
                print("Виявлено рух!")
                threading.Timer(5.0, self.reset_motion).start()
            if random.random() < 0.05:
                current_state = self.devices_state["door_sensor"]["open"]
                new_state = not current_state
                self.devices_state["door_sensor"]["open"] = new_state
                self.client.publish("smarthome/door_sensor/state", "OPEN" if new_state else "CLOSED")
                print(f"Двері {'відчинено' if new_state else 'зачинено'}")
            if self.devices_state["smart_socket"]["power"]:
                consumption = random.randint(50, 200)
                self.devices_state["smart_socket"]["consumption"] = consumption
                self.client.publish("smarthome/smart_socket/power", consumption)
            time.sleep(10)

    def reset_motion(self):
        self.devices_state["motion_detector"]["motion"] = False
        self.client.publish("smarthome/motion_detector/state", "OFF")

    def start_simulation(self):
        print("Запуск симулятора розумного будинку")
        self.connect()
        for device in self.devices_state:
            self.publish_device_state(device)
        threading.Thread(target=self.lighting_simulator, daemon=True).start()
        threading.Thread(target=self.climate_simulator, daemon=True).start()
        threading.Thread(target=self.sensors_simulator, daemon=True).start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Зупинка симуляторів")
            self.running = False
            self.client.loop_stop()
            self.client.disconnect()

if __name__ == "__main__":
    simulator = SmartHomeSimulator()
    simulator.start_simulation()