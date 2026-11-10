import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Real Estate RAG Assistant",
    layout="wide",
)


def money(value):
    return "Unknown" if value is None else f"${value:,.2f}"


def number_default(value):
    return 0.0 if value is None else float(value)


def post_json(endpoint, payload, timeout=30):
    response = requests.post(
        f"{API_URL}{endpoint}",
        json=payload,
        timeout=timeout,
    )

    if not response.ok:
        st.error(f"Request rejected ({response.status_code}).")
        try:
            st.json(response.json())
        except ValueError:
            st.text(response.text)
        return None

    return response.json()


def show_calculation(result):
    labels = {
        "principal_and_interest": "Principal and interest",
        "property_tax": "Property tax",
        "homeowners_insurance": "Homeowners insurance",
        "hoa": "HOA",
        "mortgage_insurance": "Mortgage insurance",
    }

    for name, amount in result["monthly_components"].items():
        st.write(f"**{labels.get(name, name)}:** {money(amount)}")

    st.write(
        "**Separate maintenance reserve:** "
        f"{money(result['monthly_maintenance_reserve'])}"
    )

    if result["complete"]:
        st.metric(
            "Estimated monthly housing cost",
            money(result["monthly_housing_cost"]),
        )
        st.metric(
            "Estimated monthly cost including reserve",
            money(result["monthly_cost_with_reserve"]),
        )
    else:
        missing = ", ".join(
            name.replace("_", " ")
            for name in result["missing_inputs"]
        )
        st.warning(f"Incomplete estimate. Missing: {missing}.")
        st.metric(
            "Known monthly subtotal — excludes missing costs and reserve",
            money(result["known_monthly_subtotal"]),
        )


