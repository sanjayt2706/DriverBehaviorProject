package com.driverisk.app.data.repository

import com.driverisk.app.data.local.DriveRiskDatabase
import com.driverisk.app.data.local.TripStatus
import com.driverisk.app.data.local.entity.SensorDataEntity
import com.driverisk.app.data.local.entity.TripEntity
import java.time.Instant

/**
 * The only class touching Room (FolderStructure.md's MVVM boundary rule) for trip recording.
 * Retrofit/upload will extend this later; nothing here calls the network.
 */
class TripRepository(database: DriveRiskDatabase) {

    private val tripDao = database.tripDao()
    private val sensorDataDao = database.sensorDataDao()

    suspend fun createTrip(tripId: String, userId: String, deviceModel: String?, startTime: Instant) {
        tripDao.insert(
            TripEntity(
                tripId = tripId,
                userId = userId,
                deviceModel = deviceModel,
                startTime = startTime.toString(),
                status = TripStatus.CREATED,
                createdAt = Instant.now().toString()
            )
        )
    }

    suspend fun insertSamples(samples: List<SensorDataEntity>) {
        if (samples.isNotEmpty()) sensorDataDao.insertAll(samples)
    }

    suspend fun finalizeTrip(tripId: String, endTime: Instant, durationS: Double, distanceKm: Double, sampleCount: Int) {
        tripDao.finalize(tripId, endTime.toString(), durationS, distanceKm, sampleCount)
    }

    suspend fun getTrip(tripId: String): TripEntity? = tripDao.getById(tripId)

    suspend fun getAllTrips(): List<TripEntity> = tripDao.getAll()

    suspend fun countSamples(tripId: String): Int = sensorDataDao.countForTrip(tripId)
}
