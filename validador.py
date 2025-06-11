import os
import re
from lxml import etree

estructura_esperada = {
    'AttachedTransportEquipment': {
        'permitido_en': ['TransportEquipment'],
        'descripcion': 'Información sobre equipos de transporte asociados como contenedores, remolques, etc.'
    },
    'ShipmentDocumentReference': {
        'permitido_en': ['Shipment'],
        'descripcion': 'Referencia a documentos de envío relacionados.'
    },
    'ContainedInTransportEquipment': {
        'permitido_en': ['Shipment'],
        'descripcion': 'Relación del envío con un equipo de transporte.'
    },
    'Package': {
        'permitido_en': ['Shipment', 'GoodsItem'],
        'descripcion': 'Información de los paquetes enviados.'
    },
    'GoodsItem': {
        'permitido_en': ['Shipment'],
        'descripcion': 'Detalles de los bienes incluidos en el envío.'
    }
}

def traducir_error_lxml(err_msg, linea):
    mensaje = f"Línea {linea}: {err_msg}"

    if "Element" in err_msg and "is not expected" in err_msg and "Expected is one of" in err_msg:
        elemento_mal = re.search(r"Element '\{.*?\}(.*?)'", err_msg)
        elementos_esperados = re.search(r"Expected is one of\s*\((.*?)\)", err_msg)

        if elemento_mal:
            nombre_mal = elemento_mal.group(1)
            mensaje = f"❌ Línea {linea}: Usaste la etiqueta <{nombre_mal}> en una ubicación no válida."

            if elementos_esperados:
                opciones = elementos_esperados.group(1)
                opciones = [f"<{tag.split('}')[-1]}>" for tag in opciones.split(',')]
                sugerencia = ", ".join(opciones)
                mensaje += f" En su lugar, deberías usar una de las siguientes etiquetas: {sugerencia}."

            if nombre_mal in estructura_esperada:
                ubicacion = estructura_esperada[nombre_mal]['permitido_en']
                desc = estructura_esperada[nombre_mal]['descripcion']
                ubicacion_str = ', '.join([f"<{u}>" for u in ubicacion])
                mensaje += f" Esta etiqueta normalmente debe ir dentro de: {ubicacion_str}. {desc}"

    return mensaje

def extraer_version(xml_doc):
    ns = xml_doc.nsmap
    cbc_ns = ns.get('cbc')
    if cbc_ns:
        tag_version = f"{{{cbc_ns}}}UBLVersionID"
        elem_version = xml_doc.find(tag_version)
        if elem_version is not None:
            return elem_version.text.strip()
    return None

def validar_xml(xml_string, tipo, corregir=False):
    try:
        # Parsear el XML
        try:
            xml_doc = etree.fromstring(xml_string.encode('utf-8'))
        except etree.XMLSyntaxError:
            if corregir:
                parser = etree.XMLParser(recover=True)
                xml_doc = etree.fromstring(xml_string.encode('utf-8'), parser)
                xml_string = etree.tostring(xml_doc, pretty_print=True, encoding='unicode')
            else:
                raise

        # Extraer versión
        version = extraer_version(xml_doc)
        if not version:
            return False, "No se pudo detectar la versión del XML (falta <cbc:UBLVersionID>)", None

        # Para UBL 2.0, los archivos XSD usan 1.0 en su nombre
        xsd_version = "1.0" if version == "2.0" else version

        # Ruta base de los esquemas
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.join(script_dir, "esquemas", version)

        # Determinar tipo
        root_tag = xml_doc.tag.lower()
        if 'invoice' in root_tag:
            archivo_xsd = f"UBL-Invoice-{xsd_version}.xsd"
        elif 'creditnote' in root_tag:
            archivo_xsd = f"UBL-CreditNote-{xsd_version}.xsd"
        elif 'debitnote' in root_tag:
            archivo_xsd = f"UBL-DebitNote-{xsd_version}.xsd"
        elif 'despatchadvice' in root_tag:
            archivo_xsd = f"UBL-DespatchAdvice-{xsd_version}.xsd"
        else:
            return False, f"No se pudo identificar el tipo de comprobante a partir del tag raíz: {root_tag}", None

        xsd_path = os.path.join(base_path, "maindoc", archivo_xsd)

        if not os.path.exists(xsd_path):
            return False, f"No se encontró el esquema XSD para {root_tag} versión {version}: {xsd_path}", None

        parser = etree.XMLParser(load_dtd=True, no_network=False)

        class LocalResolver(etree.Resolver):
            def resolve(self, url, pubid, context):
                local_path = os.path.join(base_path, 'common', os.path.basename(url))
                return self.resolve_filename(local_path, context)

        parser.resolvers.add(LocalResolver())

        with open(xsd_path, 'rb') as f:
            schema_doc = etree.parse(f, parser)
            schema = etree.XMLSchema(schema_doc)

        schema.assertValid(xml_doc)

        return True, "✅ XML válido y conforme al esquema XSD.", xml_string

    except etree.DocumentInvalid as e:
        errores = schema.error_log
        mensajes = [traducir_error_lxml(err.message, err.line) for err in errores]
        return False, "\n".join(mensajes), xml_string if corregir else None

    except Exception as e:
        return False, str(e), None
