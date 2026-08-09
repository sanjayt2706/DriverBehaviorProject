package com.driverisk.app.sensors

import android.Manifest
import android.content.Context
import android.util.Log
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.rule.GrantPermissionRule
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.take
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeoutOrNull
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Runs SensorCollector against the real accelerometer/gyroscope hardware on the connected
 * device, with LocationCollector running concurrently in the background -- the same concurrent
 * IMU+GPS condition TripRecordingService produces in production, and the condition under which
 * this project's hardware was observed delivering ~114-123 Hz instead of the requested 50 Hz.
 * Verifies SensorCollector's throttle brings the emitted rate back to approximately 50 Hz, not
 * just that the code compiles. take(n) lets the flow complete normally once n samples are
 * collected (rather than being cancelled mid-collection by a timeout), so a slower-than-expected
 * device still returns a full, unambiguous result instead of null.
 */
@RunWith(AndroidJUnit4::class)
class SensorCollectorInstrumentedTest {

    @get:Rule
    val permissionRule: GrantPermissionRule = GrantPermissionRule.grant(
        Manifest.permission.ACCESS_FINE_LOCATION,
        Manifest.permission.ACCESS_COARSE_LOCATION
    )

    @Test
    fun imuStreamDeliversPlausibleSamplesNearFiftyHertzUnderConcurrentGps() = runBlocking {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val collector = SensorCollector(context)
        val locationCollector = LocationCollector(context)

        val expectedSamples = 100 // ~2s at the throttled ~50 Hz
        val samples = coroutineScope {
            val gpsJob = launch {
                // Mirrors TripRecordingService: GPS collected concurrently with the IMU stream,
                // since that concurrency is what originally produced the ~114-123 Hz hardware
                // rate this test guards against.
                locationCollector.collect().collect { }
            }
            val result = withTimeoutOrNull(15_000) {
                collector.collect().take(expectedSamples).toList()
            }
            gpsJob.cancel()
            result
        }

        assertTrue(
            "Expected $expectedSamples IMU samples within 15s; got null (timed out or no sensor)",
            samples != null
        )
        checkNotNull(samples)
        assertEquals(expectedSamples, samples.size)

        val elapsedMs = samples.last().timestamp - samples.first().timestamp
        val observedHz = if (elapsedMs > 0) (samples.size - 1) * 1000.0 / elapsedMs else 0.0
        Log.i(TAG, "Collected ${samples.size} IMU samples in ${elapsedMs}ms (~$observedHz Hz)")

        // Banded, not just a lower bound: SensorCollector's throttle targets 50 Hz regardless
        // of the hardware's native rate, so this must catch both "broken" (too slow) and a
        // throttle regression (too fast, e.g. back to the observed ~114-123 Hz).
        assertTrue(
            "Observed rate ${observedHz}Hz is outside the expected ~50Hz throttled band",
            observedHz in 30.0..65.0
        )

        for (sample in samples) {
            assertTrue("accelX out of range: ${sample.accelX}", sample.accelX.isFinite() && kotlin.math.abs(sample.accelX) < 100f)
            assertTrue("accelY out of range: ${sample.accelY}", sample.accelY.isFinite() && kotlin.math.abs(sample.accelY) < 100f)
            assertTrue("accelZ out of range: ${sample.accelZ}", sample.accelZ.isFinite() && kotlin.math.abs(sample.accelZ) < 100f)
            assertTrue("gyroX out of range: ${sample.gyroX}", sample.gyroX.isFinite() && kotlin.math.abs(sample.gyroX) < 50f)
            assertTrue("gyroY out of range: ${sample.gyroY}", sample.gyroY.isFinite() && kotlin.math.abs(sample.gyroY) < 50f)
            assertTrue("gyroZ out of range: ${sample.gyroZ}", sample.gyroZ.isFinite() && kotlin.math.abs(sample.gyroZ) < 50f)
        }

        // Phone stationary on a surface: gravity should dominate one axis. accelZ carries
        // gravity per Database.md ("includes gravity"), so with the phone lying flat this
        // should read close to +/-9.8 m/s^2 -- a sanity check that we're reading
        // TYPE_ACCELEROMETER (raw) and not TYPE_LINEAR_ACCELERATION (gravity-compensated).
        val avgMagnitude = samples.map { s ->
            kotlin.math.sqrt((s.accelX * s.accelX + s.accelY * s.accelY + s.accelZ * s.accelZ).toDouble())
        }.average()
        Log.i(TAG, "Average accel magnitude: ${avgMagnitude} m/s^2 (expect ~9.8 if stationary)")
        assertTrue("Accel magnitude implausible for a phone at rest under gravity: $avgMagnitude", avgMagnitude in 5.0..15.0)
    }

    companion object {
        private const val TAG = "SensorCollectorTest"
    }
}
