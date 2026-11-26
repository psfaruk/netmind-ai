package com.netmindai.node

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.widget.FrameLayout
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import com.google.android.material.bottomnavigation.BottomNavigationView

class MainActivity : AppCompatActivity() {

    private lateinit var content: FrameLayout
    private lateinit var bottomNav: BottomNavigationView

    private lateinit var chat: ChatController
    private lateinit var tasks: TasksController
    private lateinit var node: NodeController

    private val sections = mutableListOf<SectionController>()

    /** SAF picker to import a user-supplied .gguf model file. */
    val importModelLauncher = registerForActivityResult(
        ActivityResultContracts.OpenDocument()
    ) { uri: Uri? ->
        uri?.let { if (::chat.isInitialized) chat.onModelUri(it) }
    }

    fun pickModelFile() {
        importModelLauncher.launch(arrayOf("*/*"))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_main)

        content = findViewById(R.id.content)
        bottomNav = findViewById(R.id.bottom_nav)

        // alpha.2 fix: edge-to-edge is enforced on modern Android; without
        // insets padding the status row sat under the status bar and the
        // input row under the nav bar / IME. Pad the root for all of them.
        val root = findViewById<android.view.View>(R.id.root)
        ViewCompat.setOnApplyWindowInsetsListener(root) { v, insets ->
            val bars = insets.getInsets(
                WindowInsetsCompat.Type.systemBars() or
                WindowInsetsCompat.Type.displayCutout()
            )
            val ime = insets.getInsets(WindowInsetsCompat.Type.ime())
            v.setPadding(bars.left, bars.top, bars.right, maxOf(bars.bottom, ime.bottom))
            WindowInsetsCompat.CONSUMED
        }

        chat = ChatController(this)
        tasks = TasksController(this)
        node = NodeController(this)

        sections += chat
        sections += tasks
        sections += node

        sections.forEach { section ->
            section.view.visibility = View.GONE
            content.addView(
                section.view,
                FrameLayout.LayoutParams(
                    FrameLayout.LayoutParams.MATCH_PARENT,
                    FrameLayout.LayoutParams.MATCH_PARENT
                )
            )
        }

        bottomNav.setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_chat -> showSection(chat)
                R.id.nav_tasks -> showSection(tasks)
                R.id.nav_node -> showSection(node)
            }
            true
        }

        showSection(chat)
    }

    private fun showSection(section: SectionController) {
        sections.forEach { it.view.visibility = View.GONE }
        section.view.visibility = View.VISIBLE
        section.onShown()
    }

    override fun onDestroy() {
        sections.forEach { it.onDestroy() }
        super.onDestroy()
    }
}
