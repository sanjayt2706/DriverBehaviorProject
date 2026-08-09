package com.driverisk.app

import android.app.Application
import com.driverisk.app.data.local.DriveRiskDatabase
import com.driverisk.app.data.repository.TripRepository

/**
 * Application entry point. Retrofit client initialization is added here once the
 * data/remote module is built.
 */
class DriveRiskApplication : Application() {

    lateinit var database: DriveRiskDatabase
        private set

    lateinit var tripRepository: TripRepository
        private set

    override fun onCreate() {
        super.onCreate()
        database = DriveRiskDatabase.build(this)
        tripRepository = TripRepository(database)
    }
}
