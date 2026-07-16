from flask import Flask, render_template, request
from luna_engine import run_local_luna, generate_modern_seasons

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    seasons = generate_modern_seasons()
    result_data = None
    error_msg = None

    if request.method == "POST":
        player_name = request.form.get("player_name")
        season_choice = request.form.get("season_choice")
        season_type = request.form.get("season_type")

        target_year = None
        target_name = "All Career"
        if season_choice != "ALL":
            for s_year, s_name in seasons:
                if season_choice == s_name:
                    target_year = s_year
                    target_name = s_name
                    break
        
        result = run_local_luna(player_name, target_year, target_name, season_type)

        if isinstance(result, str):
            error_msg = result
        else:
            result_data = result

    return render_template("index.html", seasons=seasons, result_data=result_data, error_msg=error_msg)

if __name__ == "__main__":
    app.run(debug=True)
