import io
import os
import tempfile
import zipfile
from basyx.aas import model
from basyx.aas.adapter import aasx
from parser import parse_aas_xml_fallback


def load_aasx_package(uploaded_file):
    object_store = model.DictObjectStore()
    file_store = aasx.DictSupplementaryFileContainer()

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".aasx")
    tmp.write(uploaded_file.getvalue())
    tmp.flush()
    tmp.close()

    try:
        with aasx.AASXReader(tmp.name) as reader:
            reader.read_into(object_store, file_store)
    except Exception:
        pass
    if len(object_store) <= 1:
        try:
            with zipfile.ZipFile(tmp.name, 'r') as z:
                for filename in z.namelist():
                    if filename.endswith('.xml'):
                        xml_bytes = z.read(filename)
                        parse_aas_xml_fallback(xml_bytes, object_store)
                    elif any(filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg']):
                        img_bytes = z.read(filename)
                        clean_path = "/" + filename.lstrip('/')
                        file_store.add_file(clean_path, io.BytesIO(img_bytes), "image/png")
        except Exception:
            pass

    if os.path.exists(tmp.name):
        os.remove(tmp.name)

    logo_bytes = extract_raw_logo_bytes(file_store)
    return object_store, file_store, logo_bytes


def extract_raw_logo_bytes(file_store):
    if not file_store:
        return None
    try:
        for file_path in list(file_store):
            if any(file_path.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg']):
                try:
                    stream = file_store.get_file(file_path)
                    if hasattr(stream, 'read'):
                        data = stream.read()
                        if hasattr(stream, 'seek'):
                            stream.seek(0)
                        return data
                    elif isinstance(stream, (bytes, bytearray)):
                        return bytes(stream)
                except Exception:
                    pass
    except Exception:
        pass
    return None


def sync_file_elements(elements, target_path):
    for elem in elements:
        if isinstance(elem, model.File):
            elem.value = target_path
            elem.content_type = "image/png"
        elif hasattr(elem, 'value'):
            val = getattr(elem, 'value', None)
            if val is not None and hasattr(val, '__iter__') and not isinstance(val, (str, bytes, dict)):
                sync_file_elements(val, target_path)


def save_aasx_package(object_store, logo_bytes):
    file_store = aasx.DictSupplementaryFileContainer()
    target_path = "/aasx/files/DeLonghi-Logo.png"

    if logo_bytes:
        file_store.add_file(target_path, io.BytesIO(logo_bytes), "image/png")

    aas_shells = [obj for obj in object_store if isinstance(obj, model.AssetAdministrationShell)]
    submodels = [obj for obj in object_store if isinstance(obj, model.Submodel)]

    for aas in aas_shells:
        existing_sm_ids = {ref.key[0].value for ref in aas.submodel if ref.key}
        for sm in submodels:
            if sm.id not in existing_sm_ids:
                aas.submodel.add(model.ModelReference.from_referable(sm))
    for sm in submodels:
        sync_file_elements(sm.submodel_element, target_path)

    aas_ids = [aas.id for aas in aas_shells]
    buffer = io.BytesIO()
    with aasx.AASXWriter(buffer) as writer:
        writer.write_aas(
            aas_ids=aas_ids,
            object_store=object_store,
            file_store=file_store
        )
    buffer.seek(0)
    return buffer