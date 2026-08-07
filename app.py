import streamlit as st
from basyx.aas import model

from Handler import load_aasx_package, save_aasx_package
from CRUD import extract_elements, add_new_property, update_property_value, delete_property_element

st.set_page_config(
    page_title="AAS & DPP Management Portal",
    page_icon="☕",
    layout="wide"
)

st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px 6px 0px 0px;
        padding: 10px 20px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)
if "object_store" not in st.session_state:
    st.session_state.object_store = None
if "file_store" not in st.session_state:
    st.session_state.file_store = None
if "logo_bytes" not in st.session_state:
    st.session_state.logo_bytes = None
st.sidebar.header("📁 AASX Package Manager")
uploaded_file = st.sidebar.file_uploader("Upload AASX File", type=["aasx"])

if uploaded_file is not None and st.sidebar.button("📂 Load Package", use_container_width=True):
    with st.spinner("Parsing Asset Administration Shell Container..."):
        obj_store, file_store, raw_logo = load_aasx_package(uploaded_file)
        st.session_state.object_store = obj_store
        st.session_state.file_store = file_store
        st.session_state.logo_bytes = raw_logo
        st.sidebar.success(f"Package Loaded! Found {len(obj_store)} Objects.")
if st.session_state.logo_bytes:
    st.sidebar.divider()
    st.sidebar.markdown("**Asset Brand / Logo**")
    st.sidebar.image(st.session_state.logo_bytes, use_column_width=True)
