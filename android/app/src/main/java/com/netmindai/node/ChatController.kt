package com.netmindai.node

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.view.View
import android.view.ViewGroup
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
import java.io.File
import java.util.Calendar
import kotlin.concurrent.thread
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull

/**
 * Chat section — Claude-style offline chat.
 *
 * v0.2.0 changes (from alpha.2):
 *  - "Deep think" ON by default: Qwen3 reasons inside  ... </think>
 *    while a live "Thinking · N tokens" row keeps the user informed (Claude's
 *    extended-thinking UX) instead of a blank bubble.
 *  - Live streaming answer with a text cursor, meta stats per message
 *    (thought/answered tokens, tok/s), copy action.
 *  - Multilingual + thorough system prompt: mirror the user's language
 *    (Bangla, English, Hindi, Arabic, Chinese...), structured full answers.
 *  - PREDICT_LENGTH 512 → 1024 for longer, deeper replies.
 *  - Model auto-load after engine init / download / import — no "Prepare"
 *    button; the status chip itself drives download/load.
 */
class ChatController(private val main: MainActivity) : SectionController(main) {

    override val view: View = inflate(R.layout.view_chat, null)

    private val statusText: TextView = view.findViewById(R.id.status_text)
    private val statusDot: View = view.findViewById(R.id.status_dot)
    private val progressBar: ProgressBar = view.findViewById(R.id.progress)
    private val messagesRv: RecyclerView = view.findViewById(R.id.messages)
    private val emptyState: View = view.findViewById(R.id.empty_state)
    private val greeting: TextView = view.findViewById(R.id.greeting)
    private val inputEt: EditText = view.findViewById(R.id.input)
    private val sendBtn: ImageButton = view.findViewById(R.id.btn_send)
    private val deepChip: TextView = view.findViewById(R.id.chip_deep)

    private val messages = mutableListOf<Message>()
    private val messageAdapter = MessageAdapter(messages, ::copyToClipboard)

    // engine + lifecycle state
    private var engine: InferenceEngine? = null
    private var generationJob: Job? = null
    private var busy = false
    private var modelLoaded = false
    private var engineReady = false
    private var generating = false
    private var generationStartMs = 0L
    private var stoppedByUser = false

    // live generation state
    private val rawBuffer = StringBuilder()
    private var tokenCount = 0
    private var thinkAt = 0        // tokens consumed before the answer began

