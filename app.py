import streamlit as st
import json
import pandas as pd
import os
import altair as alt
from transformers import pipeline
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# --- 1. KONFIGURACIJA STRANI ---
st.set_page_config(
    page_title="eCommerce Sentiment Dashboard",
    page_icon="🛍️",
    layout="wide"
)

# --- 2. FUNKCIJE ZA NALAGANJE ---
@st.cache_data
def load_data():
    """Naloži JSON datoteko, ki jo je ustvaril scraper."""
    file_path = 'scraped_data.json'
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

@st.cache_resource
def load_sentiment_model():
    """Naloži Hugging Face model samo enkrat (cache)."""
    # Uporabljamo privzet model za sentiment analysis
    return pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")

# Naložimo podatke
data = load_data()

# Če datoteke ni, opozori uporabnika
if not data:
    st.error("⚠️ Datoteka 'scraped_data.json' ne obstaja! Prepričaj se, da si najprej pognala 'scraper.py'.")
    st.stop()

# --- 3. STRANSKI MENI (NAVIGACIJA) ---
st.sidebar.title("🔍 Navigacija")
view_option = st.sidebar.radio(
    "Izberi pogled:",
    ["Products", "Testimonials", "Reviews"]
)
st.sidebar.markdown("---")

# Dodaten filter samo za Testimonials
selected_rating_filter = "All"
if view_option == "Testimonials":
    st.sidebar.subheader("Filter po ocenah")
    selected_rating_filter = st.sidebar.radio(
        "Prikaži:",
        ["All", "5 Stars", "4 Stars", "3 Stars", "2 Stars", "1 Star"]
    )

st.sidebar.info("Dashboard za analizo mnenj.\nPodatki: leto 2023.")

# --- 4. GLAVNA VSEBINA ---
st.title(f"📊 {view_option} Dashboard")

# ==========================================
# A) PRODUCTS VIEW
# ==========================================
if view_option == "Products":
    st.markdown("Seznam vseh postrganih produktov in njihovih cen.")
    products_list = data.get("products", [])
    
    if products_list:
        df_products = pd.DataFrame(products_list)
        
        # Prikaz metrike
        st.metric("Število produktov", len(df_products))
        
        # Prikaz tabele
        st.dataframe(
            df_products, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "price": st.column_config.TextColumn("Cena", width="small"),
                "title": st.column_config.TextColumn("Ime Produkta")
            }
        )
    else:
        st.warning("Ni podatkov o produktih.")

# ==========================================
# B) TESTIMONIALS VIEW
# ==========================================
elif view_option == "Testimonials":
    st.markdown("Mnenja strank (Testimonials) s filtriranjem po zvezdicah.")
    testimonials_list = data.get("testimonials", [])
    
    if testimonials_list:
        df_testi = pd.DataFrame(testimonials_list)
        
        # Logika za filtriranje
        if "rating" in df_testi.columns:
            if selected_rating_filter != "All":
                star_num = int(selected_rating_filter.split()[0]) # "5 Stars" -> 5
                filtered_df = df_testi[df_testi['rating'] == star_num]
            else:
                filtered_df = df_testi
            
            st.metric("Prikazana mnenja", len(filtered_df))
            
            if not filtered_df.empty:
                # Dodamo vizualne zvezdice za tabelo
                filtered_df["rating_display"] = filtered_df["rating"].apply(lambda x: "⭐" * int(x))
                
                st.dataframe(
                    filtered_df[["rating_display", "text"]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "rating_display": st.column_config.TextColumn("Ocena", width="small"),
                        "text": "Besedilo mnenja"
                    }
                )
            else:
                st.info(f"Ni mnenj z oceno {selected_rating_filter}.")
        else:
            st.dataframe(df_testi, use_container_width=True)
    else:
        st.warning("Ni podatkov o testimonials.")

