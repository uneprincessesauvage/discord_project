import asyncio
import re
import subprocess
import sys
import tempfile
from pathlib import Path
import edge_tts
VOIX = {
    "Alex": "fr-FR-HenriNeural",
    "Camille": "fr-FR-DeniseNeural",
}
DOSSIER = Path("radio-ia")
def extraire_repliques(texte):
    motif = re.compile(r"(?m)^\s*(Alex|Camille)\s*:\s*")
    correspondances = list(motif.finditer(texte))
    repliques = []
    for i, match in enumerate(correspondances):
        debut = match.end()
        fin = (
            correspondances[i + 1].start()
            if i + 1 < len(correspondances)
            else len(texte)
        )
        contenu = texte[debut:fin].strip()
        if contenu:
            repliques.append((match.group(1), contenu))
    return repliques
async def generer_audio(personnage, texte, destination):
    communication = edge_tts.Communicate(
        text=texte,
        voice=VOIX[personnage],
    )
    await communication.save(str(destination))
async def creer_emission(source):
    if not source.is_file():
        raise FileNotFoundError(f"Fichier introuvable : {source}")
    texte = source.read_text(encoding="utf-8")
    repliques = extraire_repliques(texte)
    if not repliques:
        raise RuntimeError("Aucune réplique reconnue.")
    DOSSIER.mkdir(parents=True, exist_ok=True)
    sortie = DOSSIER / f"{source.stem}.mp3"
    print(f"{len(repliques)} répliques détectées.")
    print("Génération des voix...")
    with tempfile.TemporaryDirectory(prefix="radio_") as temporaire:
        repertoire = Path(temporaire)
        fichiers = []
        for numero, (personnage, contenu) in enumerate(repliques):
            fichier = repertoire / f"{numero:04d}.mp3"
            print(
                f"[{numero + 1}/{len(repliques)}] "
                f"{personnage}..."
            )
            await generer_audio(personnage, contenu, fichier)
            fichiers.append(fichier)
        # Liste des fichiers pour FFmpeg.
        liste = repertoire / "liste.txt"
        with liste.open("w", encoding="utf-8") as f:
            for fichier in fichiers:
                chemin = fichier.resolve().as_posix()
                chemin = chemin.replace("'", r"'\''")
                f.write(f"file '{chemin}'\n")
        print("Assemblage de l'émission...")
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel", "error",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(liste),
                "-c:a", "libmp3lame",
                "-q:a", "3",
                str(sortie.resolve()),
            ],
            check=True,
        )
    print(f"\nÉmission terminée : {sortie.resolve()}")
if __name__ == "__main__":
    try:
        source = (
            Path(sys.argv[1])
            if len(sys.argv) > 1
            else DOSSIER / "emission_20261022_170746.txt"
        )
        asyncio.run(creer_emission(source))
    except Exception as erreur:
        print(f"\nErreur : {erreur}")
        raise SystemExit(1)