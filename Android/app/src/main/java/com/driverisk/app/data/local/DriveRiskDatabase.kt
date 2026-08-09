package com.driverisk.app.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import com.driverisk.app.data.local.dao.SensorDataDao
import com.driverisk.app.data.local.dao.TripDao
import com.driverisk.app.data.local.entity.SensorDataEntity
import com.driverisk.app.data.local.entity.TripEntity

/**
 * Named driverisk_local.db, distinct from the backend's driverisk.db (Database.md) -- this is
 * the app's own offline buffer, not a copy of the server file. exportSchema is off; a schema
 * history directory isn't worth the setup for a project at this stage.
 */
@Database(entities = [TripEntity::class, SensorDataEntity::class], version = 1, exportSchema = false)
abstract class DriveRiskDatabase : RoomDatabase() {

    abstract fun tripDao(): TripDao
    abstract fun sensorDataDao(): SensorDataDao

    companion object {
        fun build(context: Context): DriveRiskDatabase =
            Room.databaseBuilder(
                context.applicationContext,
                DriveRiskDatabase::class.java,
                "driverisk_local.db"
            ).build()
    }
}
