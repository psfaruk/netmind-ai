package com.netmindai.node

import android.view.View
import android.widget.EditText
import android.widget.ImageButton
import android.widget.ProgressBar
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.arm.aichat.AiChat
import com.arm.aichat.InferenceEngine
import com.google.android.material.button.MaterialButton
import java.io.File
import java.util.UUID
import kotlin.concurrent.thread
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * Chat section: local, offline LLM chat backed by the llama.cpp binding.
 */
class ChatController(private val main: MainActivity) : SectionController(main) {

    override val view: View = inflate(R.layout.view_chat, null)

    private val statusText: TextView = view.findViewById(R.id.status_text)
    private val progressBar: ProgressBar = view.findViewById(R.id.progress)
    private val messagesRv: RecyclerView = view.findViewById(R.id.messages)
    private val inputEt: EditText = view.findViewById(R.id.input)
    private val sendBtn: ImageButton = view.findViewById(R.id.btn_send)
    private val stopBtn: MaterialButton = view.findViewById(R.id.btn_stop)
    private val prepareBtn: MaterialButton = view.findViewById(R.id.btn_prepare)
    private val unloadBtn: MaterialButton = view.findViewById(R.id.btn_unload)
    private val modelsBtn: MaterialButton = view.findViewById(R.id.btn_models)

    private val messages = mutableListOf<Message>()
    private val messageAdapter = MessageAdapter(messages)
    private val lastAssistantMsg = StringBuilder()

    private var engine: InferenceEngine? = null
    private var generationJob: Job? = null
    private var busy = false
    private var modelLoaded = false
    private var engineReady = false

    init {
        Prefs.init(main)

        messagesRv.layoutManager = LinearLayoutManager(main).apply { stackFromEnd = true }
        messagesRv.adapter = messageAdapter

        sendBtn.setOnClickListener { handleUserInput() }
        stopBtn.setOnClickListener {
            generationJob?.cancel()
            generationJob = null
            stopBtn.visibility = View.GONE
        }
        prepareBtn.setOnClickListener { prepareModel() }
        unloadBtn.setOnClickListener { unloadModel() }
        modelsBtn.setOnClickListener { showModelDialog() }

        addMessage("NETMIND runs fully offline on this device. "
            + "Download an open-weight model once (in-app), then chat without any "
            + "server or company API.", isUser = false)

        main.lifecycleScope.launch(Dispatchers.Default) {
            engine = AiChat.getInferenceEngine(main.applicationContext)
            withContext(Dispatchers.Main) { engineReady = true; renderButtons() }
        }
        renderStatus()
    }

    // ---------------------------------------------------------------- model

    private fun modelFile(): File? = ModelManager.currentFile(main)

    private fun prepareModel() {
        val file = modelFile()
        if (file == null) {
            toast("Select a model first (Models).")
            return
        }
        if (file.exists()) {
            loadModel(file)
        } else if (Prefs.modelIndex == ModelManager.IMPORTED_INDEX) {
            toast("Imported model file missing. Re-import it.")
        } else {
            downloadModel()
        }
    }

    private fun downloadModel() {
        if (busy) return
        val file = modelFile() ?: run { toast("No model selected."); return }
        busy = true
        renderStatus()
        val url = ModelManager.currentUrl()
        toast("Downloading model (${url.substringAfterLast('/')})…")

        thread {
            val ok = ModelManager.download(url, file) { read, total ->
                main.runOnUiThread {
                    progressBar.visibility = View.VISIBLE
                    if (total != null && total > 0) {
                        progressBar.isIndeterminate = false
                        progressBar.max = (total / 1024).toInt()
                        progressBar.progress = (read / 1024).toInt()
                        statusText.text = "Downloading… ${pct(read, total)}%"
                    } else {
                        progressBar.isIndeterminate = true
                        statusText.text = "Downloading… ${read / (1024 * 1024)} MB"
                    }
                }
            }
            main.runOnUiThread {
                progressBar.visibility = View.GONE
                busy = false
                if (ok) {
                    toast("Model downloaded. Loading…")
                    loadModel(file)
                } else {
                    toast("Download failed — check connection / URL.")
                    renderStatus()
                }
                renderButtons()
            }
        }
    }

    private fun loadModel(file: File) {
        if (busy) return
        val eng = engine
        if (eng == null || !engineReady) {
            toast("Engine is still starting, try again in a moment.")
            return
        }
        busy = true
        statusText.text = "Loading model…"
        renderButtons()
        main.lifecycleScope.launch(Dispatchers.IO) {
            try {
                eng.loadModel(file.path)
                eng.setSystemPrompt(SYSTEM_PROMPT)
                withContext(Dispatchers.Main) {
                    modelLoaded = true
                    AppState.modelLoaded = true
                    busy = false
                    renderStatus()
                    renderButtons()
                    inputEt.hint = "Ask NETMIND anything…"
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    modelLoaded = false
                    AppState.modelLoaded = false
                    busy = false
                    statusText.text = "Load failed: ${e.message ?: e.javaClass.simpleName}"
                    renderButtons()
                }
            }
        }
    }

    private fun unloadModel() {
        val eng = engine ?: return
        if (busy) return
        try {
            eng.cleanUp()
            modelLoaded = false
            AppState.modelLoaded = false
        } catch (_: Exception) {
        }
        renderStatus()
        renderButtons()
    }

    // ---------------------------------------------------------------- chat

