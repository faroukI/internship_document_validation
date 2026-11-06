import sys
import time
from pathlib import Path
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from verification import valider_convention

class ConventionWatchdog(FileSystemEventHandler):
    def on_created(self, event):
        path = event.src_path
        if event.is_directory is True or path.lower().endswith(".pdf") is False:
            return

        print("nouveau fichier détecté: ", path)
        chemin = Path(path)
        print("Attente de 2 secondes pour être sûr que le fichier est bien copié")
        # on attend que le fichier soit vraiment copié
        time.sleep(0.5)
        try:
            dossier_courant = chemin.parent
            chemin_valide = dossier_courant.parent / "valide"
            chemin_invalide = dossier_courant.parent / "invalide"
            chemin_valide.mkdir(exist_ok=True)
            chemin_invalide.mkdir(exist_ok=True)
            print("chemin_valide :", chemin_valide)
            print("chemin_invalide :", chemin_invalide)
            resultat = valider_convention(str(chemin.resolve()), 
                                          str((chemin_valide / chemin.name).resolve()), str((chemin_invalide / chemin.name).resolve()), "signature_chef.jpg", False)
            if(resultat is False):
                print("erreur, le fichier a été envoyé dans", chemin_invalide)
            else:
                print("fichier traité avec succès")

            # on supprime le fichier d'origine (il est soit dans "invalide" soit dans "valide")
            chemin.unlink()

        except Exception as e:
            print("erreur lors du traitement du fichier ", chemin.name, ":", e)


if __name__ == "__main__":
    fichier_config = Path("liste_dossiers.txt")
    dossiers_a_surveiller = []

    # --- 1. LECTURE DU FICHIER DE CONFIGURATION ---
    if fichier_config.exists():
        with open(fichier_config, "r", encoding="utf-8") as f:
            for ligne in f:
                dossier = ligne.strip()
                # On ignore les lignes vides ou celles qui commencent par un #
                if dossier and not dossier.startswith("#"):
                    dossiers_a_surveiller.append(dossier)

    # --- 2. VALEUR PAR DÉFAUT ---
    if not dossiers_a_surveiller:
        print("Aucun dossier trouvé dans liste_dossiers.txt ou le fichier n'existe pas. Utilisation du dossier par défaut.")
        dossiers_a_surveiller = ["../nouveau"]

    watcher = ConventionWatchdog()
    observer = Observer()

    # --- 3. LANCEMENT MULTI-DOSSIERS ---
    # On boucle sur notre liste pour attacher chaque dossier au Watchdog
    for dossier in dossiers_a_surveiller:
        chemin_dossier = Path(dossier).resolve()
        
        # Sécurité : Watchdog plante si le dossier à surveiller n'existe pas. 
        # On demande donc à Python de le créer s'il est manquant.
        chemin_dossier.mkdir(parents=True, exist_ok=True)
        
        observer.schedule(watcher, str(chemin_dossier), recursive=False)
        print(f"Surveillance activée sur le dossier : {chemin_dossier}")
    
    observer.start()
    
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        observer.stop()
        print("arrêt de la surveillance")
        observer.join()
