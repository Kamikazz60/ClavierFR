package org.futo.inputmethod.latin

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.text.InputType
import android.util.Log
import android.view.inputmethod.EditorInfo
import android.preference.PreferenceManager

/**
 * ClavierFR : « mode dictée seule ».
 *
 * Quand l'option est activée et que l'utilisateur passe à ClavierFR depuis un autre clavier
 * (Gboard…), la dictée démarre aussitôt ; une fois le texte inséré (ou la dictée fermée), on
 * revient automatiquement au clavier précédent.
 *
 * Jamais dans un champ de mot de passe : on reste alors sur le clavier normal.
 */
object VoiceOnlyMode {
    const val PREF_KEY = "pref_key_clavierfr_voice_only"
    private const val TAG = "VoiceOnlyMode"

    /** Vrai pendant qu'une dictée lancée par ce mode est en cours : sa fermeture ramène au clavier précédent. */
    @Volatile var active = false
        private set

    private val handler = Handler(Looper.getMainLooper())
    private var imeRef: LatinIME? = null

    fun isEnabled(context: Context): Boolean =
        try { PreferenceManager.getDefaultSharedPreferences(context).getBoolean(PREF_KEY, false) }
        catch (e: Exception) { false }

    fun isPasswordField(info: EditorInfo?): Boolean {
        val type = info?.inputType ?: return false
        val cls = type and InputType.TYPE_MASK_CLASS
        val variation = type and InputType.TYPE_MASK_VARIATION
        return when (cls) {
            InputType.TYPE_CLASS_TEXT ->
                variation == InputType.TYPE_TEXT_VARIATION_PASSWORD ||
                variation == InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD ||
                variation == InputType.TYPE_TEXT_VARIATION_WEB_PASSWORD
            InputType.TYPE_CLASS_NUMBER -> variation == InputType.TYPE_NUMBER_VARIATION_PASSWORD
            else -> false
        }
    }

    /** Appelé à l'ouverture d'un champ ; lance la dictée si le mode est actif. */
    fun onInputViewStarted(ime: LatinIME, info: EditorInfo?, restarting: Boolean) {
        if (restarting) return
        if (!isEnabled(ime) || isPasswordField(info)) { active = false; return }
        imeRef = ime
        active = true
        handler.postDelayed({
            try {
                ime.uixManager.activateInternalVoiceIME()
            } catch (e: Throwable) {
                Log.e(TAG, "Échec du démarrage de la dictée", e)
                active = false
            }
        }, 250)
    }

    /** Appelé quand la fenêtre de dictée se ferme (texte inséré, annulation, retour…). */
    fun onVoiceClosed() {
        val ime = imeRef
        if (!active || ime == null) return
        active = false
        // Petit délai : laisse le texte validé arriver dans le champ avant de changer de clavier.
        handler.postDelayed({
            try {
                val switched = ime.switchToPreviousInputMethod()
                Log.i(TAG, "Retour au clavier précédent : $switched")
            } catch (e: Throwable) {
                Log.e(TAG, "Échec du retour au clavier précédent", e)
            }
        }, 200)
    }
}
