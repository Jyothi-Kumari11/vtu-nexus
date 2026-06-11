"""
VTU ScoreMatrix - Flask Dashboard
Run: python app.py

Author  : Jyothi Kumari
USN     : 1JT24IS021
College : Jyothy Institute of Technology
Email   : jyothikumari1146@gmail.com
"""
import os, sys, subprocess, shutil
from flask import Flask, jsonify, render_template, send_file, request
import scraper_engine as engine

app = Flask(__name__)
BASE = os.path.dirname(os.path.abspath(__file__))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/start", methods=["POST"])
def start():
    data = request.get_json(silent=True) or {}
    sem = data.get("semester", "3")
    ok = engine.start_scraping(sem)
    if ok:
        return jsonify({"status": "started"})
    return jsonify({"status": "already_running"}), 400


@app.route("/api/stop", methods=["POST"])
def stop():
    engine.stop_scraping()
    return jsonify({"status": "stop_sent"})


@app.route("/api/status")
def status():
    return jsonify(engine.get_status())


@app.route("/api/generate_report", methods=["POST"])
def generate_report():
    data = request.get_json(silent=True) or {}
    sem = data.get("semester", "3")
    try:
        result = subprocess.run(
            [sys.executable, "index.py", "--report-only", f"--semester={sem}"],
            cwd=BASE, capture_output=True, text=True, timeout=600
        )
        if result.returncode == 0:
            return jsonify({"status": "ok", "msg": "Report generated successfully!"})
        return jsonify({"status": "error", "msg": result.stderr[-500:]}), 500
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500


@app.route("/api/download/<name>")
def download(name):
    allowed = {
        "raw":       "results_output.xlsx",
        "formatted": "formatted_result_sheet.xlsx",
        "final":     "final_report.xlsx",
    }
    fname = allowed.get(name)
    if not fname:
        return "Not found", 404
    path = os.path.join(BASE, fname)
    if not os.path.exists(path):
        return "File not ready yet", 404
    return send_file(path, as_attachment=True)


@app.route("/api/usn_list")
def usn_list():
    try:
        import pandas as pd
        df = pd.read_excel(os.path.join(BASE, "usn_list.xlsx"))
        usns = df.iloc[:, 0].dropna().astype(str).str.strip().tolist()
        return jsonify({"usns": usns, "count": len(usns)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/upload", methods=["POST"])
def upload_file():
    try:
        import pandas as pd
        f = request.files.get("file")
        if not f:
            return jsonify({"error": "No file provided"}), 400
        dest = os.path.join(BASE, "usn_list.xlsx")
        f.save(dest)
        df = pd.read_excel(dest)
        usns = df.iloc[:, 0].dropna().astype(str).str.strip().tolist()
        return jsonify({"count": len(usns), "usns": usns})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/results_data")
def results_data():
    """Return summarised per-student rows for the monitoring table."""
    try:
        import pandas as pd
        raw_path = os.path.join(BASE, "results_output.xlsx")
        if not os.path.exists(raw_path):
            return jsonify({"rows": []})
        raw = pd.read_excel(raw_path).fillna("")
        rows = []
        for usn, grp in raw.groupby("USN"):
            name = grp["Name"].iloc[0] if "Name" in grp.columns else ""
            total = pd.to_numeric(grp["TOTAL"], errors="coerce").sum()
            n_subj = len(grp)
            pct = round(total / n_subj, 1) if n_subj else 0
            failed = (grp["RESULT"].astype(str).str.strip().str.upper()
                      .isin(["F","AB","ABS","FAIL"])).any()
            cls = "FAIL" if failed else ("FCD" if pct > 80 else "PASS")
            # Subject breakdown
            subjects = []
            for _, sr in grp.iterrows():
                subjects.append({
                    "code": str(sr.get("SUBJECT CODE","")),
                    "name": str(sr.get("SUBJECT NAME","")),
                    "int":  str(sr.get("INTERNAL MARKS","")),
                    "ext":  str(sr.get("EXTERNAL MARKS","")),
                    "tot":  str(sr.get("TOTAL","")),
                    "res":  str(sr.get("RESULT","")),
                })
            rows.append({
                "usn": str(usn), "name": str(name),
                "total": int(total), "pct": pct,
                "cls": cls, "subjects": n_subj,
                "subject_data": subjects,
                "sem": str(grp["Semester"].iloc[0]) if "Semester" in grp.columns else ""
            })
        return jsonify({"rows": rows})
    except Exception as e:
        return jsonify({"error": str(e), "rows": []}), 500


@app.route("/api/analytics")
def analytics():
    """Subject-wise and overall analytics for the charts tab."""
    try:
        import pandas as pd
        raw_path = os.path.join(BASE, "results_output.xlsx")
        if not os.path.exists(raw_path):
            return jsonify({"subjects": [], "top3": [], "summary": {}})
        raw = pd.read_excel(raw_path).fillna("")

        # Subject-wise
        subjects = []
        for code, grp in raw.groupby("SUBJECT CODE"):
            total = len(grp)
            passed = (grp["RESULT"].astype(str).str.strip().str.upper() == "P").sum()
            pct = round(passed / total * 100, 1) if total else 0
            name = grp["SUBJECT NAME"].iloc[0] if "SUBJECT NAME" in grp.columns else code
            subjects.append({"code": str(code), "name": str(name),
                              "total": int(total), "passed": int(passed), "pct": float(pct)})
        subjects.sort(key=lambda x: x["pct"], reverse=True)

        # Top 3 scorers
        student_totals = []
        for usn, grp in raw.groupby("USN"):
            name = grp["Name"].iloc[0] if "Name" in grp.columns else ""
            tot = pd.to_numeric(grp["TOTAL"], errors="coerce").sum()
            n = len(grp)
            pct = round(tot / n, 1) if n else 0
            student_totals.append({"usn": str(usn), "name": str(name),
                                   "total": int(tot), "pct": float(pct)})
        student_totals.sort(key=lambda x: x["total"], reverse=True)
        top3 = student_totals[:3]

        # Summary
        n_students = len(student_totals)
        n_pass = sum(1 for s in student_totals if s["pct"] > 0 and
                     not raw[raw["USN"].astype(str)==s["usn"]]["RESULT"]
                     .astype(str).str.strip().str.upper().isin(["F","AB","ABS","FAIL"]).any())
        n_fcd  = sum(1 for s in student_totals if s["pct"] > 80)
        n_fail = n_students - n_pass

        return jsonify({
            "subjects": subjects,
            "top3": top3,
            "summary": {
                "total": n_students,
                "pass": n_pass,
                "fail": n_fail,
                "fcd": n_fcd,
                "pass_pct": round(n_pass/n_students*100,1) if n_students else 0
            }
        })
    except Exception as e:
        return jsonify({"error": str(e), "subjects": [], "top3": [], "summary": {}}), 500


@app.route("/api/captcha_preview")
def captcha_preview():
    path = os.path.join(BASE, "captcha.png")
    if os.path.exists(path):
        return send_file(path, mimetype="image/png")
    return "No captcha", 404


if __name__ == "__main__":
    print("\n" + "="*50)
    print("  VTU SCOREMATRIX DASHBOARD")
    print("  Open: http://127.0.0.1:5000")
    print("="*50 + "\n")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
