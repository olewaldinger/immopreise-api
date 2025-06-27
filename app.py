from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)

@app.route("/api/preise")
def preise():
    stadt = request.args.get("stadt")
    marketing_type = request.args.get("marketing_type", "buy").lower()
    property_type = request.args.get("property_type", "").lower()

    if not stadt:
        return jsonify({"error": "Parameter 'stadt' fehlt."}), 400

    if marketing_type not in ["buy", "rent"]:
        return jsonify({"error": "Ungültiger Wert für 'marketing_type'. Erlaubt: 'buy' oder 'rent'."}), 400

    # Richtiges URL-Verhalten: nur bei 'rent' Parameter hinzufügen
    if marketing_type == "rent":
        url = f"https://www.homeday.de/de/preisatlas/{stadt}?marketing_type=rent"
    else:
        url = f"https://www.homeday.de/de/preisatlas/{stadt}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        page.goto(url)

        try:
            page.wait_for_selector("p.price-block__price__average", timeout=7000)
            preisfelder = page.locator("p.price-block__price__average").all_text_contents()
        except:
            browser.close()
            return jsonify({"error": f"Preisdaten für '{stadt}' konnten nicht geladen werden."}), 500

        browser.close()

        if len(preisfelder) < 2:
            return jsonify({"error": "Nicht genügend Preisdaten gefunden."}), 404

        # Immer: Erst Haus, dann Wohnung
        haus_preis = preisfelder[0]
        wohnung_preis = preisfelder[1]

        ergebnis = {"typ": "miete" if marketing_type == "rent" else "kauf"}

        if property_type == "house":
            ergebnis_key = "haus_" + ("mietpreis_m2" if marketing_type == "rent" else "kaufpreis_m2")
            ergebnis[ergebnis_key] = haus_preis
        elif property_type == "apartment":
            ergebnis_key = "wohnung_" + ("mietpreis_m2" if marketing_type == "rent" else "kaufpreis_m2")
            ergebnis[ergebnis_key] = wohnung_preis
        else:
            ergebnis["haus_" + ("mietpreis_m2" if marketing_type == "rent" else "kaufpreis_m2")] = haus_preis
            ergebnis["wohnung_" + ("mietpreis_m2" if marketing_type == "rent" else "kaufpreis_m2")] = wohnung_preis

        return jsonify(ergebnis)

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
