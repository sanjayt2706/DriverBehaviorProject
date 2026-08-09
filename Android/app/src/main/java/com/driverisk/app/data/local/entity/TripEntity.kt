package com.driverisk.app.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.driverisk.app.data.local.TripStatus

/**
 * Local mirror of Database.md's `trips` table. `received_batches` and `processed_at` are
 * omitted here — they exist only to support server-side upload/processing state, which Module 4
 * (recording only, no Retrofit) has nothing to write into them yet. They belong with the upload
 * module that actually needs them.
 */
@Entity(tableName = "trip_table")
data class TripEntity(
    @PrimaryKey val tripId: String,
    val userId: String,
    val deviceModel: String?,
    val startTime: String,
    val endTime: String? = null,
    val durationS: Double? = null,
    val distanceKm: Double? = null,
    val sampleCount: Int = 0,
    val status: String = TripStatus.CREATED,
    val createdAt: String
)
