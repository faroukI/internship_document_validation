import fitz  # PyMuPDF
import easyocr
import numpy as np
import re
import time
from datetime import datetime

# Initialisation du lecteur (se fait une seule fois au début du script)
# Il téléchargera les modèles français/anglais au premier lancement
reader = easyocr.Reader(['fr', 'en'])

class MauvaisTraitementException(Exception):
    pass

def valider_contrat(texte_ocr: str):
    resultat = False
    # contrat : XXXXX (X = alphanumérique)
    motif = r"contrat[:\s]*(\S+)"

    resultat_recherche = re.findall(motif, texte_ocr, re.IGNORECASE)

    print(f"Valeurs trouvées après 'contrat' : {resultat_recherche}")

    # On vérifie si on a bien trouvé 3 valeurs
    if len(resultat_recherche) >= 3:
        resultat = True

    return resultat, len(resultat_recherche)

def ajout_date(page, zone_chef: tuple):
    today = datetime.now().strftime("%d/%m/%Y")
    x_date = zone_chef[0] + 7
    y_date = zone_chef[1] + 30
    print("ajout de la date:", today)
    page.insert_text((x_date, y_date), today, fontsize=10, color=(0, 0, 0))

def zone_est_remplie(zone: tuple, page) -> bool:
    x0, y0, x1, y1 = zone
    # On multiplie par 2 car on a utilisé un zoom de 2 plus haut
    rect = fitz.Rect(x0, y0, x1, y1)
    zone_pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=rect, colorspace=fitz.csGRAY)
        
    # On transforme les pixels en tableau de nombres pour compter
    # Les pixels sont en RGB (3 valeurs par pixel)
    pixels = np.frombuffer(zone_pix.samples, dtype=np.uint8)
        
    # Un pixel est considéré comme "encre" s'il est sombre ( < 200 )
    nb_pixels_sombres = np.sum(pixels < 130)
    print('nombre pixel sombres : ', nb_pixels_sombres)
    
    # On ajuste le seuil : s'il y a plus de 150 pixels sombres, c'est signé
    return nb_pixels_sombres > 500

def valide_signature_cadre(page, zones: list) -> tuple:
    """
    valide une page PDF en regardant la présence des 4 signatures dans les bonnes zones

    Parameters:
        page : opened pdf document to check the signature on

    Returns: 
        returns True if all signatures are found, False with an error message otherwise
    """

    erreurs = []

    for cadre, zone in zones.items() :
        print(f"check {cadre}")
        if not zone_est_remplie(zone, page): # Signature 1
            erreurs.append(f"Signature {cadre} manquante")

    if erreurs:
        raise MauvaisTraitementException("NON VALIDE :\n- " + "\n- ".join(erreurs))
        return False, 

    return True, ""  

def valider_convention(chemin_full: str, chemin_valide: str, chemin_invalide: str, nom_image: str, is_debug: bool = False) -> bool:
    doc = None
    erreur_exception = "Erreur lors du traitement"
    try:
        print("lancement du traitement")
        doc = fitz.open(chemin_full)
        if len(doc) < 2:
            raise MauvaisTraitementException("NON VALIDE : le fichier contient moins de 2 pages.")
    
        page = doc[1]  # Page 2
    
        # 1. Conversion de la page en image pour l'analyse
        # On utilise un zoom de 2 pour la précision
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_bytes = pix.tobytes("png")
        
        # 2. Analyse du texte avec EasyOCR
        # On passe directement les octets de l'image au lecteur
        resultats_ocr = reader.readtext(img_bytes, detail=0) # detail=0 renvoie juste le texte


        # --- Vérification du texte ---
        texte_complet = " ".join(resultats_ocr).lower()
        resultat, nb_contrats = valider_contrat(texte_complet)
        if(resultat is False):
            raise MauvaisTraitementException("NON VALIDE : Numéros de contrat manquants (trouvé: " + str(nb_contrats) + ")")

        #zones_chef = (32, 323, 207, 515)
        zones_chef = (84, 337, 216, 482)
        zones = {}
        zones["representant organisme"] = (219, 337, 365, 482)
        zones["étudiant ou représentant légal"] = (365, 337, 498, 482)
        zones["Enseignant référent"] = (84, 485, 218, 618)
        zones["Tuteur"] = (216, 485, 365, 618)

        if is_debug is True:

            # --- BLOC DE VISUALISATION (À ajouter ici) ---
            for nom, coords in zones.items():
                # On crée un rectangle PyMuPDF
                rect = fitz.Rect(coords)
                # On dessine le rectangle sur la page (rouge, épaisseur 2)
                page.draw_rect(rect, color=(1, 0, 0), width=2)
                # On écrit le nom de la zone juste au-dessus pour s'y retrouver
                page.insert_text((coords[0], coords[1] - 5), nom, color=(1, 0, 0))

            # On enregistre une COPIE pour vérifier visuellement
            doc.save("verif_zones.pdf")
            print("Le fichier 'verif_zones.pdf' a été créé. Ouvrez-le pour ajuster les cadres.")


        valide_signature_cadre(page, zones)
        # on ne veut pas regarder la zone chef
        zones['Chef'] = zones_chef

        erreur_exception = "Erreur lors de l'insertion de la signature "

        page.wrap_contents()
        print("ajout de la signature du chef d'etablissement")
        rect_signature = fitz.Rect(zones_chef)
        # pour créer un pdf avec la zone de signature du chef d'étalissement vide
        """
        page.draw_rect(rect_signature, color=(1, 1, 1), fill=(1, 1, 1))
        doc.save('../modele_sans_signature.pdf')
        """
        page.insert_image(rect_signature, filename=nom_image)
        print("signature insérée avec succès")
        erreur_exception = "Erreur lors de l'insertion de la date "
        ajout_date(page, zones_chef)
    except MauvaisTraitementException as mte:
        print(mte)
        print("envoie du fichier dans ", chemin_invalide)
        doc.save(chemin_invalide)
        doc.close()
        return False

    except Exception as e:
        print(erreur_exception, e)
        if doc is not None:
            doc.save(chemin_invalide)
            doc.close()
        return False

    doc.save(chemin_valide)
    doc.close()
    return True

