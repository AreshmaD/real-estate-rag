import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Real Estate RAG Assistant",
    layout="wide",
)

st.title("Real Estate RAG Assistant")
st.write("Choose a property and ask questions about its documents.")

with st.sidebar:
    st.header("Controls")

    if st.button("Ingest Documents"):
        try:
            with st.spinner("Processing documents..."):
                response = requests.post(
                    f"{API_URL}/ingest",
                    timeout=120,
                )
                response.raise_for_status()
                data = response.json()

            st.success(f"Ingestion complete: {data}")

        except requests.RequestException as error:
            st.error(f"Ingestion failed: {error}")

property_choice = st.selectbox(
    "Choose a property:",
    ["All documents", "SYN-001", "SYN-002", "SYN-003"],
)

property_id = (
    None if property_choice == "All documents" else property_choice
)

question = st.text_input(
    "Enter your question:",
    "Was the basement water issue at SYN-001 permanently fixed?",
)

if st.button("Ask"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        try:
            with st.spinner("Searching documents and preparing an answer..."):
                response = requests.post(
                    f"{API_URL}/ask",
                    json={
                        "question": question.strip(),
                        "property_id": property_id,
                    },
                    timeout=180,
                )
                response.raise_for_status()
                data = response.json()

            st.subheader("Answer")
            st.write(data["answer"])

            st.subheader("Sources")

            if not data["sources"]:
                st.info("No supporting sources were returned.")

            for source in data["sources"]:
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
            st.error(f"Request failed: {error}")

st.divider()
st.header("Ownership Cost Calculator")

SAMPLE_COSTS = {
    "SYN-001": {
        "price": 350000.0,
        "annual_tax": 4800.0,
        "annual_insurance": 1800.0,
        "monthly_hoa": 0.0,
    },
    "SYN-002": {
        "price": 325000.0,
        "annual_tax": 4200.0,
        "annual_insurance": 1500.0,
        "monthly_hoa": 325.0,
    },
    "SYN-003": {
        "price": 375000.0,
        "annual_tax": 5400.0,
        "annual_insurance": None,
        "monthly_hoa": 50.0,
    },
}

if property_id is None:
    st.info("Select a property above to open its cost calculator.")
else:
    sample = SAMPLE_COSTS[property_id]

    st.subheader(f"Cost scenario: {property_id}")
    st.caption(
        "Fictional sample inputs, not live quotes or automatically "
        "extracted facts. Down payment defaults to 20%, interest to 6%, "
        "and term to 30 years. Review and edit every assumption. "
        "Utilities, closing costs, and one-time repairs are excluded."
    )

    # Separate widget keys preserve each property's inputs and
    # prevent values from one property appearing under another.
    prefix = f"cost_{property_id}"

    with st.form(f"{prefix}_form"):
        purchase_price = st.number_input(
            "Purchase price ($)",
            min_value=1.0,
            value=sample["price"],
            key=f"{prefix}_price",
        )

        down_payment = st.number_input(
            "Down payment ($)",
            min_value=0.0,
            value=sample["price"] * 0.20,
            key=f"{prefix}_down_payment",
        )

        st.caption(
            "Down payment is a dollar amount. Editing the price "
            "does not automatically change it."
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
            value=True,
            key=f"{prefix}_taxes_known",
        )

        annual_tax = st.number_input(
            "Annual property taxes ($)",
            min_value=0.0,
            value=sample["annual_tax"],
            key=f"{prefix}_tax",
        )

        insurance_known = st.checkbox(
            "Use supplied or assumed homeowners insurance",
            value=sample["annual_insurance"] is not None,
            key=f"{prefix}_insurance_known",
        )

        annual_insurance = st.number_input(
            "Annual homeowners insurance ($)",
            min_value=0.0,
            value=(
                sample["annual_insurance"]
                if sample["annual_insurance"] is not None
                else 0.0
            ),
            key=f"{prefix}_insurance",
        )

        if sample["annual_insurance"] is None:
            st.caption(
                "This property's sample has no insurance estimate. "
                "The amount is excluded unless you check the box above."
            )
        else:
            st.caption(
                "The supplied insurance amount is a fictional, "
                "nonbinding estimate."
            )

        hoa_known = st.checkbox(
            "Use supplied or assumed HOA fee",
            value=True,
            key=f"{prefix}_hoa_known",
        )

        monthly_hoa = st.number_input(
            "Monthly HOA fee ($)",
            min_value=0.0,
            value=sample["monthly_hoa"],
            key=f"{prefix}_hoa",
        )

        if property_id == "SYN-002":
            st.caption(
                "Sample HOA fee: $325 from the notice effective "
                "November 1, 2026. The older listing shows $250."
            )

        mortgage_insurance_known = st.checkbox(
            "Mortgage insurance known or explicitly assumed",
            value=False,
            key=f"{prefix}_mi_known",
        )

        monthly_mortgage_insurance = st.number_input(
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
            "Unchecked costs remain unknown. Zero is used only "
            "when its checkbox is selected. For the sample base "
            "scenario, explicitly assume $0 mortgage insurance. "
            "Checkbox changes take effect when you calculate."
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
            "monthly_hoa": (
                monthly_hoa if hoa_known else None
            ),
            "monthly_mortgage_insurance": (
                monthly_mortgage_insurance
                if mortgage_insurance_known else None
            ),
            "monthly_maintenance_reserve": reserve,
        }

        try:
            response = requests.post(
                f"{API_URL}/cost-scenarios",
                json=payload,
                timeout=30,
            )

            if response.ok:
                result = response.json()

                st.subheader(f"Monthly cost breakdown: {property_id}")

                for name, amount in result["monthly_components"].items():
                    label = (
                        "HOA"
                        if name == "hoa"
                        else name.replace("_", " ").capitalize()
                    )
                    value = (
                        "Unknown"
                        if amount is None
                        else f"${amount:,.2f}"
                    )
                    st.write(f"**{label}:** {value}")

                st.write(
                    "**Separate maintenance reserve:** "
                    f"${result['monthly_maintenance_reserve']:,.2f}"
                )

                if result["complete"]:
                    st.metric(
                        "Estimated monthly housing cost",
                        f"${result['monthly_housing_cost']:,.2f}",
                    )
                    st.metric(
                        "Estimated monthly cost including reserve",
                        f"${result['monthly_cost_with_reserve']:,.2f}",
                    )
                else:
                    missing = ", ".join(
                        name.replace("_", " ")
                        for name in result["missing_inputs"]
                    )
                    st.warning(
                        f"Incomplete estimate. Missing: {missing}."
                    )
                    st.metric(
                        "Known monthly subtotal — "
                        "excludes missing costs and reserve",
                        f"${result['known_monthly_subtotal']:,.2f}",
                    )
            else:
                st.error(
                    f"Calculation rejected ({response.status_code}). "
                    "Check your inputs."
                )
                st.json(response.json())

        except requests.RequestException as error:
            st.error(f"Could not reach the calculator API: {error}")

st.divider()
st.header("Compare Property Costs")
st.caption(
    "Compare fictional sample properties using shared loan assumptions. "
    "Property taxes, HOA fees, and insurance estimates come from the "
    "sample defaults, not edits in the calculator above."
)

comparison_ids = st.multiselect(
    "Properties to compare",
    options=list(SAMPLE_COSTS),
    default=["SYN-001", "SYN-003"],
    max_selections=3,
    key="comparison_properties",
)

with st.form("property_comparison_form"):
    comparison_rate = st.number_input(
        "Shared annual interest rate (%)",
        min_value=0.0,
        value=6.0,
        step=0.1,
        key="comparison_rate",
    )

    comparison_term = st.number_input(
        "Shared loan term (years)",
        min_value=1,
        value=30,
        step=1,
        key="comparison_term",
    )

    comparison_down_percent = st.number_input(
        "Down payment for each property (%)",
        min_value=0.0,
        max_value=100.0,
        value=20.0,
        step=1.0,
        key="comparison_down_percent",
    )

    comparison_reserve = st.number_input(
        "Monthly maintenance reserve per property ($)",
        min_value=0.0,
        value=200.0,
        key="comparison_reserve",
    )

    assume_zero_mi = st.checkbox(
        "Explicitly assume $0 mortgage insurance for every property",
        value=False,
        key="comparison_zero_mi",
    )

    st.caption(
        "Without this assumption, mortgage insurance remains unknown. "
        "The app does not determine mortgage insurance requirements. "
        "SYN-003 homeowners insurance remains unknown."
    )

    compare_clicked = st.form_submit_button("Compare costs")

if compare_clicked:
    if len(comparison_ids) < 2:
        st.warning("Select at least two properties.")
    else:
        property_inputs = []

        for selected_id in comparison_ids:
            sample = SAMPLE_COSTS[selected_id]

            property_inputs.append(
                {
                    "property_id": selected_id,
                    "purchase_price": sample["price"],
                    "down_payment": (
                        sample["price"]
                        * comparison_down_percent
                        / 100
                    ),
                    "annual_interest_rate_percent": comparison_rate,
                    "loan_term_years": int(comparison_term),
                    "annual_property_tax": sample["annual_tax"],
                    "annual_insurance": sample["annual_insurance"],
                    "monthly_hoa": sample["monthly_hoa"],
                    "monthly_mortgage_insurance": (
                        0.0 if assume_zero_mi else None
                    ),
                    "monthly_maintenance_reserve": comparison_reserve,
                }
            )

        try:
            response = requests.post(
                f"{API_URL}/comparisons",
                json={"properties": property_inputs},
                timeout=30,
            )

            if response.ok:
                comparison = response.json()

                def money(value):
                    return (
                        "Unknown"
                        if value is None
                        else f"${value:,.2f}"
                    )

                rows = {
                    "Status": {},
                    "Purchase price": {},
                    "Down payment": {},
                    "Loan amount": {},
                    "Monthly principal and interest": {},
                    "Monthly property tax": {},
                    "Monthly homeowners insurance": {},
                    "Monthly HOA": {},
                    "Monthly mortgage insurance": {},
                    "Known subtotal excluding reserve": {},
                    "Monthly housing cost": {},
                    "Separate monthly maintenance reserve": {},
                    "Monthly cost including reserve": {},
                    "Missing inputs": {},
                }

                for item in comparison["properties"]:
                    selected_id = item["property_id"]
                    inputs = item["inputs"]
                    result = item["calculation"]
                    components = result["monthly_components"]

                    values = {
                        "Status": (
                            "Complete for stated assumptions"
                            if result["complete"]
                            else "Incomplete"
                        ),
                        "Purchase price": money(
                            inputs["purchase_price"]
                        ),
                        "Down payment": money(inputs["down_payment"]),
                        "Loan amount": money(result["loan_amount"]),
                        "Monthly principal and interest": money(
                            components["principal_and_interest"]
                        ),
                        "Monthly property tax": money(
                            components["property_tax"]
                        ),
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

                    for label, value in values.items():
                        rows[label][selected_id] = value

                # Convert rows into columns for a side-by-side table.
                table = {"Measure": list(rows)}

                for selected_id in comparison_ids:
                    table[selected_id] = [
                        rows[label][selected_id]
                        for label in rows
                    ]

                st.table(table)

                if any(
                    not item["calculation"]["complete"]
                    for item in comparison["properties"]
                ):
                    st.warning(
                        "Some costs are unknown. Do not compare an "
                        "incomplete subtotal against a complete total."
                    )

                for note in comparison["notes"]:
                    st.caption(note)

            else:
                st.error(
                    f"Comparison rejected ({response.status_code})."
                )
                st.json(response.json())

        except requests.RequestException as error:
            st.error(f"Could not reach the comparison API: {error}")