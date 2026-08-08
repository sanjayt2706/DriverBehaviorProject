package com.driverisk.app.ui.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * Trip recording, upload and history are later modules. Module 1's Home screen only
 * renders a static shell, so [uiState] has nothing to load yet.
 */
data class HomeUiState(
    val hasRecentTrip: Boolean = false
)

class HomeViewModel : ViewModel() {

    private val _uiState = MutableStateFlow(HomeUiState())
    val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()

    private val _featureNotAvailable = MutableSharedFlow<Unit>()
    val featureNotAvailable: SharedFlow<Unit> = _featureNotAvailable.asSharedFlow()

    fun onStartTripClicked() = notifyNotAvailable()

    fun onViewHistoryClicked() = notifyNotAvailable()

    private fun notifyNotAvailable() {
        viewModelScope.launch { _featureNotAvailable.emit(Unit) }
    }
}
