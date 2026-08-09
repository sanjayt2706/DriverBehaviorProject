package com.driverisk.app.sensors

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.os.Looper
import androidx.core.content.ContextCompat
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow

/**
 * GPS stream at 1 Hz (Architecture.md Layer 1), via FusedLocationProviderClient rather than raw
 * LocationManager for better battery behaviour. High accuracy is deliberate: Layer 4's headline
 * curve_density feature is computed from this path's bearing and curvature, which needs
 * GPS-grade fixes, not network/cell-tower positioning.
 *
 * Like [SensorCollector], this only turns location callbacks into a cold [Flow] — updates start
 * on collection and stop (removeLocationUpdates) when that collection is cancelled.
 */
class LocationCollector(context: Context) {

    private val appContext = context.applicationContext
    private val client: FusedLocationProviderClient =
        LocationServices.getFusedLocationProviderClient(appContext)

    @SuppressLint("MissingPermission")
    fun collect(): Flow<GpsSample> = callbackFlow {
        check(hasFineLocationPermission()) {
            "ACCESS_FINE_LOCATION not granted; check TripPermissions.allGranted() before starting collection"
        }

        val request = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, UPDATE_INTERVAL_MS)
            .setMinUpdateIntervalMillis(UPDATE_INTERVAL_MS)
            .build()

        val callback = object : LocationCallback() {
            override fun onLocationResult(result: LocationResult) {
                val location = result.lastLocation ?: return
                trySend(
                    GpsSample(
                        timestamp = location.time,
                        latitude = location.latitude,
                        longitude = location.longitude,
                        speedKmh = if (location.hasSpeed()) location.speed * 3.6f else null
                    )
                )
            }
        }

        client.requestLocationUpdates(request, callback, Looper.getMainLooper())

        awaitClose { client.removeLocationUpdates(callback) }
    }

    private fun hasFineLocationPermission(): Boolean = ContextCompat.checkSelfPermission(
        appContext,
        Manifest.permission.ACCESS_FINE_LOCATION
    ) == PackageManager.PERMISSION_GRANTED

    companion object {
        // 1 Hz. Architecture.md Layer 1: "GPS at 1 Hz".
        const val UPDATE_INTERVAL_MS = 1_000L
    }
}
