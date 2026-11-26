package com.netmindai.node

import android.graphics.Paint
import android.graphics.Typeface
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.ListView
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import com.google.android.material.button.MaterialButton

/**
 * Task section: a fully offline local task manager (SQLite).
 */
class TasksController(private val main: MainActivity) : SectionController(main) {

    override val view: View = inflate(R.layout.view_tasks, null)

    private val taskInput: EditText = view.findViewById(R.id.task_input)
    private val addBtn: MaterialButton = view.findViewById(R.id.btn_add_task)
    private val list: ListView = view.findViewById(R.id.tasks_list)
    private val emptyHint: TextView = view.findViewById(R.id.empty_hint)

    private val db = TaskDb(main)
    private var tasks = mutableListOf<Task>()

    private val adapter = object : android.widget.ArrayAdapter<Task>(
        main, R.layout.item_task, R.id.task_text, tasks
    ) {
        override fun getView(position: Int, convertView: View?, parent: ViewGroup): View {
            val v = super.getView(position, convertView, parent)
            val tv: TextView = v.findViewById(R.id.task_text)
            val cb: android.widget.CheckBox = v.findViewById(R.id.task_check)
            val t = tasks[position]
            cb.isChecked = t.done
            tv.text = t.title
            if (t.done) {
                tv.paintFlags = tv.paintFlags or Paint.STRIKE_THRU_TEXT_FLAG
                tv.alpha = 0.45f
            } else {
                tv.paintFlags = tv.paintFlags and Paint.STRIKE_THRU_TEXT_FLAG.inv()
                tv.alpha = 1f
            }
            return v
        }
    }

    init {
        list.adapter = adapter
        addBtn.setOnClickListener {
            val title = taskInput.text.toString().trim()
            if (title.isEmpty()) {
                toast("Task title is empty")
            } else {
                db.add(title)
                taskInput.setText("")
                refresh()
            }
        }
        list.setOnItemClickListener { _, _, position, _ ->
            val t = tasks[position]
            db.toggle(t.id, !t.done)
            refresh()
        }
        list.setOnItemLongClickListener { _, _, position, _ ->
            AlertDialog.Builder(main)
                .setTitle("Delete task?")
                .setMessage(tasks[position].title)
                .setPositiveButton("Delete") { _, _ ->
                    db.delete(tasks[position].id)
                    refresh()
                }
                .setNegativeButton("Cancel", null)
                .show()
            true
        }
        refresh()
    }

    private fun refresh() {
        tasks = db.list()
        adapter.clear()
        adapter.addAll(tasks)
        adapter.notifyDataSetChanged()
        emptyHint.visibility = if (tasks.isEmpty()) View.VISIBLE else View.GONE
    }

    private fun toast(msg: String) =
        android.widget.Toast.makeText(main, msg, android.widget.Toast.LENGTH_SHORT).show()
}