if st.session_state.object_store is not None:
    obj_store = st.session_state.object_store
    aas_shells = [obj for obj in obj_store if isinstance(obj, model.AssetAdministrationShell)]
    submodels = [obj for obj in obj_store if isinstance(obj, model.Submodel)]

    col_head1, col_head2 = st.columns([1, 5])
    with col_head1:
        if st.session_state.logo_bytes:
            st.image(st.session_state.logo_bytes, width=130)
        else:
            st.title("☕")

    with col_head2:
        st.title("Asset Administration Shell & DPP")
        st.caption("Digital Product Passport Dashboard")

    # Metrics Row
    m1, m2, m3 = st.columns(3)
    with m1:
        aas_name = aas_shells[0].id_short if aas_shells else "N/A"
        st.metric(label="Active AAS Shell", value=aas_name)
    with m2:
        st.metric(label="Loaded Submodels", value=len(submodels))
    with m3:
        total_props = sum(len(sm.submodel_element) for sm in submodels)
        st.metric(label="Total Submodel Elements", value=total_props)

    st.divider()


    tab_view, tab_edit, tab_manage, tab_export = st.tabs([
        "👁️ View Submodels",
        "✏️ Edit Values",
        "⚙️ Manage Structure & Logo",
        "📥 Export Package"
    ])


    with tab_view:
        st.subheader("📊 Submodel Inspector")
        if submodels:
            sm_dict = {sm.id_short: sm for sm in submodels if sm.id_short}
            selected_sm_view = st.selectbox("Select Submodel to Inspect:", list(sm_dict.keys()), key="view_sm_select")

            if selected_sm_view:
                target_sm = sm_dict[selected_sm_view]
                elements = extract_elements(target_sm.submodel_element)

                st.markdown(f"**Submodel ID:** `{target_sm.id}`")
                st.markdown(f"**Total Elements:** `{len(elements)}`")

                table_data = []
                for key, info in elements.items():
                    table_data.append({
                        "Element Key / Path": key,
                        "Type": info["type"],
                        "Current Value": str(info["value"])
                    })

                st.dataframe(table_data, use_container_width=True, height=400)

    with tab_edit:
        st.subheader("✏️ Edit Property Values")
        if submodels:
            sm_dict = {sm.id_short: sm for sm in submodels if sm.id_short}
            c1, c2 = st.columns([1, 1])
            with c1:
                selected_sm_edit = st.selectbox("Select Submodel:", list(sm_dict.keys()), key="edit_sm_select")

            if selected_sm_edit:
                target_sm = sm_dict[selected_sm_edit]
                elements = extract_elements(target_sm.submodel_element)

                with c2:
                    search_query = st.text_input("🔍 Filter Elements:", placeholder="Search key or value...").lower()

                if search_query:
                    elements = {k: v for k, v in elements.items() if
                                search_query in k.lower() or search_query in str(v['value']).lower()}

                with st.form("edit_values_only_form"):
                    updated_inputs = {}
                    for key, info in elements.items():
                        col_k, col_v = st.columns([2, 3])
                        with col_k:
                            st.markdown(f"**{key}**")
                            st.caption(f"Type: `{info['type']}`")
                        with col_v:
                            val_str = str(info['value']) if info['value'] is not None else ""

                            if info['type'] == "File":
                                st.text_input(
                                    label=f"input_{key}",
                                    value=val_str,
                                    disabled=True,
                                    help="File paths are managed in Tab 3.",
                                    label_visibility="collapsed"
                                )
                            else:
                                updated_inputs[key] = st.text_input(
                                    label=f"input_{key}",
                                    value=val_str,
                                    label_visibility="collapsed"
                                )

                    st.divider()
                    if st.form_submit_button("💾 Save Value Modifications", use_container_width=True):
                        for key, new_val in updated_inputs.items():
                            if key in elements and elements[key]["type"] != "File":
                                update_property_value(elements[key]["obj"], new_val)
                        st.success("Property values updated successfully in memory!")
                        st.rerun()

    with tab_manage:
        if submodels:
            sm_dict = {sm.id_short: sm for sm in submodels if sm.id_short}

            # --- SUBMODEL PROPERTY STRUCTURE MANAGEMENT ---
            st.subheader("🛠️ Submodel Element Operations")
            selected_sm_manage = st.selectbox("Select Submodel to Modify Structure:", list(sm_dict.keys()),
                                              key="manage_sm_select")
            target_sm = sm_dict[selected_sm_manage]

            col_add, col_del = st.columns(2)

            with col_add:
                st.markdown("#### ➕ Add New Property")
                with st.form("add_property_standalone_form"):
                    new_id = st.text_input("Property idShort", placeholder="e.g. WaterCapacity")
                    new_val = st.text_input("Property Value", placeholder="e.g. 1.8 Liters")
                    new_type = st.selectbox("Value Type", ["string", "double", "integer", "boolean"])

                    if st.form_submit_button("➕ Add Property", use_container_width=True) and new_id:
                        add_new_property(target_sm, new_id, new_val, new_type)
                        st.success(f"Added `{new_id}` to `{selected_sm_manage}`!")
                        st.rerun()

            with col_del:
                st.markdown("#### 🗑️ Delete Existing Property")
                root_elements = [elem.id_short for elem in target_sm.submodel_element if hasattr(elem, 'id_short')]

                if root_elements:
                    prop_to_delete = st.selectbox("Select Property to Remove:", root_elements)
                    if st.button("🗑️ Confirm Delete Property", type="primary", use_container_width=True):
                        delete_property_element(target_sm, prop_to_delete)
                        st.success(f"Deleted `{prop_to_delete}` from `{selected_sm_manage}`!")
                        st.rerun()
                else:
                    st.info("No root properties available to delete in this submodel.")

            st.divider()

            st.subheader("🖼️ Upload New Company Logo Image")
            st.caption("Upload a new PNG or JPG file to replace the company logo inside the package container.")

            c_preview, c_upload = st.columns([1, 2])
            with c_preview:
                if st.session_state.logo_bytes:
                    st.markdown("**Current Company Logo:**")
                    st.image(st.session_state.logo_bytes, width=150)
                else:
                    st.info("No company logo currently present in package.")

            with c_upload:
                new_logo_file = st.file_uploader("Upload New Image (PNG / JPG):", type=["png", "jpg", "jpeg"],
                                                 key="logo_file_input")
                if new_logo_file is not None:
                    if st.button("🔄 Replace Company Logo Image", use_container_width=True):
                        st.session_state.logo_bytes = new_logo_file.getvalue()
                        st.success("Company logo updated in session memory!")
                        st.rerun()


    with tab_export:
        st.subheader("📥 Export Updated AASX Package")
        st.info(
            "Packs all modified submodels, updated properties, and the updated logo image into a downloadable `.aasx` package.")

        export_bytes = save_aasx_package(st.session_state.object_store, st.session_state.logo_bytes)
        st.download_button(
            label="Download Updated AASX Package",
            data=export_bytes,
            file_name="smart_coffee_machine_updated.aasx",
            mime="application/vnd.aasx+zip",
            use_container_width=True
        )

else:
    st.info("👈 Upload your `smart_coffee_machine.aasx` file from the sidebar to start.")