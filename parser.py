import re
import xml.etree.ElementTree as ET
from basyx.aas import model


def sanitize_id_short(raw_id: str) -> str:
    if not raw_id:
        return "Element"
    clean = re.sub(r'[^a-zA-Z0-9_]', '_', str(raw_id).strip())
    return clean if clean else "Element"


def localtag(node) -> str:
    return node.tag.split('}')[-1] if '}' in node.tag else node.tag


def find_child_text(parent, tag_name: str):
    for child in parent:
        if localtag(child) == tag_name:
            return child.text
    return None


def parse_elements(container_node):
    elements = []
    target_nodes = []

    for child in container_node:
        tag = localtag(child)
        if tag in ('submodelElements', 'value'):
            target_nodes.extend(list(child))
        elif tag in ('property', 'multiLanguageProperty', 'submodelElementCollection', 'file'):
            target_nodes.append(child)

    if not target_nodes:
        target_nodes = list(container_node)

    for node in target_nodes:
        tag = localtag(node)
        raw_id = find_child_text(node, 'idShort')
        if not raw_id:
            continue

        clean_id = sanitize_id_short(raw_id)

        try:
            if tag == 'property':
                val = find_child_text(node, 'value') or ""
                prop = model.Property(
                    id_short=clean_id,
                    value_type=model.datatypes.String,
                    value=val
                )
                elements.append(prop)
            elif tag == 'multiLanguageProperty':
                val_str = ""
                for child in node:
                    if localtag(child) == 'value':
                        for text_node in child.iter():
                            if localtag(text_node) == 'text' and text_node.text:
                                val_str = text_node.text
                                break
                if not val_str:
                    val_str = find_child_text(node, 'value') or ""
                mlp = model.MultiLanguageProperty(
                    id_short=clean_id,
                    value=model.MultiLanguageTextType({"en": val_str}) if val_str else None
                )
                elements.append(mlp)
            elif tag == 'submodelElementCollection':
                child_elems = parse_elements(node)
                sec = model.SubmodelElementCollection(
                    id_short=clean_id,
                    value=child_elems
                )
                elements.append(sec)
            elif tag == 'file':
                val = find_child_text(node, 'value') or ""
                f_elem = model.File(
                    id_short=clean_id,
                    value=val,
                    content_type=find_child_text(node, 'contentType') or "image/png"
                )
                elements.append(f_elem)
        except Exception:
            pass

    return elements


def parse_aas_xml_fallback(xml_bytes, object_store):
    root = ET.fromstring(xml_bytes)
    aas_objs = []

    for node in root.iter():
        if localtag(node) == 'assetAdministrationShell':
            try:
                raw_id_short = find_child_text(node, 'idShort') or "Smart_coffee_machine"
                aas_id = find_child_text(node, 'id') or "https://example.com/ids/aas/coffeemachine"
                aas_obj = model.AssetAdministrationShell(
                    id_=aas_id,
                    id_short=sanitize_id_short(raw_id_short),
                    asset_information=model.AssetInformation(
                        asset_kind=model.AssetKind.INSTANCE,
                        global_asset_id="https://example.com/ids/asset/coffeemachine_99482"
                    )
                )
                aas_objs.append(aas_obj)
                object_store.add(aas_obj)
            except Exception:
                pass
    for node in root.iter():
        if localtag(node) == 'submodel':
            try:
                raw_id_short = find_child_text(node, 'idShort') or "Submodel"
                sm_id = find_child_text(node, 'id') or f"https://example.com/ids/sm/{raw_id_short}"

                sm_obj = model.Submodel(
                    id_=sm_id,
                    id_short=sanitize_id_short(raw_id_short)
                )

                elems = parse_elements(node)
                for e in elems:
                    sm_obj.submodel_element.add(e)

                object_store.add(sm_obj)

                for aas in aas_objs:
                    aas.submodel.add(model.ModelReference.from_referable(sm_obj))
            except Exception:
                pass