package com.driverisk.app.sensors

/**
 * One combined accelerometer + gyroscope reading. Field names and units mirror
 * Database.md's raw_sensor_data columns exactly: accel_* in m/s² (z includes gravity,
 * since this comes from TYPE_ACCELEROMETER, not TYPE_LINEAR_ACCELERATION), gyro_* in rad/s,
 * timestamp in epoch milliseconds.
 */
data class ImuSample(
    val timestamp: Long,
    val accelX: Float,
    val accelY: Float,
    val accelZ: Float,
    val gyroX: Float,
    val gyroY: Float,
    val gyroZ: Float
)
