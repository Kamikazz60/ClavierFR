package org.futo.inputmethod.latin

import android.content.Context
import android.util.Log
import kotlinx.serialization.builtins.MapSerializer
import kotlinx.serialization.builtins.serializer
import kotlinx.serialization.json.Json
import org.futo.ml.inference.SwipeDecoder
import java.io.File
import kotlin.math.ln

/**
 * ClavierFR : fréquence personnelle des mots validés (tapés, swipés, dictés), 100 % locale.
 *
 * Sert à reclasser les candidats du swipe : score' = score + weight * ln(1 + occurrences).
 * Fichier : filesDir/personal_freq.json (jamais envoyé nulle part).
 */
object PersonalFrequency {
    private const val TAG = "PersonalFrequency"
    private const val FILE = "personal_freq.json"
    private const val SAVE_EVERY = 20

    /** Poids du bonus (0 = désactivé). Réglé par mesure au rejeu (voir SUIVI.md). */
    @Volatile var weight: Float = 0.6f

    /** Nombre de candidats demandés au moteur quand le reclassement est actif (on en garde 4). */
    const val CANDIDATES = 8

    private val counts = HashMap<String, Int>()
    private var loaded = false
    private var unsaved = 0
    private val serializer = MapSerializer(String.serializer(), Int.serializer())

    private fun file(context: Context) = File(context.filesDir, FILE)

    @Synchronized
    fun load(context: Context) {
        if (loaded) return
        loaded = true
        try {
            val f = file(context)
            if (f.exists()) counts.putAll(Json.decodeFromString(serializer, f.readText()))
            Log.i(TAG, "${counts.size} mots chargés")
        } catch (e: Exception) {
            Log.e(TAG, "lecture impossible : $e")
        }
    }

    private fun normalize(word: String) = word.lowercase().trim()

    /** À appeler pour chaque mot validé par l'utilisateur. */
    @Synchronized
    fun record(context: Context, word: String) {
        load(context)
        val w = normalize(word)
        if (w.length < 2 || w.any { it.isDigit() || it == '@' || it == '/' }) return
        counts[w] = (counts[w] ?: 0) + 1
        if (++unsaved >= SAVE_EVERY) save(context)
    }

    @Synchronized
    fun forget(context: Context, word: String) {
        load(context)
        if (counts.remove(normalize(word)) != null) save(context)
    }

    @Synchronized
    fun save(context: Context) {
        try {
            file(context).writeText(Json.encodeToString(serializer, counts))
            unsaved = 0
        } catch (e: Exception) {
            Log.e(TAG, "écriture impossible : $e")
        }
    }

    @Synchronized
    fun count(word: String): Int = counts[normalize(word)] ?: 0

    @Synchronized
    fun size(): Int = counts.size

    fun bonus(occurrences: Int): Float = ln(1f + occurrences.coerceAtLeast(0))

    /**
     * Reclasse [results] avec le bonus de fréquence et garde [n] candidats ; [countOf] permet de substituer le compteur (rejeu).
     * Comme le moteur natif, on garantit que le meilleur candidat « géométrique » (ctcScore max) reste visible.
     */
    fun rerank(
        results: List<SwipeDecoder.Result>,
        weight: Float = this.weight,
        n: Int = 4,
        countOf: (String) -> Int = ::count,
    ): List<SwipeDecoder.Result> {
        if (weight <= 0f || results.isEmpty()) return results.take(n)
        // le score modifié est conservé : le clavier retrie ensuite les suggestions selon ce score
        val sorted = results.map { it.copy(score = it.score + weight * bonus(countOf(it.word))) }
            .sortedByDescending { it.score }
        val top = sorted.take(n).toMutableList()
        val ctcBest = sorted.maxByOrNull { it.ctcScore }
        if (ctcBest != null && top.none { it.word == ctcBest.word }) top[top.lastIndex] = ctcBest
        return top
    }
}