    init {
        Prefs.init(main)

        setupGreeting()
        messagesRv.layoutManager = LinearLayoutManager(main).apply { stackFromEnd = true }
        messagesRv.adapter = messageAdapter

        sendBtn.setOnClickListener {
            if (generating) {
                stoppedByUser = true
                generationJob?.cancel()
                generationJob = null
            } else {
                handleUserInput()
            }
        }
        deepChip.setOnClickListener { toggleDeepThink() }
        view.findViewById<View>(R.id.btn_models).setOnClickListener { showModelDialog() }
        view.findViewById<View>(R.id.btn_clear).setOnClickListener { confirmClearChat() }
        statusText.setOnClickListener { onStatusChipTap() }

        SUGGESTIONS.forEach { (id, prompt) ->
            view.findViewById<View>(id).setOnClickListener {
                if (!modelLoaded) {
                    toast("Pick & download a model first (layers icon above)")
                    return@setOnClickListener
                }
                inputEt.setText(prompt)
                handleUserInput()
            }
        }

        renderDeepChip()
        updateEmptyState()

        main.lifecycleScope.launch(Dispatchers.Default) {
            val eng = try {
                AiChat.getInferenceEngine(main.applicationContext)
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    chip("Engine failed to start: ${e.message ?: "native library error"}")
                }
                return@launch
            }
            engine = eng
            withContext(Dispatchers.Main) {
                engineReady = true
                renderStatus()
                maybeAutoStart()
            }
            // Observe engine state: reflect readiness and load errors in the UI.
            eng.state.collect { st ->
                withContext(Dispatchers.Main) {
                    if (st is InferenceEngine.State.Error) {
                        chip("Engine error: ${st.exception.message ?: "unknown"}")
                        engineReady = false
                    }
                    renderStatus()
                }
            }
        }
        renderStatus()
    }

    // ---------------------------------------------------------------- welcome

    private fun setupGreeting() {
        val h = Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
        greeting.text = when {
            h < 5 -> main.getString(R.string.greeting_default)
            h < 12 -> main.getString(R.string.greeting_morning)
            h < 17 -> main.getString(R.string.greeting_afternoon)
            else -> main.getString(R.string.greeting_evening)
        }
    }

    private fun updateEmptyState() {
        emptyState.visibility =
            if (messages.isEmpty() && !generating) View.VISIBLE else View.GONE
    }

    // ---------------------------------------------------------------- model

    private fun modelFile(): File? = ModelManager.currentFile(main)

    /** No explicit "Prepare" button anymore: the chip loads/downloads on tap. */
    private fun onStatusChipTap() {
        if (busy || generating || modelLoaded) return
        val file = modelFile()
        when {
            file != null && file.exists() -> loadModel(file)
            file != null -> downloadModel()
            else -> showModelDialog()
        }
    }

    private fun maybeAutoStart() {
        if (busy || generating || modelLoaded) return
        val file = modelFile() ?: return
        if (file.exists()) loadModel(file)
    }

    private fun downloadModel() {
        if (busy) return
        val file = modelFile() ?: run { toast("No model selected."); return }
        busy = true
        chip("Downloading ${file.name}…")
        val url = ModelManager.currentUrl()

        thread {
            val ok = ModelManager.download(url, file) { read, total ->
                main.runOnUiThread {
                    progressBar.visibility = View.VISIBLE
                    if (total != null && total > 0) {
                        progressBar.isIndeterminate = false
                        progressBar.max = (total / 1024).toInt()
                        progressBar.progress = (read / 1024).toInt()
                        chip("Downloading… ${pct(read, total)}% — one time only")
                    } else {
                        progressBar.isIndeterminate = true
                        chip("Downloading… ${read / (1024 * 1024)} MB")
                    }
                }
            }
            main.runOnUiThread {
                progressBar.visibility = View.GONE
                busy = false
                if (ok) {
                    chip("Downloaded — loading model…")
                    loadModel(file)
                } else {
                    chip("Download failed — tap to retry (check connection / URL)")
                    renderStatus()
                }
            }
        }
    }

    /** Wait (bounded) until the native engine finishes initializing. */
    private suspend fun awaitEngineInitialized(eng: InferenceEngine) {
        val st = withTimeoutOrNull(30_000) {
            eng.state.first {
                it is InferenceEngine.State.Initialized ||
                    it is InferenceEngine.State.ModelReady ||
                    it is InferenceEngine.State.Error
            }
        } ?: throw IllegalStateException("Engine init timed out (30s)")
        if (st is InferenceEngine.State.Error) throw st.exception
    }

    private fun loadModel(file: File) {
        if (busy) return
        val eng = engine
        if (eng == null) {
            chip("Engine is still starting — tap again in a moment")
            return
        }
        busy = true
        chip("Loading ${file.name}…")
        main.lifecycleScope.launch(Dispatchers.IO) {
            try {
                awaitEngineInitialized(eng)
                eng.loadModel(file.path)
                eng.setSystemPrompt(SYSTEM_PROMPT)
                withContext(Dispatchers.Main) {
                    modelLoaded = true
                    AppState.modelLoaded = true
                    busy = false
                    renderStatus()
                    inputEt.hint = "Message NetMind…"
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    modelLoaded = false
                    AppState.modelLoaded = false
                    busy = false
                    chip("Load failed: ${e.message ?: e.javaClass.simpleName}")
                }
            }
        }
    }

    // ---------------------------------------------------------------- chat

    /**
     * Qwen3 + Deep think OFF → append the documented "/no_think" switch for
     * instant replies. Deep think ON → let the model reason (quality mode).
     */
    private fun transformPrompt(userMsg: String): String {
        if (Prefs.deepThink) return userMsg
        val name = modelFile()?.name?.lowercase() ?: ""
        val isQwen3 = name.contains("qwen3") || name.contains("qwen_qwen3")
        return if (isQwen3 && !userMsg.contains("/no_think", ignoreCase = true)) {
            "$userMsg /no_think"
        } else {
            userMsg
        }
    }

    private fun handleUserInput() {
        val userMsg = inputEt.text.toString().trim()
        if (userMsg.isEmpty()) {
            toast("Type a message first")
            return
        }
        val eng = engine
        if (eng == null || !modelLoaded) {
            toast("Model not ready — see the status chip above")
            renderStatus()
            return
        }
        if (busy || generating) return

        inputEt.setText("")
        stoppedByUser = false
        generating = true
        busy = true
        setGeneratingUi(true)

        addMessage(Message(role = Role.USER, content = userMsg))
        addMessage(Message(role = Role.THINKING, content = ""))
        updateEmptyState()

        rawBuffer.setLength(0)
        tokenCount = 0
        thinkAt = 0
        generationStartMs = System.currentTimeMillis()

        val promptOut = transformPrompt(userMsg)
        generationJob = main.lifecycleScope.launch(Dispatchers.Default) {
            try {
                eng.sendUserPrompt(promptOut, PREDICT_LENGTH).collect { tok ->
                    withContext(Dispatchers.Main) { onToken(tok) }
                }
            } catch (e: kotlinx.coroutines.CancellationException) {
                // user pressed Stop — finalize happens in the finally block
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    toast("Generation failed: ${e.message ?: e.javaClass.simpleName}")
                }
            } finally {
                withContext(Dispatchers.Main) { finishGeneration() }
            }
        }
        renderStatus()
    }

    /**
     * Live split of the raw stream into thinking vs. answer:
     *  - inside the (unclosed) think block -> update the "Thinking" row
     *  - after the closing think tag -> stream the answer with a cursor
     *  - no think tags at all → stream directly (instant mode / Qwen2.5)
     */
    private fun onToken(tok: String) {
        if (tok.isEmpty()) return
        rawBuffer.append(tok)
        tokenCount++
        if (messages.isEmpty()) return
        val idx = messages.size - 1
        val raw = rawBuffer.toString()
        val closeIdx = raw.indexOf(THINK_CLOSE)
        when {
            closeIdx >= 0 -> {
                val answer = raw.substring(closeIdx + THINK_CLOSE.length).trim()
                if (answer.isNotEmpty()) streamAnswer(answer, tokenCount)
            }
            raw.contains(THINK_OPEN) || raw.contains("<|think|>") -> {
                messages[idx] = messages[idx].copy(content = "$tokenCount tokens")
                messageAdapter.notifyItemChanged(idx)
                messagesRv.scrollToPosition(idx)
            }
            else -> streamAnswer(raw.trim(), 0)
        }
        renderStatus()
    }

    private fun streamAnswer(answer: String, tokensBeforeAnswer: Int) {
        if (messages.isEmpty()) return
        val idx = messages.size - 1
        if (messages[idx].role != Role.ASSISTANT) {
            thinkAt = tokensBeforeAnswer
            messages[idx] = messages[idx].copy(role = Role.ASSISTANT)
        }
        messages[idx] = messages[idx].copy(content = answer + CURSOR)
        messageAdapter.notifyItemChanged(idx)
        messagesRv.scrollToPosition(idx)
    }

    private fun finishGeneration() {
        generating = false
        busy = false
        setGeneratingUi(false)

        if (messages.isNotEmpty()) {
            val idx = messages.size - 1
            val raw = rawBuffer.toString()
            when {
                messages[idx].role == Role.ASSISTANT -> {
                    val clean = extractAnswer(raw)
                    if (clean.isBlank()) {
                        messages.removeAt(idx)
                        messageAdapter.notifyItemRemoved(idx)
                        toast("Empty reply — try again")
                    } else {
                        messages[idx] = messages[idx].copy(content = clean, meta = statsMeta())
                        messageAdapter.notifyItemChanged(idx)
                    }
                }
                stoppedByUser -> {
                    messages.removeAt(idx)
                    messageAdapter.notifyItemRemoved(idx)
                    toast("Stopped")
                }
                else -> { // hit the length limit while still thinking
                    messages.removeAt(idx)
                    messageAdapter.notifyItemRemoved(idx)
                    chip("Ran out of length while thinking — try Deep think off for this one")
                }
            }
        }
        stoppedByUser = false
        updateEmptyState()
        renderStatus()
    }

    /** Final visible answer from the raw generation buffer. */
    private fun extractAnswer(raw: String): String {
        val closeIdx = raw.indexOf(THINK_CLOSE)
        val s = if (closeIdx >= 0) raw.substring(closeIdx + THINK_CLOSE.length) else raw
        return s.trim()
    }

    private fun statsMeta(): String {
        val secs = (System.currentTimeMillis() - generationStartMs) / 1000.0
        val rate = if (secs > 0.5) tokenCount / secs else 0.0
        val answerTokens = (tokenCount - thinkAt).coerceAtLeast(0)
        val parts = mutableListOf<String>()
        if (thinkAt > 0) parts.add("thought $thinkAt tok")
        parts.add("$answerTokens tok")
        parts.add("%.1f tok/s".format(rate))
        parts.add("%.0fs".format(secs))
        if (stoppedByUser) parts.add("stopped")
        return parts.joinToString(" · ")
    }

    private fun addMessage(m: Message) {
        messages.add(m)
        messageAdapter.notifyItemInserted(messages.size - 1)
        messagesRv.scrollToPosition(messages.size - 1)
    }

    private fun setGeneratingUi(on: Boolean) {
        sendBtn.setImageResource(if (on) R.drawable.ic_stop_square else R.drawable.ic_arrow_up)
        inputEt.isEnabled = !on
    }

    // ---------------------------------------------------------------- deep think

    private fun toggleDeepThink() {
        if (busy || generating) return
        Prefs.deepThink = !Prefs.deepThink
        renderDeepChip()
        toast(
            if (Prefs.deepThink) "Deep think on — richer answers, a bit slower"
            else "Deep think off — instant replies"
        )
    }

    private fun renderDeepChip() {
        val on = Prefs.deepThink
        deepChip.text = if (on) main.getString(R.string.deep_think_on) else main.getString(R.string.deep_think_off)
        deepChip.setBackgroundResource(if (on) R.drawable.bg_chip_deep_on else R.drawable.bg_chip)
        deepChip.alpha = if (modelLoaded || engineReady) 1f else 0.6f
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
                onStatusChipTap()   // auto-load or auto-download right away
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
                        toast("Imported $name — loading…")
                        renderStatus()
                        loadModel(dest)
                    }
                } ?: main.runOnUiThread { toast("Cannot open selected file") }
            } catch (e: Exception) {
                main.runOnUiThread { toast("Import failed: ${e.message}") }
            }
        }
    }

    private fun confirmClearChat() {
        if (messages.isEmpty()) {
            toast("Nothing to clear")
            return
        }
        AlertDialog.Builder(main)
            .setTitle(R.string.confirm_clear_title)
            .setMessage(R.string.confirm_clear_msg)
            .setPositiveButton("Clear") { _, _ -> clearConversation() }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun clearConversation() {
        messages.clear()
        messageAdapter.replaceAll(emptyList())
        updateEmptyState()
        val eng = engine
        if (eng != null && modelLoaded) {
            // Re-sending the system prompt resets the engine's conversation
            // history (processSystemPrompt clears long-term state in JNI).
            main.lifecycleScope.launch(Dispatchers.IO) {
                try {
                    eng.setSystemPrompt(SYSTEM_PROMPT)
                } catch (_: Exception) {
                }
            }
        }
        toast("New conversation")
    }

    // ---------------------------------------------------------------- ui state

    private fun pct(read: Long, total: Long): Int = (read * 100 / total).toInt()

    private fun chip(text: String) {
        statusText.visibility = View.VISIBLE
        statusText.text = text
    }

    private fun rate(): Double {
        val secs = (System.currentTimeMillis() - generationStartMs) / 1000.0
        return if (secs > 0.5) tokenCount / secs else 0.0
    }

    private fun renderStatus() {
        val file = modelFile()
        statusDot.alpha = if (modelLoaded) 1f else 0.35f
        when {
            generating -> chip("Generating · $tokenCount tok · %.1f tok/s".format(rate()))
            busy -> { /* chip text already set by download/load code */ }
            modelLoaded -> statusText.visibility = View.GONE
            file != null && file.exists() ->
                chip("Tap to load ${file.name} · ${ModelManager.sizeLabel(file)}")
            file != null -> chip("Tap to download ${file.name} · one time only")
            else -> chip("No model yet — tap to get started")
        }
        statusText.isClickable = !busy && !generating && !modelLoaded
    }

    private fun copyToClipboard(text: String) {
        val clean = text.trim()
        if (clean.isEmpty()) return
        val cm = main.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        cm.setPrimaryClip(ClipData.newPlainText("NetMind", clean))
        toast("Copied")
    }

    private fun toast(msg: String) =
        android.widget.Toast.makeText(main, msg, android.widget.Toast.LENGTH_SHORT).show()

    override fun onShown() {
        renderStatus()
    }

    override fun onDestroy() {
        engine?.destroy()
    }

    companion object {
        private const val PREDICT_LENGTH = 1024

        private const val THINK_OPEN = "<think>"
        private const val THINK_CLOSE = "</think>"

        private const val CURSOR = " ▍"

        /** Prompt presets shown on the welcome screen. */
        private val SUGGESTIONS: List<Pair<Int, String>> = listOf(
            R.id.sg_explain to
                "Explain how transformer models work — step by step, with a simple worked example.",
            R.id.sg_bangla to
                "AI কী? সহজ বাংলায় বিস্তারিত ব্যাখ্যা করো — ধাপে ধাপে, উদাহরণসহ।",
            R.id.sg_translate to
                "Translate into natural, flowing Bangla: \"The best way to learn is to teach.\" Then briefly explain your word choices.",
            R.id.sg_code to
                "Write a Python function that checks whether a number is prime, with comments explaining each step.",
        )

        private const val SYSTEM_PROMPT =
            "You are NetMind — a thoughtful, thorough AI assistant that runs entirely offline " +
                "on the user's own phone (open-weight Qwen3 on llama.cpp, part of the volunteer " +
                "NETMIND network; no cloud, no tracking).\n" +
                "Answering rules:\n" +
                "1. LANGUAGE: Always reply in the SAME language the user writes in — বাংলা, " +
                "English, हिन्दी, العربية, 中文 or any other. If the user writes Bangla, reply in " +
                "Bangla. Never switch to English unless the user asked in English.\n" +
                "2. DEPTH: Write complete, well-structured answers — short paragraphs, headings " +
                "or bullet lists where helpful, concrete examples. For code, give working code " +
                "with short comments. Do not end after one bare sentence unless the question " +
                "itself is tiny.\n" +
                "3. THINKING: Work through the problem carefully before answering; keep the " +
                "final answer clean and self-contained.\n" +
                "4. HONESTY: You are a small 0.6B on-device model, not a cloud giant. If a task " +
                "is beyond you (long essays, precise recent facts, hard math), say so briefly — " +
                "then still give your best attempt."
    }
}
