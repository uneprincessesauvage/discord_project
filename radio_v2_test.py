import os
import re
import requests
import feedparser
from datetime import datetime
from pathlib import Path
# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------
API_KEY = os.environ.get("OPENROUTER_API_KEY")
FLUX_RSS = [
    "https://www.numerama.com/feed/",
    "https://www.futura-sciences.com/rss/actualites.xml",
    "https://elevatorworld.com/feed",
]
DOSSIER = Path("./radio-ia")
# --------------------------------------------------
# RÉCUPÉRATION DES ACTUALITÉS
# --------------------------------------------------
def recuperer_actualites():
    articles = []
    for url in FLUX_RSS:
        print(f"\nLecture du flux : {url}")
        try:
            flux = feedparser.parse(url)
            if getattr(flux, "bozo", False):
                print(
                    "Attention : flux potentiellement incomplet : "
                    f"{url}"
                )
            for article in flux.entries[:4]:
                titre = article.get("title", "").strip()
                resume = article.get("summary", "")
                lien = article.get("link", "").strip()
                date_publication = (
                    article.get("published")
                    or article.get("updated")
                    or "Date non disponible"
                )
                if titre:
                    articles.append({
                        "titre": titre,
                        "resume": resume[:600],
                        "source": url,
                        "lien": lien,
                        "date": date_publication,
                    })
        except Exception as erreur:
            print(f"Flux ignoré : {erreur}")
    return articles
# --------------------------------------------------
# ENREGISTREMENT DES ARTICLES POUR CONSULTATION
# --------------------------------------------------
def enregistrer_articles(articles):
    DOSSIER.mkdir(parents=True, exist_ok=True)
    chemin = DOSSIER / "articles_selectionnes.txt"
    with chemin.open("w", encoding="utf-8") as fichier:
        fichier.write("ARTICLES SÉLECTIONNÉS POUR L'ÉMISSION\n")
        fichier.write(
            f"Date de récupération : "
            f"{datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}\n"
        )
        fichier.write("=" * 75 + "\n\n")
        for numero, article in enumerate(articles, start=1):
            fichier.write(f"ARTICLE {numero}\n")
            fichier.write("-" * 75 + "\n")
            fichier.write(f"Titre : {article['titre']}\n")
            fichier.write(f"Date de publication : {article['date']}\n")
            fichier.write(f"Flux RSS : {article['source']}\n")
            fichier.write(f"Lien original : {article['lien']}\n\n")
            fichier.write("RÉSUMÉ RSS :\n")
            fichier.write(f"{article['resume']}\n\n")
            fichier.write("=" * 75 + "\n\n")
    print(f"\nArticles enregistrés dans : {chemin.resolve()}")
    print("\nLIENS DES ARTICLES À CONSULTER :")
    for numero, article in enumerate(articles, start=1):
        print(f"\n{numero}. {article['titre']}")
        print(f"   {article['lien']}")
    return chemin
# --------------------------------------------------
# PRÉPARATION DES ACTUALITÉS POUR L'IA
# --------------------------------------------------
def preparer_actualites(articles):
    blocs = []
    for numero, article in enumerate(articles, start=1):
        bloc = (
            f"ARTICLE {numero}\n"
            f"Titre : {article['titre']}\n"
            f"Date de publication : {article['date']}\n"
            f"Résumé : {article['resume']}\n"
            f"Source RSS : {article['source']}\n"
            f"Lien original : {article['lien']}"
        )
        blocs.append(bloc)
    return "\n\n".join(blocs)
