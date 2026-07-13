from flask import Flask, render_template, jsonify
from analysis.session import Session
from sensors import create_sensor

def create_app(args) -> Flask:
    app = Flask(__name__)
    session = Session(create_sensor(args), log_path=args.log_file)
    session.start()

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/reps")
    def api_reps():
        return jsonify([{
            "index": r.index,
            "time_up_s": round(r.time_up_s, 3),
            "time_down_s": round(r.time_down_s, 3),
            "max_speed_up_mps": round(r.max_speed_up_mps, 3),
        } for r in session.latest_reps()])

    @app.route("/api/clear", methods=["POST"])
    def api_clear():
        session.clear()
        return jsonify({"status": "cleared"})

    return app


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--platform", choices=["rpi", "pc"], default="rpi")
    p.add_argument("--adc-channel", type=int, default=0)
    p.add_argument("--calib-file", default="calibration.json")
    p.add_argument("--log-file", default="reps_log.csv")
    args = p.parse_args()
    create_app(args).run(host="0.0.0.0", port=5000)