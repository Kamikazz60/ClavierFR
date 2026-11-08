# Dictée locale (anciennement ClavierFR)

**Dictée vocale française 100 % hors ligne** pour Android, avec le modèle vocal de FUTO, utilisable avec **ton clavier habituel** (Gboard…).
C'est une **version modifiée de [FUTO Keyboard](https://github.com/futo-org/android-keyboard)**. Elle n'est ni éditée ni soutenue par FUTO.
Le dépôt garde son ancien nom « ClavierFR » : le projet est né comme un clavier à swipe français, puis a changé de vocation (voir ci-dessous).

> Télécharger l'application : onglet **Releases** (fichier `DicteeLocale.apk`, guide `LISEZMOI.txt` inclus). Aussi disponible dans le store personnel « Ruche » : https://kamikazz60.github.io/Mon-Android-Store/

## Comment on l'utilise (version 1.1.0)

1. Active « Mode dictée seule » dans Réglages > Saisie vocale.
2. Dans un champ de texte, avec Gboard : **appui long** sur l'icône globe, choisis « Dictée locale ».
3. La dictée démarre seule ; le texte est inséré, puis tu retrouves ton clavier habituel.

Testé sur un Pixel 6a (Android 17) avec Gboard. Pas de démarrage dans les champs de mot de passe.

## Pourquoi ce changement de cap

Le projet visait un swipe français meilleur que Gboard. Mesuré sur le téléphone de l'auteur (5 sessions de phrases recopiées en swipe, petit échantillon) : **Gboard 88,6 % de mots justes du premier coup, ce fork 74,6 %**, soit à peu près le niveau de FUTO. L'objectif n'est donc pas atteint ; le point fort réel est la dictée hors ligne. Détails et pistes écartées : [`docs/SUIVI.md`](docs/SUIVI.md).

## Ce que ça change par rapport à FUTO Keyboard (swipe français, toujours présent)

- **Modèle de langue français pour le swipe** (ContextLM de 4,4 M de paramètres, entraîné sur du texte web français), à la place du modèle anglais. Le décodeur de gestes, lui, reste celui de FUTO (voir « Limites »).
- **Fréquence personnelle** : les mots que tu valides sont mémorisés localement et favorisent tes mots habituels au swipe.
- **Apprentissage automatique des mots** tapés ou **dictés** (les noms propres, le jargon deviennent atteignables au swipe).
- **Collecte locale optionnelle de gestes** (désactivée par défaut) : paires « geste / mot validé » gardées sur le téléphone pour améliorer plus tard le décodeur. Jamais dans les mots de passe, e-mails, adresses web ni en mode privé. Réglages > Texte prédictif.
- Nom « Dictée locale » et icône propres (dessin original, différent du logo FUTO) ; l'assistant d'installation affiche encore le nom FUTO.
- Version « ami » : nom et identifiant propres (`org.futo.inputmethod.latin.clavierfr`), **aucune permission Internet**, pas de recherche de mises à jour, pas d'outil de développement.
- La **dictée vocale** est celle de FUTO, inchangée. Le modèle vocal n'est pas inclus : au premier usage, touche le message « aucun modèle » du panneau de saisie vocale (ou va sur https://keyboard.futo.tech/voice-input-models), télécharge le modèle français et ouvre-le avec Dictée locale.

## Mesures (honnêtes)

Mesure par rejeu sur **779 premiers essais de swipe d'un seul utilisateur** (l'auteur, Pixel 6a, phrases littéraires), les mêmes gestes décodés par chaque version :

| Version | Mot voulu en 1er | Dans les 4 propositions |
|---|---|---|
| FUTO Keyboard d'origine (français) | 71,2 % | 83,7 % |
| Ce fork (swipe français) | 75,6 % | 86,9 % |

C'est une mesure sur **un seul utilisateur** et un seul téléphone, pas un banc d'essai indépendant. Les réglages (poids de la fréquence personnelle, pénalité du modèle de langue) ont été choisis sur ces mêmes gestes. Le détail, y compris les essais qui n'ont rien apporté, est dans [`docs/SUIVI.md`](docs/SUIVI.md).

## Limites connues

- Environ 66 mots sur 779 n'apparaissent même pas dans les 4 propositions : erreurs de géométrie du décodeur FUTO (conçu pour QWERTY). Un décodeur AZERTY dédié reste à faire ; il demande des gestes réels (d'où la collecte optionnelle).
- Les mots avec apostrophe (« l'ami ») sont souvent ratés au swipe.
- Un mot mal reconnu à la dictée est appris tel quel.
- Testé uniquement sur un Pixel 6a (Android 17). Certains antivirus (Avast One, observé) signalent l'appli comme « suspecte » : c'est un clavier avec micro, installé hors Play Store.

## Compiler soi-même

Prérequis : Windows, git + git-lfs, JDK 17, SDK Android (variable `ANDROID_HOME`), NDK installé par Gradle.

```powershell
.\setup.ps1          # clone FUTO Keyboard à la version de référence (base.txt), applique overlay\ et modele-fr\
.\build.ps1          # version de développement (signée avec la clé debug publique de FUTO)
```

Version à distribuer (signée avec **ta** clé, à créer une fois et à sauvegarder) :

```powershell
mkdir $env:USERPROFILE\ClavierFR-cles
keytool -genkeypair -keystore $env:USERPROFILE\ClavierFR-cles\clavierfr.jks -alias clavierfr -keyalg RSA -keysize 2048 -validity 12000
# crée cle.txt dans le même dossier, avec deux lignes :  alias=clavierfr   puis   motdepasse=<ton mot de passe>
.\build_ami.ps1      # -> apk\ami\DicteeLocale.apk
```

Contenu du dépôt : `overlay/` (fichiers de FUTO Keyboard modifiés ou ajoutés, mêmes chemins que dans `futo-keyboard/`), `modele-fr/` (ContextLM français), `ml/` (entraînement et export du modèle, Python), `outils/` (rejeu, tests, analyses ; chemins de l'auteur à adapter), `docs/` (suivi, décisions).

## Licences et crédits

- Basé sur **FUTO Keyboard** © FUTO Holdings, Inc., sous licence **FUTO Source First 1.1-kb** ([`LICENCE-FUTO.md`](LICENCE-FUTO.md)) : redistribution gratuite et non commerciale uniquement. **Ce logiciel est une version modifiée** de FUTO Keyboard. Les marques FUTO appartiennent à FUTO Holdings, Inc. Ne pas vendre ce logiciel.
- Le moteur de swipe est la bibliothèque **FUTO Swipe** (GPL) : https://gitlab.futo.org/keyboard (non modifiée ; seul le modèle de langue français est ajouté). Les modèles FUTO Swipe sont récupérés depuis https://huggingface.co/futo-org/futo-swipe.
- Le modèle de langue français a été entraîné sur **FineWeb-2** (`fra_Latn`), licence ODC-By 1.0 : https://huggingface.co/datasets/HuggingFaceFW/fineweb-2.
- Les fichiers de ce dépôt (`overlay/`, `modele-fr/`, `ml/`, `outils/`) sont diffusés dans le cadre de cette même licence FUTO Source First pour ce qui dérive de FUTO Keyboard.
