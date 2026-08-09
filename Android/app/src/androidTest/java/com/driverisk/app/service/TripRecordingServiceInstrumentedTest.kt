package com.driverisk.app.service

import android.Manifest
import android.content.Context
import android.content.Intent
import android.util.Log
import androidx.core.content.ContextCompat
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.rule.GrantPermissionRule
import com.driverisk.app.DriveRiskApplication
import kotlinx.coroutines.delay
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Runs the real TripRecordingService on the connected device: starts it, lets it record for a
 * few seconds against real hardware, stops it, then reads back what actually landed in Room.
 * This is Module 4's end-to-end proof -- start, collect, persist, stop cleanly -- as opposed to
 * unit-testing pieces in isolation.
 */
@RunWith(AndroidJUnit4::class)
class TripRecordingServiceInstrumentedTest {

    @get:Rule
    val permissionRule: GrantPermissionRule = GrantPermissionRule.grant(
        Manifest.permission.ACCESS_FINE_LOCATION,
        Manifest.permission.ACCESS_COARSE_LOCATION,
        Manifest.permission.POST_NOTIFICATIONS
    )

    @Test
    fun startRecordStopPersistsTripAndMatchingSamples(): Unit = runBlocking {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val app = context.applicationContext as DriveRiskApplication
        app.database.clearAllTables()

        ContextCompat.startForegroundService(
            context,
            Intent(context, TripRecordingService::class.java).setAction(TripRecordingService.ACTION_START)
        )

        val recordMs = 6_000L
        delay(recordMs)

        context.startService(
            Intent(context, TripRecordingService::class.java).setAction(TripRecordingService.ACTION_STOP)
        )

        // Finalization is async (cancel + join + one more DB write); poll instead of a fixed sleep.
        val trip = withTimeout(10_000) {
            var found: com.driverisk.app.data.local.entity.TripEntity? = null
            while (found?.endTime == null) {
                val trips = app.database.tripDao().getAll()
                found = trips.firstOrNull()
                if (found?.endTime == null) delay(300)
            }
            found
        }

        assertNotNull("Expected exactly one finalized trip after stop", trip)
        checkNotNull(trip)

        val allTrips = app.database.tripDao().getAll()
        assertEquals("Expected exactly one trip row for this session", 1, allTrips.size)

        val persistedCount = app.database.sensorDataDao().countForTrip(trip.tripId)
        Log.i(
            TAG,
            "Trip ${trip.tripId}: sampleCount(recorded)=${trip.sampleCount}, " +
                "rows persisted=$persistedCount, durationS=${trip.durationS}, distanceKm=${trip.distanceKm}"
        )

        // The service's own count must match what actually landed in the table -- this is the
        // "stops cleanly" check: no samples lost or double-written by the cancel + final flush path.
        assertEquals(
            "TripEntity.sampleCount must match the number of sensor_data_table rows for the trip",
            trip.sampleCount,
            persistedCount
        )

        // ~6s at the throttled ~50Hz should be ~300 samples. Banded, not just a lower bound, so
        // a regression back to the unthrottled hardware rate (Module 4 finding: ~114-123 Hz,
        // which would give ~680-740 samples here) fails loudly instead of quietly passing a
        // "plausible" lower bound.
        assertTrue(
            "Expected a plausible number of IMU samples for a ${recordMs}ms recording at ~50Hz, got $persistedCount",
            persistedCount in 150..450
        )

        assertNotNull("durationS should be set on finalize", trip.durationS)
        assertTrue("durationS should roughly match the recording window", trip.durationS!! in 3.0..15.0)

        val rows = app.database.sensorDataDao().getAllForTrip(trip.tripId)
        assertTrue("Expected non-empty rows list matching persistedCount", rows.size == persistedCount)
        for (row in rows) {
            assertTrue(row.accelX.isFinite() && row.accelY.isFinite() && row.accelZ.isFinite())
            assertTrue(row.gyroX.isFinite() && row.gyroY.isFinite() && row.gyroZ.isFinite())
        }
        val gpsTaggedRows = rows.count { it.latitude != null }
        Log.i(TAG, "Rows with a GPS fix attached: $gpsTaggedRows / ${rows.size} (0 is expected indoors)")

        // Precise rate check from the actual persisted timestamps (rows are ordered by
        // timestamp ASC), rather than assuming the full recordMs window elapsed -- this is
        // this project's Module 4 finding under its real reproduction conditions: the full
        // foreground service, concurrent IMU + GPS, persisted all the way to Room.
        val elapsedMs = rows.last().timestamp - rows.first().timestamp
        val observedHz = if (elapsedMs > 0) (rows.size - 1) * 1000.0 / elapsedMs else 0.0
        Log.i(TAG, "Persisted IMU rate: ${rows.size} samples over ${elapsedMs}ms (~$observedHz Hz)")
        assertTrue(
            "Observed persisted rate ${observedHz}Hz is outside the expected ~50Hz throttled band",
            observedHz in 30.0..65.0
        )
    }

    companion object {
        private const val TAG = "TripRecordingServiceTest"
    }
}
