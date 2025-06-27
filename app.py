from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)

@app.route("/api/preise")
def preise():
    stadt = request.args.get("stadt")
    marketing_type = request.args.get("marketing_type", "buy").lower()
    property_type = request.args.get("property_type", "").lower()  # optional: "house" oder "apartment"

    if not stadt:
        return jsonify({"error": "Parameter 'stadt' fehlt."}), 400

    if marketing_type not in ["buy", "rent"]:
        return jsonify({"error": "Ungültiger Wert für 'marketing_type'. Erlaubt: 'buy' oder 'rent'."}), 400

    # URL aufbauen ohne property_type
    url = f"https://www.homeday.de/preisatlas/{stadt.lower()}/?marketing_type={marketing_type}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        page.goto(url)

        try:
            page.wait_for_selector("div[data-testid='price-table'] td span", timeout=5000)
            preiselemente = page.locator("div[data-testid='price-table'] td span").all_text_contents()
        except:
            browser.close()
            return jsonify({"error": f"Preisdaten für '{stadt}' konnten nicht geladen werden."}), 500

        browser.close()

        # Initialisieren
        haus_preis = None
        wohnung_preis = None

        # Durchsuche die Preise nach Schlüsselbegriffen
        for text in preiselemente:
            if marketing_type == "rent":
                if "Miete pro m² Haus" in text:
                    haus_preis = text
                elif "Miete pro m² Wohnung" in text:
                    wohnung_preis = text
            elif marketing_type == "buy":
                if "Kaufpreis pro m² Haus" in text:
                    haus_preis = text
                elif "Kaufpreis pro m² Wohnung" in text:
                    wohnung_preis = text

        ergebnis = {"typ": "miete" if marketing_type == "rent" else "kauf"}

        if property_type == "house":
            if haus_preis:
                ergebnis["haus_" + ("mietpreis_m2" if marketing_type == "rent" else "kaufpreis_m2")] = haus_preis
        elif property_type == "apartment":
            if wohnung_preis:
                ergebnis["wohnung_" + ("mietpreis_m2" if marketing_type == "rent" else "kaufpreis_m2")] = wohnung_preis
        else:
            # Wenn kein spezifischer Typ gewünscht ist, gib beide aus
            if haus_preis:
                ergebnis["haus_" + ("mietpreis_m2" if marketing_type == "rent" else "kaufpreis_m2")] = haus_preis
            if wohnung_preis:
                ergebnis["wohnung_" + ("mietpreis_m2" if marketing_type == "rent" else "kaufpreis_m2")] = wohnung_preis

        if len(ergebnis) <= 1:
            return jsonify({"error": "Nicht genügend Preisdaten gefunden."}), 404

        return jsonify(ergebnis)

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