    private fun handleUserInput() {
        val userMsg = inputEt.text.toString().trim()
        if (userMsg.isEmpty()) { toast("Input message is empty!"); return }
        val eng = engine
        if (eng == null || !modelLoaded) { toast("Model not ready — press Prepare model."); return }

        inputEt.setText("")
        inputEt.isEnabled = false
        sendBtn.isEnabled = false
        stopBtn.visibility = View.VISIBLE

        addMessage(userMsg, isUser = true)
        lastAssistantMsg.clear()
        addMessage("", isUser = false)

        generationJob = main.lifecycleScope.launch(Dispatchers.Default) {
            try {
                eng.sendUserPrompt(userMsg, PREDICT_LENGTH).collect { token ->
                    withContext(Dispatchers.Main) {
                        lastAssistantMsg.append(token)
                        updateLastMessage()
                    }
                }
            } finally {
                withContext(Dispatchers.Main) {
                    inputEt.isEnabled = true
                    sendBtn.isEnabled = true
                    stopBtn.visibility = View.GONE
                }
            }
        }
    }

    private fun updateLastMessage() {
        if (messages.isEmpty()) return
        val idx = messages.size - 1
        if (messages[idx].isUser) return
        messages[idx] = messages[idx].copy(content = cleanReply(lastAssistantMsg.toString()))
        messageAdapter.notifyItemChanged(idx)
    }

    /** Hide chain-of-thought blocks that small models sometimes emit. */
    private fun cleanReply(raw: String): String {
        var s = raw.replace(Regex("(?s)(<think>|<\\|think\\|>).*?(</think>|</\\|think\\|>)"), "")
        s = s.replace(Regex("(?s)(<think>|<\\|think\\|>).*$"), "")
        return s.trim()
    }

    private fun addMessage(content: String, isUser: Boolean) {
        messages.add(Message(UUID.randomUUID().toString(), content, isUser))
        messageAdapter.notifyItemInserted(messages.size - 1)
        messagesRv.scrollToPosition(messages.size - 1)
    }

    // ---------------------------------------------------------------- dialogs

    private fun showModelDialog() {
        val dialogView = inflate(R.layout.dialog_model, null)
        val spinnerItems = ModelManager.PRESETS.map { it.label } + listOf("Custom URL…")
        val spinner = dialogView.findViewById<android.widget.Spinner>(R.id.model_spinner)
        spinner.adapter = object : android.widget.ArrayAdapter<String>(
            main, android.R.layout.simple_spinner_item, spinnerItems
        ) {
            override fun getDropDownView(position: Int, convertView: View?, parent: ViewGroup) =
                super.getDropDownView(position, convertView, parent).also {
                    it.setPadding(24, it.paddingTop, 24, it.paddingBottom)
                }
        }
        val customEt: EditText = dialogView.findViewById(R.id.custom_url)
        customEt.setText(Prefs.customUrl.takeIf { it.isNotBlank() } ?: "https://…/.gguf")

        AlertDialog.Builder(main)
            .setTitle("Model (open weights only)")
            .setView(dialogView)
            .setPositiveButton("Apply") { _, _ ->
                val pos = spinner.selectedItemPosition
                if (pos < ModelManager.PRESETS.size) {
                    Prefs.modelIndex = pos
                } else {
                    val url = customEt.text.toString().trim()
                    if (!url.endsWith(".gguf")) {
                        toast("Custom URL should point to a .gguf file")
                        return@setPositiveButton
                    }
                    Prefs.modelIndex = ModelManager.CUSTOM_INDEX
                    Prefs.customUrl = url
                    Prefs.modelFile = ModelManager.fileNameFromUrl(url)
                }
                renderStatus()
            }
            .setNeutralButton("Import file…") { _, _ ->
                main.pickModelFile()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    /** Called by MainActivity when the user picked a local .gguf file. */
    fun onModelUri(uri: android.net.Uri) {
        thread {
            try {
                main.contentResolver.openInputStream(uri)?.use { input ->
                    val name = uri.lastPathSegment?.substringAfterLast('/')?.ifBlank { null }
                        ?: "imported-${System.currentTimeMillis()}.gguf"
                    val dest = File(ModelManager.modelsDir(main), name)
                    dest.outputStream().use { input.copyTo(it) }
                    Prefs.modelIndex = ModelManager.IMPORTED_INDEX
                    Prefs.modelFile = name
                    main.runOnUiThread {
                        toast("Imported $name. Press Prepare model to load.")
                        renderStatus()
                    }
                } ?: main.runOnUiThread { toast("Cannot open selected file") }
            } catch (e: Exception) {
                main.runOnUiThread { toast("Import failed: ${e.message}") }
            }
        }
    }

    // ---------------------------------------------------------------- ui state

    private fun pct(read: Long, total: Long): Int = (read * 100 / total).toInt()

    private fun renderStatus() {
        val file = modelFile()
        statusText.text = when {
            busy -> statusText.text
            modelLoaded -> "Model ready — 100% offline"
            file != null && file.exists() -> "Model present: ${file.name} (${ModelManager.sizeLabel(file)}) — press Prepare"
            else -> "No model downloaded yet"
        }
    }

    private fun renderButtons() {
        prepareBtn.isEnabled = !busy && engineReady && !modelLoaded
        unloadBtn.isEnabled = !busy && modelLoaded
        sendBtn.isEnabled = !busy && modelLoaded
    }

    private fun toast(msg: String) =
        android.widget.Toast.makeText(main, msg, android.widget.Toast.LENGTH_SHORT).show()

    override fun onShown() {
        renderStatus()
        renderButtons()
    }

    override fun onDestroy() {
        engine?.destroy()
    }

    companion object {
        private const val PREDICT_LENGTH = 512

        private const val SYSTEM_PROMPT =
            "You are NETMIND, a helpful offline assistant running entirely on the " +
            "user's phone as part of a volunteer distributed AI network. " +
            "Reply in the same language the user writes in (Bangla or English). " +
            "Be concise and practical unless the user asks for detail."
    }
}
