package com.netmindai.node

/**
 * Tiny cross-section shared state.
 */
object AppState {
    @Volatile
    var modelLoaded: Boolean = false
}
