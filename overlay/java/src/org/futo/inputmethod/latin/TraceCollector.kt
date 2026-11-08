package org.futo.inputmethod.latin

import android.content.Context
import android.preference.PreferenceManager
import android.util.Log
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import org.futo.ml.inference.SwipeDecoder
import java.io.File
import kotlin.math.abs

/**
 * ClavierFR : collecte locale des paires (geste, mot validé) pendant l'usage normal.
 *
 * - Désactivée par défaut ; l'utilisateur l'active dans Réglages > Texte prédictif.
 * - Le geste reste en mémoire jusqu'à la validation du mot ; il n'est écrit que si le champ n'est pas
 *   sensible (l'appelant, InputLogic.commitChosenWord, exclut mots de passe, champs code/e-mail/URL,
 *   mode privé) et si le mot validé correspond bien au geste.
 * - Fichier : `collecte_gestes.jsonl` dans le dossier externe privé de l'appli ; jamais envoyé nulle part.
 *   Même format que `traces_fr.jsonl` (+ `label`), donc lisible par les mêmes outils.
 */
object TraceCollector {
    private const val TAG = "TraceCollector"
    const val PREF_KEY = "pref_key_clavierfr_collect"
    private const val FILE = "collecte_gestes.jsonl"
    private const val MAX_BYTES = 40L * 1024 * 1024
    private const val MAX_AGE_MS = 120_000L
    private const val MAX_START_DIST = 0.2f   // distance (unités du clavier) pour accepter un mot hors candidats

    @Serializable
    data class Entry(
        val kind: String = "swipe",
        val id: Long,
        val session: String = "collecte",
        val sentence: Int = 0,
        val wordIndex: Int = 0,
        val target: String,
        val letters: String,
        val xs: List<Float>,
        val ys: List<Float>,
        val left: List<SwipeRecorder.Seg>,
        val right: List<SwipeRecorder.Seg>,
        val beam: Int,
        val results: List<SwipeRecorder.Candidate>,
        val context: List<String>,
        /** top1 = le mot validé était la 1re proposition ; alt = une autre proposition ; other = mot absent des propositions (corrigé à la main). */
        val label: String,
    )

    private class Pending(
        val time: Long,
        val layout: LayoutInfoForModel,
        val left: List<SwipeDecoder.SwipeSeg>,
        val right: List<SwipeDecoder.SwipeSeg>,
        val beam: Int,
        val results: List<SwipeDecoder.Result>,
        val context: List<String>,
    )

    @Volatile private var pending: Pending? = null
    @Volatile private var appContext: Context? = null
    private val json = Json { encodeDefaults = true }
    private val wordRegex = Regex("^\\p{L}[\\p{L}'-]*\\p{L}$")

    fun isEnabled(context: Context): Boolean =
        try { PreferenceManager.getDefaultSharedPreferences(context).getBoolean(PREF_KEY, false) }
        catch (e: Exception) { false }

    fun file(context: Context): File =
        File(context.getExternalFilesDir(null) ?: context.filesDir, FILE)

    /** Nombre de gestes collectés (une ligne = un geste). */
    fun count(context: Context): Int = try {
        val f = file(context)
        if (!f.exists()) 0 else f.useLines { it.count() }
    } catch (e: Exception) { 0 }

    /** Efface toute la collecte ; renvoie le nombre de gestes supprimés. */
    fun deleteAll(context: Context): Int {
        val n = count(context)
        pending = null
        try { file(context).delete() } catch (e: Exception) { Log.e(TAG, "suppression impossible : $e") }
        return n
    }

    /** Oublie le geste en attente (changement de champ de saisie, fin de saisie…). */
    fun clearPending() { pending = null }

    /** Appelé à la fin d'un swipe (passe haute précision) : garde le geste en mémoire uniquement. */
    fun onSwipe(
        context: Context,
        layout: LayoutInfoForModel,
        left: List<SwipeDecoder.SwipeSeg>,
        right: List<SwipeDecoder.SwipeSeg>,
        beam: Int,
        results: List<SwipeDecoder.Result>,
        wordsContext: List<String>,
    ) {
        if (!isEnabled(context)) { pending = null; return }
        appContext = context.applicationContext
        pending = Pending(System.currentTimeMillis(), layout, left, right, beam, results, wordsContext)
    }

    /** Appelé quand un mot est validé dans un champ non sensible. [wasBatch] : le mot vient d'un swipe non retouché. */
    fun onWordCommitted(word: String, wasBatch: Boolean) {
        val p = pending ?: return
        pending = null
        val context = appContext ?: return
        if (!wasBatch || !isEnabled(context)) return
        if (System.currentTimeMillis() - p.time > MAX_AGE_MS) return
        val target = word.lowercase().replace('’', '\'')
        if (!wordRegex.matches(target)) return

        val words = p.results.map { it.word.lowercase() }
        val label = when (words.indexOf(target)) {
            0 -> "top1"
            in 1..Int.MAX_VALUE -> "alt"
            else -> "other"
        }
        if (label == "other" && !startsNearFirstLetter(p, target)) return

        val first = p.left.firstOrNull() ?: p.right.firstOrNull() ?: return
        if (first.x.size < 4) return   // un simple toucher n'est pas un swipe

        val entry = Entry(
            id = System.currentTimeMillis(),
            target = target,
            letters = p.layout.letters, xs = p.layout.xs, ys = p.layout.ys,
            left = p.left.map { SwipeRecorder.Seg(it.x.toList(), it.y.toList(), it.t.toList()) },
            right = p.right.map { SwipeRecorder.Seg(it.x.toList(), it.y.toList(), it.t.toList()) },
            beam = p.beam,
            results = p.results.map { SwipeRecorder.Candidate(it.word, it.score) },
            context = p.context,
            label = label,
        )
        try {
            val f = file(context)
            synchronized(this) {
                if (f.exists() && f.length() > MAX_BYTES) return
                f.appendText(json.encodeToString(Entry.serializer(), entry) + "\n")
            }
        } catch (e: Exception) {
            Log.e(TAG, "écriture impossible : $e")
        }
    }

    /** Pour un mot hors propositions : le geste doit au moins commencer près de sa première lettre. */
    private fun startsNearFirstLetter(p: Pending, target: String): Boolean {
        val i = p.layout.letters.indexOf(target[0])
        if (i < 0) return false
        val seg = p.left.firstOrNull() ?: p.right.firstOrNull() ?: return false
        if (seg.x.isEmpty()) return false
        return abs(seg.x[0] - p.layout.xs[i]) < MAX_START_DIST && abs(seg.y[0] - p.layout.ys[i]) < MAX_START_DIST
    }
}
