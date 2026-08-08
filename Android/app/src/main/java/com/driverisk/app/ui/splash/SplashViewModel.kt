package com.driverisk.app.ui.splash

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.launch

private const val SPLASH_DISPLAY_MS = 1200L

/**
 * Module 1 has nothing to initialize (no Room/session state yet), so the splash's only
 * job is a brief branding pause before handing off to Home.
 */
class SplashViewModel : ViewModel() {

    private val _navigateToHome = MutableSharedFlow<Unit>(replay = 0)
    val navigateToHome: SharedFlow<Unit> = _navigateToHome.asSharedFlow()

    init {
        viewModelScope.launch {
            delay(SPLASH_DISPLAY_MS)
            _navigateToHome.emit(Unit)
        }
    }
}
