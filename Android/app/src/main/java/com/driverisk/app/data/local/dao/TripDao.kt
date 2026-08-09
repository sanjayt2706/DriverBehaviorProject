package com.driverisk.app.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import com.driverisk.app.data.local.entity.TripEntity

@Dao
interface TripDao {

    @Insert
    suspend fun insert(trip: TripEntity)

    @Query(
        """
        UPDATE trip_table
        SET endTime = :endTime, durationS = :durationS, distanceKm = :distanceKm, sampleCount = :sampleCount
        WHERE tripId = :tripId
        """
    )
    suspend fun finalize(tripId: String, endTime: String, durationS: Double, distanceKm: Double, sampleCount: Int)

    @Query("SELECT * FROM trip_table WHERE tripId = :tripId")
    suspend fun getById(tripId: String): TripEntity?

    @Query("SELECT * FROM trip_table ORDER BY startTime DESC")
    suspend fun getAll(): List<TripEntity>
}
