from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
import urllib.parse

app = Flask(__name__)

def normalize_location(text):
    # Ersetzt Umlaute und Leerzeichen für URL
    replacements = {
        'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss',
        'Ä': 'Ae', 'Ö': 'Oe', 'Ü': 'Ue'
    }
    for search, replace in replacements.items():
        text = text.replace(search, replace)
    return urllib.parse.quote_plus(text.strip().lower())

@app.route("/api/preise")
def preise():
    stadt = request.args.get("stadt")
    strasse = request.args.get("strasse", "")
    plz = request.args.get("plz", "")
    marketing_type = request.args.get("marketing_type", "sell").lower()
    property_type = request.args.get("property_type", "").lower()

    if not stadt:
        return jsonify({"error": "Parameter 'stadt' fehlt."}), 400

    # URL-Pfad zusammensetzen
    pfad = normalize_location(stadt)
    if strasse and plz:
        pfad += "/" + normalize_location(f"{strasse}, {plz}")

    url = f"https://www.homeday.de/de/preisatlas/{pfad}?marketing_type={marketing_type}"
    if property_type:
        url += f"&property_type={property_type}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        page.goto(url)

        try:
            page.wait_for_selector(".price-block__price__average", timeout=5000)
            elements = page.query_selector_all(".price-block__price__average")
            texts = [el.inner_text().strip() for el in elements]
        except:
            browser.close()
            return jsonify({"error": f"Preisdaten für '{pfad}' konnten nicht geladen werden."}), 500

        browser.close()

        if len(texts) < 2:
            return jsonify({"error": "Nicht genügend Preisdaten gefunden."}), 404

        # Haus = immer zweiter Eintrag bei Miet- und Kaufpreisen
        return {
            "wohnung_" + ("mietpreis_m2" if marketing_type == "rent" else "kaufpreis_m2"): texts[0],
            "haus_" + ("mietpreis_m2" if marketing_type == "rent" else "kaufpreis_m2"): texts[1],
            "typ": "miete" if marketing_type == "rent" else "kauf"
        }

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
