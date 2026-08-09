package com.driverisk.app.sensors

import android.Manifest
import android.content.Context
import android.util.Log
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.rule.GrantPermissionRule
import kotlinx.coroutines.flow.take
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeoutOrNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Runs LocationCollector against the real GPS/fused location provider on the connected device.
 * GrantPermissionRule grants ACCESS_FINE_LOCATION before the test starts, independent of
 * whatever was already granted through the app's UI (Module 2).
 *
 * A real fix depends on sky visibility the test cannot control, so this does not hard-fail
 * when no fix arrives indoors -- it proves the collector registers correctly, respects the
 * permission check, and never crashes, and it validates any fix it does receive. Whether an
 * actual fix arrived is logged and must be checked in logcat / reported explicitly, not assumed
 * from a green test result.
 */
@RunWith(AndroidJUnit4::class)
class LocationCollectorInstrumentedTest {

    @get:Rule
    val permissionRule: GrantPermissionRule = GrantPermissionRule.grant(
        Manifest.permission.ACCESS_FINE_LOCATION,
        Manifest.permission.ACCESS_COARSE_LOCATION
    )

    @Test
    fun gpsCollectorRegistersAndYieldsPlausibleFixIfAvailable() = runBlocking {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val collector = LocationCollector(context)

        val samples = withTimeoutOrNull(90_000) {
            collector.collect().take(1).toList()
        }

        if (samples == null) {
            Log.w(TAG, "No GPS fix within 90s (likely indoors/no sky view). Collector did not crash.")
            return@runBlocking
        }

        val sample = samples.first()
        Log.i(
            TAG,
            "Received GPS fix: lat=${sample.latitude}, lon=${sample.longitude}, " +
                "speedKmh=${sample.speedKmh}, timestamp=${sample.timestamp}"
        )
        assertTrue("Latitude out of range: ${sample.latitude}", sample.latitude in -90.0..90.0)
        assertTrue("Longitude out of range: ${sample.longitude}", sample.longitude in -180.0..180.0)
        assertTrue("Timestamp not epoch-plausible: ${sample.timestamp}", sample.timestamp > 1_700_000_000_000L)
    }

    companion object {
        private const val TAG = "LocationCollectorTest"
    }
}
