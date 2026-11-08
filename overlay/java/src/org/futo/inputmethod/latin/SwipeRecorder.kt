package org.futo.inputmethod.latin

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.util.Log
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import org.futo.ml.inference.SwipeDecoder
import java.io.File
import java.text.Normalizer

/**
 * Enregistreur de tracés de swipe (outil de mesure et de collecte de données ClavierFR).
 *
 * Quand [active] est vrai et que [target] est défini, chaque swipe terminé est ajouté à
 * `traces_fr.jsonl` (dossier externe de l'appli) avec : le mot visé, le tracé tel qu'envoyé
 * au modèle, la disposition (lettres + positions), et les 4 meilleurs mots proposés.
 * Tout reste sur le téléphone.
 */
object SwipeRecorder {
    @Serializable
    data class Seg(val x: List<Float>, val y: List<Float>, val t: List<Float>)

    @Serializable
    data class Candidate(val word: String, val score: Float)

    @Serializable
    data class Record(
        val kind: String = "swipe",
        val id: Long,
        val session: String,
        val sentence: Int,
        val wordIndex: Int,
        val target: String,
        val letters: String,
        val xs: List<Float>,
        val ys: List<Float>,
        val left: List<Seg>,
        val right: List<Seg>,
        val beam: Int,
        val results: List<Candidate>,
        val context: List<String>,
    )

    /** Ligne d'annulation : le tracé `id` est à ignorer (l'utilisateur a refait le mot). */
    @Serializable
    data class Undo(val kind: String = "undo", val id: Long)

    data class Outcome(
        val record: Record,
        val rank: Int,        // 1 = bon mot en tête, 0 = absent des résultats
        val rankNoAccent: Int // idem en ignorant les accents
    )

    @Volatile var active = false
    @Volatile var target: String? = null
    @Volatile var session: String = ""
    @Volatile var sentenceIndex = 0
    @Volatile var wordIndex = 0
    @Volatile var listener: ((Outcome) -> Unit)? = null

    private val json = Json { encodeDefaults = true }
    private val main = Handler(Looper.getMainLooper())
    private var lastSignature = 0

    fun file(context: Context): File =
        File(context.getExternalFilesDir(null) ?: context.filesDir, "traces_fr.jsonl")

    fun stripAccents(s: String): String =
        Normalizer.normalize(s, Normalizer.Form.NFD).replace(Regex("\\p{Mn}+"), "")

    private fun toSeg(s: SwipeDecoder.SwipeSeg) = Seg(s.x.toList(), s.y.toList(), s.t.toList())

    /** Appelé par SwipeDecoderDictionary à la fin d'un swipe (passe « haute précision »). */
    fun onSwipe(
        context: Context,
        layout: LayoutInfoForModel,
        left: List<SwipeDecoder.SwipeSeg>,
        right: List<SwipeDecoder.SwipeSeg>,
        beam: Int,
        results: List<SwipeDecoder.Result>,
        wordsContext: List<String>,
    ) {
        if (!active) return
        val tgt = target ?: return
        val first = left.firstOrNull() ?: right.firstOrNull() ?: return

        // Le même swipe peut être décodé plusieurs fois : on ne l'enregistre qu'une fois.
        val signature = 31 * first.x.contentHashCode() + first.y.contentHashCode() + first.t.contentHashCode()
        if (signature == lastSignature) return
        lastSignature = signature

        val rec = Record(
            id = System.currentTimeMillis(),
            session = session, sentence = sentenceIndex, wordIndex = wordIndex,
            target = tgt,
            letters = layout.letters, xs = layout.xs, ys = layout.ys,
            left = left.map(::toSeg), right = right.map(::toSeg),
            beam = beam,
            results = results.map { Candidate(it.word, it.score) },
            context = wordsContext,
        )

        try {
            synchronized(this) {
                file(context).appendText(json.encodeToString(Record.serializer(), rec) + "\n")
            }
        } catch (e: Exception) {
            Log.e("SwipeRecorder", "Écriture impossible", e)
            return
        }

        val words = results.map { it.word.lowercase() }
        val t = tgt.lowercase()
        val rank = words.indexOf(t).let { if (it < 0) 0 else it + 1 }
        val tn = stripAccents(t)
        val rankNo = words.indexOfFirst { stripAccents(it) == tn }.let { if (it < 0) 0 else it + 1 }

        listener?.let { l -> main.post { l(Outcome(rec, rank, rankNo)) } }
    }

    fun writeUndo(context: Context, id: Long) {
        try {
            synchronized(this) {
                file(context).appendText(json.encodeToString(Undo.serializer(), Undo(id = id)) + "\n")
            }
        } catch (e: Exception) {
            Log.e("SwipeRecorder", "Écriture impossible", e)
        }
        lastSignature = 0
    }
}
