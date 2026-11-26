package com.netmindai.node

import android.content.Context
import android.content.SharedPreferences
import java.io.File

/**
 * Small SharedPreferences wrapper for NETMIND Node.
 */
object Prefs {

    private const val NAME = "netmind_node"
    private const val KEY_MODEL_INDEX = "model_index"
    private const val KEY_CUSTOM_URL = "custom_url"
    private const val KEY_MODEL_FILE = "model_file"
    private const val KEY_DEEP_THINK = "deep_think"
    private const val KEY_MIGRATED_V2 = "migrated_v2"

    private lateinit var prefs: SharedPreferences

    fun init(context: Context) {
        prefs = context.applicationContext.getSharedPreferences(NAME, Context.MODE_PRIVATE)
        migrateV2(context)
    }

    /**
     * v0.2.0: the default model changed from Qwen3-0.6B to Gemma 3 4B (the
     * first phone-sized model with genuinely good বাংলা). Keep existing
     * installs pointed at their already-downloaded Qwen file instead of
     * silently switching them to a new 2.4 GB download.
     */
    private fun migrateV2(context: Context) {
        if (prefs.getBoolean(KEY_MIGRATED_V2, false)) return
        val editor = prefs.edit()
        if (prefs.getInt(KEY_MODEL_INDEX, 0) == 0) {
            val qwenFile = File(File(context.filesDir, "models"), "Qwen3-0.6B-Q4_K_M.gguf")
            if (qwenFile.exists()) {
                // user already has the old default (Qwen3-0.6B, now index 1)
                editor.putInt(KEY_MODEL_INDEX, 1)
            }
        }
        editor.putBoolean(KEY_MIGRATED_V2, true).apply()
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

    /** Deep think (Qwen3 reasoning) — default ON for quality. */
    var deepThink: Boolean
        get() = prefs.getBoolean(KEY_DEEP_THINK, true)
        set(value) = prefs.edit().putBoolean(KEY_DEEP_THINK, value).apply()
}