# --------------------------------------------------
# GÉNÉRATION DE L'ÉMISSION
# --------------------------------------------------
def generer_emission(articles):
    if not API_KEY:
        raise RuntimeError(
            "Clé OpenRouter absente. "
            "Vérifie le chargement de secrets.env."
        )
    if not articles:
        raise RuntimeError("Aucune actualité récupérée.")
    actualites = preparer_actualites(articles)
    messages = [
        {
            "role": "system",
            "content": """
Tu écris une émission de radio en français entre deux animateurs.
Alex est passionné de métros et de trains.
Camille est spécialiste de technologie et d'électronique.
OBJECTIF PRIORITAIRE : L'EXACTITUDE DES INFORMATIONS.
Règles de vérification :
- N'invente jamais de faits, de chiffres, de dates, de prix ou de déclarations.
- Utilise uniquement les informations étayées par les actualités fournies.
- Les résumés RSS peuvent être incomplets ou imprécis.
- Ne prétends jamais avoir vérifié une information si tu ne l'as pas réellement vérifiée.
- Tu ne disposes ici que des informations fournies dans le message utilisateur.
- Tu ne peux pas considérer les liens comme des articles que tu aurais lus.
- Ne prétends donc pas avoir consulté les pages Web.
- Ne transforme pas une possibilité en certitude.
- Ne présente pas une information ancienne comme une nouveauté.
- Vérifie la cohérence des dates et des chiffres présents dans les informations fournies.
- Si une information est douteuse, incomplète ou contradictoire, omets-la ou signale clairement l'incertitude.
- Ne fabrique jamais de source ou de citation.
- Ne prétends pas qu'un article parle de transports s'il n'en parle pas.
- Ne crée pas de transition artificielle entre deux sujets sans rapport.
- N'ajoute pas de produits, de promotions ou d'actualités absents des sources.
- Ne répète pas plusieurs fois la même information pour remplir l'émission.
- Privilégie la précision plutôt que la quantité d'informations.
FORMAT OBLIGATOIRE :
Chaque réplique commence sur une nouvelle ligne par :
Alex : texte prononcé
ou
Camille : texte prononcé
Règles de rédaction :
- Produis uniquement le dialogue prononcé à l'antenne.
- N'ajoute aucun titre, commentaire ou balise.
- Fais alterner naturellement Alex et Camille.
- Écris une introduction, des transitions pertinentes et une conclusion.
- Explique les termes techniques simplement.
- Vise environ 800 mots, sans ajouter de remplissage pour atteindre cette longueur.
- La première réplique doit commencer par Alex :
- Chaque réplique doit être sur sa propre ligne.
- La dernière réplique doit commencer par Alex : ou Camille :.
- La qualité journalistique et l'exactitude passent avant la longueur et le divertissement.
""",
        },
        {
            "role": "user",
            "content": (
                "Rédige une émission de radio vivante, naturelle "
                "et pédagogique à partir des actualités ci-dessous.\n\n"
                "N'utilise pas d'informations qui ne figurent pas "
                "dans les données fournies.\n\n"
                f"ACTUALITÉS :\n{actualites}"
            ),
        },
    ]
    print("\nEnvoi des actualités à OpenRouter...")
    reponse = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "openrouter/free",
            "messages": messages,
            "max_tokens": 3500,
            "temperature": 0.4,
        },
        timeout=180,
    )
    reponse.raise_for_status()
    donnees = reponse.json()
    if donnees.get("error"):
        raise RuntimeError(
            f"Erreur OpenRouter : {donnees['error']}"
        )
    choix = donnees.get("choices", [])
    if not choix:
        raise RuntimeError(
            f"OpenRouter n'a renvoyé aucun choix : {donnees}"
        )
    choix_modele = choix[0]
    message = choix_modele.get("message") or {}
    texte = message.get("content") or ""
    print("Modèle utilisé :", donnees.get("model"))
    print(
        "Fin de génération :",
        choix_modele.get("finish_reason")
    )
    print("Utilisation des tokens :", donnees.get("usage"))
    if not isinstance(texte, str) or not texte.strip():
        raise RuntimeError(
            "OpenRouter a renvoyé un texte vide ou inexploitable."
        )
    lignes_valides = re.findall(
        r"(?im)^\s*(?:\*\*)?(Alex|Camille)(?:\*\*)?\s*:",
        texte,
    )
    if len(lignes_valides) < 10:
        extrait = texte[:500].replace("\n", " ")
        raise RuntimeError(
            "La réponse ne contient pas assez de répliques "
            f"reconnues. Extrait reçu : {extrait}"
        )
    if not any(nom.lower() == "alex" for nom in lignes_valides):
        raise RuntimeError("Aucune réplique d'Alex reconnue.")
    if not any(
        nom.lower() == "camille"
        for nom in lignes_valides
    ):
        raise RuntimeError("Aucune réplique de Camille reconnue.")
    return texte.strip() + "\n"
# --------------------------------------------------
# PROGRAMME PRINCIPAL
# --------------------------------------------------
if __name__ == "__main__":
    try:
        DOSSIER.mkdir(parents=True, exist_ok=True)
        articles = recuperer_actualites()
        print(f"\n{len(articles)} actualités récupérées.")
        if not articles:
            raise RuntimeError(
                "Aucune actualité récupérée depuis les flux RSS."
            )
        # Enregistre les articles AVANT la génération.
        enregistrer_articles(articles)
        print("\nGénération de l'émission...")
        texte = generer_emission(articles)
        nom_fichier = (
            "emission_"
            + datetime.now().strftime("%Y%m%d_%H%M%S")
            + ".txt"
        )
        chemin = DOSSIER / nom_fichier
        chemin.write_text(texte, encoding="utf-8")
        print(f"\nÉmission enregistrée dans : {chemin.resolve()}")
        print("\nDébut du dialogue :\n")
        print(texte[:1500])
        print("\nLes articles originaux sont disponibles dans :")
        print((DOSSIER / "articles_selectionnes.txt").resolve())
    except Exception as erreur:
        print(f"\nErreur : {erreur}")
        if isinstance(erreur, requests.HTTPError):
            print(
                "Réponse HTTP :",
                erreur.response.text[:1000]
                if erreur.response is not None
                else "Aucune réponse disponible."
            )
        raise SystemExit(1)