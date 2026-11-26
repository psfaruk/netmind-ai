package com.netmindai.node

import android.annotation.SuppressLint
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageButton
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import java.util.UUID

enum class Role { USER, ASSISTANT, THINKING }

data class Message(
    val id: String = UUID.randomUUID().toString(),
    val role: Role,
    val content: String,
    val meta: String = "",
)

/**
 * Chat transcript adapter — Claude-style: user bubbles on the right, plain
 * assistant text on the left with an avatar, a stats/meta row and a copy
 * action, plus a live "Thinking…" row while the model reasons.
 */
class MessageAdapter(
    private val messages: MutableList<Message>,
    private val onCopy: (String) -> Unit,
) : RecyclerView.Adapter<RecyclerView.ViewHolder>() {

    companion object {
        private const val TYPE_ASSISTANT = 0
        private const val TYPE_THINKING = 1
        private const val TYPE_USER = 2
    }

    class UserVh(val root: View, val text: TextView) : RecyclerView.ViewHolder(root)

    class AssistantVh(
        val root: View,
        val text: TextView,
        val metaRow: View,
        val metaText: TextView,
        val copyBtn: ImageButton,
    ) : RecyclerView.ViewHolder(root)

    class ThinkingVh(val root: View, val count: TextView) : RecyclerView.ViewHolder(root)

    override fun getItemViewType(position: Int): Int = when (messages[position].role) {
        Role.USER -> TYPE_USER
        Role.ASSISTANT -> TYPE_ASSISTANT
        Role.THINKING -> TYPE_THINKING
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): RecyclerView.ViewHolder {
        val inf = LayoutInflater.from(parent.context)
        return when (viewType) {
            TYPE_USER ->
                inf.inflate(R.layout.item_message_user, parent, false).let {
                    UserVh(it, it.findViewById(R.id.message_text))
                }
            TYPE_THINKING ->
                inf.inflate(R.layout.item_thinking, parent, false).let {
                    ThinkingVh(it, it.findViewById(R.id.thinking_count))
                }
            else ->
                inf.inflate(R.layout.item_message_assistant, parent, false).let {
                    AssistantVh(
                        it,
                        it.findViewById(R.id.message_text),
                        it.findViewById(R.id.meta_row),
                        it.findViewById(R.id.meta_text),
                        it.findViewById(R.id.btn_copy),
                    )
                }
        }
    }

    override fun getItemCount(): Int = messages.size

    override fun onBindViewHolder(holder: RecyclerView.ViewHolder, position: Int) {
        val m = messages[position]
        when (holder) {
            is UserVh -> holder.text.text = m.content
            is ThinkingVh -> holder.count.text = m.content
            is AssistantVh -> {
                holder.text.text = m.content
                holder.metaText.text = m.meta
                holder.metaRow.visibility = if (m.meta.isBlank()) View.GONE else View.VISIBLE
                holder.copyBtn.setOnClickListener { onCopy(m.content) }
            }
        }
    }

    @SuppressLint("NotifyDataSetChanged")
    fun replaceAll(newItems: List<Message>) {
        val oldSize = messages.size
        messages.clear()
        messages.addAll(newItems)
        if (oldSize > 0) notifyItemRangeRemoved(0, oldSize)
        if (newItems.isNotEmpty()) notifyItemRangeInserted(0, newItems.size)
    }
}
