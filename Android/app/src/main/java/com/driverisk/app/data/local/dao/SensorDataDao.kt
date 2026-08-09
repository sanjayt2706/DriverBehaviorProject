package com.driverisk.app.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import com.driverisk.app.data.local.entity.SensorDataEntity

@Dao
interface SensorDataDao {

    @Insert
    suspend fun insertAll(samples: List<SensorDataEntity>)

    @Query("SELECT COUNT(*) FROM sensor_data_table WHERE tripId = :tripId")
    suspend fun countForTrip(tripId: String): Int

    @Query("SELECT COUNT(*) FROM sensor_data_table")
    suspend fun countAll(): Int

    @Query("SELECT * FROM sensor_data_table WHERE tripId = :tripId ORDER BY timestamp ASC")
    suspend fun getAllForTrip(tripId: String): List<SensorDataEntity>
}
