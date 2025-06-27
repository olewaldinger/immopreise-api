from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)

def normalize(text):
    return (
        text.lower()
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
        .replace(" ", "-")
    )

@app.route("/api/preise")
def preise():
    stadt = request.args.get("stadt", "")
    strasse = request.args.get("strasse", "")
    plz = request.args.get("plz", "")
    marketing_type = request.args.get("marketing_type", "sell").lower()
    property_type = request.args.get("property_type", "").lower()

    if not stadt:
        return jsonify({"error": "Parameter 'stadt' fehlt."}), 400

    if marketing_type not in ["sell", "rent"]:
        return jsonify({"error": "Ungültiger Wert für 'marketing_type'. Erlaubt: 'sell' oder 'rent'."}), 400

    stadt_slug = normalize(stadt)
    strasse_slug = normalize(strasse)
    plz = plz.strip()

    # URL bauen
    if strasse and plz:
        if not property_type:
            return jsonify({"error": "Für straßengenaue Abfragen ist 'property_type' erforderlich (house oder apartment)."}), 400
        url = f"https://www.homeday.de/de/preisatlas/{stadt_slug}/{strasse_slug},+{plz}?marketing_type={marketing_type}&property_type={property_type}&map_layer=standard"
    else:
        # Nur Stadt -> property_type NICHT anhängen
        url = f"https://www.homeday.de/de/preisatlas/{stadt_slug}?marketing_type={marketing_type}&map_layer=standard"

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
            return jsonify({"error": f"Preisdaten für '{stadt}' konnten nicht geladen werden."}), 500

        browser.close()

        if not texts:
            return jsonify({"error": "Nicht genügend Preisdaten gefunden."}), 404

        if strasse and plz:
            # Bei Straße: es gibt nur einen Preis, je nach property_type
            if property_type == "apartment":
                return {"wohnung_" + ("mietpreis_m2" if marketing_type == "rent" else "kaufpreis_m2"): texts[0], "typ": "miete" if marketing_type == "rent" else "kauf"}
            elif property_type == "house":
                return {"haus_" + ("mietpreis_m2" if marketing_type == "rent" else "kaufpreis_m2"): texts[0], "typ": "miete" if marketing_type == "rent" else "kauf"}
            else:
                return jsonify({"error": "Ungültiger property_type"}), 400
        else:
            # Bei Stadt: es gibt zwei Werte (Haus & Wohnung)
            if len(texts) < 2:
                return jsonify({"error": "Nicht genügend Preisdaten gefunden."}), 404

            return {
                "haus_" + ("mietpreis_m2" if marketing_type == "rent" else "kaufpreis_m2"): texts[0],
                "wohnung_" + ("mietpreis_m2" if marketing_type == "rent" else "kaufpreis_m2"): texts[1],
                "typ": "miete" if marketing_type == "rent" else "kauf"
            }

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)