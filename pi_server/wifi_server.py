import socket
import picar_4wd as pc4
import json
import time
import qwiic_icm20948
from gpiozero import CPUTemperature
import numpy as np
import os

os.system('ulimit -n 4096') 

HOST = "192.168.86.46" # IP address of your Raspberry PI
PORT = 65432          # Port to listen on (non-privileged ports are > 1023)
speed = 30
distance_traveled = 0
moving = False  # Track if the car is currently moving
start_time = None
scanning = False
scan_step = 0
current_angle = -90

def calibrate_gyro(IMU, num_samples=100):
    """Calibrate the gyroscope by averaging raw readings over a specified number of samples."""
    gx_sum, gy_sum, gz_sum = 0, 0, 0
    
    print("Calibrating gyroscope... Please keep the sensor still.")
    for _ in range(num_samples):
        if IMU.dataReady():
            IMU.getAgmt()
            gx_sum += IMU.gxRaw
            gy_sum += IMU.gyRaw
            gz_sum += IMU.gzRaw
        time.sleep(0.01)  # Short sleep to avoid flooding

    # Calculate the average offsets
    gx_offset = gx_sum / num_samples
    gy_offset = gy_sum / num_samples
    gz_offset = gz_sum / num_samples
    
    print(f"Gyro Offsets: gx_offset={gx_offset}, gy_offset={gy_offset}, gz_offset={gz_offset}")
    return gx_offset, gy_offset, gz_offset

IMU = qwiic_icm20948.QwiicIcm20948()
IMU.begin()

# Calibrate the gyroscope
# gx_offset, gy_offset, gz_offset = calibrate_gyro(IMU, 10)
gx_offset, gy_offset, gz_offset = calibrate_gyro(IMU, 1000)

# Initialize angle
angle = 0.0
last_time = time.time()
cpu = CPUTemperature()

def update_distance_traveled(speed, start_time):
    global distance_traveled
    elapsed_time = time.time() - start_time
    distance_traveled += (speed / 4.2) * elapsed_time  # Convert speed to m/s and update distance
    return time.time()  # Return current time as new start_time
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    try:
        while 1:
            client, clientInfo = s.accept()
            data = client.recv(1024)
            if data != b"":
                print(data)
                if (data == b"up" or data == b"down"):
                    if not moving:
                        moving = True
                        start_time = time.time()  # Start timing movement
                if (data == b"up"):
                    pc4.forward(speed)
                elif (data == b"down"):
                    pc4.backward(speed)
                elif (data == b"left"):
                    pc4.turn_left(speed)
                elif (data == b"right"):
                    pc4.turn_right(speed)
                elif (data == b"stop"):
                    if moving and start_time:  # Update distance before stopping
                        start_time = update_distance_traveled(speed, start_time)
                        moving = False
                    pc4.stop()
                elif (data.startswith(b"speed:")):
                    speed_str = data.replace(b"speed:", b"")
                    data = speed_str
                    speed = int(speed_str)
                if moving:  # Continuously update the distance if the car is moving
                    start_time = update_distance_traveled(speed, start_time)
                if IMU.dataReady():
                    IMU.getAgmt()
                    gz = IMU.gzRaw - gz_offset
                    # Calculate the elapsed time
                    current_time = time.time()
                    dt = current_time - last_time
                    last_time = current_time
                    # Integrate the gyroscope reading to get the angle (in degrees)
                    angle += gz * dt * (1 / 131)  # Convert raw gyro reading to degrees (assuming 131 LSB/deg/s for ±250°/s)
                if (data == b"scan"):
                    scanning = True
                x = -1
                y = -1
                obstacle = 0
                if scanning:
                    us_step = 2
                    if scan_step < 90:
                        distance = pc4.get_distance_at(current_angle)
                        if distance > 0:
                            x = int(distance * np.cos(np.radians(current_angle + 90))) + 49
                            y = int(distance * np.sin(np.radians(current_angle + 90)))
                            if 0 <= x < 100 and 0 <= y < 100:  
                                obstacle = 1
                        current_angle += us_step
                        scan_step += 1
                    else:
                        current_angle = -90
                        scanning = False
                        scan_step = 0
                client.sendall(str.encode(json.dumps({
                    'data': data.decode("utf-8"),
                    'speed': speed/4.2 if moving else 0,
                    'distanceTraveled': distance_traveled,
                    'cpuTemp': cpu.temperature,
                    'angle': angle,
                    'x': x,
                    'y': y,
                    'obstacle' : obstacle,
                    'scanning' : scanning,
                    'scan_step': scan_step,
                    'current_angle': current_angle,
                    'battery' : pc4.power_read()
                }))) # Echo back to client
    except (KeyboardInterrupt, Exception) as e:
        print(e)
        print("Closing socket")
        client.close()
        s.close()    