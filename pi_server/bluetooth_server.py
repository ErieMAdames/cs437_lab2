from bluedot.btcomm import BluetoothServer
from signal import pause
import picar_4wd as pc4
import json
import time
import qwiic_icm20948
from gpiozero import CPUTemperature
import numpy as np
import os

os.system('ulimit -n 4096') 
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
def data_received(r_data):
    global speed, distance_traveled, moving, start_time, scanning, scan_step, current_angle, gx_offset, gy_offset, gz_offset, IMU, last_time, cpu, angle
    data = r_data.strip()
    if data != "":
        print(data)
        data = data.replace('update', '')
        if (data == "up" or data == "down"):
            if not moving:
                moving = True
                start_time = time.time()  # Start timing movement
        if (data == "up"):
            pc4.forward(speed)
        elif (data == "down"):
            pc4.backward(speed)
        elif (data == "left"):
            pc4.turn_left(speed)
        elif (data == "right"):
            pc4.turn_right(speed)
        elif (data == "stop"):
            if moving and start_time:  # Update distance before stopping
                start_time = update_distance_traveled(speed, start_time)
                moving = False
            pc4.stop()
        elif (data.startswith("speed:")):
            speed_str = data.replace("speed:", "")
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
        if (data == "scan"):
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
        s.send(json.dumps({
            'data': r_data.strip(),
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
        }) + '\n') # Echo back to client
    # s.send('you said ' + data)

s = BluetoothServer(data_received)
pause()
