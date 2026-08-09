package com.driverisk.app.util

import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.pow
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Great-circle distance between two GPS fixes. Used to accumulate a best-effort local
 * distance_km while recording (Database.md notes distance_km as "computed from GPS path
 * (haversine)"). This is a client-side estimate for offline display; once a trip is uploaded,
 * the backend's own computation during /process (Layer 4) is authoritative.
 */
object Haversine {
    private const val EARTH_RADIUS_KM = 6371.0

    fun distanceKm(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
        val dLat = Math.toRadians(lat2 - lat1)
        val dLon = Math.toRadians(lon2 - lon1)
        val a = sin(dLat / 2).pow(2) +
            cos(Math.toRadians(lat1)) * cos(Math.toRadians(lat2)) * sin(dLon / 2).pow(2)
        val c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return EARTH_RADIUS_KM * c
    }
}
