package com.driverisk.app

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity

/**
 * Single-activity host for the Navigation Component graph.
 * No business logic here: destinations own their own Fragment + ViewModel pair (MVVM).
 */
class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
    }
}
