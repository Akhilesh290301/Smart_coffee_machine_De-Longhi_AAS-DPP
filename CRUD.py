from basyx.aas import model
from parser import sanitize_id_short


def extract_elements(submodel_elements, prefix=""):
    extracted = {}
    for elem in submodel_elements:
        key = f"{prefix}{elem.id_short}" if prefix else elem.id_short

        if isinstance(elem, model.Property):
            extracted[key] = {
                "type": "Property",
                "value": elem.value,
                "value_type": getattr(elem, "value_type", "string"),
                "obj": elem
            }
        elif isinstance(elem, model.MultiLanguageProperty):
            lang_val = ""
            if elem.value:
                try:
                    lang_val = list(elem.value.values())[0] if len(elem.value) > 0 else ""
                except Exception:
                    lang_val = str(elem.value)
            extracted[key] = {
                "type": "MultiLanguageProperty",
                "value": lang_val,
                "obj": elem
            }
        elif isinstance(elem, model.File):
            extracted[key] = {
                "type": "File",
                "value": elem.value,
                "obj": elem
            }
        elif isinstance(elem, model.SubmodelElementCollection) or hasattr(elem, 'value'):
            val = getattr(elem, 'value', None)
            if val is not None and hasattr(val, '__iter__') and not isinstance(val, (str, bytes, dict)):
                extracted.update(extract_elements(val, prefix=f"{key} ➔ "))

    return extracted


def add_new_property(submodel, id_short: str, value: str, value_type: str = "string"):
    type_map = {
        "string": model.datatypes.String,
        "double": model.datatypes.Double,
        "integer": model.datatypes.Integer,
        "boolean": model.datatypes.Boolean
    }
    clean_id = sanitize_id_short(id_short)
    new_prop = model.Property(
        id_short=clean_id,
        value_type=type_map.get(value_type, model.datatypes.String),
        value=value
    )
    submodel.submodel_element.add(new_prop)


def update_property_value(element_obj, new_value: str):
    if isinstance(element_obj, model.Property):
        element_obj.value = str(new_value)
    elif isinstance(element_obj, model.MultiLanguageProperty):
        element_obj.value = model.MultiLanguageTextType({"en": str(new_value)})


def delete_property_element(submodel, id_short: str):
    to_remove = [elem for elem in submodel.submodel_element if elem.id_short == id_short]
    for elem in to_remove:
        submodel.submodel_element.remove(elem)