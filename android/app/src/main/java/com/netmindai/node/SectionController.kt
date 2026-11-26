package com.netmindai.node

import android.view.View
import android.view.ViewGroup
import androidx.appcompat.app.AppCompatActivity

/**
 * Base class for the three main sections of NETMIND Node (Chat / Tasks / Node).
 * Each controller inflates and manages its own view subtree.
 */
abstract class SectionController(protected val activity: AppCompatActivity) {

    abstract val view: View

    /** Called every time the section becomes visible via bottom navigation. */
    open fun onShown() {}

    open fun onDestroy() {}

    protected fun inflate(layoutRes: Int, root: ViewGroup?): View =
        activity.layoutInflater.inflate(layoutRes, root, false)
}
