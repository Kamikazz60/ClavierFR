package org.futo.inputmethod.latin

import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.provider.Settings
import android.text.InputType
import android.text.Spannable
import android.text.SpannableString
import android.text.style.BackgroundColorSpan
import android.text.style.StyleSpan
import android.view.Gravity
import android.view.View
import android.view.inputmethod.InputMethodManager
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.graphics.Insets
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat

/**
 * Écran d'enregistrement : affiche une phrase, surligne le mot à swiper, et enregistre
 * chaque tracé avec le mot visé (voir [SwipeRecorder]). Affiche le score top-1 / top-4 en direct.
 */
class SwipeRecorderActivity : AppCompatActivity() {
    private lateinit var progress: TextView
    private lateinit var sentenceView: TextView
    private lateinit var status: TextView
    private lateinit var input: EditText

    private var sentences: List<List<String>> = emptyList()
    private var si = 0
    private var wi = 0

    private class Done(val rec: SwipeRecorder.Outcome, val si: Int, val wi: Int)
    private val history = ArrayList<Done>()

    private var n = 0; private var top1 = 0; private var top4 = 0
    private var top1n = 0; private var top4n = 0   // sans accents

    private val prefs by lazy { getSharedPreferences("swipe_recorder", MODE_PRIVATE) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        sentences = assets.open("swipe-recorder/corpus_fr.txt").bufferedReader().readLines()
            .map { it.trim() }.filter { it.isNotEmpty() }
            .map { line -> line.split(' ').filter { it.isNotEmpty() } }
        si = prefs.getInt("si", 0).coerceIn(0, sentences.size)

        val dp = resources.displayMetrics.density
        fun px(v: Int) = (v * dp).toInt()

        progress = TextView(this).apply { textSize = 14f; setTextColor(Color.GRAY) }
        sentenceView = TextView(this).apply { textSize = 22f; setPadding(0, px(12), 0, px(12)) }
        status = TextView(this).apply { textSize = 15f; setPadding(0, 0, 0, px(8)) }
        input = EditText(this).apply {
            hint = "Swipe le mot surligné ici"
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE
            gravity = Gravity.TOP or Gravity.START
            minLines = 2
        }

        fun button(label: String, onClick: () -> Unit) = Button(this).apply {
            text = label; isAllCaps = false
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
            setOnClickListener { onClick() }
        }
        val buttons = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            addView(button("Refaire") { undo() })
            addView(button("Passer") { skip() })
            addView(button("Début") { restart() })
            addView(button("Rejeu") { startReplay(300) })
        }

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(px(16), px(16), px(16), px(16))
            addView(progress)
            addView(sentenceView)
            addView(status)
            addView(input, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f))
            addView(buttons)
        }
        setContentView(root)

        // Android 15 : l'appli passe sous les barres système, on décale pour la barre et le clavier.
        ViewCompat.setOnApplyWindowInsetsListener(root) { v, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            val ime = insets.getInsets(WindowInsetsCompat.Type.ime())
            val b = Insets.max(bars, ime)
            v.setPadding(px(16) + b.left, px(16) + b.top, px(16) + b.right, px(16) + b.bottom)
            insets
        }

        status.setOnClickListener {
            (getSystemService(INPUT_METHOD_SERVICE) as InputMethodManager).showInputMethodPicker()
        }

        SwipeRecorder.session = System.currentTimeMillis().toString()
        render()
    }

    override fun onResume() {
        super.onResume()
        SwipeRecorder.active = true
        SwipeRecorder.listener = { onOutcome(it) }
        publishTarget()
        input.requestFocus()
        checkKeyboard()

        // Réglage « Personalized suggestions » (apprentissage des mots) : am start ... --ez personalize true|false
        if (intent.hasExtra("personalize")) {
            val on = intent.getBooleanExtra("personalize", true)
            intent.removeExtra("personalize")
            android.preference.PreferenceManager.getDefaultSharedPreferences(applicationContext)
                .edit().putBoolean("pref_key_use_personalized_dicts", on).apply()
            status.text = "Suggestions personnalisées (apprentissage) : " + if (on) "activées" else "désactivées"
        }

        // Réglage de collecte des gestes (test) : am start ... --ez collect true|false
        if (intent.hasExtra("collect")) {
            val on = intent.getBooleanExtra("collect", false)
            intent.removeExtra("collect")
            android.preference.PreferenceManager.getDefaultSharedPreferences(applicationContext)
                .edit().putBoolean(TraceCollector.PREF_KEY, on).apply()
            status.text = "Collecte des gestes : " + if (on) "activée" else "désactivée"
        }

        // Lancement par adb : am start ... --ez replay true [--ei beam 300]
        if (intent.getBooleanExtra("replay", false)) {
            intent.removeExtra("replay")
            SwipeReplay.maxTries = intent.getIntExtra("tries", -1)
            SwipeReplay.synthWords = intent.getStringExtra("synth") ?: ""
            SwipeReplay.learnText = intent.getStringExtra("learn") ?: ""
            SwipeReplay.forgetText = intent.getStringExtra("forget") ?: ""
            SwipeReplay.pfWeight = intent.getIntExtra("pf", 0) / 100f
            startReplay(intent.getIntExtra("beam", 300))
        }
    }

    private var replaying = false

    /** Rejoue les tracés enregistrés dans le décodeur courant (voir [SwipeReplay]). */
    private fun startReplay(beam: Int) {
        if (replaying) return
        replaying = true
        status.setTextColor(Color.GRAY)
        status.text = "Rejeu : attente du clavier…"
        // Le clavier doit être affiché une fois pour charger sa disposition et ses dictionnaires.
        input.postDelayed({
            (getSystemService(INPUT_METHOD_SERVICE) as InputMethodManager).showSoftInput(input, 0)
        }, 300)

        Thread {
            var waited = 0
            while (!SwipeReplay.isReady() && waited < 20000) {
                Thread.sleep(250); waited += 250
                if (waited % 2000 == 0) runOnUiThread {
                    input.requestFocus()
                    (getSystemService(INPUT_METHOD_SERVICE) as InputMethodManager).showSoftInput(input, 0)
                }
            }
            if (SwipeReplay.forgetText.isNotEmpty()) {
                val ws = SwipeReplay.forgetText.split(",").map { it.trim() }.filter { it.isNotEmpty() }; SwipeReplay.forgetText = ""
                runOnUiThread {
                    org.futo.inputmethod.engine.general.GeneralIME.active?.let { ime -> ws.forEach { ime.forgetWord(it) }; ime.refreshSwipeTries() }
                }
                Thread.sleep(2000)
                var w3 = 0
                while (!SwipeReplay.isReady() && w3 < 10000) { Thread.sleep(250); w3 += 250 }
            }
            if (SwipeReplay.learnText.isNotEmpty()) {
                val t = SwipeReplay.learnText; SwipeReplay.learnText = ""
                runOnUiThread {
                    org.futo.inputmethod.engine.general.GeneralIME.active?.let { it.learnFromDictation(t); it.refreshSwipeTries() }
                }
                Thread.sleep(2000)
                var w2 = 0
                while (!SwipeReplay.isReady() && w2 < 10000) { Thread.sleep(250); w2 += 250 }
            }
            if (SwipeReplay.synthWords.isNotEmpty()) {
                val ok = try { SwipeReplay.runSynth(applicationContext) } catch (e: Throwable) { android.util.Log.e("SwipeReplay", "Échec synth", e); false }
                SwipeReplay.synthWords = ""
                runOnUiThread { replaying = false; status.text = if (ok) "Test d'atteignabilité écrit (synth_last.json)" else "Échec : ${SwipeReplay.lastError}" }
                return@Thread
            }
            val summary = try {
                SwipeReplay.run(applicationContext, beam) { i, total ->
                    if (i % 25 == 0) runOnUiThread { status.text = "Rejeu : $i / $total" }
                }
            } catch (e: Throwable) {
                android.util.Log.e("SwipeReplay", "Échec du rejeu", e)
                null
            }
            runOnUiThread {
                replaying = false
                status.text = if (summary == null)
                    "Rejeu impossible : ${SwipeReplay.lastError.ifEmpty { "erreur inconnue (voir logcat)" }}"
                else
                    "Rejeu (beam ${summary.beam}) sur ${summary.n} mots" +
                    (if (summary.skipped > 0) " (${summary.skipped} ignorés)" else "") +
                    " : top-1 ${"%.1f".format(summary.top1)} % · top-4 ${"%.1f".format(summary.top4)} %" +
                    "\nEnregistré à l'époque : ${"%.1f".format(summary.top1Orig)} % / ${"%.1f".format(summary.top4Orig)} %" +
                    " · ${"%.0f".format(summary.avgMs)} ms/mot"
            }
        }.start()
    }

    // Relance par adb sans arrêt forcé (un force-stop remet Gboard comme clavier par défaut).
    override fun onNewIntent(intent: android.content.Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
    }

    override fun onPause() {
        super.onPause()
        SwipeRecorder.active = false
        SwipeRecorder.listener = null
        prefs.edit().putInt("si", si).apply()
    }

    private fun checkKeyboard() {
        val current = Settings.Secure.getString(contentResolver, Settings.Secure.DEFAULT_INPUT_METHOD) ?: ""
        if (!current.startsWith(packageName)) {
            status.setTextColor(Color.rgb(200, 60, 0))
            status.text = "⚠ Le clavier actif n'est pas celui-ci. Touche ici pour le choisir."
        }
    }

    private fun currentWord(): String? = sentences.getOrNull(si)?.getOrNull(wi)

    private fun publishTarget() {
        SwipeRecorder.target = currentWord()
        SwipeRecorder.sentenceIndex = si
        SwipeRecorder.wordIndex = wi
    }

    private fun prefixText(): String {
        val words = sentences.getOrNull(si) ?: return ""
        return words.take(wi).joinToString(" ") + if (wi > 0) " " else ""
    }

    private fun resetInput() {
        input.setText(prefixText())
        input.setSelection(input.text.length)
    }

    private fun render() {
        publishTarget()
        if (si >= sentences.size) {
            sentenceView.text = "Terminé 🎉"
            progress.text = summary()
            return
        }
        val words = sentences[si]
        val sb = StringBuilder()
        var start = 0; var end = 0
        words.forEachIndexed { i, w ->
            if (i > 0) sb.append(' ')
            if (i == wi) start = sb.length
            sb.append(w)
            if (i == wi) end = sb.length
        }
        val span = SpannableString(sb.toString())
        span.setSpan(BackgroundColorSpan(Color.rgb(255, 224, 120)), start, end, Spannable.SPAN_EXCLUSIVE_EXCLUSIVE)
        span.setSpan(StyleSpan(Typeface.BOLD), start, end, Spannable.SPAN_EXCLUSIVE_EXCLUSIVE)
        sentenceView.text = span
        progress.text = "Phrase ${si + 1}/${sentences.size} · mot ${wi + 1}/${words.size}\n${summary()}"
    }

    private fun pct(a: Int) = if (n == 0) "–" else "${(100 * a / n)} %"
    private fun summary() = "Enregistrés : $n · top-1 ${pct(top1)} · top-4 ${pct(top4)} (sans accents : ${pct(top1n)} / ${pct(top4n)})"

    private fun advance() {
        wi++
        if (wi >= (sentences.getOrNull(si)?.size ?: 0)) {
            si++; wi = 0
            input.setText("")
        }
        render()
    }

    private fun onOutcome(o: SwipeRecorder.Outcome) {
        if (si >= sentences.size) return
        history.add(Done(o, si, wi))
        n++
        if (o.rank == 1) top1++
        if (o.rank in 1..4) top4++
        if (o.rankNoAccent == 1) top1n++
        if (o.rankNoAccent in 1..4) top4n++

        val got = o.record.results.take(4).joinToString(", ") { it.word }
        status.setTextColor(if (o.rank == 1) Color.rgb(0, 130, 0) else if (o.rank in 2..4) Color.rgb(200, 120, 0) else Color.rgb(190, 0, 0))
        status.text = when (o.rank) {
            1 -> "✓ « ${o.record.target} » en tête"
            0 -> "✗ « ${o.record.target} » absent. Reçu : $got"
            else -> "~ « ${o.record.target} » en position ${o.rank}. Reçu : $got"
        }
        advance()
    }

    private fun undo() {
        val last = history.removeLastOrNull() ?: return
        SwipeRecorder.writeUndo(this, last.rec.record.id)
        n--
        if (last.rec.rank == 1) top1--
        if (last.rec.rank in 1..4) top4--
        if (last.rec.rankNoAccent == 1) top1n--
        if (last.rec.rankNoAccent in 1..4) top4n--
        si = last.si; wi = last.wi
        status.setTextColor(Color.GRAY)
        status.text = "Dernier mot annulé, refais-le."
        render()
        resetInput()
    }

    private fun skip() {
        if (si >= sentences.size) return
        status.setTextColor(Color.GRAY)
        status.text = "Mot passé (non enregistré)."
        wi++
        if (wi >= sentences[si].size) { si++; wi = 0; input.setText("") }
        render()
        resetInput()
    }

    private fun restart() {
        si = 0; wi = 0
        n = 0; top1 = 0; top4 = 0; top1n = 0; top4n = 0
        history.clear()
        SwipeRecorder.session = System.currentTimeMillis().toString()
        input.setText("")
        status.text = ""
        render()
    }
}
