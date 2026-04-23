import json
import sqlite3
from importlib import import_module
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st


st.set_page_config(
    page_title="Questionnaire Salariés - Bilan Carbone",
    layout="centered",
)

if "show_thanks_screen" not in st.session_state:
    st.session_state.show_thanks_screen = False


def save_salarie_response(reponses: dict) -> tuple[bool, str]:
    errors = []
    supabase_key_name = None
    if "SUPABASE_SERVICE_ROLE_KEY" in st.secrets:
        supabase_key_name = "SUPABASE_SERVICE_ROLE_KEY"
    elif "SUPABASE_KEY" in st.secrets:
        supabase_key_name = "SUPABASE_KEY"

    supabase_configured = "SUPABASE_URL" in st.secrets and supabase_key_name is not None

    try:
        if supabase_configured:
            supabase = import_module("supabase")
            create_client = getattr(supabase, "create_client")

            raw_url = str(st.secrets["SUPABASE_URL"]).strip().rstrip("/")
            parsed = urlparse(raw_url)
            if parsed.scheme and parsed.netloc:
                supabase_url = f"{parsed.scheme}://{parsed.netloc}"
            else:
                supabase_url = raw_url

            client = create_client(supabase_url, str(st.secrets[supabase_key_name]))
            payload = {
                "poste": reponses.get("poste", ""),
                "ville": reponses.get("ville", ""),
                "jours_teletravail": reponses.get("jours_teletravail", 0),
                "distance_ar_km": reponses.get("distance_ar_km", 0),
                "transport_bus_tram": reponses.get("transport_bus_tram", 0),
                "transport_velo": reponses.get("transport_velo", 0),
                "transport_marche": reponses.get("transport_marche", 0),
                "transport_voiture": reponses.get("transport_voiture", 0),
                "type_voiture": reponses.get("type_voiture", None),
                "repas_vegetariens": reponses.get("repas_vegetariens", 0),
                "repas_viande_rouge": reponses.get("repas_viande_rouge", 0),
                "repas_viande_blanche_poisson": reponses.get("repas_viande_blanche_poisson", 0),
                "reponses": reponses,
            }

            try:
                client.table("questionnaire_salaries_reponses").insert(payload).execute()
                return True, "Questionnaire salarie enregistre dans Supabase avec succes."
            except Exception:
                # Compatibilite avec les schemas historiques (nom/prenom requis, sans ville).
                legacy_payload = {
                    "nom": "",
                    "prenom": "",
                    "poste": reponses.get("poste", ""),
                    "email": "",
                    "jours_teletravail": reponses.get("jours_teletravail", 0),
                    "distance_ar_km": reponses.get("distance_ar_km", 0),
                    "transport_bus_tram": reponses.get("transport_bus_tram", 0),
                    "transport_velo": reponses.get("transport_velo", 0),
                    "transport_marche": reponses.get("transport_marche", 0),
                    "transport_voiture": reponses.get("transport_voiture", 0),
                    "type_voiture": reponses.get("type_voiture", None),
                    "repas_vegetariens": reponses.get("repas_vegetariens", 0),
                    "repas_viande_rouge": reponses.get("repas_viande_rouge", 0),
                    "repas_viande_blanche_poisson": reponses.get("repas_viande_blanche_poisson", 0),
                    "reponses": reponses,
                }
                try:
                    client.table("questionnaire_salaries_reponses").insert(legacy_payload).execute()
                    return True, (
                        "Questionnaire salarie enregistre dans Supabase "
                        "(mode compatibilite schema historique)."
                    )
                except Exception:
                    minimal_payload = {"reponses": reponses}
                    client.table("questionnaire_salaries_reponses").insert(minimal_payload).execute()
                    return True, (
                        "Questionnaire salarie enregistre dans Supabase "
                        "(mode compatibilite schema minimal)."
                    )
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Supabase indisponible pour le moment : {exc}")

    try:
        db_path = Path(__file__).parent / "bilan_carbone_local.db"
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS questionnaire_salaries_reponses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    nom TEXT NOT NULL,
                    prenom TEXT NOT NULL,
                    poste TEXT,
                    ville TEXT,
                    email TEXT NOT NULL,
                    jours_teletravail REAL NOT NULL,
                    distance_ar_km REAL NOT NULL,
                    transport_bus_tram REAL NOT NULL,
                    transport_velo REAL NOT NULL,
                    transport_marche REAL NOT NULL,
                    transport_voiture REAL NOT NULL,
                    repas_vegetariens INTEGER NOT NULL,
                    repas_viande_rouge INTEGER NOT NULL,
                    repas_viande_blanche_poisson INTEGER NOT NULL,
                    reponses TEXT NOT NULL
                )
                """
            )

            existing_columns = {
                row[1] for row in cur.execute("PRAGMA table_info(questionnaire_salaries_reponses)").fetchall()
            }
            if "ville" not in existing_columns:
                cur.execute("ALTER TABLE questionnaire_salaries_reponses ADD COLUMN ville TEXT")

            cur.execute(
                """
                INSERT INTO questionnaire_salaries_reponses (
                    nom,
                    prenom,
                    poste,
                    ville,
                    email,
                    jours_teletravail,
                    distance_ar_km,
                    transport_bus_tram,
                    transport_velo,
                    transport_marche,
                    transport_voiture,
                    repas_vegetariens,
                    repas_viande_rouge,
                    repas_viande_blanche_poisson,
                    reponses
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reponses.get("nom", ""),
                    reponses.get("prenom", ""),
                    reponses.get("poste", ""),
                    reponses.get("ville", ""),
                    reponses.get("email", ""),
                    reponses.get("jours_teletravail", 0),
                    reponses.get("distance_ar_km", 0),
                    reponses.get("transport_bus_tram", 0),
                    reponses.get("transport_velo", 0),
                    reponses.get("transport_marche", 0),
                    reponses.get("transport_voiture", 0),
                    reponses.get("repas_vegetariens", 0),
                    reponses.get("repas_viande_rouge", 0),
                    reponses.get("repas_viande_blanche_poisson", 0),
                    json.dumps(reponses, ensure_ascii=False),
                ),
            )
            conn.commit()

        if errors and supabase_configured:
            return False, (
                "Sauvegarde locale effectuee dans SQLite, mais echec Supabase. "
                + " | ".join(errors)
            )
        if errors:
            return True, "Questionnaire enregistre localement dans SQLite. " + " | ".join(errors)
        return True, "Questionnaire enregistre localement dans SQLite (bilan_carbone_local.db)."
    except Exception as exc:  # noqa: BLE001
        return False, f"Echec de l'enregistrement en base locale SQLite : {exc}"


