package com.driverisk.app.permissions

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.content.ContextCompat

/**
 * Permissions needed before trip recording (sensors, GPS, foreground service) can start.
 * Accelerometer/gyroscope readings themselves need no runtime permission — only location
 * and, from Android 13, the foreground-service notification do.
 */
object TripPermissions {

    val required: Array<String> = buildList {
        add(Manifest.permission.ACCESS_FINE_LOCATION)
        add(Manifest.permission.ACCESS_COARSE_LOCATION)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            add(Manifest.permission.POST_NOTIFICATIONS)
        }
    }.toTypedArray()

    fun missing(context: Context): Array<String> = required.filter {
        ContextCompat.checkSelfPermission(context, it) != PackageManager.PERMISSION_GRANTED
    }.toTypedArray()

    fun allGranted(context: Context): Boolean = missing(context).isEmpty()
}
