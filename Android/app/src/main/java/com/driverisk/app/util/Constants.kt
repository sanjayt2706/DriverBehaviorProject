package com.driverisk.app.util

object Constants {
    const val RECORDING_NOTIFICATION_CHANNEL_ID = "trip_recording"
    const val RECORDING_NOTIFICATION_ID = 1001

    // ~1s of IMU samples at 50 Hz per Room write, balancing write frequency against memory.
    const val SENSOR_BATCH_FLUSH_SIZE = 50
}
