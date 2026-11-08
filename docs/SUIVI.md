# SUIVI — ClavierFR

## Objectif
Swipe français AZERTY très précis dans un clavier Android hors ligne, dictée FUTO conservée.

## État actuel (07/11/2026)
- Cadrage fait. FUTO Keyboard testé par Doanh : dictée validée, swipe très mauvais en français.
- Cause probable : FUTO n'a de décodeur spécialisé que pour l'anglais QWERTY ; en français AZERTY seul l'encodeur universel sert.
- **FUTO Keyboard cloné (sous-modules inclus) et compilé par nous** : `apk\ClavierFR-debug.apk` (152 Mo). Niveau de validation : **validé sur appareil** (07/11/2026).
- Modèles FUTO Swipe déjà dans le dépôt (voir CLAUDE.md §8) → plus besoin d'aller les chercher.

- APK installé sur le Pixel 6a (07/11/2026) à côté de la version Play Store ; Doanh l'a activé. Retour de Doanh : dictée vocale OK, swipe aussi mauvais en français que la version Play Store (point de départ confirmé).
- Sources C++ de la bibliothèque swipe clonées dans `swipe-library\` (beam search, trie, layouts dont `fr_azerty.json`, JNI, benchmark, scripts d'export) : on peut donc modifier et recompiler la recherche de mots.

## Score de référence FUTO (07/11/2026, première série de Doanh)
Outil : écran « Enregistreur swipe » (icône dans le Pixel) → `traces_fr.jsonl` ; récupération : `adb pull /sdcard/Android/data/org.futo.inputmethod.latin.unstable/files/traces_fr.jsonl donnees\` ; analyse : `python -I donnees\score.py donnees\traces_fr.jsonl`.
Données : 731 swipes dont 146 annulés (Refaire), 50 phrases, 336 mots distincts. **Mesure sans biais = premier essai de chaque mot (n=580)** :
- Global : **top-1 71,2 % · top-4 84,3 %**
- 1-2 lettres 87,8 / 95,3 · 3-4 lettres 70,9 / 87,3 · 5-7 lettres 62,8 / 77,9 · 8+ lettres 61,3 / 73,3
- **Avec accent 42,6 / 66,7 · avec apostrophe 15,4 / 38,5 (n=13)** → points faibles nets
- Attention : « Refaire » gonfle les scores des essais retenus (80,5 / 95,4) ; ne comparer que des premiers essais.
- Parasites vus dans les propositions : mots anglais/noms propres (neely, benny, salinger, smith, fans, kda…) → dictionnaire français à nettoyer/repondérer.
Limites : un seul utilisateur, texte écrit par Claude, mots refaits ≠ rejeu : la comparaison de versions du décodeur exige de rejouer les mêmes tracés (outil de rejeu à faire).

## Outil de rejeu (terminé 07/11/2026, validé sur appareil)
- Écran « Enregistreur swipe » → bouton **Rejeu** (ou `adb shell am start -n org.futo.inputmethod.latin.unstable/org.futo.inputmethod.latin.SwipeRecorderActivity --ez replay true --ei beam 300` après `am force-stop`). Prérequis : le clavier **FUTO unstable doit être le clavier actif** (Android remet Gboard à chaque réinstallation de l'APK : le re-sélectionner).
- Il relit `traces_fr.jsonl`, redécode le premier essai de chaque mot (587 mots : 580 de la 1re série + 7 d'une 2e série lancée par erreur avec « Début ») et écrit `replay_last.json` (récupérer avec `adb pull`).
- **Contrôle de fidélité réussi** : rejeu = **top-1 71,2 % · top-4 84,5 %**, identique à l'enregistrement d'origine (n=587), 7 ms/mot. Référence sauvegardée : `donnees
eplay_baseline_fr.json`.
- « Début » n'efface rien : il ouvre une nouvelle session dans le même fichier (les anciens tracés restent).
- Limite : le rejeu utilise le décodeur et les dictionnaires installés (y compris l'historique utilisateur) ; seuls les paramètres modifiables dans l'appli (largeur de faisceau, modèles, dictionnaires, poids) peuvent être testés sans recompiler la bibliothèque.

## Étude du ContextLM (P0-4, étape 1, 07/11/2026)
- **Le rapport technique FUTO (arxiv 2606.25247) ne documente pas le ContextLM** (ni architecture, ni données, ni entraînement) : lecture faite par sous-agent (début du HTML + résumé du reste, PDF brut non relu) ; à ne pas considérer comme prouvé à 100 %, mais rien d'utile n'en ressort. Il faut donc **concevoir notre propre LM** conforme au contrat ci-dessous.
- **Contrat du modèle** (lu dans `swipe-library/src/context_lm.cpp`) : fichier `.pte` + `metadata.json` (`{"kind":"contextlm","codename":...}`) + `vocab.txt` (32 768 mots, un par ligne, triés par fréquence). Méthode `forward(context_ids int64 [1,L], context_hashes int64 [1,L,2]) -> h [1,L,E]` (fp32 ou fp16, causale : on lit la position du dernier mot) ; méthode `get_embeddings() -> (exact_embed [32768,E], exact_bias [32768], hash_embed [B,E], hash_bias [B])`. Score d'un mot = h·emb + bias ; mot hors vocabulaire = somme des 2 buckets hachés (wyhash + multiplication-décalage, B puissance de 2, voir `vocab_hash.hpp`). L = taille du 1er argument de `forward`.
- **Opérateurs** : l'.aar embarqué ne contient que les opérateurs listés dans `swipe-library/models/*/ops.txt` (hungry_jellyfish = embedding, layer_norm, clamp, lt, sum, unsqueeze, where) ; le reste du réseau doit passer par le délégué XNNPACK (comme l'encodeur). Notre modèle doit respecter cette liste, sinon recompiler `swipe-library` (sources + NDK dispos).
- Les `.pte` actuels : `chosen_planarian` (anglais, 6,2 Mo, 32 768 mots) est dans l'APK ; `hungry_jellyfish` (plus récent) n'y est pas.
- **Machine** : i5-6600K 4 cœurs, 24 Go RAM, 791 Go libres. GTX 970 (Maxwell) probablement non supportée par PyTorch récent → entraînement **sur processeur** (modèle ≈1,5 M de paramètres : faisable en quelques heures pour 100-300 M de mots). PyPI (executorch 1.6.0, torch) et Hugging Face / dumps Wikipédia / Gutenberg sont joignables depuis le PC.
- **Plan** : venv Python dans `clavierPers\ml\` ; corpus français (FineWeb-2 « fra_Latn » et/ou Wikipédia fr, filtré/normalisé, + texte de Doanh plus tard) ; vocabulaire 32 768 mots ; modèle DFSMN/convolutions causales, embeddings exacts + hachés ; perplexité sur jeu de validation ; export ExecuTorch (XNNPACK) vérifié contre la liste d'opérateurs ; intégration (`contextLMs` dans SwipeDecoderDictionary.kt, assets, `scoring.json`) ; mesure par rejeu sur jeu de test séparé.
- **Accords demandés à Doanh avant d'agir** : installation de PyTorch/ExecuTorch dans un venv du projet (≈3 Go), téléchargement d'un corpus (≈2-5 Go), calcul de plusieurs heures sur le PC.

## ContextLM français : chaîne validée de bout en bout (07/11/2026)
- Environnement : `mlenv` (torch 2.15 CPU, executorch 1.6.0, pyarrow ; 1,1 Go). Scripts : `ml\common.py` (normalisation + wyhash Python **vérifié identique au C++ sur le téléphone**, 12/12 mots), `prepare.py` (corpus -> vocabulaire + ids, en flux), `model.py` (embeddings exacts + hachés, 4 blocs convolution causale + MLP, E=64, L=16, 4,4 M de paramètres), `train.py` (softmax échantillonné, évaluation softmax complet), `export.py` (.pte XNNPACK + contrôle des opérateurs). Export : il faut `executorch\datain` dans le PATH (flatc.exe), sinon `FileNotFoundError`.
- **Mini-modèle** (8 min, 4,9 M de mots de Wikipédia fr, shard 16 = articles d'astéroïdes quasi identiques → ses scores de validation, perplexité 2 / top-1 80 %, ne signifient RIEN) : exporté en 17,6 Mo, **opérateurs identiques à ceux de `hungry_jellyfish` (7), aucun hors liste**, chargé dans l'appli (`futo-swipe/french_lm/`, codename provisoire `hungry_jellyfish`, entrée `SpecialContextLM("fr", ...)`), actif sur le téléphone : rejeu = top-1 32,4 % / top-4 67,3 % (contre 71,2 / 84,5 sans LM) → preuve que le LM agit sur le classement ; mauvais score normal (LM sans valeur + réglages d'un autre modèle).
- Pièges : le scoring (gamma, lambda, beta, alpha par couple de codenames) est **compilé dans l'.aar** (aucun chemin passé par la JNI) → un codename inconnu retombe sur les réglages « encodeur seul » (LM ignoré). Provisoire : codename `hungry_jellyfish`. Pour régler alpha/beta sur nos données il faudra recompiler `swipe-library` avec un accès aux réglages (`Config.gamma/lambda_/beta/alpha` existent déjà en C++) ou des entrées de scoring françaises.
- `adb install -r` conserve le clavier actif ; seul `force-stop` le remet sur Gboard.
- Vitesse d'entraînement CPU (batch × négatifs) : 256×4096 = 9,6 k mots/s · 512×2048 = 13,9 k · 512×1024 = 18 k · 1024×1024 = 19,7 k.
- Corpus réel : FineWeb-2 `fra_Latn/train/000_00000.parquet` (4,6 Go, licence odc-by) en cours de téléchargement dans `ml\data
aw\`.

## Entraînement du vrai ContextLM français (lancé le 07/11/2026 vers 21h15)
- Corpus : FineWeb-2 fr (`ml\dataw`) : 165 M de mots d'entraînement, 1,5 M de validation (3 000 premiers documents), vocabulaire 32 767 mots (couvre 94,0 %), 5,8 % de mots hors vocabulaire (hachés).
- Commande (processus caché, priorité basse, PID dans `mlunsw1.pid`) : `mlenv\Scripts\python.exe train.py --data dataw --out runsw1 --minutes 180 --batch 512 --neg 1024 --eval_every 1500 --lr 3e-3`. Journal : `mluns_fw1.log` ; point de reprise `mlunsw1\model.pt` (sauvé toutes les 1 500 étapes) ; fin prévue vers 00h15, écrit `runsw1esult.json`. Vitesse : ≈ 17 800 mots/s (≈ 190 M de mots vus = 1,15 époque). Ne pas lancer de calcul lourd en parallèle.
- Si le processus est arrêté (redémarrage du PC) : reprendre avec `--resume runsw1\model.pt --minutes <reste>` (le planning du taux d'apprentissage repart de zéro).
- Après l'entraînement : lire la perplexité/top-1 de validation (valeurs réelles, corpus de web), puis `export.py --run runsw1 --data dataw --out exportw1 --codename hungry_jellyfish --allowed ...`, copier dans `futo-keyboard\javassetsuto-swiperench_lm\`, `build.ps1`, `adb install -r`, rejeu.

## Test de la largeur de faisceau (07/11/2026, rejeu sur 587 mots)
beam 16 : 61,2 / 66,6 % · 32 : 66,6 / 75,6 · 64 : 68,5 / 79,7 · 100 : 69,3 / 81,9 · **300 : 71,2 / 84,5** · 600 et 1200 : identiques à 300 (le décodeur est créé avec beamWidth max = 300, `BeamValues.highestBeam`, donc au-delà de 300 le test ne change rien). Temps : 3 ms → 7 ms par mot.
Conclusion : la recherche est déjà saturée à 300, **ce n'est pas un levier** ; le plafond vient des scores du modèle (encodeur seul en français). Les aperçus pendant le swipe utilisent 32/64 et sont donc moins bons que le résultat final (normal).
Procédure de test sans réinstaller (une réinstallation OU un `force-stop` remet Gboard comme clavier actif) : lancer `am start -n org.futo.inputmethod.latin.unstable/org.futo.inputmethod.latin.SwipeRecorderActivity -f 0x18000000 --ez replay true --ei beam N` (nouvelle instance), attendre `replay_last.json`, `adb pull`.

## Diagnostic accents / apostrophes / dictionnaire (07/11/2026)
Outils : `donnees\diag.py` (échecs par type), `donnees\diag_dico.py` (contenu de `futo-keyboard\dictionariesr_wordlist.combined.gz`).
- **Le dictionnaire n'est PAS la cause principale** : 190 425 mots dont 27 756 élisions (l', d', s', n', qu'…) ; 334 des 337 mots testés y sont (absents : afrique, compliquons, déplia). Fréquences correctes (« bibliothèque », « d'une », « l'eau » présents).
- Le code natif gère déjà accents (lettre de base) et apostrophes (sautées dans le trie) : `native/jni/src/suggest/core/dictionary/dictionary_itrie.cpp`.
- Sur les 580 premiers essais : bon mot en tête 71 % ; **bon mot proposé mais pas en tête (rang 2-4) 13 %** (ex. dans/sans, tout/toit, cire/cie, père/mère, hésitante/hésitant) ; **absent du top-4 16 %** (21 mots jamais proposés sur 337).
  → rang 2-4 : un modèle de contexte français (ContextLM, P0-4) peut corriger une bonne part ; absent : limite de l'encodeur seul (décodeur AZERTY, P0-5).
- Parasites (neely, salinger, marty, benny, blair…) : ABSENTS de la liste source et du dico utilisateur du téléphone (253 octets) → viennent du dictionnaire compilé `java/res-large/raw/main_fr.dict`, qui diffère de la liste source. Non inspecté (format binaire ; il faudrait compiler `native/dicttoolkit`). Impact limité : surtout des candidats de rang 3-4.
- Réglages de scoring (gamma, lambda, beta) : lecture seule depuis l'appli dans l'.aar actuel ; les changer demande de modifier `scoring.json` (asset) ou de recompiler swipe-library. Piste à tester avec l'outil de rejeu.
- Hypothèse « corriger accents/apostrophes dans le dictionnaire » : réfutée. Priorité confirmée : outil de rejeu (P0-3) → ContextLM français (P0-4) → décodeur AZERTY (P0-5).

## Constats P0-2 (lecture du code, 07/11/2026)
- Appli : `futo-keyboard/java/src/org/futo/inputmethod/latin/SwipeDecoderDictionary.kt`. Décodeur spécial (`magic_macaw`) : seulement si langue = en ET lettres/positions = QWERTY ; ContextLM (`chosen_planarian`) : seulement langue = en. Dans les deux cas c'est codé en dur (listes `specialDecoders` et `contextLMs`). Pour le français AZERTY : encodeur seul + trie du dictionnaire français + paramètres `fallback`/`encoder:honorable_sturgeon` de `scoring.json`.
- Brancher un décodeur ou un LM français = ajouter une entrée dans ces deux listes + le modèle .pte + le vocab (pour le LM) ; la clé de scoring correspondante existe déjà dans `scoring.json`.
- `swipe-library` (gitlab) mentionne un LM `hungry_jellyfish` absent de l'APK : la lib est plus récente que l'.aar embarqué ; à vérifier.
- Piste rapide sans entraînement à tester d'abord : régler les paramètres de scoring (gamma, lambda, beta, beam) pour l'encodeur seul, et la qualité/fréquences du dictionnaire français. À juger sur le banc de mesure (P0-3), donc le banc passe avant tout entraînement.

## Feuille de route
### P0 — Indispensable
1. [terminé 07/11/2026] Environnement PC + APK d'origine compilé, installé et validé sur le Pixel.
2. [en cours] Modèles FUTO Swipe : récupérés. Reste : lire le rapport technique (arxiv 2606.25247), comprendre le format .pte et la recherche de mots (swipe-library, sources C++ sur gitlab.futo.org/keyboard/swipe-library), exécuter l'encodeur hors de l'appli (ExecuTorch Python).
3. [en cours] Banc de mesure. Fait : enregistreur dans l'appli + score de référence (voir ci-dessus). Reste : outil de **rejeu** des tracés enregistrés dans un décodeur modifié (pour comparer les versions sur les mêmes tracés), jeu de test séparé de l'entraînement.
4. [à venir] ContextLM français : entraînement, intégration, mesure.
5. [à venir] Décodeur AZERTY français : tracés simulés, entraînement, intégration, mesure.
6. [à venir] APK complet installé et validé sur le Pixel.
### P1 — Important
7. [à venir] Mode apprentissage personnel (tracés locaux + réentraînement).
8. [à venir] Dictionnaire perso (noms, mots fréquents de Doanh) prioritaire.
### P2 — Bonus
9. [à venir] Modèles vocaux Parakeet face à Whisper.
10. [à venir] Nettoyage de la dictée (ponctuation, « euh »).

## Problèmes connus / risques
- Code d'entraînement FUTO non public → reproduire l'architecture.
- Compatibilité PyTorch avec la GTX 970 à vérifier (sinon entraînement sur processeur, possible vu la taille des modèles).
- La bibliothèque swipe est un .aar précompilé : si on doit changer la recherche de mots, il faudra recompiler depuis swipe-library.
- Le build exige `PYTHONUTF8=1` sous Windows (géré par `build.ps1`).
- APK debug de 152 Mo (modèles vocaux inclus) : normal.

## Dernière session
07/11/2026 — Relevé des outils, clone de futo-keyboard, installation auto du NDK 28.2 par Gradle, 1er build en échec (updateLocales : encodage cp1252), corrigé par PYTHONUTF8=1, 2e build réussi en 14 min. Fichiers créés : `build.ps1`, `.gitignore`, `apk\ClavierFR-debug.apk`, `futo-keyboard\local.properties` (dans le clone). Logs : build1/2.log/.err. Aucun appareil détecté par adb.

## Prochaine tâche exacte
Attendre la fin de l'entraînement `runsw1` (≈ 00h15), vérifier `runs_fw1.log`, puis exporter, installer et rejouer (voir ci-dessus). Comparer top-1/top-4 à la référence 71,2 / 84,5 (sans LM).

## Session du 07-08/11/2026 (nuit) — premier ContextLM français réel
- Entraînement `ml/runs/fw1` terminé : 25 467 étapes, validation perplexité 199, top-1 13,3 %, top-4 26,8 % (texte web, mots exacts).
- Export OK (7 opérateurs, tous autorisés), installé sur le Pixel, rejeu 587 mots (beam 300) : **top-1 25,7 % / top-4 63,2 %** contre baseline 71,2 / 84,5 → **régression forte**, candidats aberrants (« SL », « SMUR », « Benny »).
- Cause trouvée (`ml/diag_oov.py`) : les tables hachées (mots hors vocabulaire) n'ont été entraînées qu'avec des positifs ; 99 % des mots inventés au hasard dépassent le meilleur mot réel. Un softmax ne fixe pas le niveau absolu → il faut ancrer.
- Correctif en cours : `ml/finetune_hash.py` (tables hachées seules, imitation des scores exacts + softmax) → `ml/runs/fw1h`. 2 min : 99 % → 18 %. Run de 15 min lancé.
- Suite : export de `fw1h` (codename hungry_jellyfish), assets, build, `adb install -r`, rejeu (`MSYS_NO_PATHCONV=1` sous Git Bash pour les chemins /sdcard), comparer à 71,2 / 84,5. Si encore pire : régler les paramètres de scoring (recompiler swipe-library) ou n'utiliser le LM que pour les mots du vocabulaire.

### Résultat (08/11/2026, ~01h30) — ContextLM français retenu
- `fw1h` (tables hachées recalibrées) + **pénalité 32** sur les mots hors vocabulaire LM (option `export.py --hash_penalty 32`) : rejeu 587 mots, beam 300 → **top-1 77,0 % / top-4 88,8 %** (baseline 71,2 / 84,5).
- Balayage pénalité : 0 → 37,8/74,8 ; 17 → 73,4/88,1 ; 20 → 75,6/88,6 ; 32 → 77,0/88,8 ; 40 → 76,7/88,8 ; 50 → 76,5/88,6 (plateau). Essais 10, 14, 26 : rejeu non rendu (artefact, script relancé automatiquement depuis).
- Limite : réglage et mesure sur les mêmes 587 mots (1 seul paramètre). Test honnête à faire : partager les phrases (train/test).
- Outils : `essai_penalite.ps1 -pen N -tag T` (export+build+install+rejeu), `ml/finetune_hash.py`, `ml/diag_oov.py`, `donnees/cmp_lm.py`.
- Livrable : `apk\ClavierFR-debug.apk` (pénalité 32 embarquée), installé sur le Pixel.
- Suite : validation sur nouvelles phrases / usage réel ; P0-5 décodeur AZERTY français ; scoring (gamma/lambda/beta/alpha) ; apprentissage personnel (P1).

### Réglage du scoring (08/11/2026) — conclusion : pas un levier
- Correction : `SCORING_ASSET`/`scoring.json` n'est **jamais lu** (le JNI n'envoie pas de `scoring_path`, le moteur utilise `DEFAULT_SCORING` compilé). Recompiler swipe-library est lourd (sous-module ExecuTorch absent, Makefile Linux). Solution retenue : `patch_aar.py` modifie à longueur égale les nombres du tableau texte dans `libswipe_jni.so` (original sauvegardé : `futo-swipe-release.aar.orig` ; `patch_aar.py - - - -` le restaure). Script de balayage : `essai_scoring.ps1 -alpha/-beta/-gamma/-lambda`.
- Rejeu sur 779 mots (tracés enregistrés au 08/11, baseline FUTO 71,2/83,7), réglage = 400 premiers, contrôle = 379 derniers. Valeur actuelle : 75,6/86,9.
- `alpha` 0,3→1,2 : total 75,0–75,7 / 86,1–87,0 (plat). `beta` 1,5→5 : 72,9–76,3 / 85,8–86,8 (meilleur 4,0 : 76,3/86,4, plat vs actuel). Aucun gain net → réglages d'origine conservés (AAR restauré, installé).
- Reste des erreurs (rejeu 587 mots) : 66 absents du top-4 (géométrie : décodeur EN/QWERTY, mots accentués, apostrophes 14/18 ratées), 69 en rang 2-4. → levier suivant = décodeur AZERTY français (P0-5) et/ou dictionnaire personnel (P1).

### Dictionnaire de fréquence personnel (08/11/2026) — implémenté, installé
- Constat : le moteur décode séparément principal / utilisateur / historique (bonus fréquence = lambda 0,022 × log-fréquence, très faible). Le rejeu n'a que 2 tries et couper le 2e ne change rien (75,6/86,9) : l'historique FUTO n'aide pas le swipe, et les mesures n'étaient pas gonflées par lui.
- `PersonalFrequency.kt` : compteur local de mots validés (`filesDir/personal_freq.json`, jamais envoyé), alimenté par `GeneralIME.addToHistory` (mots tapés/swipés). Au swipe : 8 candidats demandés au moteur, reclassés par `score + poids × ln(1+occurrences)`, 4 gardés, avec garantie du meilleur candidat géométrique (comme le moteur natif ; sans elle le top-4 chutait de 1,4 pt).
- Mesure (rejeu 779 mots, compteurs bâtis sur les cibles, mot testé exclu) : poids 0 → 75,6/86,9 ; 0,3 → 76,0/86,9 ; **0,6 → 76,8/87,0** ; 1,0 → 76,4/87,2 ; 1,6 → 76,1/87,5. Poids retenu 0,6 (`PersonalFrequency.weight`). Gain ≈ +1 pt top-1, modeste : le test n'a que 48 phrases littéraires, ce n'est pas ton vocabulaire réel.
- Pas encore fait : (1) dictée vocale → compteur (probablement hors chemin `addToHistory`, à vérifier dans le code de la dictée) ; (2) mots absents du dictionnaire (noms propres) : ils restent inaccessibles tant qu'ils ne sont pas dans un trie ; (3) validation en usage réel (le fichier se remplit en tapant) ; (4) outils : `rejeu.ps1 -tag T [-pf 60] [-tries 1]`.

### Ajout automatique des mots au dictionnaire (08/11/2026) — implémenté, validé par test synthétique
- Cause racine trouvée : sur le Pixel, `pref_key_use_personalized_dicts` valait **false** (FUTO « Personalized suggestions » désactivé) → aucun apprentissage (ni historique FUTO, ni `PersonalFrequency`, car tous deux passent par `addToHistory`). Activé avec l'accord de Doanh (`perso.ps1 -on $true`, écrit via l'app, sans force-stop). Réversible dans les réglages du clavier.
- Mécanisme FUTO existant (saisie) : un mot inconnu tapé est ajouté à `userunigram.fr.dict` (historique), qui est l'un des tries du swipe → atteignable. Preuve : « Doanh » et « ia » appris à la main, « doanh » sort en 1er pour un geste parfait.
- Ajouté : la **dictée** n'alimentait rien (texte écrit via `commitText`). Hook dans `VoiceInputAction.finished` → `GeneralIME.learnFromDictation(texte)` : compteur de fréquence + `addToUserHistory` ; si un mot est inconnu, invalidation des tries (`onAnyBinaryDictionaryClosed`), reconstruits au prochain swipe (≈ 1 ms). `PersonalFrequency.save` aussi à `onFinishInput`.
- Test (outil `synth.ps1`, geste parfait par les centres de touches, mots inventés « zorgblatt »/« clavierfr ») : avant apprentissage inatteignables ; après `learnFromDictation` → 1er candidat. Oubli (`-forget`) les retire. **Niveau : appareil réel, mais avec la fonction appelée par adb, pas avec de la vraie voix** ; la vraie dictée reste à essayer par Doanh.
- Limites : (1) un mot mal reconnu par la dictée entre dans le dictionnaire (pas de détection de correction ultérieure) ; (2) l'historique FUTO est écrit sur disque avec retard : un mot appris juste avant un arrêt forcé du processus (ex. `adb install -r`) est perdu ; (3) un mot appris reste « demoted » côté FUTO (fréquence invalide) mais atteignable.
- Outils : `synth.ps1 -words a,b [-learn "x,y"] [-forget "x"]`, `perso.ps1 -on $true|$false`, `rejeu.ps1`. Les mots de test ont été oubliés ; l'historique ne contient que « Doanh » et « ia ».

## Calibration du geste : expérience hors ligne (08/11/2026)
- Jeu : 779 premiers essais (traces_fr.jsonl re-tiré du téléphone, 1143 lignes ; ancienne copie : donnees/traces_fr_877.bak).
- Mesure : écart entre le point de départ / d'arrivée du doigt et le centre de la première / dernière lettre du mot visé (coordonnées normalisées, une touche ≈ 0,1 de large).
  Décalage moyen : départ dx -0,011 dy +0,002 ; arrivée dx -0,003 dy +0,003. Dispersion : 0,08 à 0,12 (≈ une touche).
- Conclusion : **aucun biais systématique** (moyenne ≈ 3 à 10 % d'une touche, bruit ≈ 100 %). Une calibration par décalage/échelle ne peut rien rapporter chez Doanh. Niveau de validation : mesure indirecte (indicateur de biais), pas un rejeu avec correction ; jugée inutile car l'ordre de grandeur est sans appel.
- Utile à garder pour un autre utilisateur : l'outil de mesure est trivial à relancer sur ses propres traces.
- Décision : la valeur de la collecte de traces est d'abord de fournir des données d'entraînement (décodeur AZERTY), pas de calibrer.

## Collecte des gestes dans l'appli (08/11/2026)
- Code : `TraceCollector.kt` (nouveau), hooks dans `SwipeDecoderDictionary` (fin de swipe → geste gardé en mémoire), `InputLogic.commitChosenWord` (mot validé → écriture), `GeneralIME.onFinishInput` (oubli du geste en attente). Réglages : Texte prédictif > « Collecter mes gestes » (désactivé par défaut) + « Effacer les gestes collectés » (affiche le nombre).
- Garde-fous : rien si champ sensible (`mNoLearning` : mot de passe, code, incognito) ou autocorrection coupée (e-mail, URL) ; seulement si le mot vient d'un swipe non retouché ; geste de moins de 4 points ignoré ; mot hors propositions accepté seulement si le geste commence près de sa 1re lettre ; plafond 40 Mo.
- Fichier : `collecte_gestes.jsonl` (dossier externe privé de l'appli ; même format que traces_fr.jsonl + `label` = top1 / alt / other). Récupération : `adb pull /sdcard/Android/data/org.futo.inputmethod.latin.unstable/files/collecte_gestes.jsonl`.
- Test (Pixel, gestes simulés par `adb shell input motionevent`, outil `swipe_adb.py`) : collecte activée → 1 ligne par mot swipé et validé, bon label ; collecte désactivée → rien. Interrupteur de test : `am start ... SwipeRecorderActivity --ez collect true|false`.
- Niveau : testé sur appareil réel avec gestes simulés. **Non testé** : champ mot de passe réel (on s'appuie sur `mNoLearning`, la garde de FUTO), choix manuel d'une autre suggestion (label alt), usage réel prolongé.
- Limite connue : le label « top1 » signifie « accepté », pas « correct » (un mot faux non corrigé est enregistré tel quel) ; à filtrer à l'entraînement.
- Test fait dans l'enregistreur : traces_fr.jsonl restauré à l'identique (1143 lignes) après le test.

## Version « ami » (08/11/2026)
- Livrable : `apk\ami\ClavierFR.apk` (167 Mo) + `LICENCE-FUTO.md` + `LISEZMOI.txt` ; commande `.\build_ami.ps1` (saveur Gradle `ami`, release non minifiée, signée avec `C:\Users\Doanh\ClavierFR-cles\clavierfr.jks` — HORS projet, À SAUVEGARDER).
- Vérifié sur l'APK : id `org.futo.inputmethod.latin.clavierfr`, nom « ClavierFR », non débogable, signature = clé perso (SHA-256 ed5766c4…), pas d'enregistreur de dev, **pas de permission INTERNET**, aucune donnée perso (traces, historique) dans le fichier.
- Testé sur le Pixel (installé à côté de la version dev, puis désinstallé) : le clavier s'active, démarre en AZERTY français, swipe de 3 mots OK (build release), assistant d'installation en 2 étapes OK. Clavier dev remis par défaut.
- Non testé : dictée vocale sur la version ami (import du modèle téléchargé sur keyboard.futo.tech), mise à jour par-dessus, autre téléphone qu'un Pixel 6a, apprentissage/collecte sur la version ami.
- Licence FUTO lue : distribution gratuite non commerciale OK si texte de licence joint + mention de modification (faite : nom, LISEZMOI, titre des réglages) + fonction de paiement conservée.
- Réglages calés sur les gestes de Doanh (poids fréquence 0,6, pénalité LM 32) : valeurs non vérifiées sur un autre utilisateur.

## Tests version ami sur le Pixel — en cours (08/11/2026)
- Import du modèle vocal sur la version ami : OK (ouverture du fichier avec ClavierFR → choix « français (fr_FR) » → 264 Mo copiés dans le dossier de l'appli ami). Dictée elle-même : **pas encore testée** (demande la voix de Doanh).
- Constat : l'app s'affichait « Clavier FUTO » en français (traductions FUTO prioritaires sur la saveur) → ajout de `java/ami/res/values-fr/strings-appname.xml` ; APK reconstruit (nom « ClavierFR » dans toutes les langues), pas encore installé sur le Pixel.
- Constat : **Avast One signale l'appli comme « suspecte »** (clavier + micro, APK hors Play Store). À mettre dans le guide de l'ami ; décision de Doanh sur l'alerte du Pixel en attente.
- AAR `libs/futo-swipe-release.aar` : contenu identique à l'original (seulement ré-empaqueté) → le dépôt public peut renvoyer à l'AAR amont.
- Dépôt public / store : NON commencés (attendent la fin des tests et l'accord).

## Publication (08/11/2026)
- Tests Pixel avant publication : mise à jour par-dessus OK (modèle vocal conservé), dictée à la voix OK (phrase reconnue, une erreur « genêts » → « gênés »), apprentissage OK (mot inventé tapé 2 fois devenu swipeable), import du modèle OK. L'APK 1.0.0 final n'a été reconstruit qu'avec versionName 1.0.0 après ces tests (pas retesté sur le téléphone).
- Dépôt public : https://github.com/Kamikazz60/ClavierFR (overlay des fichiers FUTO modifiés + modèle français + outils ; commits sous l'adresse noreply de GitHub). Release v1.0.0 : ClavierFR.apk (SHA-256 0270150417…b69a), LICENCE-FUTO.md, LISEZMOI.txt. Dossier de préparation local : `Programme IA\ClavierFR-depot`.
- Store Ruche : fiche `clavierfr` ajoutée (audit « points de vigilance »), déployée sur GitHub Pages.
- À faire : retirer le chemin de compilation des bibliothèques natives (option de compilation file-prefix-map) ; changer l'icône de l'appli (c'est encore le logo FUTO) ; avertissement Avast à surveiller ; retester l'APK 1.0.0 final sur le Pixel si besoin.

## Version 1.0.1 et installation sur le Pixel (08/11/2026)
- Nouvelle icône ClavierFR (flavor ami : `java/ami/res/drawable/ic_launcher_foreground.xml`, couleur de fond, icône Android 7) ; versionName 1.0.1, versionCode 11769 (à incrémenter à chaque version distribuée).
- ClavierFR 1.0.1 installé sur le Pixel de Doanh, clavier par défaut, modèle vocal importé, collecte de gestes activée (0 geste au départ ; 2 gestes de test effacés). Icône vérifiée à l'écran. Le Pixel garde aussi la version de développement (outil de rejeu, traces).
- Release GitHub v1.0.1 publiée, dépôt mis à jour, fiche Ruche mise à jour (déploiement Pages OK). Audit refait sur la 1.0.1 (permissions identiques, pas d'Internet, pas de secret).
- Constat : cadre « Avis de mise à jour » dans les réglages de la version ami (pas d'Internet) ; Avast signale l'appli à chaque installation.
- Reste à faire : retirer le chemin de compilation des bibliothèques natives ; mesurer sur d'autres utilisateurs ; décodeur AZERTY.

## Premier benchmark en conditions réelles (ClavierBench, 08/11/2026)
Phrases françaises recopiées en swipe sur le Pixel 6a, 5 sessions (niveau 5 : appareil réel, mais petit échantillon et nom du clavier saisi à la main).
- Gboard : 88,6 % des mots justes du premier coup (265/299), 17 retours arrière pour 299 mots.
- ClavierFR : 74,6 % (223/299), 158 retours arrière ; version de développement : 72,2 % (70/97, 1 seule session). Soit à peu près le niveau de FUTO : l'objectif « mieux que Gboard » n'est PAS atteint.
- Le 75,6 % de notre rejeu hors ligne (mots isolés) n'avait jamais été comparé à Gboard ; on le retrouve en phrases réelles (75,7 %).
- Erreurs ClavierFR : mots courts voisins (les/mes, l/m, fait/faut, le/me, si/soir), accents (a/à, ou/où, acheter/acheté, atteindre/éteindre), quelques vrais ratés de géométrie (bonjour, aujourd'hui, retard, pourrais).
- Limite de l'outil : l'identifiant du clavier détecté (imeId) est périmé dans 3 sessions sur 5 ; les noms saisis à la main concordent avec les scores. À corriger (relever le clavier à chaque phrase).
- Biais possible : ClavierFR (ami) est neuf, sans mots appris ; Gboard a des mois d'apprentissage.

### Étude du décodeur AZERTY (08/11/2026) — conclusion : à ne PAS faire en priorité
- Correction d'une erreur d'analyse : j'avais présenté le décodeur AZERTY comme le plus gros levier. Le rapport FUTO (arXiv 2606.25247, Table 3, lu via le HTML, certains chiffres de l'annexe non vérifiés) montre que leur décodeur n'apporte que +0,55 à +0,76 point de top-1 en anglais, avec 1,04 M de gestes réels. Avec ~1 100 gestes (tous de Doanh), le gain attendu est négligeable face aux 14 points d'écart avec Gboard.
- Faisabilité technique : décodeur = petit réseau DFSMN (304 k paramètres) sur les sorties gelées de l'encodeur ; le runtime ExecuTorch Python marche sur le PC ; mais PyTorch est CPU seul (GTX 970, capacité 5.2, non utilisable) et le code d'entraînement FUTO n'est pas public. Pas de jeu de gestes français/AZERTY public.
- Même l'encodeur FUTO fait 92,5 % top-1 en anglais/QWERTY (mots isolés) contre 75,6 % chez nous en français : l'écart vient surtout du français (accents, apostrophes, mots courts, dictionnaire, modèle de langue), pas de la disposition. Pistes réelles à évaluer : ré-entraîner/affiner l'encodeur sur du français (poids à extraire du .pte, architecture dans le rapport), modèle de langue/contexte plus fort (rang 2-4 = 11 % des mots), apprentissage perso.
- Gboard n'est pas comparé dans le rapport FUTO (seulement SHARK2).

## Version 1.1.0 « Dictée locale » (08/11/2026) — mode dictée seule, nouveau nom et icône
- Nouveauté : réglage « Mode dictée seule » (Saisie vocale, défaut désactivé). Depuis Gboard, appui long sur le globe > Dictée locale : la dictée démarre seule, le texte est inséré, puis retour automatique au clavier précédent (`VoiceOnlyMode.kt`, hooks dans `LatinIME.onStartInputView` et la fermeture des fenêtres de dictée). Pas de démarrage dans les champs de mot de passe.
- Niveau 5 (Pixel 6a, Gboard + Dictée locale) : ouverture automatique, retour par la flèche, dictée vocale réelle validée par Doanh (texte inséré + retour à Gboard). Non testé : autres applis que ClavierBench, champ mot de passe, autres téléphones.
- Constat : un appui COURT sur le globe de Gboard ne change que la langue de Gboard (FR/EN/RU) ; il faut l'appui LONG pour choisir un autre clavier.
- Nouveau nom « Dictée locale » (libellés seulement ; l'identifiant technique `org.futo.inputmethod.latin.clavierfr` est conservé pour que la mise à jour par-dessus fonctionne) et nouvelle icône micro + bulle de texte. Livrable : `apk\ami\DicteeLocale.apk`.
- À faire : publier (dépôt GitHub encore nommé ClavierFR, release, fiche Ruche) après accord de Doanh ; installateur : l'APK 1.0.1 publié s'appelle encore ClavierFR.apk.
- Publié le 08/11/2026 : dépôt (commit 2926c69, nom GitHub inchangé « ClavierFR »), Release v1.1.0 (DicteeLocale.apk, SHA-256 ead67cf7…db6b, 167 131 943 octets), fiche Ruche mise à jour et déployée (catalogue en ligne : « Dictée locale » 1.1.0, APK téléchargeable). Audit refait sur la 1.1.0 : même certificat, mêmes permissions, pas d'Internet, non débogable. Reste : chemin de compilation dans les bibliothèques natives ; ClavierBench à corriger (relever le clavier à chaque phrase).
