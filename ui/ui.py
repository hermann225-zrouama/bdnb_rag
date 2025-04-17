import streamlit as st
import requests
import plotly.express as px
import polars as pl
from tools.config import API_HOST, API_PORT


# Configuration de l'API
API_URL = f"http://{API_HOST}:{API_PORT}/chat"

# Titre et description de l'application
st.title("Assistant BDNB")
st.markdown("""
Interrogez la Base de Données Nationale des Bâtiments (BDNB) en langage naturel ou utilisez les filtres pour explorer les données.
Exemples de questions :
- "Quels sont les bâtiments résidentiels de plus de 1000 m² classés F ou G dans le département 93 ?"
- "Quelle est la surface moyenne des bâtiments tertiaires avant 1975 dans le Rhône ?"
""")

# Champ pour poser une question
query = st.text_input("Posez votre question sur les bâtiments :", key="query_input")
if query:
    try:
        response = requests.post(API_URL, json={"message": query}, timeout=3600)
        response.raise_for_status()
        result = response.json()

        st.write("**Réponse :**")
        if isinstance(result["response"], list):
            # Cas des réponses SQL (quantitatives)
            df = pl.DataFrame(result["response"])
            st.dataframe(df)

            # Visualisations adaptées au type de réponse
            if "nb_passoires" in df.columns:
                fig = px.bar(df, x="nom_quartier", y="nb_passoires", 
                            title="Passoires thermiques par quartier")
                st.plotly_chart(fig)
            elif "surface_moyenne" in df.columns:
                st.write(f"Surface moyenne : {df['surface_moyenne'][0]:.2f} m²")
            elif "pourcentage" in df.columns:
                st.write(f"Pourcentage : {df['pourcentage'][0]:.2f}%")
            elif "nb_class_g" in df.columns:
                st.write(f"Commune avec le plus de bâtiments classés G : {df['libelle_commune_insee'][0]} "
                         f"({df['nb_class_g'][0]} bâtiments)")
        else:
            # Cas des réponses RAG (descriptives)
            st.write(result["response"])

            if result["retrieved_nodes"]:
                st.write("**Documents récupérés :**")
                for node in result["retrieved_nodes"]:
                    st.markdown(f"- **Bâtiment {node['batiment_groupe_id']}** (Score: {node['score']:.2f})")
                    with st.expander("Détails"):
                        st.write(f"**Commune** : {node['metadata']['libelle_commune_insee']}")
                        st.write(f"**Département** : {node['metadata']['code_departement_insee']}")
                        st.write(f"**Usage** : {node['metadata']['usage_principal']}")
                        st.write(f"**Surface** : {node['metadata']['s_totale_bat'] or 'Inconnue'} m²")
                        st.write(f"**Classe DPE** : {node['metadata']['classe_bilan_dpe']}")
                        st.write(f"**Passoire thermique** : {'Oui' if node['metadata']['is_passoire_thermique'] else 'Non'}")

    except requests.exceptions.RequestException as e:
        st.error(f"Erreur de connexion à l'API : {str(e)}")
    except Exception as e:
        st.error(f"Erreur : {str(e)}")

# Footer
st.markdown("---")
st.markdown("BDNB RAG - Version 1.0")

if __name__ == "__main__":
    print("Streamlit UI started")