package com.driverisk.app.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.os.SystemClock
import androidx.core.app.NotificationCompat
import com.driverisk.app.DriveRiskApplication
import com.driverisk.app.R
import com.driverisk.app.data.local.entity.SensorDataEntity
import com.driverisk.app.data.repository.TripRepository
import com.driverisk.app.sensors.GpsSample
import com.driverisk.app.sensors.LocationCollector
import com.driverisk.app.sensors.SensorCollector
import com.driverisk.app.sensors.TripDetector
import com.driverisk.app.util.Constants
import com.driverisk.app.util.Haversine
import com.driverisk.app.util.UserIdProvider
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.Job
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.time.Instant
import java.util.UUID

/**
 * Foreground service that owns the recording session's lifetime: it is what makes recording
 * survive screen-off and navigating away from the app, since (unlike a ViewModel) it is not
 * tied to any Activity/Fragment lifecycle.
 *
 * All merge/buffer state (`pendingGps`, `buffer`, `sampleCount`, `distanceKm`) is only ever
 * touched from the single-threaded [serviceScope] dispatcher, so the GPS and IMU collector
 * coroutines never race each other despite running "concurrently".
 */
class TripRecordingService : Service() {

    @OptIn(ExperimentalCoroutinesApi::class)
    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Default.limitedParallelism(1))

    @Volatile
    private var currentTripId: String? = null
    private var recordingJob: Job? = null

    private lateinit var repository: TripRepository
    private lateinit var sensorCollector: SensorCollector
    private lateinit var locationCollector: LocationCollector
    private val tripDetector = TripDetector()

    private var startElapsedRealtimeMs: Long = 0
    private var sampleCount = 0
    private var distanceKm = 0.0
    private var lastFix: GpsSample? = null

    override fun onCreate() {
        super.onCreate()
        val app = application as DriveRiskApplication
        repository = app.tripRepository
        sensorCollector = SensorCollector(this)
        locationCollector = LocationCollector(this)
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> if (currentTripId == null) startRecording()
            ACTION_STOP -> stopRecording()
        }
        // A killed recording has no meaningful state to resume without its original session
        // context, so redelivering an empty restart intent (START_STICKY) would be misleading.
        return START_NOT_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        serviceScope.cancel()
        super.onDestroy()
    }

    private fun startRecording() {
        val tripId = UUID.randomUUID().toString()
        currentTripId = tripId
        sampleCount = 0
        distanceKm = 0.0
        lastFix = null
        startElapsedRealtimeMs = SystemClock.elapsedRealtime()
        tripDetector.reset()

        startForeground(Constants.RECORDING_NOTIFICATION_ID, buildNotification())

        recordingJob = serviceScope.launch {
            repository.createTrip(
                tripId = tripId,
                userId = UserIdProvider.getOrCreate(this@TripRecordingService),
                deviceModel = "${Build.MANUFACTURER} ${Build.MODEL}",
                startTime = Instant.now()
            )

            var pendingGps: GpsSample? = null
            val buffer = mutableListOf<SensorDataEntity>()

            try {
                coroutineScope {
                    launch {
                        locationCollector.collect().collect { gps ->
                            lastFix?.let { previous ->
                                distanceKm += Haversine.distanceKm(
                                    previous.latitude, previous.longitude,
                                    gps.latitude, gps.longitude
                                )
                            }
                            lastFix = gps
                            pendingGps = gps
                            if (tripDetector.onSpeedSample(gps.speedKmh)) {
                                stopRecording()
                            }
                        }
                    }

                    sensorCollector.collect().collect { imu ->
                        val gpsTag = pendingGps
                        pendingGps = null // attach a fresh fix to exactly one row, then go back to null
                        buffer += SensorDataEntity(
                            tripId = tripId,
                            timestamp = imu.timestamp,
                            latitude = gpsTag?.latitude,
                            longitude = gpsTag?.longitude,
                            speed = gpsTag?.speedKmh,
                            accelX = imu.accelX,
                            accelY = imu.accelY,
                            accelZ = imu.accelZ,
                            gyroX = imu.gyroX,
                            gyroY = imu.gyroY,
                            gyroZ = imu.gyroZ
                        )
                        sampleCount++
                        if (buffer.size >= Constants.SENSOR_BATCH_FLUSH_SIZE) {
                            val toFlush = buffer.toList()
                            buffer.clear()
                            repository.insertSamples(toFlush)
                        }
                    }
                }
            } finally {
                // Runs on cancellation too (manual Stop or auto-stop). NonCancellable so the
                // final DB write for a partially-filled buffer isn't itself cut off mid-suspend.
                withContext(NonCancellable) {
                    if (buffer.isNotEmpty()) {
                        repository.insertSamples(buffer.toList())
                    }
                }
            }
        }
    }

    private fun stopRecording() {
        val tripId = currentTripId ?: return
        currentTripId = null
        val job = recordingJob
        recordingJob = null

        serviceScope.launch {
            job?.cancelAndJoin() // waits for collectors to unregister and the final buffer flush
            val durationS = (SystemClock.elapsedRealtime() - startElapsedRealtimeMs) / 1000.0
            repository.finalizeTrip(tripId, Instant.now(), durationS, distanceKm, sampleCount)
            stopForeground(STOP_FOREGROUND_REMOVE)
            stopSelf()
        }
    }

    private fun buildNotification(): Notification =
        NotificationCompat.Builder(this, Constants.RECORDING_NOTIFICATION_CHANNEL_ID)
            .setContentTitle(getString(R.string.recording_notification_title))
            .setContentText(getString(R.string.recording_notification_text))
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                Constants.RECORDING_NOTIFICATION_CHANNEL_ID,
                getString(R.string.recording_notification_channel_name),
                NotificationManager.IMPORTANCE_LOW
            )
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    companion object {
        const val ACTION_START = "com.driverisk.app.action.START_RECORDING"
        const val ACTION_STOP = "com.driverisk.app.action.STOP_RECORDING"
    }
}
