import requests
import streamlit as st
from html import escape
from pathlib import Path

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Property Research",
    page_icon="🏠",
    layout="wide",
)

style_path = Path(__file__).with_name("styles.css")
st.html(style_path)

# ---------- Shared helpers ----------

def money(value):
    return "Unknown" if value is None else f"${value:,.2f}"


def number_default(value):
    return 0.0 if value is None else float(value)


def api_request(method, path, payload=None, timeout=30):
    response = requests.request(
        method,
        f"{API_URL}{path}",
        json=payload,
        timeout=timeout,
    )

    if not response.ok:
        st.error(f"Request failed ({response.status_code}).")
        try:
            st.json(response.json())
        except ValueError:
            st.text(response.text)
        return None

    return response.json()


def show_cost_result(result):
    if result["complete"]:
        left, right = st.columns(2)

        left.metric(
            "Monthly housing estimate",
            money(result["monthly_housing_cost"]),
        )
        right.metric(
            "Including maintenance reserve",
            money(result["monthly_cost_with_reserve"]),
        )
    else:
        missing = ", ".join(
            name.replace("_", " ")
            for name in result["missing_inputs"]
        )
        st.warning(f"Incomplete estimate. Missing: {missing}.")

        st.metric(
            "Known monthly subtotal",
            money(result["known_monthly_subtotal"]),
        )
        st.caption("Excludes unknown costs and maintenance reserve.")

    labels = {
        "principal_and_interest": "Principal and interest",
        "property_tax": "Property tax",
        "homeowners_insurance": "Homeowners insurance",
        "hoa": "HOA",
        "mortgage_insurance": "Mortgage insurance",
    }

    st.table(
        {
            "Monthly component": [
                labels[name]
                for name in result["monthly_components"]
            ],
            "Amount": [
                money(value)
                for value in result["monthly_components"].values()
            ],
        }
    )

    st.caption(
        "Separate monthly maintenance reserve: "
        f"{money(result['monthly_maintenance_reserve'])}"
    )


def comparison_values(item):
    inputs = item["inputs"]
    result = item["calculation"]
    parts = result["monthly_components"]

    return {
        "Status": (
            "Complete for stated assumptions"
            if result["complete"]
            else "Incomplete"
        ),
        "Purchase price": money(inputs["purchase_price"]),
        "Down payment": money(inputs["down_payment"]),
        "Loan amount": money(result["loan_amount"]),
        "Annual interest rate": (
            f"{inputs['annual_interest_rate_percent']:g}%"
        ),
        "Loan term": f"{inputs['loan_term_years']} years",
        "Monthly principal and interest": money(
            parts["principal_and_interest"]
        ),
        "Monthly property tax": money(parts["property_tax"]),
        "Monthly homeowners insurance": money(
            parts["homeowners_insurance"]
        ),
        "Monthly HOA": money(parts["hoa"]),
        "Monthly mortgage insurance": money(
            parts["mortgage_insurance"]
        ),
        "Known subtotal excluding reserve": money(
            result["known_monthly_subtotal"]
        ),
        "Monthly housing cost": money(
            result["monthly_housing_cost"]
        ),
        "Separate monthly maintenance reserve": money(
            result["monthly_maintenance_reserve"]
        ),
        "Monthly cost including reserve": money(
            result["monthly_cost_with_reserve"]
        ),
        "Missing inputs": (
            ", ".join(
                name.replace("_", " ")
                for name in result["missing_inputs"]
            )
            or "None"
        ),
    }


# ---------- Load database-backed property records ----------

try:
    property_data = api_request("GET", "/properties", timeout=15)
except requests.RequestException as error:
    st.error(f"Could not reach the API: {error}")
    st.stop()

if property_data is None:
    st.stop()

properties = {
    item["property_id"]: item
    for item in property_data["properties"]
}

if not properties:
    st.info("No property records found. Run the property seed script.")
    st.stop()


# ---------- Sidebar ----------

