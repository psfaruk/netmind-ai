package com.netmindai.node

import android.app.ActivityManager
import android.os.Build
import android.os.BatteryManager
import android.os.StatFs
import android.view.View
import android.widget.TextView
import com.google.android.material.button.MaterialButton

/**
 * Node section: this device's profile as a NETMIND volunteer node (offline alpha).
 */
class NodeController(private val main: MainActivity) : SectionController(main) {

    override val view: View = inflate(R.layout.view_node, null)

    private val infoText: TextView = view.findViewById(R.id.node_info)
    private val refreshBtn: MaterialButton = view.findViewById(R.id.btn_refresh_node)

    init {
        refreshBtn.setOnClickListener { render() }
        render()
    }

    private fun ram(): Pair<String, String> {
        val am = main.getSystemService(ActivityManager::class.java)
        val mi = ActivityManager.MemoryInfo()
        am?.getMemoryInfo(mi)
        val total = mi.totalMem / (1024L * 1024)
        val avail = mi.availMem / (1024L * 1024)
        return "$total MB" to "$avail MB free"
    }

    private fun battery(): String {
        val bm = main.getSystemService(android.content.Context.BATTERY_SERVICE) as? BatteryManager
        val pct = bm?.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY) ?: -1
        return if (pct in 0..100) "$pct%" else "n/a"
    }

    private fun storage(): String {
        val stat = StatFs(main.filesDir.path)
        val free = stat.availableBytes / (1024L * 1024)
        return "$free MB free (app storage)"
    }

    private fun versionName(): String = try {
        val pi = main.packageManager.getPackageInfo(main.packageName, 0)
        pi.versionName ?: "?"
    } catch (_: Exception) {
        "?"
    }

    private fun render() {
        val (ramTotal, ramAvail) = ram()
        val modelFile = ModelManager.currentFile(main)
        val modelInfo = if (modelFile != null && modelFile.exists()) {
            "${modelFile.name} (${ModelManager.sizeLabel(modelFile)}) — ${if (AppState.modelLoaded) "loaded" else "on disk"}"
        } else {
            "no model downloaded yet"
        }

        infoText.text = buildString {
            appendLine("NETMIND volunteer node — offline alpha")
            appendLine()
            appendLine("Device        : ${Build.MANUFACTURER} ${Build.MODEL}")
            appendLine("Android       : ${Build.VERSION.RELEASE} (SDK ${Build.VERSION.SDK_INT})")
            appendLine("CPU cores     : ${Runtime.getRuntime().availableProcessors()}")
            appendLine("RAM           : $ramTotal ($ramAvail)")
            appendLine("Battery       : ${battery()}")
            appendLine("Storage       : ${storage()}")
            appendLine()
            appendLine("App           : NETMIND Node v${versionName()}")
            appendLine("Engine        : llama.cpp (on-device, open source)")
            appendLine("LLM           : $modelInfo")
            appendLine()
            appendLine("Policy: no vendor API, no telemetry, no cloud model.")
            appendLine("All inference runs locally on this device.")
        }
    }

    override fun onShown() {
        render()
    }
}
