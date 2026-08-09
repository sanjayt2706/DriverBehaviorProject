package com.driverisk.app.data.local

/**
 * Status values are stored as plain TEXT columns (matching Database.md's locked
 * `trips.status` enum), not a Room-mapped Kotlin enum, so the on-disk value is always exactly
 * the string the backend will one day see too — no separate TypeConverter to keep in sync.
 *
 * Module 4 only ever writes CREATED (trip exists locally, not yet synced). UPLOADING onward
 * belongs to the upload module (Retrofit), not built yet.
 */
object TripStatus {
    const val CREATED = "CREATED"
    const val UPLOADING = "UPLOADING"
    const val UPLOADED = "UPLOADED"
    const val PROCESSING = "PROCESSING"
    const val PROCESSED = "PROCESSED"
    const val FAILED = "FAILED"
}
