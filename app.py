from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)

@app.route("/api/preise")
def preise():
    stadt = request.args.get("stadt")
    marketing_type = request.args.get("marketing_type", "buy").lower()
    property_type = request.args.get("property_type", "").lower()  # optional

    if not stadt:
        return jsonify({"error": "Parameter 'stadt' fehlt."}), 400

    if marketing_type not in ["buy", "rent"]:
        return jsonify({"error": "Ungültiger Wert für 'marketing_type'. Erlaubt: 'buy' oder 'rent'."}), 400

    url = f"https://www.homeday.de/de/preisatlas/{stadt.lower()}?marketing_type={marketing_type}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        page.goto(url)

        try:
            page.wait_for_selector("div.price-block", timeout=5000)
            blocks = page.locator("div.price-block").all()
        except:
            browser.close()
            return jsonify({"error": f"Preisdaten für '{stadt}' konnten nicht geladen werden."}), 500

        haus_preis = None
        wohnung_preis = None

        for block in blocks:
            icon_class = block.locator("div[class*='price-block__property__icon']").get_attribute("class")
            preis = block.locator("p.price-block__price__average").inner_text()

            if "house" in icon_class:
                haus_preis = preis
            elif "apartment" in icon_class:
                wohnung_preis = preis

        browser.close()

        ergebnis = {"typ": "miete" if marketing_type == "rent" else "kauf"}

        if property_type == "house" and haus_preis:
            ergebnis["haus_" + ("mietpreis_m2" if marketing_type == "rent" else "kaufpreis_m2")] = haus_preis
        elif property_type == "apartment" and wohnung_preis:
            ergebnis["wohnung_" + ("mietpreis_m2" if marketing_type == "rent" else "kaufpreis_m2")] = wohnung_preis
        elif property_type == "":
            if haus_preis:
                ergebnis["haus_" + ("mietpreis_m2" if marketing_type == "rent" else "kaufpreis_m2")] = haus_preis
            if wohnung_preis:
                ergebnis["wohnung_" + ("mietpreis_m2" if marketing_type == "rent" else "kaufpreis_m2")] = wohnung_preis

        if len(ergebnis) <= 1:
            return jsonify({"error": "Nicht genügend Preisdaten gefunden."}), 404

        return jsonify(ergebnis)

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
