package com.driverisk.app.permissions

import androidx.activity.result.contract.ActivityResultContracts
import androidx.fragment.app.Fragment

/**
 * Wraps the multi-permission request flow for [TripPermissions.required]. Must be constructed
 * as a field initializer (not lazily, not inside onViewCreated) so the launcher registers
 * before the host fragment leaves the CREATED state, per ActivityResultContracts' requirement.
 */
class TripPermissionRequester(
    private val fragment: Fragment,
    private val onResult: (granted: Boolean, permanentlyDenied: List<String>) -> Unit
) {

    private val launcher = fragment.registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { result ->
        val denied = result.filterValues { granted -> !granted }.keys
        val permanentlyDenied = denied.filter { permission ->
            !fragment.shouldShowRequestPermissionRationale(permission)
        }
        onResult(denied.isEmpty(), permanentlyDenied)
    }

    fun launch(permissions: Array<String> = TripPermissions.required) {
        launcher.launch(permissions)
    }
}
