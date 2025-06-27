from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)

@app.route("/api/preise")
def preise():
    stadt = request.args.get("stadt")
    marketing_type = request.args.get("marketing_type", "buy")
    property_type = request.args.get("property_type", "")

    if not stadt:
        return jsonify({"error": "Parameter 'stadt' fehlt."}), 400

    # URL zusammenbauen
    base_url = f"https://www.homeday.de/preisatlas/{stadt.lower()}/"
    url = f"{base_url}?marketing_type={marketing_type}"
    if property_type:
        url += f"&property_type={property_type}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)

        try:
            # Preise auslesen
            page.wait_for_selector("text=Ø Kaufpreis", timeout=5000)
            preiselemente = page.locator("div[data-testid='price-table'] td span").all_text_contents()
        except:
            browser.close()
            return jsonify({"error": f"Preisdaten für '{stadt}' konnten nicht geladen werden."}), 500

        browser.close()

        # Werte extrahieren
        haus_preis = next((p for p in preiselemente if "Haus" in p), None)
        wohnung_preis = next((p for p in preiselemente if "Wohnung" in p), None)

        ergebnis = {}
        if marketing_type == "rent":
            ergebnis["typ"] = "miete"
            if haus_preis:
                ergebnis["haus_mietpreis_m2"] = haus_preis
            if wohnung_preis:
                ergebnis["wohnung_mietpreis_m2"] = wohnung_preis
        else:
            ergebnis["typ"] = "kauf"
            if haus_preis:
                ergebnis["haus_kaufpreis_m2"] = haus_preis
            if wohnung_preis:
                ergebnis["wohnung_kaufpreis_m2"] = wohnung_preis

        return jsonify(ergebnis)
