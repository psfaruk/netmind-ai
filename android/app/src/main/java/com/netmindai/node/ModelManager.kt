package com.netmindai.node

import android.content.Context
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL

/**
 * Model catalogue + downloader for open-weight GGUF files.
 *
 * NETMIND policy: only open-weight model files (Apache-2.0 etc.) are offered.
 * Files are downloaded once, stored locally, and inference happens 100%
 * on-device with llama.cpp. No vendor inference API is ever contacted.
 */
object ModelManager {

    data class Preset(
        val label: String,
        val url: String,
        val file: String,
        val size: String,
        val license: String,
    )

    val PRESETS = listOf(
        Preset(
            label = "Gemma 3 4B — বাংলা / 140+ languages (default)",
            url = "https://huggingface.co/unsloth/gemma-3-4b-it-GGUF/resolve/main/gemma-3-4b-it-Q4_K_M.gguf",
            file = "gemma-3-4b-it-Q4_K_M.gguf",
            size = "~2.4 GB download · ~4 GB RAM while running",
            license = "Gemma open weights (runs 100% on this device)",
        ),
        Preset(
            label = "Qwen3-0.6B — light · Deep Think · English/中文",
            url = "https://huggingface.co/bartowski/Qwen_Qwen3-0.6B-GGUF/resolve/main/Qwen_Qwen3-0.6B-Q4_K_M.gguf",
            file = "Qwen3-0.6B-Q4_K_M.gguf",
            size = "~484 MB download · ~2 GB RAM",
            license = "Apache-2.0 (Qwen3 open weights)",
        ),
    )

    const val CUSTOM_INDEX = -1
    const val IMPORTED_INDEX = -2

    fun modelsDir(context: Context): File =
        File(context.filesDir, "models").also { if (!it.exists()) it.mkdirs() }

    /**
     * Resolve the currently selected model file (may not exist yet).
     */
    fun currentFile(context: Context): File? {
        return when (Prefs.modelIndex) {
            CUSTOM_INDEX -> {
                val name = Prefs.modelFile.ifBlank { fileNameFromUrl(Prefs.customUrl) }
                if (name.isBlank()) null else File(modelsDir(context), name)
            }
            IMPORTED_INDEX -> {
                val name = Prefs.modelFile
                if (name.isBlank()) null else File(modelsDir(context), name)
            }
            else -> {
                val idx = Prefs.modelIndex
                val preset = PRESETS.getOrNull(idx) ?: PRESETS.first()
                File(modelsDir(context), preset.file)
            }
        }
    }

    fun currentUrl(): String = when (Prefs.modelIndex) {
        CUSTOM_INDEX -> Prefs.customUrl
        else -> PRESETS.getOrNull(Prefs.modelIndex)?.url ?: PRESETS.first().url
    }

    fun fileNameFromUrl(url: String): String =
        url.substringAfterLast('/').substringBefore('?').ifBlank { "model.gguf" }

    /**
     * Blocking download of [url] into [dest]; invoke [onProgress] with bytes
     * read and total (if known). Returns true on success.
     */
    fun download(url: String, dest: File, onProgress: (Long, Long?) -> Unit): Boolean {
        val part = File(dest.parentFile, dest.name + ".part")
        try {
            val conn = URL(url).openConnection() as HttpURLConnection
            conn.instanceFollowRedirects = true
            conn.connectTimeout = 30_000
            conn.readTimeout = 30_000
            conn.setRequestProperty("User-Agent", "NETMIND-Node/0.1 (Android)")
            val code = conn.responseCode
            if (code != HttpURLConnection.HTTP_OK) {
                conn.disconnect()
                return false
            }
            val total: Long? = conn.contentLengthLong.takeIf { it > 0 }
            dest.parentFile?.mkdirs()
            var read = 0L
            val buf = ByteArray(64 * 1024)
            conn.inputStream.use { input ->
                FileOutputStream(part).use { out ->
                    while (true) {
                        val n = input.read(buf)
                        if (n < 0) break
                        out.write(buf, 0, n)
                        read += n
                        onProgress(read, total)
                    }
                }
            }
            conn.disconnect()
            if (read == 0L) return false
            if (dest.exists()) dest.delete()
            return part.renameTo(dest)
        } catch (e: Exception) {
            e.printStackTrace()
            part.delete()
            return false
        }
    }

    /** Human-readable size of the local model file, if present. */
    fun sizeLabel(file: File?): String {
        if (file == null || !file.exists()) return "not downloaded"
        val mb = file.length() / (1024.0 * 1024.0)
        return String.format("%.0f MB", mb)
    }
}
