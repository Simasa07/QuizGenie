package com.ailivequiz.app.data.network

/**
 * Holds the login token for the current session.
 *
 * Kept in memory only, on purpose: nothing is written to disk, so there is
 * no stored credential for another app or person to find. The trade-off is
 * that closing the app ends the session and you log in again next time.
 * (Staying logged in across restarts would need encrypted storage - a
 * separate, deliberate step.)
 */
object TokenStore {
    @Volatile
    var token: String? = null

    fun clear() {
        token = null
    }
}
