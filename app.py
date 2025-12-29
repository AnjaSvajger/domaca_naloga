import streamlit as st
import json
import pandas as pd
import os
import altair as alt
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# --- 1. KONFIGURACIJA STRANI ---
st.set_page_config(
    page_title="Analiza Trga 2023", # Malo spremenjen naslov
    page_icon="📈",
    layout="wide"
)

# --- 2. FUNKCIJE ZA NALAGANJE ---
@st.cache_data
def load_data():
    file_path = 'scraped_data.json'
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

# --- 3. SIDEBAR (Samo navigacija, brez filtrov!) ---
st.sidebar.header("Meni")
view_option = st.sidebar.radio("Pojdi na:", ["Products", "Testimonials", "Reviews"])
st.sidebar.markdown("---")
st.sidebar.caption("Podatki pridobljeni za leto 2023.")

data = load_data()
if not data:
    st.error("Ni podatkov! Preveri scraped_data.json.")
    st.stop()

# --- 4. GLAVNA VSEBINA ---
st.title(f"📌 {view_option}")

# ==========================================
# A) PRODUCTS VIEW
# ==========================================
if view_option == "Products":
    st.markdown("### Katalog izdelkov")
    df = pd.DataFrame(data.get("products", []))
    if not df.empty:
        # Prikaz v dveh stolpcih za lepši izgled
        col1, col2 = st.columns([1, 3])
        col1.metric("Skupaj izdelkov", len(df))
        col2.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.warning("Ni produktov.")

# ==========================================
# B) TESTIMONIALS VIEW
# ==========================================
elif view_option == "Testimonials":
    st.markdown("### Kaj pravijo stranke?")
    df = pd.DataFrame(data.get("testimonials", []))
    if not df.empty:
        # Izračunamo povprečje zvezdic, če obstajajo
        avg_rating = df["rating"].mean()
        
        c1, c2 = st.columns(2)
        c1.metric("Število mnenj", len(df))
        c2.metric("Povprečna ocena", f"{avg_rating:.1f} / 5.0")
        
        st.divider()
        
        # Lepši prikaz z zvezdicami
        df["Ocena"] = df["rating"].apply(lambda x: "⭐" * int(x) if str(x).isdigit() else "⭐")
        st.dataframe(df[["Ocena", "text"]], use_container_width=True, hide_index=True)
    else:
        st.warning("Ni testimonials.")

# ==========================================
# C) REVIEWS VIEW (PRENOVLJEN DIZAJN)
# ==========================================
elif view_option == "Reviews":
    st.markdown("### Analiza mnenj in sentimenta")
    df = pd.DataFrame(data.get("reviews", []))
    
    if not df.empty:
        # Priprava datuma
        df['date_obj'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date_obj'])
        
        # --- NOVI FILTRI (Zgoraj v stolpcih, ne v sidebarju) ---
        st.write("🛠️ **Filtri podatkov:**")
        
        filter_col1, filter_col2 = st.columns(2)
        
        with filter_col1:
            # 1. Izbira meseca (Dropdown namesto Sliderja)
            months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
            selected_month = st.selectbox("📅 Izberi mesec:", months, index=4) # Privzeto May
            month_idx = months.index(selected_month) + 1
            
        with filter_col2:
            # 2. Nov filter za ocene (Multiselect) - To te loči od sošolcev
            # Uporabnik lahko izbere npr. samo "5" in "1"
            available_ratings = sorted(df['rating'].unique())
            selected_ratings = st.multiselect("⭐ Prikaži ocene:", available_ratings, default=available_ratings)

        # --- LOGIKA FILTRIRANJA ---
        filtered_df = df[
            (df['date_obj'].dt.month == month_idx) & 
            (df['date_obj'].dt.year == 2023) &
            (df['rating'].isin(selected_ratings)) # Dodaten filter
        ].copy()
        
        st.divider()

        # --- PRIKAZ REZULTATOV ---
        if not filtered_df.empty:
            
            # KPI Metrike
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Prikazanih mnenj", len(filtered_df))
            avg_r = filtered_df['rating'].mean()
            kpi2.metric("Povpr. ocena meseca", f"{avg_r:.2f}")
            
            # Simuliran sentiment (Za Render Free Tier)
            # > 3 je pozitivno, <= 3 je negativno
            positive_count = len(filtered_df[filtered_df['rating'] > 3])
            kpi3.metric("Pozitivnih mnenj", f"{positive_count}")

            # 1. WORD CLOUD (Oblak besed)
            st.subheader(f"☁️ Najpogostejše besede v mesecu {selected_month}")
            try:
                text_data = " ".join(filtered_df['text'].astype(str).tolist())
                # Spremenimo barvo ozadja na črno za drug stil
                wc = WordCloud(width=800, height=350, background_color='black', colormap='Pastel1').generate(text_data)
                
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.imshow(wc, interpolation='bilinear')
                ax.axis("off")
                st.pyplot(fig)
            except: st.info("Premalo besedila za generiranje oblaka besed.")
            
            # 2. SENTIMENT GRAF (Altair)
            st.subheader("📊 Sentiment Analiza")
            
            # Priprava podatkov za graf
            filtered_df['Sentiment'] = filtered_df['rating'].apply(lambda x: 'POZITIVNO 😊' if int(x) > 3 else 'NEGATIVNO 😠')
            
            # Grafikon (Donut chart namesto Bar chart - da bo drugače!)
            chart_base = alt.Chart(filtered_df).encode(theta=alt.Theta("count()", stack=True))
            
            pie = chart_base.mark_arc(outerRadius=120).encode(
                color=alt.Color("Sentiment", scale=alt.Scale(domain=['POZITIVNO 😊', 'NEGATIVNO 😠'], range=['#66c2a5', '#fc8d62'])),
                order=alt.Order("Sentiment", sort="descending"),
                tooltip=["Sentiment", "count()"]
            )
            text = chart_base.mark_text(radius=140).encode(
                text="count()",
                order=alt.Order("Sentiment", sort="descending"),
                color=alt.value("black")  
            )
            
            st.altair_chart(pie + text, use_container_width=True)
            
            # 3. TABELA PODATKOV
            with st.expander("Poglej podrobne podatke (Tabela)"):
                st.dataframe(
                    filtered_df[['date', 'rating', 'Sentiment', 'text']], 
                    use_container_width=True,
                    hide_index=True
                )
            
        else:
            st.warning(f"Za mesec {selected_month} in izbrane ocene ni najdenih mnenj.")
