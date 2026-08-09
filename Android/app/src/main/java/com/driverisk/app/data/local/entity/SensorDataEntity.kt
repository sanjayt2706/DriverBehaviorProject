package com.driverisk.app.data.local.entity

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

/**
 * Local mirror of Database.md's `raw_sensor_data` table. Field names and units match exactly:
 * epoch-ms timestamp, accel_* and gyro_* required (m/s^2 and rad/s), lat/lon/speed nullable because
 * GPS (1 Hz) is sparse relative to the IMU (50 Hz) -- most rows carry no fix, by design, not by
 * omission. See TripRecordingService for how a fix gets attached to exactly one row per update.
 */
@Entity(
    tableName = "sensor_data_table",
    foreignKeys = [
        ForeignKey(
            entity = TripEntity::class,
            parentColumns = ["tripId"],
            childColumns = ["tripId"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [Index(value = ["tripId", "timestamp"])]
)
data class SensorDataEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val tripId: String,
    val timestamp: Long,
    val latitude: Double?,
    val longitude: Double?,
    val speed: Float?,
    val accelX: Float,
    val accelY: Float,
    val accelZ: Float,
    val gyroX: Float,
    val gyroY: Float,
    val gyroZ: Float
)
