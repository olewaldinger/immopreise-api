from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)

def get_prices_from_homeday(city_slug):
    url = f"https://www.homeday.de/de/preisatlas/{city_slug}"
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

        if len(texts) >= 2:
            return {
                "haus_kaufpreis_m2": texts[0],
                "wohnung_kaufpreis_m2": texts[1]
            }
        return {"error": "Nicht genügend Preisdaten gefunden."}

@app.route("/api/preise", methods=["GET"])
def get_preise():
    city = request.args.get("stadt", "").lower().replace(" ", "-")
    if not city:
        return jsonify({"error": "Parameter 'stadt' fehlt."}), 400

    try:
        data = get_prices_from_homeday(city)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
