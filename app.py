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

    stadt = normalize(stadt)
    strasse = normalize(strasse)
    plz = plz.strip()

    # URL bauen
    if strasse and plz:
        url = f"https://www.homeday.de/de/preisatlas/{stadt}/{strasse},+{plz}?marketing_type={marketing_type}&property_type={property_type}&map_layer=standard"
    else:
        url = f"https://www.homeday.de/de/preisatlas/{stadt}?marketing_type={marketing_type}&property_type={property_type}&map_layer=standard"

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

        if len(texts) < 2:
            return jsonify({"error": "Nicht genügend Preisdaten gefunden."}), 404

        # Reihenfolge beachten (Wohnung kommt zuerst)
        if marketing_type == "rent":
            return {
                "wohnung_mietpreis_m2": texts[0],
                "haus_mietpreis_m2": texts[1],
                "typ": "miete"
            }
        else:
            return {
                "haus_kaufpreis_m2": texts[0],
                "wohnung_kaufpreis_m2": texts[1],
                "typ": "kauf"
            }

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
