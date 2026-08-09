package com.driverisk.app.util

import android.content.Context
import java.util.UUID

/**
 * API.md's `user_id` requires a value, but the locked architecture has no login/account system
 * (Architecture.md explicitly puts multi-user fleet roles out of scope). A per-install anonymous
 * id, generated once and persisted, is the simplest thing that satisfies the contract without
 * inventing an auth system nobody asked for.
 */
object UserIdProvider {
    private const val PREFS_NAME = "driverisk_prefs"
    private const val KEY_USER_ID = "user_id"

    fun getOrCreate(context: Context): String {
        val prefs = context.applicationContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        return prefs.getString(KEY_USER_ID, null) ?: UUID.randomUUID().toString().also { newId ->
            prefs.edit().putString(KEY_USER_ID, newId).apply()
        }
    }
}
