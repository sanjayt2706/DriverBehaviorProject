package com.driverisk.app.ui.home

import android.os.Bundle
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
import com.google.android.material.snackbar.Snackbar
import kotlinx.coroutines.launch

class HomeFragment : Fragment() {

    private var _binding: FragmentHomeBinding? = null
    private val binding get() = _binding!!

    private val viewModel: HomeViewModel by viewModels()

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

        binding.buttonStartTrip.setOnClickListener { viewModel.onStartTripClicked() }
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

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