# ==========================================
# C) REVIEWS VIEW (GLAVNI DEL Z AI)
# ==========================================
elif view_option == "Reviews":
    st.markdown("Analiza mnenj (Reviews) za leto 2023 s pomočjo umetne inteligence.")
    
    reviews_list = data.get("reviews", [])
    
    if reviews_list:
        df_reviews = pd.DataFrame(reviews_list)
        
        # Pretvorba datuma
        df_reviews['date_obj'] = pd.to_datetime(df_reviews['date'], errors='coerce')
        # Odstranimo vrstice, kjer datum ni bil prepoznan
        df_reviews = df_reviews.dropna(subset=['date_obj'])
        
        # --- IZBIRA MESECA (SLIDER) ---
        months = ["January", "February", "March", "April", "May", "June", 
                  "July", "August", "September", "October", "November", "December"]
        
        # Slider vrne ime meseca (npr. "May")
        selected_month_name = st.select_slider("Izberi mesec (leto 2023):", options=months, value="May")
        
        # Pretvorimo ime v številko (May -> 5)
        month_map = {m: i+1 for i, m in enumerate(months)}
        selected_month_num = month_map[selected_month_name]
        
        # Filtriranje DataFrame-a
        filtered_df = df_reviews[
            (df_reviews['date_obj'].dt.month == selected_month_num) & 
            (df_reviews['date_obj'].dt.year == 2023)
        ].copy()
        
        # Prikaz metrik
        col1, col2 = st.columns(2)
        col1.metric("Izbran mesec", f"{selected_month_name} 2023")
        col2.metric("Najdenih mnenj", len(filtered_df))
        
        if not filtered_df.empty:
            
            # --- 1. WORD CLOUD (BONUS) ---
            st.divider()
            st.subheader("☁️ Word Cloud (Najpogostejše besede)")
            try:
                all_text = " ".join(filtered_df['text'].astype(str).tolist())
                if len(all_text) > 0:
                    wordcloud = WordCloud(width=800, height=300, background_color='white').generate(all_text)
                    fig, ax = plt.subplots(figsize=(10, 4))
                    ax.imshow(wordcloud, interpolation='bilinear')
                    ax.axis("off")
                    st.pyplot(fig)
                else:
                    st.info("Premalo besedila za Word Cloud.")
            except Exception as e:
                st.warning(f"Word Cloud napaka: {e}")

            st.divider()

            # --- 2. AI SENTIMENT ANALYSIS ---
            st.subheader("🤖 AI Analiza Sentiment-a")
            st.caption("Uporabljen model: distilbert-base-uncased-finetuned-sst-2-english")
            
            with st.spinner('AI analizira mnenja... Prosim počakaj.'):
                try:
                    sentiment_pipeline = load_sentiment_model()
                    
                    # Hugging Face analiza
                    texts = filtered_df['text'].astype(str).tolist()
                    # Omejimo dolžino teksta, ker imajo modeli limit (512 tokenov)
                    texts = [t[:512] for t in texts] 
                    
                    results = sentiment_pipeline(texts)
                    
                    # Dodamo rezultate v tabelo
                    filtered_df['sentiment_label'] = [r['label'] for r in results]
                    filtered_df['sentiment_score'] = [r['score'] for r in results]
                    
                    # --- 3. GRAF (ALTAIR) ---
                    st.markdown("#### Porazdelitev (Pozitivno vs. Negativno)")
                    
                    chart_data = filtered_df.groupby('sentiment_label').agg(
                        count=('sentiment_label', 'count'),
                        avg_conf=('sentiment_score', 'mean')
                    ).reset_index()
                    
                    # Barva glede na sentiment
                    chart = alt.Chart(chart_data).mark_bar().encode(
                        x=alt.X('sentiment_label', axis=alt.Axis(title="Sentiment")),
                        y=alt.Y('count', axis=alt.Axis(title="Število mnenj")),
                        color=alt.Color('sentiment_label', scale=alt.Scale(domain=['POSITIVE', 'NEGATIVE'], range=['#28a745', '#dc3545'])),
                        tooltip=['sentiment_label', 'count', alt.Tooltip('avg_conf', format='.2%')]
                    ).properties(height=300)
                    
                    st.altair_chart(chart, use_container_width=True)
                    
                    # --- 4. PODROBNA TABELA ---
                    st.markdown("#### Podrobni podatki")
                    
                    # Lepši izpis za tabelo
                    filtered_df['AI Sentiment'] = filtered_df['sentiment_label'].apply(lambda x: "🟢 Pozitivno" if x == "POSITIVE" else "🔴 Negativno")
                    filtered_df['Confidence'] = filtered_df['sentiment_score'].apply(lambda x: f"{x:.1%}")
                    
                    st.dataframe(
                        filtered_df[["date", "AI Sentiment", "Confidence", "text"]],
                        use_container_width=True,
                        hide_index=True
                    )
                    
                except Exception as e:
                    st.error(f"Napaka pri AI analizi: {e}")
                    
        else:
            st.info(f"V mesecu {selected_month_name} 2023 ni bilo najdenih mnenj. Poskusi premakniti drsnik (npr. na September ali May).")
    else:
        st.warning("Ni naloženih mnenj (Reviews).")