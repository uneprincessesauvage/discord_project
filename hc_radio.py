import os
import re
import requests
import feedparser
from datetime import datetime
from pathlib import Path

API_KEY = os.environ.get("OPENROUTER_API_KEY")

FLUX_RSS = [
    "https://www.numerama.com/feed/",
    "https://www.futura-sciences.com/rss/actualites.xml",
    "https://elevatorworld.com/feed",
]

DOSSIER = Path.home() / "radio-ia"


def recuperer_actualites():
    articles = []

    for url in FLUX_RSS:
        print(f"Lecture du flux : {url}")

        try:
            flux = feedparser.parse(url)

            if getattr(flux, "bozo", False):
                print(f"Attention : flux potentiellement incomplet : {url}")

            for article in flux.entries[:4]:
                titre = article.get("title", "")
                resume = article.get("summary", "")
                lien = article.get("link", "")

                if titre:
                    articles.append(
                        f"Titre : {titre}\n"
                        f"Résumé : {resume[:600]}\n"
                        f"Source : {url}\n"
                        f"Lien : {lien}\n"
                    )

        except Exception as erreur:
            print(f"Flux ignoré : {erreur}")

    return articles


def generer_emission(articles):
    if not API_KEY:
        raise RuntimeError(
            "Clé OpenRouter absente. Vérifie le chargement de secrets.env."
        )

    if not articles:
        raise RuntimeError("Aucune actualité récupérée.")

    actualites = "\n\n".join(articles)

    messages = [
        {
            "role": "system",
            "content": """
Tu écris une émission de radio en français entre deux animateurs.

Alex est passionné de métros et de trains.
Camille est spécialiste de technologie et d'électronique.

FORMAT OBLIGATOIRE :
Chaque réplique commence sur une nouvelle ligne par :
Alex : texte prononcé
ou
Camille : texte prononcé

Règles :
- Produis uniquement le dialogue prononcé à l'antenne.
- N'ajoute aucun titre, commentaire ou balise.
- Fais alterner naturellement Alex et Camille.
- Écris une introduction, plusieurs sujets, des transitions et une conclusion.
- Explique les termes techniques simplement.
- Utilise les actualités fournies sans inventer de faits.
- Si une information manque, ne l'invente pas.
- Ne présente pas une information ancienne comme une nouveauté.
- Ne prétends pas qu'un article parle de transports s'il n'en parle pas.
- Vise environ 800 mots.
- La première réplique doit commencer par Alex :
- Chaque réplique doit être sur sa propre ligne.
- La dernière réplique doit commencer par Alex : ou Camille :
""",
        },
        {
            "role": "user",
            "content": (
                "Rédige l'émission complète à partir des actualités "
                "suivantes. Fais une conversation vivante, naturelle "
                "et pédagogique entre les deux animateurs.\n\n"
                f"ACTUALITÉS :\n{actualites}"
            ),
        },
    ]

    reponse = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "openrouter/auto",
            "messages": messages,
            "max_tokens": 3500,
            "temperature": 0.7,
        },
        timeout=180,
    )

    reponse.raise_for_status()
    donnees = reponse.json()

    if donnees.get("error"):
        raise RuntimeError(f"Erreur OpenRouter : {donnees['error']}")

    choix = donnees.get("choices", [])

    if not choix:
        raise RuntimeError(
            f"OpenRouter n'a renvoyé aucun choix : {donnees}"
        )

    choix_modele = choix[0]
    message = choix_modele.get("message") or {}
    texte = message.get("content") or ""
    print("Diagnostic : type du contenu =", type(message.get("content")).__name__)
    print("Diagnostic : clés du message =", list(message.keys()))
    print("Diagnostic : raison de fin =", choix_modele.get("finish_reason"))
    print("Modèle utilisé :", donnees.get("model"))
    print("Diagnostic : type du contenu =", type(message.get("content")).__name__)
    print("Diagnostic : clés du message =", list(message.keys()))
    print("Diagnostic : raison de fin =", choix_modele.get("finish_reason"))
    print("Diagnostic : nombre de tokens =", choix_modele.get("usage"))

    print("Modèle utilisé :", donnees.get("model"))
    print("Fin de génération :", choix_modele.get("finish_reason"))

    if not isinstance(texte, str) or not texte.strip():
        raise RuntimeError(
            f"OpenRouter a renvoyé un texte vide ou inexploitable : "
            f"{texte!r}"
        )

    print("Début de la réponse :", repr(texte[:300]))

    lignes_valides = re.findall(
        r"(?im)^\s*(?:\*\*)?(Alex|Camille)(?:\*\*)?\s*:",
        texte,
    )

    if len(lignes_valides) < 10:
        extrait = texte[:500].replace("\n", " ")
        raise RuntimeError(
            "La réponse ne contient pas assez de répliques reconnues. "
            f"Extrait reçu : {extrait}"
        )

    if not any(nom.lower() == "alex" for nom in lignes_valides):
        raise RuntimeError("Aucune réplique d'Alex reconnue.")

    if not any(nom.lower() == "camille" for nom in lignes_valides):
        raise RuntimeError("Aucune réplique de Camille reconnue.")

    return texte.strip() + "\n"


if __name__ == "__main__":
    try:
        articles = recuperer_actualites()
        print(f"\n{len(articles)} actualités récupérées.")

        print("\nGénération de l'émission...")
        texte = generer_emission(articles)

        nom_fichier = (
            "emission_"
            + datetime.now().strftime("%Y%m%d_%H%M%S")
            + ".txt"
        )

        chemin = DOSSIER / nom_fichier
        chemin.write_text(texte, encoding="utf-8")

        print(f"\nÉmission enregistrée dans : {chemin}")
        print("\nDébut du dialogue :\n")
        print(texte[:1500])

    except Exception as erreur:
        print(f"\nErreur : {erreur}")

        if isinstance(erreur, requests.HTTPError):
            print("Réponse HTTP :", erreur.response.text[:1000])

        raise SystemExit(1)
