package com.netmindai.node

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

data class Task(val id: Long, val title: String, val done: Boolean)

/**
 * Tiny local SQLite store for the task manager. 100% offline.
 */
class TaskDb(context: Context) : SQLiteOpenHelper(
    context.applicationContext, "netmind_tasks.db", null, 1
) {

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL(
            "CREATE TABLE tasks (" +
                "id INTEGER PRIMARY KEY AUTOINCREMENT, " +
                "title TEXT NOT NULL, " +
                "done INTEGER NOT NULL DEFAULT 0, " +
                "created_at INTEGER NOT NULL)"
        )
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        // v1 only; future migrations go here
    }

    fun list(): MutableList<Task> {
        val out = mutableListOf<Task>()
        readableDatabase.query(
            "tasks", null, null, null, null, null, "created_at DESC"
        ).use { c ->
            while (c.moveToNext()) {
                out.add(
                    Task(
                        c.getLong(0),
                        c.getString(1),
                        c.getInt(2) != 0,
                    )
                )
            }
        }
        return out
    }

    fun add(title: String) {
        writableDatabase.insert(
            "tasks", null, ContentValues().apply {
                put("title", title)
                put("done", 0)
                put("created_at", System.currentTimeMillis())
            }
        )
    }

    fun toggle(id: Long, done: Boolean) {
        writableDatabase.execSQL(
            "UPDATE tasks SET done = ? WHERE id = ?",
            arrayOf(if (done) 1 else 0, id)
        )
    }

    fun delete(id: Long) {
        writableDatabase.execSQL("DELETE FROM tasks WHERE id = ?", arrayOf(id))
    }
}
