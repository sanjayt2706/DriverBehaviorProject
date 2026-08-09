package com.driverisk.app.service

import android.Manifest
import android.content.Context
import android.content.Intent
import android.util.Log
import androidx.core.content.ContextCompat
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.rule.GrantPermissionRule
import androidx.test.uiautomator.UiDevice
import com.driverisk.app.DriveRiskApplication
import kotlinx.coroutines.delay
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Literal test of Architecture.md's "foreground service, survives screen-off" requirement:
 * turns the physical screen off with UiDevice, keeps it off while the service should be
 * recording, then confirms samples kept accumulating throughout -- not just before/after.
 *
 * No Activity is ever launched in this test, so this also demonstrates the recording session's
 * independence from any Activity/Fragment lifecycle, not only from screen state.
 */
@RunWith(AndroidJUnit4::class)
class RecordingScreenOffInstrumentedTest {

    @get:Rule
    val permissionRule: GrantPermissionRule = GrantPermissionRule.grant(
        Manifest.permission.ACCESS_FINE_LOCATION,
        Manifest.permission.ACCESS_COARSE_LOCATION,
        Manifest.permission.POST_NOTIFICATIONS
    )

    @Test
    fun recordingContinuesWhileScreenIsOff(): Unit = runBlocking {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val app = context.applicationContext as DriveRiskApplication
        app.database.clearAllTables()
        val device = UiDevice.getInstance(InstrumentationRegistry.getInstrumentation())

        ContextCompat.startForegroundService(
            context,
            Intent(context, TripRecordingService::class.java).setAction(TripRecordingService.ACTION_START)
        )
        delay(2_000)
        val countBeforeScreenOff = app.database.sensorDataDao().countAll()

        device.sleep()
        assertTrue("Expected the display to actually turn off", !device.isScreenOn)
        Log.i(TAG, "Screen off. countBeforeScreenOff=$countBeforeScreenOff")

        delay(8_000) // recording should keep going with no UI, no Activity, and no display

        val countWhileScreenOff = app.database.sensorDataDao().countAll()
        device.wakeUp()
        Log.i(TAG, "Screen back on. countWhileScreenOff=$countWhileScreenOff")

        context.startService(
            Intent(context, TripRecordingService::class.java).setAction(TripRecordingService.ACTION_STOP)
        )

        val trip = withTimeout(10_000) {
            var found: com.driverisk.app.data.local.entity.TripEntity? = null
            while (found?.endTime == null) {
                found = app.database.tripDao().getAll().firstOrNull()
                if (found?.endTime == null) delay(300)
            }
            found
        }
        assertNotNull("Expected the trip to finalize after stop", trip)

        val finalCount = app.database.sensorDataDao().countAll()
        Log.i(
            TAG,
            "Final: countBeforeScreenOff=$countBeforeScreenOff, countWhileScreenOff=$countWhileScreenOff, " +
                "finalCount=$finalCount over an 8s screen-off window"
        )

        assertTrue(
            "Expected sample count to grow during the screen-off window " +
                "(before=$countBeforeScreenOff, during=$countWhileScreenOff)",
            countWhileScreenOff > countBeforeScreenOff + 50
        )
        assertTrue(
            "Expected sample count to keep growing after screen back on until stop " +
                "(during=$countWhileScreenOff, final=$finalCount)",
            finalCount >= countWhileScreenOff
        )
    }

    companion object {
        private const val TAG = "RecordingScreenOffTest"
    }
}
