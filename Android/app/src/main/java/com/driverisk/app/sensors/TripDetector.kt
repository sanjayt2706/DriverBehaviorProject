package com.driverisk.app.sensors

import android.os.SystemClock
import kotlin.time.Duration
import kotlin.time.Duration.Companion.seconds

/**
 * Auto-stop condition from Architecture.md Layer 1: "speed ~= 0 for N seconds". Neither the
 * epsilon nor N is fixed in the design document, so both are [INFERRED] defaults, kept as
 * constructor parameters so they're easy to retune from one place without touching the logic.
 *
 * A null speed reading (no GPS fix) is treated as inconclusive -- it neither resets nor advances
 * the stopped-timer, since a momentary fix loss while genuinely parked shouldn't cancel a
 * detection in progress, and a momentary fix loss while still moving shouldn't fake one either.
 *
 * Takes an explicit clock reading as a parameter (rather than calling SystemClock internally)
 * purely so it stays unit-testable with fake times, no Android framework / instrumentation
 * needed.
 */
class TripDetector(
    private val stopSpeedThresholdKmh: Float = STOP_SPEED_THRESHOLD_KMH,
    private val stopDuration: Duration = STOP_DURATION
) {
    private var belowThresholdSinceMs: Long? = null

    fun onSpeedSample(speedKmh: Float?, nowElapsedRealtimeMs: Long = SystemClock.elapsedRealtime()): Boolean {
        when {
            speedKmh == null -> Unit // inconclusive: leave existing state as-is
            speedKmh > stopSpeedThresholdKmh -> belowThresholdSinceMs = null
            belowThresholdSinceMs == null -> belowThresholdSinceMs = nowElapsedRealtimeMs
        }
        val since = belowThresholdSinceMs ?: return false
        return nowElapsedRealtimeMs - since >= stopDuration.inWholeMilliseconds
    }

    fun reset() {
        belowThresholdSinceMs = null
    }

    companion object {
        const val STOP_SPEED_THRESHOLD_KMH = 2f
        val STOP_DURATION: Duration = 180.seconds
    }
}