def show_comparison(comparison):
    columns = {}

    for item in comparison["properties"]:
        inputs = item["inputs"]
        result = item["calculation"]
        components = result["monthly_components"]

        columns[item["property_id"]] = {
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
                components["principal_and_interest"]
            ),
            "Monthly property tax": money(components["property_tax"]),
            "Monthly homeowners insurance": money(
                components["homeowners_insurance"]
            ),
            "Monthly HOA": money(components["hoa"]),
            "Monthly mortgage insurance": money(
                components["mortgage_insurance"]
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

    measures = list(next(iter(columns.values())))
    table = {"Measure": measures}

    for property_id, values in columns.items():
        table[property_id] = [
            values[measure] for measure in measures
        ]

    st.table(table)

    if any(
        not item["calculation"]["complete"]
        for item in comparison["properties"]
    ):
        st.warning(
            "Some costs are unknown. Do not compare an incomplete "
            "subtotal against a complete total."
        )

    for note in comparison.get("notes", []):
        st.caption(note)


st.title("Real Estate RAG Assistant")
st.write("Research property documents and compare ownership costs.")

with st.sidebar:
    st.header("Controls")

    if st.button("Ingest Documents"):
        try:
            with st.spinner("Processing documents..."):
                ingestion = post_json("/ingest", {}, timeout=120)

            if ingestion is not None:
                st.success(f"Ingestion complete: {ingestion}")

        except requests.RequestException as error:
            st.error(f"Ingestion failed: {error}")


# Read property values from the database-backed API.
try:
    response = requests.get(
        f"{API_URL}/properties",
        timeout=15,
    )
    response.raise_for_status()
    property_records = response.json()["properties"]

except (requests.RequestException, ValueError, KeyError) as error:
    st.error(f"Could not load property records: {error}")
    st.info("Check that the API and database are running.")
    st.stop()

if not property_records:
    st.info("No properties found. Run the property seed script first.")
    st.stop()

properties = {
    item["property_id"]: item
    for item in property_records
}

property_choice = st.selectbox(
    "Choose a property:",
    ["All documents", *properties.keys()],
)

property_id = (
    None if property_choice == "All documents" else property_choice
)

if property_id is not None:
    selected = properties[property_id]

    st.write(
        f"**{selected['address']}**, "
        f"{selected['city']}, {selected['state']}"
    )

    if selected["is_synthetic"]:
        st.caption("Fictional development property.")

    st.caption(selected["source_notes"])


# Document research.
st.header("Document Research")

question = st.text_input(
    "Enter your question:",
    "What findings and missing information are documented?",
)

if st.button("Ask"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        try:
            with st.spinner("Searching documents and preparing an answer..."):
                answer = post_json(
                    "/ask",
                    {
                        "question": question.strip(),
                        "property_id": property_id,
                    },
                    timeout=180,
                )

            if answer is not None:
                st.subheader("Answer")
                st.write(answer["answer"])

                st.subheader("Sources")

                if not answer["sources"]:
                    st.info("No supporting sources were returned.")

                for source in answer["sources"]:
                    page = source.get("page_number")
                    page_label = page if page is not None else "N/A"

                    label = (
                        f"{source['document_name']} | "
                        f"page {page_label} | "
                        f"chunk {source['chunk_id']}"
                    )

                    with st.expander(label, expanded=True):
                        st.write(source["preview"])
                        st.caption(
                            f"Hybrid score: {source['hybrid_score']} · "
                            f"Vector distance: {source['vector_distance']} · "
                            f"Keyword score: {source['keyword_score']}"
                        )

        except requests.RequestException as error:
            st.error(f"Research request failed: {error}")


# Single-property calculator.
st.divider()
st.header("Ownership Cost Calculator")

if property_id is None:
    st.info("Select a property above to open its cost calculator.")
else:
    record = properties[property_id]
    prefix = f"db_cost_{property_id}"

    st.subheader(f"Cost scenario: {property_id}")
    st.caption(
        "Defaults come from database records. Form edits affect this "
        "scenario only; they do not update the database. "
        "Down payment defaults to 20%, interest to 6%, and term to "
        "30 years. Review these assumptions."
    )
    st.caption(
        "Utilities, closing costs, and one-time repairs are excluded. "
        "The maintenance reserve is separate."
    )

    with st.form(f"{prefix}_form"):
        purchase_price = st.number_input(
            "Purchase price ($)",
            min_value=1.0,
            value=float(record["asking_price"]),
            key=f"{prefix}_price",
        )

        down_payment = st.number_input(
            "Down payment ($)",
            min_value=0.0,
            value=float(record["asking_price"]) * 0.20,
            key=f"{prefix}_down",
        )

        st.caption(
            "Changing the purchase price does not automatically "
            "change the dollar down payment."
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

        taxes_known = st.checkbox(
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

        if record["annual_insurance"] is None:
            st.caption(
                "The database has no insurance estimate. The entered "
                "amount is excluded unless its checkbox is selected."
            )
        elif record["is_synthetic"]:
            st.caption(
                "The insurance default is a fictional, "
                "nonbinding estimate."
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

        mi_known = st.checkbox(
            "Mortgage insurance known or explicitly assumed",
            value=False,
            key=f"{prefix}_mi_known",
        )

        monthly_mi = st.number_input(
            "Monthly mortgage insurance ($)",
            min_value=0.0,
            value=0.0,
            key=f"{prefix}_mi",
        )

        reserve = st.number_input(
            "Optional monthly maintenance reserve ($)",
            min_value=0.0,
            value=200.0,
            key=f"{prefix}_reserve",
        )

        st.caption(
            "Unchecked costs remain unknown. Enter zero only when "
            "confirmed or explicitly assumed. Form changes take "
            "effect when you calculate."
        )

        calculate = st.form_submit_button("Calculate ownership cost")

    if calculate:
        payload = {
            "purchase_price": purchase_price,
            "down_payment": down_payment,
            "annual_interest_rate_percent": rate,
            "loan_term_years": int(term),
            "annual_property_tax": (
                annual_tax if taxes_known else None
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
            result = post_json("/cost-scenarios", payload)

            if result is not None:
                st.subheader(f"Monthly cost breakdown: {property_id}")
                show_calculation(result)

        except requests.RequestException as error:
            st.error(f"Calculator request failed: {error}")


# Multi-property comparison.
st.divider()
st.header("Compare Property Costs")
st.caption(
    "Uses current database property values and the shared assumptions "
    "below. Edits in the single-property calculator are not included."
)

available_ids = list(properties)
default_ids = [
    item for item in ("SYN-001", "SYN-003")
    if item in properties
]

if len(default_ids) < 2:
    default_ids = available_ids[:2]

comparison_ids = st.multiselect(
    "Properties to compare",
    options=available_ids,
    default=default_ids,
    max_selections=3,
    key="db_comparison_properties",
)

with st.form("db_comparison_form"):
    comparison_rate = st.number_input(
        "Shared annual interest rate (%)",
        min_value=0.0,
        value=6.0,
        step=0.1,
        key="db_comparison_rate",
    )

    comparison_term = st.number_input(
        "Shared loan term (years)",
        min_value=1,
        value=30,
        step=1,
        key="db_comparison_term",
    )

    down_percent = st.number_input(
        "Down payment for each property (%)",
        min_value=0.0,
        max_value=100.0,
        value=20.0,
        step=1.0,
        key="db_comparison_down",
    )

    comparison_reserve = st.number_input(
        "Monthly maintenance reserve per property ($)",
        min_value=0.0,
        value=200.0,
        key="db_comparison_reserve",
    )

    assume_zero_mi = st.checkbox(
        "Explicitly assume $0 mortgage insurance for every property",
        value=False,
        key="db_comparison_zero_mi",
    )

    st.caption(
        "Otherwise mortgage insurance remains unknown. "
        "The app does not determine insurance requirements. "
        "Missing database costs remain unknown."
    )

    compare_clicked = st.form_submit_button("Compare costs")

if compare_clicked:
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
            comparison = post_json(
                "/comparisons",
                {"properties": scenarios},
            )

            if comparison is not None:
                show_comparison(comparison)

                with st.expander("Property value sources"):
                    for selected_id in comparison_ids:
                        st.write(f"**{selected_id}**")
                        st.write(
                            properties[selected_id]["source_notes"]
                        )

        except requests.RequestException as error:
            st.error(f"Comparison request failed: {error}")