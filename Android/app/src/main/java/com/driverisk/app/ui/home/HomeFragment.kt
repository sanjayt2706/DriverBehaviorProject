package com.driverisk.app.ui.home

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.driverisk.app.R
import com.driverisk.app.databinding.FragmentHomeBinding
import com.driverisk.app.permissions.TripPermissionRequester
import com.driverisk.app.permissions.TripPermissions
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.android.material.snackbar.Snackbar
import kotlinx.coroutines.launch

class HomeFragment : Fragment() {

    private var _binding: FragmentHomeBinding? = null
    private val binding get() = _binding!!

    private val viewModel: HomeViewModel by viewModels()

    // Must be a field initializer, not created lazily in onViewCreated: the launcher it wraps
    // has to register before this fragment leaves the CREATED state.
    private val permissionRequester = TripPermissionRequester(this) { granted, permanentlyDenied ->
        when {
            granted -> viewModel.onStartTripClicked()
            permanentlyDenied.isNotEmpty() -> showPermissionSettingsDialog()
            else -> showPermissionRationale()
        }
    }

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentHomeBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.buttonStartTrip.setOnClickListener { onStartTripClicked() }
        binding.buttonViewHistory.setOnClickListener { viewModel.onViewHistoryClicked() }

        viewLifecycleOwner.lifecycleScope.launch {
            viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
                launch {
                    viewModel.uiState.collect { state -> render(state) }
                }
                launch {
                    viewModel.featureNotAvailable.collect {
                        Snackbar.make(binding.root, R.string.home_feature_coming_soon, Snackbar.LENGTH_SHORT)
                            .show()
                    }
                }
            }
        }
    }

    private fun render(state: HomeUiState) {
        // hasRecentTrip is always false until the trip history module lands; the branch
        // exists now so the binding point for a real trip summary is already in place.
        binding.textRecentTrip.text = getString(R.string.home_no_recent_trip)
    }

    // Trip recording (Module 3) isn't built yet, so a granted permission set still falls
    // through to viewModel.onStartTripClicked()'s "not available yet" snackbar for now.
    private fun onStartTripClicked() {
        if (TripPermissions.allGranted(requireContext())) {
            viewModel.onStartTripClicked()
        } else {
            permissionRequester.launch(TripPermissions.required)
        }
    }

    private fun showPermissionRationale() {
        Snackbar.make(binding.root, R.string.permission_rationale_message, Snackbar.LENGTH_LONG)
            .setAction(R.string.permission_rationale_grant) {
                permissionRequester.launch(TripPermissions.missing(requireContext()))
            }
            .show()
    }

    private fun showPermissionSettingsDialog() {
        MaterialAlertDialogBuilder(requireContext())
            .setTitle(R.string.permission_denied_title)
            .setMessage(R.string.permission_denied_message)
            .setPositiveButton(R.string.permission_denied_open_settings) { _, _ ->
                startActivity(
                    Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                        data = Uri.fromParts("package", requireContext().packageName, null)
                    }
                )
            }
            .setNegativeButton(R.string.permission_denied_cancel, null)
            .show()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
