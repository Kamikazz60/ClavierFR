package org.futo.inputmethod.latin

import android.content.Context
import android.util.Log
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.futo.ml.inference.SwipeDecoder
import java.io.File

/**
 * Rejeu : relit `traces_fr.jsonl`, redécode le premier essai de chaque mot avec le décodeur
 * actuel (mêmes tracés, même disposition) et calcule top-1 / top-4.
 * Sert à comparer deux versions du décodeur sur exactement les mêmes swipes.
 * Écrit `replay_last.json` à côté des tracés.
 */
object SwipeReplay {
    @Serializable
    data class Item(
        val target: String,
        val rankOrig: Int,
        val rank: Int,
        val top4: List<String>,
        val ms: Float,
    )

    @Serializable
    data class Summary(
        val n: Int,
        val skipped: Int,
        val top1: Float,
        val top4: Float,
        val top1Orig: Float,
        val top4Orig: Float,
        val beam: Int,
        val avgMs: Float,
        val items: List<Item>,
    )

    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true; prettyPrint = false }

    fun resultFile(context: Context) =
        File(context.getExternalFilesDir(null) ?: context.filesDir, "replay_last.json")

    /** Vrai quand le clavier a chargé sa disposition et ses dictionnaires (il faut l'avoir affiché une fois). */
    fun isReady(): Boolean {
        // Le décodeur n'est créé qu'au premier swipe réel : on le crée ici, ce qui applique
        // aussi la disposition et les dictionnaires en attente.
        try { DictionaryFacilitatorImpl.swipeDecoderDictionary?.decoderForReplay() }
        catch (e: Throwable) { Log.w("SwipeReplay", "création du décodeur impossible", e) }
        return SwipeDecoderDictionary.appliedTries?.isNotEmpty() == true
    }

    private fun rankOf(words: List<String>, target: String): Int {
        val i = words.indexOf(target.lowercase())
        return if (i < 0) 0 else i + 1
    }

    @Volatile var lastError: String = ""

    private fun fail(msg: String): Summary? {
        lastError = msg
        Log.w("SwipeReplay", msg)
        return null
    }

    @Volatile var maxTries: Int = -1

    /** Test d'atteignabilité : mots (séparés par des virgules) dont on fabrique un geste passant par les touches. */
    @Volatile var synthWords: String = ""

    /** Test : texte à faire apprendre comme s'il avait été dicté, une fois le clavier prêt. */
    @Volatile var learnText: String = ""

    /** Test : mots à oublier (séparés par des virgules). */
    @Volatile var forgetText: String = ""

    /** Fabrique un geste parfait (centre des touches) pour chaque mot et écrit les candidats dans synth_last.json. */
    fun runSynth(context: Context): Boolean {
        lastError = ""
        val dict = DictionaryFacilitatorImpl.swipeDecoderDictionary ?: run { fail("décodeur non initialisé"); return false }
        val tries = SwipeDecoderDictionary.appliedTries
        if (tries == null || tries.isEmpty()) { fail("tries vides"); return false }
        val layout = SwipeDecoderDictionary.appliedLayoutInfo
        val decoder = dict.decoderForReplay()
        val weights = FloatArray(tries.size) { 1.0f }
        val sb = StringBuilder()
        sb.append("{\"tries\":${tries.size},\"results\":[")
        synthWords.split(",").map { it.trim().lowercase() }.filter { it.isNotEmpty() }.forEachIndexed { n, word ->
            val idx = word.mapNotNull { c -> layout.letters.indexOf(c).takeIf { it >= 0 } }
            val keys = idx.filterIndexed { i, k -> i == 0 || k != idx[i - 1] }
            val xs = ArrayList<Float>(); val ys = ArrayList<Float>()
            for (i in keys.indices) {
                val x1 = layout.xs[keys[i]]; val y1 = layout.ys[keys[i]]
                if (i == 0) { xs.add(x1); ys.add(y1); continue }
                val x0 = layout.xs[keys[i - 1]]; val y0 = layout.ys[keys[i - 1]]
                for (k in 1..10) { xs.add(x0 + (x1 - x0) * k / 10f); ys.add(y0 + (y1 - y0) * k / 10f) }
            }
            val seg = SwipeDecoder.SwipeSeg(xs.toFloatArray(), ys.toFloatArray(), FloatArray(xs.size) { it * 12f })
            val results = synchronized(BinaryDictionary.sTrieUsageLock) {
                decoder.setContext(emptyList())
                decoder.recognize(arrayOf(seg), emptyArray(), topK = 8, beamWidth = 300, trieWeights = weights)
            }
            if (n > 0) sb.append(",")
            sb.append("{\"word\":\"$word\",\"results\":[${results.joinToString(",") { "\"${it.word}\"" }}]}")
        }
        sb.append("]}")
        File(resultFile(context).parentFile, "synth_last.json").writeText(sb.toString())
        return true
    }

    /** Test de la fréquence personnelle : poids du bonus (0 = désactivé). Compteurs « laisser-un-de-côté » bâtis sur les cibles des tracés. */
    @Volatile var pfWeight: Float = 0f

    fun run(context: Context, beam: Int = 300, onProgress: (Int, Int) -> Unit = { _, _ -> }): Summary? {
        lastError = ""
        val dict = DictionaryFacilitatorImpl.swipeDecoderDictionary
            ?: return fail("le décodeur de swipe n'est pas initialisé (clavier jamais affiché dans ce processus)")
        val tries = SwipeDecoderDictionary.appliedTries
        if (tries == null || tries.isEmpty())
            return fail("dictionnaires du clavier pas encore chargés (tries vides) : le clavier unstable est-il bien le clavier actif et affiché ?")

        val file = SwipeRecorder.file(context)
        if (!file.exists()) return fail("fichier de tracés introuvable : ${file.path}")

        // Premier essai de chaque mot (même règle que donnees/score.py).
        val firsts = LinkedHashMap<Triple<String, Int, Int>, SwipeRecorder.Record>()
        file.forEachLine { line ->
            if (line.isBlank()) return@forEachLine
            val obj = json.parseToJsonElement(line).jsonObject
            if (obj["kind"]?.jsonPrimitive?.content != "swipe") return@forEachLine
            val rec = json.decodeFromString(SwipeRecorder.Record.serializer(), line)
            val key = Triple(rec.session, rec.sentence, rec.wordIndex)
            val prev = firsts[key]
            if (prev == null || rec.id < prev.id) firsts[key] = rec
        }
        val records = firsts.values.sortedBy { it.id }

        val decoder = dict.decoderForReplay()
        val layout = SwipeDecoderDictionary.appliedLayoutInfo
        Log.i("SwipeReplay", "départ : ${records.size} tracés, disposition='${layout.letters}', ${tries.size} trie(s)")
        // Poids par dictionnaire : ceux du dernier swipe réel, sinon 1.0 pour chaque trie.
        val weights = (SwipeDecoderDictionary.appliedTrieWeights.takeIf { it.size == tries.size }
            ?: FloatArray(tries.size) { 1.0f }).copyOf()
        // Test : ne garder que les N premiers dictionnaires (1 = dictionnaire principal seul, sans historique ni dico utilisateur)
        if (maxTries >= 0) for (i in weights.indices) if (i >= maxTries) weights[i] = 0f
        Log.i("SwipeReplay", "poids des tries : ${weights.toList()} (maxTries=$maxTries)")

        val pfCounts = HashMap<String, Int>()
        records.forEach { r -> pfCounts.merge(r.target.lowercase(), 1, Int::plus) }
        val items = ArrayList<Item>(records.size)
        var skipped = 0
        records.forEachIndexed { index, rec ->
            onProgress(index, records.size)
            if (rec.letters != layout.letters || rec.xs.size != layout.xs.size) { skipped++; return@forEachIndexed }

            fun seg(s: SwipeRecorder.Seg) = SwipeDecoder.SwipeSeg(s.x.toFloatArray(), s.y.toFloatArray(), s.t.toFloatArray())
            val left = rec.left.map(::seg).toTypedArray()
            val right = rec.right.map(::seg).toTypedArray()

            val t0 = System.nanoTime()
            val results = synchronized(BinaryDictionary.sTrieUsageLock) {
                decoder.setContext(rec.context)
                decoder.recognize(left, right, topK = if (pfWeight > 0f) PersonalFrequency.CANDIDATES else 4, beamWidth = beam, trieWeights = weights)
            }.let { raw ->
                if (pfWeight <= 0f) raw else {
                    val tl = rec.target.lowercase()
                    PersonalFrequency.rerank(raw, pfWeight, 4) { w ->
                        val k = w.lowercase()
                        (pfCounts[k] ?: 0) - (if (k == tl) 1 else 0)   // sans le mot cible lui-même (pas de triche)
                    }
                }
            }
            val ms = (System.nanoTime() - t0) / 1e6f

            val words = results.map { it.word.lowercase() }
            items.add(Item(
                target = rec.target,
                rankOrig = rankOf(rec.results.map { it.word.lowercase() }, rec.target),
                rank = rankOf(words, rec.target),
                top4 = results.map { it.word },
                ms = ms,
            ))
        }

        val n = items.size.coerceAtLeast(1)
        val summary = Summary(
            n = items.size, skipped = skipped,
            top1 = items.count { it.rank == 1 } * 100f / n,
            top4 = items.count { it.rank in 1..4 } * 100f / n,
            top1Orig = items.count { it.rankOrig == 1 } * 100f / n,
            top4Orig = items.count { it.rankOrig in 1..4 } * 100f / n,
            beam = beam,
            avgMs = items.sumOf { it.ms.toDouble() }.toFloat() / n,
            items = items,
        )
        try {
            resultFile(context).writeText(json.encodeToString(Summary.serializer(), summary))
        } catch (e: Exception) {
            Log.e("SwipeReplay", "Écriture impossible", e)
        }
        Log.i("SwipeReplay", "n=${summary.n} skipped=$skipped top1=${summary.top1} top4=${summary.top4} " +
                "(enregistré: ${summary.top1Orig}/${summary.top4Orig}) beam=$beam ms=${summary.avgMs}")
        return summary
    }
}
