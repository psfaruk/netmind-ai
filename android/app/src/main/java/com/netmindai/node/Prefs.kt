package com.netmindai.node

import android.content.Context
import android.content.SharedPreferences

/**
 * Small SharedPreferences wrapper for NETMIND Node.
 */
object Prefs {

    private const val NAME = "netmind_node"
    private const val KEY_MODEL_INDEX = "model_index"
    private const val KEY_CUSTOM_URL = "custom_url"
    private const val KEY_MODEL_FILE = "model_file"

    private lateinit var prefs: SharedPreferences

    fun init(context: Context) {
        prefs = context.applicationContext.getSharedPreferences(NAME, Context.MODE_PRIVATE)
    }

    /** 0 / 1 = preset index, -1 = custom URL, -2 = imported local file */
    var modelIndex: Int
        get() = prefs.getInt(KEY_MODEL_INDEX, 0)
        set(value) = prefs.edit().putInt(KEY_MODEL_INDEX, value).apply()

    var customUrl: String
        get() = prefs.getString(KEY_CUSTOM_URL, "") ?: ""
        set(value) = prefs.edit().putString(KEY_CUSTOM_URL, value).apply()

    var modelFile: String
        get() = prefs.getString(KEY_MODEL_FILE, "") ?: ""
        set(value) = prefs.edit().putString(KEY_MODEL_FILE, value).apply()
}