st.markdown(
    '<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap" rel="stylesheet">',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
        :root {
            --bg-soft: #f4f7fb;
            --ink: #0f172a;
            --muted: #475569;
            --line: #dbe4f0;
            --s1: #93c5fd;
            --s2: #99f6e4;
        }

        html, body, [class*="css"] {
            font-family: 'Poppins', sans-serif;
            color: var(--ink);
        }

        .stApp {
            background:
                radial-gradient(1200px 500px at 10% -10%, #dbeafe 0%, transparent 60%),
                radial-gradient(900px 450px at 90% -20%, #e0f2fe 0%, transparent 60%),
                linear-gradient(180deg, #f8fbff 0%, var(--bg-soft) 100%);
        }

        .hero {
            padding: 1rem 1.2rem;
            border: 1px solid var(--line);
            border-left: 6px solid #1d4ed8;
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.86);
            margin: 0.25rem 0 1rem 0;
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
        }

        .hero h1 {
            margin: 0;
            font-size: 1.2rem;
            font-weight: 800;
            color: #0b3a75;
        }

        .hero p {
            margin: 0.45rem 0 0;
            color: var(--muted);
            font-size: 0.95rem;
        }

        [data-testid="stExpander"] {
            border: 1px solid #dbe4f0;
            border-left: 5px solid #bfdbfe;
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.92);
            margin-bottom: 1rem;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
        }

        .sec-contact,.sec-trajets,.sec-alimentation { display: none; }

        .page-title {
            font-family: 'Poppins', sans-serif;
            font-size: 1.5rem;
            font-weight: 700;
            color: #0b3a75;
            letter-spacing: -0.3px;
            margin: 0.6rem 0 0.2rem 0;
            line-height: 1.3;
        }

        .page-title span {
            font-weight: 400;
            color: #1d4ed8;
            font-size: 1rem;
            display: block;
            margin-top: 0.1rem;
            letter-spacing: 0.2px;
        }

        .transport-label {
            font-size: 0.9rem;
            font-weight: 400;
            color: #0f172a;
            margin-top: 0.6rem;
            margin-bottom: 0.2rem;
        }

        [data-testid="stExpander"] > details > summary {
            font-size: 1rem;
            font-weight: 700;
            color: #0b3a75;
            letter-spacing: 0.1px;
        }

        .stButton > button {
            width: 100%;
            border-radius: 12px;
            border: none;
            padding: 0.8rem 1.1rem;
            font-weight: 800;
            background: linear-gradient(135deg, #0f4aa3 0%, #1d4ed8 55%, #2563eb 100%);
            color: white;
            box-shadow: 0 10px 24px rgba(29, 78, 216, 0.35);
        }

        .thanks-screen {
            position: fixed;
            inset: 0;
            width: 100vw;
            height: 100vh;
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
            background:
                radial-gradient(1200px 500px at 12% -12%, #dbeafe 0%, transparent 60%),
                radial-gradient(900px 450px at 88% -18%, #dcfce7 0%, transparent 58%),
                linear-gradient(180deg, #f8fbff 0%, #edf4fb 100%);
            animation: fadeIn 280ms ease-out;
        }

        .thanks-card {
            text-align: center;
            background: rgba(255, 255, 255, 0.96);
            border: 1px solid #d3deea;
            border-radius: 14px;
            box-shadow: 0 16px 34px rgba(15, 23, 42, 0.09);
            padding: 2rem 1.8rem;
            max-width: 620px;
            margin: 0 auto;
            width: 100%;
        }

        .thanks-leaf {
            font-size: 2.35rem;
            line-height: 1;
            margin-bottom: 0.5rem;
        }

        .thanks-title {
            margin: 0;
            color: #123b6b;
            font-size: 1.55rem;
            font-weight: 700;
            letter-spacing: -0.15px;
        }

        .thanks-subtitle {
            margin: 0.6rem 0 0;
            color: #475569;
            font-size: 0.98rem;
            font-weight: 500;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

if st.session_state.show_thanks_screen:
    st.markdown(
        """
        <div class="thanks-screen">
            <div class="thanks-card">
                <div class="thanks-leaf">🌱</div>
                <h1 class="thanks-title">Merci pour votre participation !</h1>
                <p class="thanks-subtitle">Vos informations ont bien été enregistrées pour l'analyse du bilan carbone.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

image_path = Path(__file__).parent / "entete_question.png"
if image_path.exists():
    st.image(str(image_path))

st.markdown(
    """
    <div class="page-title">
      Questionnaire Bilan Carbone — Salariés
      <span>Évaluation des habitudes individuelles · 2025</span>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="hero">
      <h1>Votre quotidien compte pour le climat 🌱</h1>
      <p>
        Merci pour votre participation. Ce questionnaire aide votre entreprise à mieux comprendre
        les habitudes de trajets et d'alimentation des équipes afin de construire un plan d'action
        carbone concret, positif et adapté à la réalité terrain.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="sec-contact"></div>', unsafe_allow_html=True)
with st.expander("Informations du salarié", expanded=True):
    poste = st.text_input("Poste :")
    ville = st.selectbox(
        "Ville :*",
        ["", "Bordeaux", "Chatou", "Lille", "Massy", "Nice", "Toulouse"],
        format_func=lambda x: "Sélectionnez une ville" if x == "" else x,
    )

st.markdown('<div class="sec-trajets"></div>', unsafe_allow_html=True)
with st.expander("Trajets domicile-travail", expanded=True):
    jours_teletravail = st.number_input(
        "Nombre de jours de télétravail moyen par semaine :",
        min_value=0,
        max_value=5,
        step=1,
    )

    st.markdown('<p class="transport-label">Mode de transport — fréquence en jours par semaine</p>', unsafe_allow_html=True)
    transport_bus_tram = st.number_input("Bus / Tram", min_value=0, max_value=7, step=1)
    transport_velo = st.number_input("Vélo", min_value=0, max_value=7, step=1)
    transport_marche = st.number_input("Marche à pieds", min_value=0, max_value=7, step=1)
    transport_voiture = st.number_input("Voiture", min_value=0, max_value=7, step=1)

    type_voiture = None
    if transport_voiture > 0:
        type_voiture = st.radio(
            "Type de voiture :",
            ["Électrique", "Hybride", "Thermique"],
            horizontal=True,
        )

    distance_ar_km = st.number_input(
        "Distance moyenne Aller-Retour par jour de travail (km) :",
        min_value=0,
        step=1,
    )

st.markdown('<div class="sec-alimentation"></div>', unsafe_allow_html=True)
with st.expander("Alimentation", expanded=True):
    repas_vegetariens = st.number_input(
        "Nombre de repas végétariens du midi par semaine (au travail) :",
        min_value=0,
        step=1,
    )
    repas_viande_rouge = st.number_input(
        "Nombre de repas du midi avec viande rouge par semaine :",
        min_value=0,
        step=1,
    )
    repas_viande_blanche_poisson = st.number_input(
        "Nombre de repas du midi avec viande blanche / poisson par semaine :",
        min_value=0,
        step=1,
    )

st.markdown("---")
if st.button("🚀 Envoyer le questionnaire"):
    erreurs = []

    if not ville:
        erreurs.append("- Ville")

    total_transport = transport_bus_tram + transport_velo + transport_marche + transport_voiture
    if total_transport <= 0:
        erreurs.append("- Indiquer au moins une fréquence de mode de transport")

    if erreurs:
        st.error("Veuillez corriger les champs suivants :\n\n" + "\n".join(erreurs))
    else:
        reponses = {
            "poste": poste,
            "ville": ville,
            "jours_teletravail": jours_teletravail,
            "transport_bus_tram": transport_bus_tram,
            "transport_velo": transport_velo,
            "transport_marche": transport_marche,
            "transport_voiture": transport_voiture,
            "type_voiture": type_voiture,
            "distance_ar_km": distance_ar_km,
            "repas_vegetariens": repas_vegetariens,
            "repas_viande_rouge": repas_viande_rouge,
            "repas_viande_blanche_poisson": repas_viande_blanche_poisson,
        }

        db_ok, db_message = save_salarie_response(reponses)
        if db_ok:
            st.session_state.show_thanks_screen = True
            st.rerun()
        else:
            st.error("Le questionnaire est valide, mais l'enregistrement principal a échoué.")
            st.warning(db_message)
