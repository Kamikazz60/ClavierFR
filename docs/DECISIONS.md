# DÉCISIONS — ClavierFR

## 07/11/2026 — Partir de FUTO Keyboard
Décision : modifier FUTO Keyboard plutôt que créer un clavier de zéro.
Raison : la dictée FUTO convient déjà à Doanh ; FUTO Swipe fournit une base réutilisable (encodeur universel, bibliothèque d'inférence GPL).
Alternatives écartées : HeliBoard (swipe via bibliothèque Google fermée, même qualité que Gboard), WhisperType (pas de swipe), clavier de zéro (beaucoup plus long).
Conséquences : licence FUTO Source First → usage personnel uniquement, pas de dépôt public ni de redistribution.

## 07/11/2026 — Priorité au swipe français AZERTY
Décision : le travail porte d'abord sur la prédiction du swipe, en français seul et en AZERTY.
Raison : demande de Doanh ; c'est le seul point qui ne le satisfait pas dans FUTO.
Conséquences : la dictée reste celle de FUTO ; les améliorations vocales passent en P2.

## 07/11/2026 — Décider sur mesures
Décision : chaque changement du swipe est jugé sur un jeu de tracés réels de Doanh (erreur top-1/top-4).
Raison : le ressenti seul ne permet pas de comparer les versions.

## 07/11/2026 — Collecte de tracés par un texte littéraire dans le clavier lui-même
Décision : enregistrer les tracés de Doanh dans un écran du fork (hook dans SwipeDecoderDictionary), en tapant des phrases connues, plutôt que dans une appli séparée.
Raison : idée de Doanh ; le tracé est capté avec la vraie géométrie du clavier et le vrai décodeur, donc score de référence immédiat et données réutilisables pour l'entraînement.
Alternatives écartées : appli d'enregistrement séparée (géométrie différente du vrai clavier).
Conséquences : ne comparer que les premiers essais (le bouton Refaire biaise) ; données personnelles dans `donnees\` (hors Git).

## 07/11/2026 — Concevoir notre propre ContextLM français
Décision : écrire et entraîner nous-mêmes un ContextLM français conforme au contrat de la bibliothèque swipe, au lieu de réutiliser une recette FUTO.
Raison : le rapport technique ne décrit pas le ContextLM ; le contrat d'entrée/sortie est lisible dans swipe-library ; 13 % des mots sont proposés mais pas en tête, cible naturelle d'un modèle de contexte.
Alternatives écartées : attendre une recette publique (inexistante), tout recompiler la bibliothèque (inutile tant que les opérateurs restent dans la liste).
Conséquences : installation de PyTorch/ExecuTorch et téléchargement d'un corpus (soumis à l'accord de Doanh) ; première chaîne complète sur un mini-modèle avant le gros entraînement.

## 08/11/2026 — Tout l'apprentissage est par installation
Décision : fréquences, mots appris, traces et réglages vivent dans le stockage privé de l'appli ; rien de personnel dans l'APK ; collecte de traces désactivée par défaut (consentement), exclue des champs mot de passe, effaçable ; outils d'enregistrement/rejeu réservés au développement.
Raison : Doanh pourrait donner l'appli à un ami. Alternative écartée : réglages codés en dur sur les traces de Doanh.
À vérifier avant toute remise à un tiers : licence FUTO Source First (« pas de redistribution publique »), APK propre et signature stable.

## 08/11/2026 — Pivot : l'appli devient « Dictée locale » (dictée seule + clavier habituel)
Décision : après le benchmark (Gboard 88,6 % contre 74,6 % en swipe), Doanh garde Gboard pour écrire et utilise notre appli pour la dictée FUTO hors ligne, via un « mode dictée seule » avec retour automatique. Nom « Dictée locale » (choix de Doanh), icône micro + bulle.
Raison : le swipe français n'atteint pas Gboard et aucune voie courte n'existe ; la dictée est le vrai point fort.
Alternatives écartées : bouton flottant par accessibilité (permission sensible, restreinte sous Android 17) ; décodeur AZERTY (gain attendu < 1 point).
Conséquence : l'identifiant technique reste `...latin.clavierfr` (renommer casserait la mise à jour et ferait perdre le modèle vocal importé).
