# ClavierFR (nom provisoire) — instructions du projet
(Règles générales : skill developpement-pro. En cas de conflit, ce fichier et la sécurité priment.)

## 1. Présentation
Objectif : clavier Android avec un swipe en **français AZERTY** nettement meilleur que FUTO Keyboard (et si possible que Gboard), en gardant la dictée vocale hors ligne de FUTO, que Doanh a validée.
Plateforme cible : Android, Google Pixel 6a (Android 17, API 37).
Livrable attendu : APK autonome, 100 % hors ligne, pour usage personnel (store perso de Doanh).
Public : Doanh uniquement. Langue : français seul, disposition AZERTY.

## 2. Environnement (vérifié le 07/11/2026)
Espace cloud de Claude : Linux, 2 CPU, 7 Go de RAM, pas de GPU, Java 21, Gradle, Python 3, git. **Pas de SDK Android ni de PyTorch installés.**
Réseau du cloud (testé) : GitHub OK (git), dl.google.com OK ; **gitlab.futo.org et huggingface.co bloqués** → impossible d'y récupérer les sous-modules de FUTO Keyboard et les modèles FUTO Swipe.
Machine de compilation prévue : PC fixe de Doanh (i5-6600K, GTX 970 4 Go, 24 Go de RAM, Windows). À vérifier : Android Studio, SDK/NDK, Python, PyTorch compatible GTX 970.
Emplacement du projet : C:\Users\Doanh\Desktop\Programme IA\clavierPers (connecté).
Emplacement des livrables : `clavierPers\apk\` (ignoré par Git).
Note : depuis le PC fixe, GitHub ET gitlab.futo.org sont accessibles (clone complet réussi) ; les restrictions réseau ci-dessus ne valent que pour le cloud.

## 3. Outils installés sur le PC fixe (vérifiés le 07/11/2026)
Git 2.55, Python 3.12.10 (PATH), Node 24, Android Studio, SDK Android `C:\Users\Doanh\AppData\Local\Android\Sdk` (plateformes 35/36/37, build-tools 34-36, platform-tools, NDK 28.2.13676358 installé par Gradle). **JDK 17 Temurin** `C:\Users\Doanh\Documents\Codex\AndroidDev\java\jdk-17.0.20.1+1` (pas dans le PATH, le build le fixe). Gradle 8.14.3 via wrapper. adb : `...\Sdk\platform-tools\adb.exe` (pas dans le PATH). Pas de PyTorch vérifié. Espace libre C: ≈ 800 Go.

## 4. Appareils
Pixel 6a (Android 17). Au 07/11/2026 aucun appareil détecté par `adb devices` : brancher en USB avec le débogage USB activé.
Émulateur : non vérifié (peu utile pour juger un swipe : le test se fait sur le vrai téléphone).

## 5. Réseau et autorisations
Sources nécessaires : github.com/futo-org/android-keyboard (+ sous-modules gitlab.futo.org), huggingface.co/futo-org/futo-swipe (modèles), jeu de 1 M de tracés FUTO (Hugging Face, MIT), corpus de textes français.
Actions qui nécessitent Doanh : connecter le dossier du projet, installer les outils sur le PC, brancher le Pixel, enregistrer ses propres tracés de test.

## 6. Architecture (prévue)
- Base : fork de FUTO Keyboard (licence FUTO Source First 1.1-kb (lue le 08/11/2026) : modification et redistribution autorisées **gratuitement et sans but commercial**, à condition de joindre le texte de la licence, d'indiquer clairement que le logiciel est modifié, de ne retirer aucune mention FUTO ni la fonction de paiement. Vente interdite).
- Dictée : celle de FUTO, inchangée.
- Swipe : bibliothèque d'inférence FUTO Swipe (C++, GPL) avec 3 modèles :
  - encodeur universel FUTO (réutilisé) ;
  - **ContextLM français** (à entraîner sur du texte français) ;
  - **décodeur AZERTY français** (à entraîner sur des tracés simulés + tracés réels de Doanh).
- Outils PC (Python) : générateur de tracés simulés, entraînement, banc de mesure.
- Mode apprentissage : tracés + mot validé enregistrés localement, réentraînement périodique.

## 7. Contraintes
100 % hors ligne, aucune donnée envoyée. Modèles légers (FUTO Swipe ≈ 2,5 M de paramètres) pour rester rapides sur le Pixel 6a.
Risque principal : le code d'entraînement FUTO n'est pas public ; il faut reproduire l'architecture à partir de leur rapport technique pour produire des modèles compatibles.
Hors périmètre : autres langues, QWERTY, publication publique du fork.

## 8. Commandes
- Compilation + copie du livrable : `.\build.ps1` (à la racine ; fixe JAVA_HOME et `PYTHONUTF8=1`, nécessaire sinon la tâche `updateLocales` plante sur l'encodage cp1252). Première compilation : 14 min ; ensuite plus rapide (cache Gradle).
- Livrable : `apk\ClavierFR-debug.apk` (≈ 152 Mo, signé avec la clé debug du dépôt, id `org.futo.inputmethod.latin.unstable`).
- Source FUTO : `futo-keyboard\` (clone de github.com/futo-org/android-keyboard avec sous-modules ; `local.properties` pointe vers le SDK).
- Modèles swipe FUTO déjà présents : `futo-keyboard\java\assets\futo-swipe\` (honorable_sturgeon = encodeur, magic_macaw = décodeur EN/QWERTY, chosen_planarian = ContextLM EN). La bibliothèque d'inférence est fournie compilée : `futo-keyboard\libs\futo-swipe-release.aar`.

## 9. Particularités
Mesure de qualité : taux d'erreur top-1 et top-4 sur un jeu de tracés réels de Doanh (même méthode que FUTO). Une amélioration n'est retenue que si elle est mesurée.

## 10. Version « ami » (ajoutée le 08/11/2026)
- Saveur Gradle `ami` (id `org.futo.inputmethod.latin.clavierfr`, nom « Dictée locale » depuis la 1.1.0), build release non minifié, sans enregistreur de dev, sans vérif. de mises à jour FUTO. Commande : `.\build_ami.ps1` → `apk\ami\DicteeLocale.apk` + `LICENCE-FUTO.md` + `LISEZMOI.txt`.
- Signature : clé personnelle `C:\Users\Doanh\ClavierFR-cles\clavierfr.jks` + `cle.txt` (HORS projet, à sauvegarder : sans elle, plus de mise à jour par-dessus). Passée à Gradle par variables d'environnement `CLAVIERFR_KS_*`.
- Le modèle vocal n'est pas dans l'APK : l'ami doit le télécharger une fois sur keyboard.futo.tech puis l'importer.
