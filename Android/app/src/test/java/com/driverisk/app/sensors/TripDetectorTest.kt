package com.driverisk.app.sensors

import kotlin.time.Duration.Companion.seconds
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Pure logic test -- no Android framework, no instrumentation. Time is injected explicitly so
 * this runs on the JVM in milliseconds instead of waiting on a real clock.
 */
class TripDetectorTest {

    private val detector = TripDetector(stopSpeedThresholdKmh = 2f, stopDuration = 10.seconds)

    @Test
    fun `does not trigger before the stop duration elapses`() {
        assertFalse(detector.onSpeedSample(0f, nowElapsedRealtimeMs = 0))
        assertFalse(detector.onSpeedSample(0f, nowElapsedRealtimeMs = 5_000))
    }

    @Test
    fun `triggers once speed stays at or below threshold for the full duration`() {
        assertFalse(detector.onSpeedSample(1f, nowElapsedRealtimeMs = 0))
        assertTrue(detector.onSpeedSample(1f, nowElapsedRealtimeMs = 10_000))
    }

    @Test
    fun `moving above threshold resets the timer`() {
        assertFalse(detector.onSpeedSample(0f, nowElapsedRealtimeMs = 0))
        assertFalse(detector.onSpeedSample(30f, nowElapsedRealtimeMs = 8_000)) // moving again
        // Without the reset this would trigger (10s since t=0); with it, timer restarts at t=8000.
        assertFalse(detector.onSpeedSample(0f, nowElapsedRealtimeMs = 9_000))
        assertFalse(detector.onSpeedSample(0f, nowElapsedRealtimeMs = 18_000)) // 9000ms since t=9000
        assertTrue(detector.onSpeedSample(0f, nowElapsedRealtimeMs = 19_000)) // 10000ms since t=9000
    }

    @Test
    fun `a null reading is inconclusive and neither resets nor advances the timer`() {
        assertFalse(detector.onSpeedSample(0.5f, nowElapsedRealtimeMs = 0))
        assertFalse(detector.onSpeedSample(null, nowElapsedRealtimeMs = 5_000)) // fix lost mid-window
        assertTrue(detector.onSpeedSample(0.5f, nowElapsedRealtimeMs = 10_000)) // still counts from t=0
    }

    @Test
    fun `reset clears an in-progress stop window`() {
        assertFalse(detector.onSpeedSample(0f, nowElapsedRealtimeMs = 0))
        detector.reset()
        assertFalse(detector.onSpeedSample(0f, nowElapsedRealtimeMs = 9_000))
    }
}
