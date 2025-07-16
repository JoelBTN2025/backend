# envio_sunat.py
import os
from zeep import Client, Settings
from zeep.transports import Transport
from requests import Session
from lxml import etree
import base64

# Opcional: firmador separado
from utils.firmador import firmar_xml

# Datos SUNAT prueba
ENDPOINTS = {
    "sunat": {
        "wsdl": "https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService?wsdl",
        "usuario": "YOUR_RUC+MODDATOS",   # Ej: 20123456789MODDATOS
        "password": "MODDATOS"
    },
    "ose": {
        "wsdl": "https://your-ose.com/endpoint.wsdl",  # Reemplaza por el WSDL real de OSE
        "usuario": "ose_usuario",
        "password": "ose_clave"
    }
}

# Ruta de certificado y clave privada (ya convertidos a .pem)
CERT_PATH = os.path.join(os.path.dirname(__file__), "certs", "sunat_cert.pem")


def enviar_comprobante(xml_string, tipo, firmar, destino):
    try:
        # Si el usuario marca "firmar", firmamos el XML
        if firmar:
            xml_firmado = firmar_xml(xml_string, CERT_PATH)
        else:
            xml_firmado = xml_string

        # Codificar XML en base64 para enviarlo
        xml_bytes = xml_firmado.encode('utf-8')
        zip_content = base64.b64encode(xml_bytes).decode()

        # Obtener datos del destino
        config = ENDPOINTS.get(destino)
        if not config:
            return {"exito": False, "error": "Destino no reconocido"}

        # Crear cliente SOAP con zeep
        session = Session()
        transport = Transport(session=session)
        settings = Settings(strict=False, xml_huge_tree=True)
        client = Client(wsdl=config['wsdl'], transport=transport, settings=settings)

        # Obtener nombre del archivo XML (obligatorio para SUNAT)
        nombre_archivo = "demo_factura.xml"  # ← Esto deberías extraerlo del XML si deseas

        # Llamada al método sendBill de SUNAT
        respuesta = client.service.sendBill(
            fileName=nombre_archivo,
            contentFile=zip_content,
            username=config['usuario'],
            password=config['password']
        )

        # Decodificar respuesta si devuelve CDR (como sunat)
        if hasattr(respuesta, 'applicationResponse'):
            cdr_bytes = base64.b64decode(respuesta.applicationResponse)
            cdr_xml = etree.tostring(etree.fromstring(cdr_bytes), pretty_print=True).decode()
            return {
                "exito": True,
                "mensaje": "Documento enviado correctamente.",
                "cdr": cdr_xml
            }

        return {
            "exito": True,
            "mensaje": "Documento enviado correctamente (sin CDR).",
            "cdr": None
        }

    except Exception as e:
        return {"exito": False, "error": str(e)}
