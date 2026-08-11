from flask import Flask, jsonify, render_template

from analysis.session import Session
from sensors import create_sensor


def create_app(args) -> Flask:
    app = Flask(__name__)
    session = Session(create_sensor(args), log_path=args.log_file, print_sensor=args.print, print_rep=args.rep)
    session.start()

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/reps")
    def api_reps():
        return jsonify({
            "reps": [{
                "index": r.index,
                "time_up_s": round(r.time_up_s, 3),
                "time_down_s": round(r.time_down_s, 3),
                "max_speed_up_mps": round(r.max_speed_up_mps, 3),
            } for r in session.latest_reps()],
            "full": session.is_full(),
        })

    @app.route("/api/clear", methods=["POST"])
    def api_clear():
        session.clear()
        return jsonify({"status": "cleared"})

    return app
