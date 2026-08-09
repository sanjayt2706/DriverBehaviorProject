package com.driverisk.app.sensors

/**
 * One GPS fix. Field names and units mirror Database.md's raw_sensor_data columns:
 * timestamp in epoch milliseconds, speed in km/h (converted from the platform's m/s).
 * speedKmh is null when the fix carries no speed estimate.
 */
data class GpsSample(
    val timestamp: Long,
    val latitude: Double,
    val longitude: Double,
    val speedKmh: Float?
)
