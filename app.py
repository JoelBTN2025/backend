import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from validador import validar_xml

app = Flask(__name__)
CORS(app)

# Ruta API para validación JSON
@app.route('/validar', methods=['POST'])
def validar():
    try:
        data = request.get_json()
        xml = data.get('xml')
        tipo = data.get('tipo')

        if not xml or not tipo:
            return jsonify({"valido": False, "error": "Falta el XML o el tipo de comprobante"}), 400

        # ✅ Llamada con corrección automática habilitada
        valido, mensaje, corrected_xml = validar_xml(xml, tipo, corregir=True)

        return jsonify({
            "valido": valido,
            "mensaje": mensaje if valido else None,
            "error": mensaje if not valido else None,
            "correctedXml": corrected_xml  # <-- Esto debe llamarse exactamente así
        })


    except Exception as e:
        return jsonify({
            "valido": False,
            "error": f"Error interno del servidor: {str(e)}"
        })

# Ruta web
@app.route("/", methods=["GET", "POST"])
def index():
    mensaje = None
    valido = None

    if request.method == "POST":
        archivo = request.files.get("archivo")

        if archivo and archivo.filename.endswith(".xml"):
            contenido = archivo.read().decode("utf-8")
            valido, mensaje, _ = validar_xml(contenido, tipo="guia", corregir=True)
        else:
            mensaje = "Por favor sube un archivo .xml válido."
            valido = False

    return render_template("index.html", mensaje=mensaje, valido=valido)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
