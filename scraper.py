import json
import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

class WebScraper:
    def __init__(self):
        options = Options()
        # options.add_argument("--headless")  # Če želiš videti brskalnik, pusti zakomentirano
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        
        print("🔧 Inicializacija gonilnika...")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        self.data = {
            "products": [],
            "reviews": [],
            "testimonials": []
        }

    def count_yellow_stars(self, element):
        try:
            stars = element.find_elements(By.CSS_SELECTOR, "svg path[fill='#ffce31']")
            return min(len(stars), 5) # Omejimo na max 5
        except:
            return 0

    def scrape_products(self):
        print("\n📦 Zbiram: PRODUCTS (s cenami)...")
        page = 1
        while True:
            self.driver.get(f"https://web-scraping.dev/products?page={page}")
            time.sleep(1)
            
            prods = self.driver.find_elements(By.CSS_SELECTOR, "div.product-item, div.row.product, div[class*='product-item']")
            if not prods: break
            
            added = 0
            for p in prods:
                try:
                    text_parts = p.text.split('\n')
                    title = text_parts[0]
                    price_match = re.search(r'[$€£]?\s?\d+\.\d{2}', p.text)
                    price = price_match.group(0).strip() if price_match else "N/A"
                    
                    if title and title != "Log in":
                        if not any(prod['title'] == title for prod in self.data['products']):
                            self.data["products"].append({"title": title, "price": price})
                            added += 1
                except: continue
            
            print(f"   Stran {page}: +{added} produktov.")
            if added == 0: break
            page += 1

    def scrape_reviews(self):
        print("\n⭐ Zbiram: REVIEWS (Samo 2023)...")
        self.driver.get("https://web-scraping.dev/reviews")
        time.sleep(2)
        
        while True:
            reviews = self.driver.find_elements(By.CLASS_NAME, "review")
            for review in reviews:
                try:
                    text_all = review.text
                    lines = text_all.strip().split('\n')
                    
                    date_str = None
                    found_year = 0
                    for line in lines:
                        year_match = re.search(r'(20\d\d)', line)
                        if year_match:
                            found_year = int(year_match.group(1))
                            date_str = line
                            break
                    
                    if not date_str or found_year != 2023: continue
                        
                    comment_text = max(lines, key=len)
                    rating = self.count_yellow_stars(review)
                    
                    if not any(r['text'] == comment_text for r in self.data['reviews']):
                        try:
                            dt = datetime.strptime(date_str, "%B %d, %Y")
                            clean_date = dt.strftime("%Y-%m-%d")
                        except: clean_date = date_str

                        self.data["reviews"].append({
                            "date": clean_date, "text": comment_text, "rating": rating
                        })
                except: continue
            
            try:
                load_more = self.driver.find_element(By.ID, "page-load-more")
                if load_more.is_displayed():
                    self.driver.execute_script("arguments[0].click();", load_more)
                    time.sleep(1.5)
                else: break
            except: break
                
        print(f"   ✅ Skupaj shranjenih {len(self.data['reviews'])} mnenj.")

    def scrape_testimonials(self):
        print("\n💬 Zbiram: TESTIMONIALS (Popravljeno)...")
        self.driver.get("https://web-scraping.dev/testimonials")
        time.sleep(2)
        
        # Scroll do dna
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height: break
            last_height = new_height
            
        # UPORABIMO ŠIROK SELEKTOR, KI DELA
        cards = self.driver.find_elements(By.CSS_SELECTOR, "div[class*='testimonial']")
        
        added = 0
        for card in cards:
            try:
                text = card.text.replace("\n", " ").strip()
                
                # --- FILTRIRANJE SMETI ---
                # Če tekst vsebuje "Take a look" (glava), ga preskočimo
                if "Take a look" in text or "Reviews" in text:
                    continue
                
                # Če je tekst prekratek, ga preskočimo
                if len(text) < 10:
                    continue

                if not any(t['text'] == text for t in self.data['testimonials']):
                    rating = self.count_yellow_stars(card)
                    self.data["testimonials"].append({
                        "text": text,
                        "rating": rating
                    })
                    added += 1
            except: continue
            
        print(f"   ✅ Skupaj shranjenih {len(self.data['testimonials'])} pričevanj.")

    def save_data(self):
        with open("scraped_data.json", "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)
        print(f"\n💾 Podatki uspešno shranjeni v scraped_data.json")
        self.driver.quit()

if __name__ == "__main__":
    scraper = WebScraper()
    scraper.scrape_products()
    scraper.scrape_reviews()
    scraper.scrape_testimonials()
    scraper.save_data()