with st.sidebar:
    st.title("Property Research")
    st.caption("Evidence and ownership costs")

    options = ["All documents", *properties.keys()]

    def property_label(value):
        if value == "All documents":
            return value

        record = properties[value]
        return f"{record['address']} · {value}"

    property_choice = st.selectbox(
        "Active property",
        options,
        index=1,
        format_func=property_label,
        key="modern_workspace_property",
    )

    property_id = (
        None if property_choice == "All documents"
        else property_choice
    )

    if property_id is not None:
        record = properties[property_id]

        st.write(f"**{record['address']}**")
        st.caption(f"{record['city']}, {record['state']}")

        if record["is_synthetic"]:
            st.info("Fictional sample property")

    st.divider()
    st.caption(
        "Research and cost inputs come from your local database. "
        "Review source dates and scenario assumptions."
    )

    with st.expander("Developer tools"):
        st.caption(
            "Indexes supported files already placed in data/raw/. "
            "Property upload and automatic linking are not available yet."
        )

        if st.button("Run bulk ingestion"):
            try:
                with st.spinner("Processing documents..."):
                    ingestion = api_request(
                        "POST",
                        "/ingest",
                        {},
                        timeout=120,
                    )

                if ingestion is not None:
                    st.success("Ingestion completed.")
                    st.json(ingestion)

            except requests.RequestException as error:
                st.error(f"Ingestion failed: {error}")


# ---------- Property summary ----------

if property_id is None:
    st.html(
        """
        <section class="workspace-hero">
            <div class="workspace-eyebrow">Property intelligence</div>
            <h1 class="workspace-title">Make your next move informed.</h1>
            <div class="workspace-subtitle">
                Research property documents, uncover missing information,
                and compare ownership costs in one workspace.
            </div>
            <div class="workspace-badge">
                Local development workspace
            </div>
        </section>
        """
    )
else:
    record = properties[property_id]

    address = escape(record["address"])
    location = escape(
        f"{record['city']}, {record['state']} · {property_id}"
    )
    badge = (
        "Fictional sample property"
        if record["is_synthetic"]
        else "Review source dates and assumptions"
    )

    st.html(
        f"""
        <section class="workspace-hero">
            <div class="workspace-eyebrow">Property workspace</div>
            <h1 class="workspace-title">{address}</h1>
            <div class="workspace-subtitle">{location}</div>
            <div class="workspace-badge">{badge}</div>
        </section>
        """
    )

    price_col, hoa_col, insurance_col = st.columns(3)

    price_col.metric(
        "Asking price",
        money(record["asking_price"]),
    )
    hoa_col.metric(
        "Monthly HOA",
        money(record["monthly_hoa"]),
    )
    insurance_col.metric(
        "Annual insurance input",
        money(record["annual_insurance"]),
    )

    with st.expander("Property data sources"):
        st.write(record["source_notes"])

research_tab, costs_tab, compare_tab = st.tabs(
    ["Research", "Cost Calculator", "Compare Properties"]
)



# ---------- Research ----------

