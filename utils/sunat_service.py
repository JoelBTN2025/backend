from zeep import Client
from zeep.transports import Transport
from requests import Session
import base64
import os

def enviar_a_sunat(xml_zip_bytes, ruc):
    """
    Envía el XML empaquetado a SUNAT en entorno de pruebas.
    """
    usuario_secundario = f"{ruc}MODDATOS"
    clave_secundaria = "MODDATOS"

    # Ruta al certificado PEM (ajústala según tu estructura)
    cert_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../certs/sunat_cert.pem'))

    # Configura la sesión segura con el certificado
    session = Session()
    session.cert = cert_path
    session.verify = False  # Desactiva verificación SSL solo para entorno beta

    # Crea el cliente Zeep con el WSDL de SUNAT
    client = Client(
        wsdl="https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService?wsdl",
        transport=Transport(session=session)
    )

    # Codifica el archivo ZIP en base64
    contenido_zip_b64 = base64.b64encode(xml_zip_bytes).decode("utf-8")
    nombre_zip = "documento_prueba.zip"

    # Intenta enviar el documento
    try:
        response = client.service.sendBill(
            nombre_zip,
            contenido_zip_b64,
            _soapheaders={
                'wsse:Security': {
                    'wsse:UsernameToken': {
                        'wsse:Username': usuario_secundario,
                        'wsse:Password': clave_secundaria
                    }
                }
            }
        )

        return {
            "exito": True,
            "mensaje": "✅ Enviado correctamente a SUNAT (entorno pruebas)",
            "respuesta_sunat": str(response)
        }

    except Exception as e:
        return {
            "exito": False,
            "mensaje": "❌ Error al enviar a SUNAT",
            "error": str(e)
        }
