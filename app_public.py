
import os
from flask import Flask, request, jsonify, send_file, render_template_string, abort
from flask_cors import CORS
import pandas as pd
import io
import threading

# --- Settings ---
MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "20"))
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "changeme")
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",")]

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_MB * 1024 * 1024  # limit upload size
CORS(app, resources={r"/*": {"origins": ALLOWED_ORIGINS if ALLOWED_ORIGINS != ["*"] else "*"}})

# Thread-safe in-memory dataframe
_lock = threading.Lock()
df = pd.DataFrame()

delegaciones_permitidas = [
    "AMAZONAS", "ANCASH - CHIMBOTE", "ANCASH - HUARAZ", "APURIMAC", "AREQUIPA", "AYACUCHO", "CAJAMARCA",
    "CUSCO - CUSCO", "CUSCO - MACHUPICCHU", "HUANUCO", "ICA - CHINCHA", "ICA - ICA", "JUNIN - CHANCHAMAYO",
    "JUNIN - HUANCAYO", "LA LIBERTAD", "LAMBAYEQUE", 
    "LIMA NORTE - PROVINCIA", "LORETO", "MADRE DE DIOS", "MOQUEGUA", "PIURA - PIURA", 
    "PIURA - TALARA", "PUNO", "SAN MARTIN", "TACNA", "TUMBES", "UCAYALI" 
]

def _ensure_data_loaded():
    global df
    with _lock:
        if df.empty:
            default_path = os.getenv("DEFAULT_DATA_PATH", "data/inventario.xlsx")
            if os.path.exists(default_path):
                try:
                    tmp = pd.read_excel(default_path, usecols=lambda x: 'Unnamed' not in x)
                    if 'Delegación' in tmp.columns:
                        tmp['Delegación'] = tmp['Delegación'].astype(str).str.strip()
                        tmp = tmp[tmp['Delegación'].isin(delegaciones_permitidas)]
                    df = tmp
                except Exception:
                    pass  # keep empty

@app.route('/delegaciones', methods=['GET'])
def get_delegaciones():
    _ensure_data_loaded()
    with _lock:
        if df.empty:
            return jsonify({"error": "No hay datos cargados aún."}), 400
        delegaciones = sorted([d for d in df['Delegación'].dropna().unique() if d in delegaciones_permitidas])
        return jsonify(delegaciones)

@app.route('/estado', methods=['GET'])
def get_estado():
    _ensure_data_loaded()
    delegacion = request.args.get('delegacion', '')
    with _lock:
        if df.empty:
            return jsonify({"error": "No hay datos cargados aún."}), 400
        filtered_df = df[df['Delegación'] == delegacion] if delegacion else df
        if 'Ubicación' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Ubicación'] != 'TRANSITO']
        pendientes = filtered_df[filtered_df['Estado'] == 'Pend. revisar'].shape[0] if 'Estado' in filtered_df.columns else 0
        operativo = filtered_df[filtered_df['Estado'] == 'Operativo'].shape[0] if 'Estado' in filtered_df.columns else 0
        nuevo = filtered_df[filtered_df['Estado'] == 'Nuevo'].shape[0] if 'Estado' in filtered_df.columns else 0
        return jsonify({'Pendiente de Revisar': pendientes, 'Operativo': operativo, 'Nuevo': nuevo})

@app.route('/ubicacion', methods=['GET'])
def get_ubicacion():
    _ensure_data_loaded()
    delegacion = request.args.get('delegacion', '')
    with _lock:
        if df.empty:
            return jsonify({"error": "No hay datos cargados aún."}), 400
        filtered_df = df[df['Delegación'] == delegacion] if delegacion else df
        if 'Ubicación' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Ubicación'] != 'TRANSITO']
            ubicaciones = filtered_df['Ubicación'].astype(str).str.upper().value_counts().to_dict()
        else:
            ubicaciones = {}
        return jsonify(ubicaciones)

@app.route('/destino', methods=['GET'])
def get_destino():
    _ensure_data_loaded()
    delegacion = request.args.get('delegacion', '')
    with _lock:
        if df.empty:
            return jsonify({"error": "No hay datos cargados aún."}), 400
        filtered_df = df[df['Delegación'] == delegacion] if delegacion else df
        destinos = filtered_df['Destino Expedición'].value_counts().to_dict() if 'Destino Expedición' in filtered_df.columns else {}
        return jsonify(destinos)

def _is_authorized(req):
    auth = req.headers.get("Authorization", "")
    if not ADMIN_TOKEN or ADMIN_TOKEN == "changeme":
        # allow if not set (demo), but set a real token in prod
        return True
    return auth == f"Bearer {ADMIN_TOKEN}"

@app.route('/subir', methods=['POST'])
def subir_archivo():
    if not _is_authorized(request):
        return abort(401)
    archivo = request.files.get('archivo')
    if not archivo:
        return jsonify({"error": "No se ha subido ningún archivo"}), 400
    try:
        new_df = pd.read_excel(archivo, usecols=lambda x: 'Unnamed' not in x)
        if 'Delegación' not in new_df.columns:
            return jsonify({"error": "El archivo no contiene la columna 'Delegación'."}), 400
        new_df['Delegación'] = new_df['Delegación'].astype(str).str.strip()
        new_df = new_df[new_df['Delegación'].isin(delegaciones_permitidas)]
        with _lock:
            global df
            df = new_df
        return jsonify({"mensaje": "Archivo cargado correctamente"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/descargar', methods=['GET'])
def descargar_datos():
    _ensure_data_loaded()
    delegacion = request.args.get('delegacion', '')
    with _lock:
        if df.empty:
            return jsonify({"error": "No hay datos cargados aún."}), 400
        filtered_df = df[df['Delegación'] == delegacion] if delegacion else df
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            filtered_df.to_excel(writer, index=False, sheet_name='Datos')
        output.seek(0)
    slug = (delegacion or "todas").replace(" ", "_").replace("/", "-")
    return send_file(output, as_attachment=True,
                    download_name=f"datos_inventario_{slug}.xlsx",
                    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

def _load_index():
    path = os.getenv("INDEX_PATH", "index.html")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "<!doctype html><html><body><h2>Servidor en línea</h2><p>Sube index.html</p></body></html>"

HTML = _load_index()

@app.route('/')
def index():
    return render_template_string(HTML)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")), debug=False)