with research_tab:
    if property_id is not None:
        with st.expander("Add a property document"):
            st.caption(
                f"Upload a PDF or UTF-8 TXT file for {property_id}. "
                "Maximum size: 10 MiB. Scanned PDFs require OCR "
                "and are not supported yet."
            )

            with st.form(f"upload_form_{property_id}"):
                uploaded_file = st.file_uploader(
                    "Choose a document",
                    type=["pdf", "txt"],
                    key=f"upload_file_{property_id}",
                )

                upload_clicked = st.form_submit_button(
                    "Upload and index"
                )

            if upload_clicked:
                if uploaded_file is None:
                    st.warning("Choose a file first.")

                elif uploaded_file.size > 10 * 1024 * 1024:
                    st.error("The upload limit is 10 MiB.")

                else:
                    try:
                        with st.spinner(
                            "Reading, indexing, and linking the document..."
                        ):
                            response = requests.post(
                                (
                                    f"{API_URL}/properties/"
                                    f"{property_id}/documents"
                                ),
                                files={
                                    "file": (
                                        uploaded_file.name,
                                        uploaded_file.getvalue(),
                                        uploaded_file.type
                                        or "application/octet-stream",
                                    )
                                },
                                timeout=180,
                            )

                        if response.ok:
                            upload_result = response.json()

                            if upload_result["status"] == "already_indexed":
                                st.info(
                                    "This file is already indexed "
                                    "for the selected property."
                                )
                            else:
                                st.success(
                                    "Document indexed and linked "
                                    f"to {property_id}. "
                                    f"{upload_result['chunks_inserted']} "
                                    "searchable chunks created."
                                )

                            # Existing answers predate this upload.
                            st.session_state.pop(
                                f"research_result_{property_id}",
                                None,
                            )

                            st.caption(
                                "Ask a new question below to search "
                                "the updated evidence."
                            )

                            with st.expander("Document reference"):
                                st.code(upload_result["document_name"])

                        else:
                            st.error(
                                f"Upload rejected ({response.status_code})."
                            )
                            try:
                                st.json(response.json())
                            except ValueError:
                                st.text(response.text)

                    except requests.Timeout:
                        st.warning(
                            "The upload request timed out. Processing "
                            "may still finish on the server. Retrying "
                            "the same file will check for duplicates."
                        )

                    except requests.RequestException as error:
                        st.error(f"Upload request failed: {error}")

    else:
        st.info(
            "Select a property in the sidebar to upload a document."
        )

    st.subheader("Ask about the evidence")
    st.caption(
        "Search scope: "
        + (
            "all indexed documents."
            if property_id is None
            else f"documents linked to {property_id}."
        )
    )

    research_key = f"research_result_{property_id or 'all'}"

    with st.form(f"research_form_{property_id or 'all'}"):
        question = st.text_input(
            "Your question",
            placeholder=(
                "What findings, fee changes, or missing records "
                "should I review?"
            ),
        )
        ask_clicked = st.form_submit_button("Research documents")

    if ask_clicked:
        if not question.strip():
            st.warning("Enter a question first.")
        else:
            # Remove an older answer before a new request.
            st.session_state.pop(research_key, None)

            try:
                with st.spinner("Reviewing document evidence..."):
                    answer = api_request(
                        "POST",
                        "/ask",
                        {
                            "question": question.strip(),
                            "property_id": property_id,
                        },
                        timeout=180,
                    )

                if answer is not None:
                    st.session_state[research_key] = answer

            except requests.RequestException as error:
                st.error(f"Research request failed: {error}")

    saved_answer = st.session_state.get(research_key)

    if saved_answer is not None:
        st.divider()
        st.caption(f"Question: {saved_answer['question']}")
        st.markdown(saved_answer["answer"])

        st.subheader("Supporting sources")

        if not saved_answer["sources"]:
            st.info("No supporting sources were returned.")

        for index, source in enumerate(saved_answer["sources"], 1):
            page = source.get("page_number")
            page_label = "N/A" if page is None else page

            label = (
                f"{index}. {source['document_name']} "
                f"— page {page_label}"
            )

            with st.expander(label):
                st.write(source["preview"])

                with st.expander("Technical details"):
                    st.json(
                        {
                            "chunk_id": source["chunk_id"],
                            "hybrid_score": source["hybrid_score"],
                            "vector_distance": source["vector_distance"],
                            "keyword_score": source["keyword_score"],
                        }
                    )

        st.caption(
            "Review supporting passages before relying on a finding. "
            "Generated claims and citations are not automatically verified."
        )


# ---------- Cost calculator ----------

