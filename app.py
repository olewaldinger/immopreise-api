from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)

def get_prices_from_homeday(city_slug, marketing_type="buy"):
    suffix = f"?marketing_type={marketing_type}" if marketing_type == "rent" else ""
    url = f"https://www.homeday.de/de/preisatlas/{city_slug}{suffix}"

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox"]
        )
        page = browser.new_page()
        page.goto(url)
        page.wait_for_selector('.price-block__price__average', timeout=5000)

        elements = page.query_selector_all('.price-block__price__average')
        texts = [el.inner_text().strip() for el in elements]

        browser.close()

        if marketing_type == "rent":
            if len(texts) >= 2:
                return {
                    "wohnung_mietpreis_m2": texts[0],
                    "haus_mietpreis_m2": texts[1],
                    "typ": "miete"
                }
        else:
            if len(texts) >= 2:
                return {
                    "wohnung_kaufpreis_m2": texts[1],  # Achtung: Reihenfolge beachten
                    "haus_kaufpreis_m2": texts[0],
                    "typ": "kauf"
                }

        return {"error": "Nicht genügend Preisdaten gefunden."}

@app.route("/api/preise", methods=["GET"])
def get_preise():
    city = request.args.get("stadt", "").lower().replace(" ", "-")
    marketing_type = request.args.get("marketing_type", "buy").lower()

    if not city:
        return jsonify({"error": "Parameter 'stadt' fehlt."}), 400

    if marketing_type not in ["buy", "rent"]:
        return jsonify({"error": "Ungültiger Wert für 'marketing_type'. Erlaubt: 'buy' oder 'rent'."}), 400

    try:
        data = get_prices_from_homeday(city, marketing_type)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
