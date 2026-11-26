package com.netmindai.node

import android.annotation.SuppressLint
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView

data class Message(val id: String, val content: String, val isUser: Boolean)

/**
 * Simple chat transcript adapter with user/assistant bubbles.
 */
class MessageAdapter(private val messages: MutableList<Message>) :
    RecyclerView.Adapter<MessageAdapter.ViewHolder>() {

    companion object {
        private const val TYPE_USER = 1
        private const val TYPE_ASSISTANT = 0
    }

    class ViewHolder(val root: View, val text: TextView) : RecyclerView.ViewHolder(root)

    override fun getItemViewType(position: Int): Int =
        if (messages[position].isUser) TYPE_USER else TYPE_ASSISTANT

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val res = if (viewType == TYPE_USER) R.layout.item_message_user
                  else R.layout.item_message_assistant
        val root = LayoutInflater.from(parent.context).inflate(res, parent, false)
        return ViewHolder(root, root.findViewById(R.id.message_text))
    }

    @SuppressLint("NotifyDataSetChanged")
    fun replaceAll(new: List<Message>) {
        messages.clear()
        messages.addAll(new)
        notifyDataSetChanged()
    }

    override fun getItemCount(): Int = messages.size

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.text.text = messages[position].content
    }
}