with costs_tab:
    st.subheader("Build an ownership cost scenario")

    if property_id is None:
        st.info("Choose a property in the sidebar to calculate its costs.")
    else:
        record = properties[property_id]
        prefix = f"clean_cost_{property_id}"
        result_key = f"{prefix}_result"

        st.caption(
            "Database values provide defaults. Editing this form does "
            "not update the property record. Loan assumptions are editable."
        )

        with st.form(f"{prefix}_form"):
            left, right = st.columns(2)

            with left:
                st.markdown("#### Purchase and financing")

                price = st.number_input(
                    "Purchase price ($)",
                    min_value=1.0,
                    value=float(record["asking_price"]),
                    key=f"{prefix}_price",
                )
                down = st.number_input(
                    "Down payment ($)",
                    min_value=0.0,
                    value=float(record["asking_price"]) * 0.20,
                    key=f"{prefix}_down",
                )
                st.caption(
                    "Defaults to 20% of the recorded price. "
                    "Changing price does not change this amount."
                )

                rate = st.number_input(
                    "Assumed annual interest rate (%)",
                    min_value=0.0,
                    value=6.0,
                    step=0.1,
                    key=f"{prefix}_rate",
                )
                term = st.number_input(
                    "Loan term (years)",
                    min_value=1,
                    value=30,
                    step=1,
                    key=f"{prefix}_term",
                )

                mi_known = st.checkbox(
                    "Use known or explicitly assumed mortgage insurance",
                    value=False,
                    key=f"{prefix}_mi_known",
                )
                monthly_mi = st.number_input(
                    "Monthly mortgage insurance ($)",
                    min_value=0.0,
                    value=0.0,
                    key=f"{prefix}_mi",
                )

            with right:
                st.markdown("#### Recurring costs")

                tax_known = st.checkbox(
                    "Use supplied or assumed property taxes",
                    value=record["annual_property_tax"] is not None,
                    key=f"{prefix}_tax_known",
                )
                annual_tax = st.number_input(
                    "Annual property taxes ($)",
                    min_value=0.0,
                    value=number_default(record["annual_property_tax"]),
                    key=f"{prefix}_tax",
                )

                insurance_known = st.checkbox(
                    "Use supplied or assumed homeowners insurance",
                    value=record["annual_insurance"] is not None,
                    key=f"{prefix}_insurance_known",
                )
                annual_insurance = st.number_input(
                    "Annual homeowners insurance ($)",
                    min_value=0.0,
                    value=number_default(record["annual_insurance"]),
                    key=f"{prefix}_insurance",
                )

                hoa_known = st.checkbox(
                    "Use supplied or assumed HOA fee",
                    value=record["monthly_hoa"] is not None,
                    key=f"{prefix}_hoa_known",
                )
                monthly_hoa = st.number_input(
                    "Monthly HOA fee ($)",
                    min_value=0.0,
                    value=number_default(record["monthly_hoa"]),
                    key=f"{prefix}_hoa",
                )

                reserve = st.number_input(
                    "Optional monthly maintenance reserve ($)",
                    min_value=0.0,
                    value=200.0,
                    key=f"{prefix}_reserve",
                )

            st.caption(
                "Unchecked costs remain unknown. Zero is included only "
                "when explicitly selected. Form changes take effect "
                "when you calculate. Utilities, closing costs, and "
                "one-time repairs are excluded."
            )

            calculate_clicked = st.form_submit_button(
                "Calculate ownership cost"
            )

        if calculate_clicked:
            st.session_state.pop(result_key, None)

            payload = {
                "purchase_price": price,
                "down_payment": down,
                "annual_interest_rate_percent": rate,
                "loan_term_years": int(term),
                "annual_property_tax": (
                    annual_tax if tax_known else None
                ),
                "annual_insurance": (
                    annual_insurance if insurance_known else None
                ),
                "monthly_hoa": monthly_hoa if hoa_known else None,
                "monthly_mortgage_insurance": (
                    monthly_mi if mi_known else None
                ),
                "monthly_maintenance_reserve": reserve,
            }

            try:
                result = api_request(
                    "POST",
                    "/cost-scenarios",
                    payload,
                )

                if result is not None:
                    st.session_state[result_key] = {
                        "inputs": payload,
                        "calculation": result,
                    }

            except requests.RequestException as error:
                st.error(f"Calculator request failed: {error}")

        saved_cost = st.session_state.get(result_key)

        if saved_cost is not None:
            st.divider()
            st.subheader("Last calculated scenario")
            st.caption(
                "Results reflect the last submitted inputs. "
                "Recalculate after editing the form."
            )

            show_cost_result(saved_cost["calculation"])

            with st.expander("Submitted scenario assumptions"):
                st.json(saved_cost["inputs"])


