#!/usr/bin/env python3
"""
MCP Server — Entreprises Françaises v2
Agrège 3 sources officielles et gratuites :
  1. API Recherche d'Entreprises  (recherche-entreprises.api.gouv.fr) — sans clé
  2. Pappers API v2               (api.pappers.fr) — clé gratuite requise
  3. BODACC API DILA              (bodacc-datadila.opendatasoft.com) — sans clé
"""

import json
import os
import pathlib
from typing import Optional
import httpx
from pydantic import BaseModel, Field, field_validator, ConfigDict
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("entreprises_france_mcp")

API_RECHERCHE = "https://recherche-entreprises.api.gouv.fr"
API_PAPPERS   = "https://api.pappers.fr/v2"
API_BODACC    = "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales/records"

def _get_pappers_token() -> Optional[str]:
    token = os.environ.get("PAPPERS_API_TOKEN", "").strip()
    if token:
        return token
    config_path = pathlib.Path(__file__).parent / "config.json"
    if config_path.exists():
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            return cfg.get("pappers_token", "").strip() or None
        except Exception:
            pass
    return None

async def _get(url: str, params: dict) -> dict:
    params = {k: v for k, v in params.items() if v is not None}
    async with httpx.AsyncClient(timeout=25.0) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.json()

def _err(e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError):
        c = e.response.status_code
        if c == 400: return "Erreur : Requete invalide."
        if c == 401: return "Erreur Pappers : Token invalide ou manquant."
        if c == 404: return "Erreur : SIREN/SIRET introuvable."
        if c == 429: return "Erreur : Trop de requetes. Patientez."
        return f"Erreur API HTTP {c}"
    if isinstance(e, httpx.TimeoutException):
        return "Erreur : Delai depasse."
    return f"Erreur : {type(e).__name__} — {e}"

_TRANCHE_EFF = {
    "NN": "Non renseigne", "00": "0 salarie", "01": "1-2", "02": "3-5",
    "03": "6-9", "11": "10-19", "12": "20-49", "21": "50-99",
    "22": "100-199", "31": "200-249", "32": "250-499", "41": "500-999",
    "42": "1 000-1 999", "51": "2 000-4 999", "52": "5 000-9 999",
    "53": "10 000 et plus"
}

def _fmt_base(e: dict) -> dict:
    s = e.get("siege", {})
    fins = e.get("finances") or {}
    finances_hist = [
        {"annee": a, "chiffre_affaires": fins[a].get("ca"), "resultat_net": fins[a].get("resultat_net")}
        for a in sorted(fins.keys(), reverse=True)
    ]
    tc = s.get("tranche_effectif_salarie", "NN")
    compl = e.get("complements", {})
    return {
        "siren": e.get("siren"),
        "nom": e.get("nom_complet"),
        "raison_sociale": e.get("nom_raison_sociale"),
        "sigle": e.get("sigle"),
        "statut": "Actif" if e.get("etat_administratif") == "A" else "Ferme",
        "date_creation": e.get("date_creation"),
        "date_fermeture": e.get("date_fermeture"),
        "date_mise_a_jour": e.get("date_mise_a_jour"),
        "siege": {
            "siret": s.get("siret"),
            "adresse_complete": s.get("adresse"),
            "numero_voie": s.get("numero_voie"),
            "type_voie": s.get("type_voie"),
            "libelle_voie": s.get("libelle_voie"),
            "complement": s.get("complement_adresse"),
            "code_postal": s.get("code_postal"),
            "commune": s.get("libelle_commune"),
            "cedex": s.get("libelle_cedex"),
            "departement": s.get("departement"),
            "region": s.get("region"),
            "coordonnees_gps": s.get("coordonnees"),
            "etat_etablissement": "Actif" if s.get("etat_administratif") == "A" else "Ferme",
        },
        "activite": {
            "code_naf": e.get("activite_principale"),
            "section": e.get("section_activite_principale"),
        },
        "effectif": {
            "tranche_code": tc,
            "tranche_libelle": _TRANCHE_EFF.get(tc, tc),
            "annee_reference": s.get("annee_tranche_effectif_salarie"),
        },
        "categorie_entreprise": e.get("categorie_entreprise"),
        "nature_juridique": e.get("nature_juridique"),
        "nb_etablissements": e.get("nombre_etablissements"),
        "nb_etablissements_ouverts": e.get("nombre_etablissements_ouverts"),
        "dirigeants": [
            {
                "nom": d.get("nom", d.get("denomination", "")),
                "prenom": d.get("prenoms", ""),
                "qualite": d.get("qualite"),
                "type": d.get("type_dirigeant"),
                "annee_naissance": d.get("annee_de_naissance"),
            }
            for d in e.get("dirigeants", [])
        ],
        "finances_base": finances_hist,
        "qualifications": {
            "est_association":             compl.get("est_association"),
            "est_ess":                     compl.get("est_ess"),
            "est_entrepreneur_individuel": compl.get("est_entrepreneur_individuel"),
            "est_service_public":          compl.get("est_service_public"),
            "est_organisme_formation":     compl.get("est_organisme_formation"),
            "est_qualiopi":                compl.get("est_qualiopi"),
            "est_rge":                     compl.get("est_rge"),
            "est_bio":                     compl.get("est_bio"),
            "est_societe_mission":         compl.get("est_societe_mission"),
        },
        "conventions_collectives": compl.get("liste_idcc"),
        "source": "API Recherche Entreprises (data.gouv.fr)",
    }


