package com.driverisk.app.sensors

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.SystemClock
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow

/**
 * Combined accelerometer + gyroscope stream at 50 Hz (Architecture.md Layer 1). Both sensors
 * are registered at the same period but fire independently; each accelerometer event is paired
 * with the most recently observed gyroscope reading (sample-and-hold) so every emitted
 * [ImuSample] has both, matching raw_sensor_data's NOT NULL accel_* and gyro_* columns.
 *
 * [SAMPLING_PERIOD_US] is only a requested *minimum* period — some hardware ignores it and
 * delivers faster (observed: ~114-123 Hz on Samsung devices during concurrent IMU+GPS
 * recording, instead of the requested 50 Hz). Every downstream consumer of raw_sensor_data
 * (Backend/app/processing, the trained model, Database.md's row-count assumptions) is built
 * around the 50 Hz contract, so accelerometer events are throttled to a fixed 50 Hz emission
 * grid in [onSensorChanged] before they ever reach [ImuSample] — this is the single place that
 * decides what "one sample" means, so nothing downstream needs to know the hardware's native
 * rate. Gyroscope events are never throttled themselves; they only update a sample-and-hold
 * value that is read at whatever rate accelerometer events are actually emitted.
 *
 * No feature extraction happens here — this class only turns hardware callbacks into a cold
 * [Flow], rate-limited. Collection starts when the flow is collected and stops (unregistering
 * both listeners) when that collection is cancelled, so callers get lifecycle safety for free
 * from structured concurrency rather than needing an explicit stop() call.
 */
class SensorCollector(context: Context) {

    private val sensorManager =
        context.applicationContext.getSystemService(Context.SENSOR_SERVICE) as SensorManager

    fun collect(): Flow<ImuSample> = callbackFlow {
        val accelerometer = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
            ?: error("Device has no accelerometer")
        val gyroscope = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE)
            ?: error("Device has no gyroscope")

        var lastGyroX = 0f
        var lastGyroY = 0f
        var lastGyroZ = 0f

        // Fixed 50 Hz emission grid in the sensor timebase (nanoseconds). -1 marks "not yet
        // started"; the first accelerometer event seeds the grid from its own timestamp so it
        // is always emitted immediately, whatever the hardware's native rate.
        var nextEmitAtNs = -1L

        val listener = object : SensorEventListener {
            override fun onSensorChanged(event: SensorEvent) {
                when (event.sensor.type) {
                    Sensor.TYPE_GYROSCOPE -> {
                        lastGyroX = event.values[0]
                        lastGyroY = event.values[1]
                        lastGyroZ = event.values[2]
                    }

                    Sensor.TYPE_ACCELEROMETER -> {
                        if (nextEmitAtNs == -1L) {
                            nextEmitAtNs = event.timestamp
                        }
                        if (event.timestamp < nextEmitAtNs) return
                        // Advance the grid from itself (not from event.timestamp) so jitter in
                        // any one sample doesn't drift the long-run average away from 50 Hz —
                        // except after a real gap (e.g. delivery paused), where catching up
                        // would otherwise burst-emit backlogged samples all at once.
                        nextEmitAtNs = if (event.timestamp - nextEmitAtNs > EMIT_PERIOD_NS) {
                            event.timestamp + EMIT_PERIOD_NS
                        } else {
                            nextEmitAtNs + EMIT_PERIOD_NS
                        }

                        trySend(
                            ImuSample(
                                timestamp = event.timestamp.sensorTimeToEpochMillis(),
                                accelX = event.values[0],
                                accelY = event.values[1],
                                accelZ = event.values[2],
                                gyroX = lastGyroX,
                                gyroY = lastGyroY,
                                gyroZ = lastGyroZ
                            )
                        )
                    }
                }
            }

            override fun onAccuracyChanged(sensor: Sensor, accuracy: Int) = Unit
        }

        sensorManager.registerListener(listener, gyroscope, SAMPLING_PERIOD_US)
        sensorManager.registerListener(listener, accelerometer, SAMPLING_PERIOD_US)

        awaitClose { sensorManager.unregisterListener(listener) }
    }

    companion object {
        // 50 Hz = 1_000_000 / 50 microseconds. Architecture.md Layer 1: "Records accelerometer
        // and gyroscope at 50 Hz". This is a requested minimum period, not a hardware guarantee
        // -- see the throttle in onSensorChanged for why that matters.
        const val SAMPLING_PERIOD_US = 20_000
        const val EMIT_PERIOD_NS = SAMPLING_PERIOD_US * 1_000L
    }
}

/**
 * SensorEvent.timestamp is nanoseconds in the elapsedRealtimeNanos() timebase, not epoch time.
 * raw_sensor_data.timestamp (Database.md) and API.md's sample payloads are epoch milliseconds,
 * so every sample is converted at the point of capture.
 */
private fun Long.sensorTimeToEpochMillis(): Long {
    val elapsedMillisSinceEvent = (SystemClock.elapsedRealtimeNanos() - this) / 1_000_000
    return System.currentTimeMillis() - elapsedMillisSinceEvent
}
