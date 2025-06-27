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

    url = f"https://www.homeday.de/preisatlas/{stadt.lower()}/?marketing_type={marketing_type}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        page.goto(url)

        try:
            page.wait_for_selector("div[data-testid='price-table'] td", timeout=5000)
            zellen = page.locator("div[data-testid='price-table'] td").all_text_contents()
        except:
            browser.close()
            return jsonify({"error": f"Preisdaten für '{stadt}' konnten nicht geladen werden."}), 500

        browser.close()

        # Die Tabelle ist wie folgt aufgebaut:
        # Zellen = ["Haus", "Ø 13,50 €/m²", "Wohnung", "Ø 11,20 €/m²"]
        ergebnis = {"typ": "miete" if marketing_type == "rent" else "kauf"}
        for i in range(0, len(zellen) - 1, 2):
            label = zellen[i].lower()
            wert = zellen[i + 1]

            if "haus" in label:
                key = "haus_" + ("mietpreis_m2" if marketing_type == "rent" else "kaufpreis_m2")
                ergebnis[key] = wert
            elif "wohnung" in label:
                key = "wohnung_" + ("mietpreis_m2" if marketing_type == "rent" else "kaufpreis_m2")
                ergebnis[key] = wert

        if len(ergebnis) <= 1:
            return jsonify({"error": "Nicht genügend Preisdaten gefunden."}), 404

        return jsonify(ergebnis)

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