# ── OUTIL 1 : Recherche multi-critères ─────────────────────────────────────────
class RechercheInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    q: str = Field(..., description="Nom, mot-cle, SIREN (9 chiffres) ou SIRET (14 chiffres)", min_length=2, max_length=200)
    page: Optional[int] = Field(default=1, ge=1)
    par_page: Optional[int] = Field(default=10, ge=1, le=25)
    etat: Optional[str] = Field(default=None, description="'A'=actif, 'F'=ferme")
    departement: Optional[str] = Field(default=None, description="Ex: '13', '75'")
    code_postal: Optional[str] = Field(default=None, description="Ex: '13100'")
    activite_principale: Optional[str] = Field(default=None, description="Code NAF ex: '69.10Z'")
    categorie: Optional[str] = Field(default=None, description="TPE, PME, ETI ou GE")
    est_association: Optional[bool] = Field(default=None)
    est_ess: Optional[bool] = Field(default=None)
    est_organisme_formation: Optional[bool] = Field(default=None)
    est_qualiopi: Optional[bool] = Field(default=None)
    est_rge: Optional[bool] = Field(default=None)
    est_entrepreneur_individuel: Optional[bool] = Field(default=None)

    @field_validator("q")
    @classmethod
    def check_q(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("La requete ne peut pas etre vide")
        return v.strip()


@mcp.tool(name="entreprise_search", annotations={"title": "Rechercher des entreprises francaises", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True})
async def entreprise_search(params: RechercheInput) -> str:
    """Recherche des entreprises francaises par nom, SIREN, SIRET, mot-cle.
    Filtres : departement, code postal, code NAF, taille (TPE/PME/ETI/GE), statut,
    qualifications (ESS, Qualiopi, RGE, organisme de formation, EI, association).
    Retourne : nom, SIREN, SIRET siege, adresse complete detaillee (numero, voie,
    complement, CP, commune, cedex, departement, region, GPS), statut, NAF, effectif
    (tranche + libelle), categorie, nb etablissements, qualifications, finances.
    """
    try:
        def _b(v): return str(v).lower() if v is not None else None
        data = await _get(f"{API_RECHERCHE}/search", {
            "q": params.q, "page": params.page, "per_page": params.par_page,
            "etat_administratif": params.etat,
            "departement": params.departement,
            "code_postal": params.code_postal,
            "activite_principale": params.activite_principale,
            "categorie_entreprise": params.categorie,
            "est_association": _b(params.est_association),
            "est_ess": _b(params.est_ess),
            "est_organisme_formation": _b(params.est_organisme_formation),
            "est_qualiopi": _b(params.est_qualiopi),
            "est_rge": _b(params.est_rge),
            "est_entrepreneur_individuel": _b(params.est_entrepreneur_individuel),
        })
        results = data.get("results", [])
        if not results:
            return json.dumps({"message": f"Aucune entreprise trouvee pour '{params.q}'", "total": 0}, ensure_ascii=False)
        return json.dumps({
            "total": data.get("total_results", 0),
            "page": params.page, "par_page": params.par_page,
            "entreprises": [_fmt_base(e) for e in results],
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return _err(e)


# ── OUTIL 2 : Fiche complète enrichie (Pappers + fallback Recherche) ───────────
class SirenInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    siren: str = Field(..., description="SIREN a 9 chiffres ex: '380129866'", min_length=9, max_length=9, pattern=r"^\d{9}$")

    @field_validator("siren")
    @classmethod
    def check(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 9:
            raise ValueError("SIREN = exactement 9 chiffres")
        return v


def _fmt_pappers(p: dict) -> dict:
    finances = []
    for f in p.get("finances", []):
        ca, res = f.get("chiffre_affaires"), f.get("resultat")
        finances.append({
            "annee": f.get("annee"),
            "date_cloture": f.get("date_de_cloture_exercice"),
            "duree_mois": f.get("duree_exercice"),
            "chiffre_affaires_eur": ca,
            "resultat_net_eur": res,
            "effectif_salaries": f.get("effectif"),
            "capitaux_propres_eur": f.get("capitaux_propres"),
            "total_bilan_eur": f.get("total_bilan"),
            "dette_financiere_eur": f.get("dette_financiere"),
            "marge_nette_pct": round(res / ca * 100, 2) if ca and res else None,
            "ratio_dette_capitaux": round(f["dette_financiere"] / f["capitaux_propres"], 2)
                if f.get("dette_financiere") and f.get("capitaux_propres") else None,
        })
    score = p.get("score_de_confiance")
    return {
        "source": "Pappers API v2",
        "siren": p.get("siren"),
        "nom": p.get("nom_entreprise"),
        "forme_juridique": p.get("forme_juridique"),
        "capital_social_eur": p.get("capital"),
        "tva_intracommunautaire": p.get("tva_intracommunautaire"),
        "objet_social": p.get("objet_social"),
        "statut": "Actif" if not p.get("date_cessation_activite") else "Ferme",
        "date_creation": p.get("date_creation"),
        "date_cessation": p.get("date_cessation_activite"),
        "employeur": p.get("entreprise_employeuse"),
        "code_naf": p.get("code_naf"),
        "libelle_naf": p.get("libelle_code_naf"),
        "categorie_entreprise": p.get("categorie_entreprise"),
        "tranche_effectif": p.get("tranche_effectif"),
        "siege": {
            "siret": p.get("siege", {}).get("siret"),
            "adresse_ligne_1": p.get("siege", {}).get("adresse_ligne_1"),
            "adresse_ligne_2": p.get("siege", {}).get("adresse_ligne_2"),
            "complement": p.get("siege", {}).get("complement_adresse"),
            "numero": p.get("siege", {}).get("numero_voie"),
            "type_voie": p.get("siege", {}).get("type_voie"),
            "voie": p.get("siege", {}).get("libelle_voie"),
            "code_postal": p.get("siege", {}).get("code_postal"),
            "ville": p.get("siege", {}).get("ville"),
            "cedex": p.get("siege", {}).get("cedex"),
            "pays": p.get("siege", {}).get("pays", "France"),
        },
        "score_de_sante": {
            "note_sur_10": score,
            "interpretation": (
                "Excellent (8-10)" if score and score >= 8 else
                "Bon (6-7.9)" if score and score >= 6 else
                "Moyen (4-5.9)" if score and score >= 4 else
                "Risque (< 4)" if score else "Non disponible"
            ),
        },
        "procedures_collectives": [
            {"type": pc.get("type"), "date_ouverture": pc.get("date_ouverture"),
             "tribunal": pc.get("tribunal"), "etat": pc.get("etat")}
            for pc in p.get("procedures_collectives", [])
        ],
        "dirigeants": [
            {"type": d.get("type"), "nom": d.get("nom", d.get("denomination", "")),
             "prenom": d.get("prenom", ""), "qualite": d.get("qualite"),
             "date_prise_de_poste": d.get("date_prise_de_poste"),
             "nationalite": d.get("nationalite")}
            for d in p.get("dirigeants", [])
        ],
        "beneficiaires_effectifs": [
            {"nom": b.get("nom"), "prenom": b.get("prenom"),
             "pourcentage_parts": b.get("pourcentage_parts"),
             "pourcentage_votes": b.get("pourcentage_votes_directs"),
             "type_controle": b.get("types_de_controle")}
            for b in p.get("beneficiaires_effectifs", [])
        ],
        "finances_historique": finances,
        "actes_recents": [
            {"date_depot": a.get("date_depot"), "type": a.get("type_acte"),
             "libelle": a.get("libelle"), "url": a.get("url")}
            for a in p.get("actes", [])[:10]
        ],
        "bodacc_recent": [
            {"date": pub.get("date"), "type": pub.get("type"),
             "famille": pub.get("famille"), "tribunal": pub.get("tribunal"),
             "resume": pub.get("resume")}
            for pub in p.get("publications_bodacc", [])[:5]
        ],
    }


@mcp.tool(name="entreprise_fiche_complete", annotations={"title": "Fiche complete enrichie (bilans, actes, score sante, procedures)", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True})
async def entreprise_fiche_complete(params: SirenInput) -> str:
    """Fiche complete et enrichie d'une entreprise. Combine Pappers API + API Recherche.
    Avec token Pappers retourne : identite complete (forme juridique, capital, TVA intra,
    objet social), adresse siege detaillee (ligne 1, ligne 2, complement, cedex, pays),
    score de sante 0-10 avec interpretation, procedures collectives (redressement,
    liquidation, sauvegarde), dirigeants complets (qualite, date de prise de poste,
    nationalite), beneficiaires effectifs (parts, votes, type de controle), historique
    financier multi-annees (CA, resultat, effectif, capitaux propres, total bilan, dette,
    marge nette calculee), 10 derniers actes legaux avec lien telechargement, 5 dernieres
    publications BODACC. Sans token : donnees partielles via API Recherche.
    Config token : variable env PAPPERS_API_TOKEN ou config.json {pappers_token}.
    """
    token = _get_pappers_token()
    pappers_err = None
    if token:
        try:
            data = await _get(f"{API_PAPPERS}/entreprise", {"siren": params.siren, "api_token": token})
            return json.dumps(_fmt_pappers(data), ensure_ascii=False, indent=2)
        except Exception as e:
            pappers_err = _err(e)
    else:
        pappers_err = "Token Pappers non configure (PAPPERS_API_TOKEN). Donnees partielles."
    try:
        data = await _get(f"{API_RECHERCHE}/search", {"q": params.siren, "per_page": 5})
        results = data.get("results", [])
        exact = next((r for r in results if r.get("siren") == params.siren), None)
        if not exact:
            return json.dumps({"erreur": f"SIREN {params.siren} introuvable."}, ensure_ascii=False)
        result = _fmt_base(exact)
        result["avertissement"] = pappers_err
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return _err(e)


# ── OUTIL 3 : Historique bilans comptables ─────────────────────────────────────
@mcp.tool(name="entreprise_finances", annotations={"title": "Historique bilans comptables multi-annees", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True})
async def entreprise_finances(params: SirenInput) -> str:
    """Historique complet des bilans comptables via Pappers API.
    Retourne annee par annee : chiffre d'affaires, resultat net, effectif salaries,
    capitaux propres, total bilan, dette financiere, marge nette calculee,
    ratio dette/capitaux, duree de l'exercice, date de cloture.
    Necessite un token Pappers gratuit (pappers.fr/api).
    """
    token = _get_pappers_token()
    if not token:
        return json.dumps({
            "erreur": "Token Pappers requis. Inscription gratuite sur pappers.fr/api.",
            "conseil": "Ajoutez PAPPERS_API_TOKEN en variable d'env ou dans config.json"
        }, ensure_ascii=False, indent=2)
    try:
        data = await _get(f"{API_PAPPERS}/entreprise", {"siren": params.siren, "api_token": token})
        fins = []
        for f in data.get("finances", []):
            ca, res = f.get("chiffre_affaires"), f.get("resultat")
            fins.append({
                "annee": f.get("annee"),
                "date_cloture": f.get("date_de_cloture_exercice"),
                "duree_exercice_mois": f.get("duree_exercice"),
                "chiffre_affaires_eur": ca,
                "resultat_net_eur": res,
                "effectif_salaries": f.get("effectif"),
                "capitaux_propres_eur": f.get("capitaux_propres"),
                "total_bilan_eur": f.get("total_bilan"),
                "dette_financiere_eur": f.get("dette_financiere"),
                "marge_nette_pct": round(res / ca * 100, 2) if ca and res else None,
                "ratio_dette_capitaux": round(f["dette_financiere"] / f["capitaux_propres"], 2)
                    if f.get("dette_financiere") and f.get("capitaux_propres") else None,
            })
        if not fins:
            return json.dumps({"message": "Aucun bilan disponible.", "siren": params.siren}, ensure_ascii=False)
        return json.dumps({
            "siren": params.siren, "nom": data.get("nom_entreprise"),
            "nb_bilans": len(fins), "annee_plus_recente": fins[0]["annee"] if fins else None,
            "source": "Pappers API v2", "bilans": fins,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return _err(e)


# ── OUTIL 4 : Annonces légales BODACC ─────────────────────────────────────────
class BodaccInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    siren: str = Field(..., description="SIREN a 9 chiffres", min_length=9, max_length=9, pattern=r"^\d{9}$")
    limite: Optional[int] = Field(default=10, ge=1, le=50, description="Nombre d'annonces (max 50)")
    type_annonce: Optional[str] = Field(default=None,
        description="Filtre : 'Vente et cession', 'Creation', 'Modification', 'Radiation', "
                    "'Depot des comptes', 'Procedures collectives'")


@mcp.tool(name="entreprise_bodacc", annotations={"title": "Annonces legales BODACC officielles", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True})
async def entreprise_bodacc(params: BodaccInput) -> str:
    """Annonces legales officielles publiees au BODACC pour une entreprise.
    Le BODACC publie tous les evenements legaux : creations, modifications, cessions,
    radiations, depots de comptes, procedures collectives (redressement, liquidation).
    Source officielle DILA — gratuite, sans cle API.
    """
    try:
        where = f'siren_personnemorale="{params.siren}"'
        if params.type_annonce:
            where += f' AND typeavis_lib="{params.type_annonce}"'
        data = await _get(API_BODACC, {
            "where": where, "limit": params.limite,
            "order_by": "dateparution desc", "timezone": "Europe/Paris",
        })
        annonces = []
        for r in data.get("results", []):
            acte = r.get("acte") or {}
            annonces.append({
                "date_parution": r.get("dateparution"),
                "numero_parution": r.get("numeroparu"),
                "type_avis": r.get("typeavis_lib"),
                "famille": r.get("familleavis_lib"),
                "tribunal": r.get("tribunal"),
                "departement": r.get("numerodepartement"),
                "denomination": r.get("denomination"),
                "registre": r.get("registre"),
                "detail_acte": {
                    "type": acte.get("typeActe") or acte.get("typeAvisLibelle"),
                    "date_commencement": acte.get("dateCommencementActivite"),
                    "descriptif": acte.get("descriptif"),
                },
            })
        if not annonces:
            return json.dumps({"message": f"Aucune annonce BODACC pour SIREN {params.siren}", "siren": params.siren}, ensure_ascii=False)
        return json.dumps({
            "siren": params.siren,
            "total_annonces": data.get("total_count", len(annonces)),
            "source": "BODACC — DILA (bodacc.fr)",
            "annonces": annonces,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return _err(e)


# ── OUTIL 5 : Dirigeants + bénéficiaires effectifs ────────────────────────────
@mcp.tool(name="entreprise_dirigeants", annotations={"title": "Dirigeants et beneficiaires effectifs (UBO)", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True})
async def entreprise_dirigeants(params: SirenInput) -> str:
    """Dirigeants complets et beneficiaires effectifs (UBO) d'une entreprise.
    Dirigeants : nom, prenom, qualite (PDG, DG, Gerant...), date prise de poste, nationalite.
    Beneficiaires effectifs : identite, pourcentage parts, pourcentage votes, type controle.
    Necessite token Pappers pour les UBO. Sans token : dirigeants partiels via API Recherche.
    """
    token = _get_pappers_token()
    if not token:
        try:
            data = await _get(f"{API_RECHERCHE}/search", {"q": params.siren, "per_page": 5})
            exact = next((r for r in data.get("results", []) if r.get("siren") == params.siren), None)
            if not exact:
                return json.dumps({"erreur": f"SIREN {params.siren} introuvable."}, ensure_ascii=False)
            return json.dumps({
                "siren": params.siren, "nom": exact.get("nom_complet"),
                "dirigeants": [
                    {"nom": d.get("nom", d.get("denomination", "")), "prenom": d.get("prenoms", ""),
                     "qualite": d.get("qualite"), "type": d.get("type_dirigeant")}
                    for d in exact.get("dirigeants", [])
                ],
                "beneficiaires_effectifs": [],
                "avertissement": "Token Pappers requis pour les UBO.",
                "source": "API Recherche Entreprises",
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            return _err(e)
    try:
        data = await _get(f"{API_PAPPERS}/entreprise", {"siren": params.siren, "api_token": token})
        return json.dumps({
            "siren": params.siren, "nom": data.get("nom_entreprise"),
            "source": "Pappers API v2",
            "dirigeants": [
                {"type": d.get("type"), "nom": d.get("nom", d.get("denomination", "")),
                 "prenom": d.get("prenom", ""), "qualite": d.get("qualite"),
                 "date_prise_de_poste": d.get("date_prise_de_poste"),
                 "nationalite": d.get("nationalite")}
                for d in data.get("dirigeants", [])
            ],
            "beneficiaires_effectifs": [
                {"nom": b.get("nom"), "prenom": b.get("prenom"),
                 "pourcentage_parts": b.get("pourcentage_parts"),
                 "pourcentage_votes": b.get("pourcentage_votes_directs"),
                 "type_controle": b.get("types_de_controle")}
                for b in data.get("beneficiaires_effectifs", [])
            ],
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return _err(e)


# ── OUTIL 6 : Verification rapide SIREN/SIRET ─────────────────────────────────
class VerifInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    identifiant: str = Field(..., description="SIREN (9 chiffres) ou SIRET (14 chiffres)", min_length=9, max_length=14)

    @field_validator("identifiant")
    @classmethod
    def check(cls, v: str) -> str:
        v = v.replace(" ", "").replace("-", "")
        if not v.isdigit(): raise ValueError("Uniquement des chiffres")
        if len(v) not in (9, 14): raise ValueError("SIREN=9 ou SIRET=14 chiffres")
        return v


@mcp.tool(name="entreprise_verifier", annotations={"title": "Verifier un SIREN ou SIRET", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True})
async def entreprise_verifier(params: VerifInput) -> str:
    """Verifie la validite et retourne le statut d'un SIREN ou SIRET.
    Retourne : valide/invalide, nom, statut actif/ferme, adresse siege complete,
    activite NAF, categorie (TPE/PME/ETI/GE), effectif, date creation.
    Utile pour valider l'identite d'un client, prestataire ou partenaire.
    """
    try:
        siren = params.identifiant[:9]
        data = await _get(f"{API_RECHERCHE}/search", {"q": params.identifiant, "per_page": 5})
        exact = next((r for r in data.get("results", []) if r.get("siren") == siren), None)
        if not exact:
            return json.dumps({"valide": False, "identifiant": params.identifiant,
                "message": "SIREN/SIRET non trouve ou non diffuse publiquement."}, ensure_ascii=False, indent=2)
        s = exact.get("siege", {})
        tc = s.get("tranche_effectif_salarie", "NN")
        return json.dumps({
            "valide": True,
            "type_identifiant": "SIRET" if len(params.identifiant) == 14 else "SIREN",
            "identifiant": params.identifiant,
            "siren": exact.get("siren"),
            "siret_siege": s.get("siret"),
            "nom": exact.get("nom_complet"),
            "statut": "Actif" if exact.get("etat_administratif") == "A" else "Ferme",
            "date_creation": exact.get("date_creation"),
            "adresse_complete": s.get("adresse"),
            "numero_voie": s.get("numero_voie"),
            "type_voie": s.get("type_voie"),
            "libelle_voie": s.get("libelle_voie"),
            "complement": s.get("complement_adresse"),
            "code_postal": s.get("code_postal"),
            "commune": s.get("libelle_commune"),
            "departement": s.get("departement"),
            "code_naf": exact.get("activite_principale"),
            "categorie": exact.get("categorie_entreprise"),
            "effectif_tranche": _TRANCHE_EFF.get(tc, tc),
            "nb_etablissements_ouverts": exact.get("nombre_etablissements_ouverts"),
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return _err(e)


# ── Lancement ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
