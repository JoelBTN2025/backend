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

def validar_xml(xml_string, tipo=None, corregir=False):
    try:
        # 1. Parsear XML con o sin recuperación
        try:
            xml_doc = etree.fromstring(xml_string.encode('utf-8'))
        except etree.XMLSyntaxError:
            if corregir:
                parser = etree.XMLParser(recover=True)
                xml_doc = etree.fromstring(xml_string.encode('utf-8'), parser)
                xml_string = etree.tostring(xml_doc, pretty_print=True, encoding='unicode')
            else:
                raise

        # 2. Detectar versión UBL (2.0, 2.1, etc.)
        version = extraer_version(xml_doc)
        if not version:
            return False, "No se pudo detectar la versión del XML (falta <cbc:UBLVersionID>)", None


        # 3. Obtener tag raíz sin namespace
        tag_completo = xml_doc.tag  # ej: '{urn:oasis:names:specification:ubl:schema:xsd:Invoice-2}Invoice'
        nombre_tag = tag_completo.split('}')[-1].strip()  # ej: 'Invoice'

        # 4. Armar nombre dinámico del archivo XSD
        archivo_xsd = f"UBL-{nombre_tag}-{version}.xsd"

        # 5. Ruta base a esquema
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.join(script_dir, "esquemas", version)
        xsd_path = os.path.join(base_path, "maindoc", archivo_xsd)

        # 6. Verificar que el archivo exista
        if not os.path.exists(xsd_path):
            return False, f"No se encontró el esquema XSD para {nombre_tag} versión {version}: {xsd_path}", None

        # 7. Preparar parser con resolvers para archivos locales
        parser = etree.XMLParser(load_dtd=True, no_network=False)

        class LocalResolver(etree.Resolver):
            def resolve(self, url, pubid, context):
                local_path = os.path.join(base_path, 'common', os.path.basename(url))
                return self.resolve_filename(local_path, context)

        parser.resolvers.add(LocalResolver())

        # 8. Cargar esquema
        with open(xsd_path, 'rb') as f:
            schema_doc = etree.parse(f, parser)
            schema = etree.XMLSchema(schema_doc)

        # 9. Validar el XML
        schema.assertValid(xml_doc)

        return True, "✅ XML válido y conforme al esquema XSD.", xml_string

    except etree.DocumentInvalid as e:
        errores = schema.error_log
        mensajes = [traducir_error_lxml(err.message, err.line) for err in errores]
        return False, "\n".join(mensajes), xml_string if corregir else None

    except Exception as e:
        return False, str(e), None