# ---------- Property comparison ----------

with compare_tab:
    st.subheader("Compare ownership cost scenarios")
    st.caption(
        "Uses database property values and the shared assumptions below. "
        "Edits in the single-property calculator are not included."
    )

    available_ids = list(properties)
    default_ids = [
        item for item in ("SYN-001", "SYN-003")
        if item in properties
    ]

    if len(default_ids) < 2:
        default_ids = available_ids[:2]

    comparison_ids = st.multiselect(
        "Choose two or three properties",
        options=available_ids,
        default=default_ids,
        format_func=property_label,
        max_selections=3,
        key="clean_comparison_ids",
    )

    with st.form("clean_comparison_form"):
        left, right = st.columns(2)

        with left:
            comparison_rate = st.number_input(
                "Shared annual interest rate (%)",
                min_value=0.0,
                value=6.0,
                step=0.1,
            )
            comparison_term = st.number_input(
                "Shared loan term (years)",
                min_value=1,
                value=30,
                step=1,
            )

        with right:
            down_percent = st.number_input(
                "Down payment for each property (%)",
                min_value=0.0,
                max_value=100.0,
                value=20.0,
            )
            comparison_reserve = st.number_input(
                "Monthly maintenance reserve per property ($)",
                min_value=0.0,
                value=200.0,
            )

        assume_zero_mi = st.checkbox(
            "Explicitly assume $0 mortgage insurance for every property",
            value=False,
        )
        st.caption(
            "Otherwise mortgage insurance remains unknown. "
            "Missing database costs stay unknown. The app does not "
            "determine mortgage insurance requirements."
        )

        compare_clicked = st.form_submit_button("Compare costs")

    comparison_key = "clean_comparison_result"

    if compare_clicked:
        st.session_state.pop(comparison_key, None)

        if len(comparison_ids) < 2:
            st.warning("Select at least two properties.")
        else:
            scenarios = []

            for selected_id in comparison_ids:
                record = properties[selected_id]

                scenarios.append(
                    {
                        "property_id": selected_id,
                        "purchase_price": record["asking_price"],
                        "down_payment": (
                            record["asking_price"] * down_percent / 100
                        ),
                        "annual_interest_rate_percent": comparison_rate,
                        "loan_term_years": int(comparison_term),
                        "annual_property_tax": record["annual_property_tax"],
                        "annual_insurance": record["annual_insurance"],
                        "monthly_hoa": record["monthly_hoa"],
                        "monthly_mortgage_insurance": (
                            0.0 if assume_zero_mi else None
                        ),
                        "monthly_maintenance_reserve": comparison_reserve,
                    }
                )

            try:
                comparison = api_request(
                    "POST",
                    "/comparisons",
                    {"properties": scenarios},
                )

                if comparison is not None:
                    st.session_state[comparison_key] = comparison

            except requests.RequestException as error:
                st.error(f"Comparison request failed: {error}")

    saved_comparison = st.session_state.get(comparison_key)

    if saved_comparison is not None:
        saved_ids = [
            item["property_id"]
            for item in saved_comparison["properties"]
        ]

        if saved_ids != comparison_ids:
            st.info(
                "Property selection changed. Click Compare costs "
                "to generate a new comparison."
            )
        else:
            st.divider()
            st.subheader("Last calculated comparison")
            st.caption(
                "Reflects the last submitted assumptions, not "
                "unsubmitted form edits or later database changes."
            )

            values = {
                item["property_id"]: comparison_values(item)
                for item in saved_comparison["properties"]
            }

            measures = list(next(iter(values.values())))
            table = {"Measure": measures}

            for selected_id, property_values in values.items():
                table[selected_id] = [
                    property_values[measure]
                    for measure in measures
                ]

            st.table(table)

            if any(
                not item["calculation"]["complete"]
                for item in saved_comparison["properties"]
            ):
                st.warning(
                    "Some costs are unknown. Do not compare incomplete "
                    "subtotals against complete totals."
                )

            for note in saved_comparison.get("notes", []):
                st.caption(note)