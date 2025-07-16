import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from validador import validar_xml
from utils.sunat_service import enviar_a_sunat  #Importamos el nuevo módulo

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

#Validación estructural XML
@app.route('/validar', methods=['POST'])
def validar():
    try:
        data = request.get_json()
        xml = data.get('xml')
        tipo = data.get('tipo')

        if not xml or not tipo:
            return jsonify({"valido": False, "error": "Falta el XML o el tipo de comprobante"}), 400

        valido, mensaje, corrected_xml = validar_xml(xml, tipo, corregir=True)

        return jsonify({
            "valido": valido,
            "mensaje": mensaje if valido else None,
            "error": mensaje if not valido else None,
            "correctedXml": corrected_xml
        })

    except Exception as e:
        return jsonify({
            "valido": False,
            "error": f"Error interno del servidor: {str(e)}"
        })

#Nueva ruta para enviar ZIP firmado a SUNAT (modo pruebas)
@app.route('/enviar-sunat', methods=['POST'])
def enviar_sunat():
    try:
        data = request.get_json()
        ruc = data.get('ruc')
        zip_base64 = data.get('zip_base64')

        if not ruc or not zip_base64:
            return jsonify({"exito": False, "mensaje": "Falta RUC o ZIP codificado en base64"}), 400

        import base64
        zip_bytes = base64.b64decode(zip_base64)

        resultado = enviar_a_sunat(zip_bytes, ruc)
        return jsonify(resultado)

    except Exception as e:
        return jsonify({"exito": False, "mensaje": f"Error interno: {str(e)}"}), 500

# Vista web
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

from envio_sunat import enviar_comprobante

@app.route('/enviar', methods=['POST'])
def enviar():
    try:
        data = request.get_json()
        xml = data.get('xml')
        tipo = data.get('tipo')
        firmar = data.get('firmar', False)
        destino = data.get('destino')  # 'sunat' o 'ose'

        if not xml or not tipo or not destino:
            return jsonify({"exito": False, "error": "Faltan datos requeridos"}), 400

        resultado = enviar_comprobante(xml, tipo, firmar, destino)

        return jsonify(resultado)

    except Exception as e:
        return jsonify({
            "exito": False,
            "error": f"Error interno al enviar: {str(e)}"
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
