from district_intelligence import (
    build_tract_indicators,
    build_district_profiles,
    statewide_benchmarks,
    prioritize_needs,
    match_assistance_programs
)

import streamlit as st
import folium
import geopandas as gpd
import pandas as pd
from branca.element import Element
from streamlit_folium import st_folium

st.set_page_config(
    page_title="Project Deep Bet",
    page_icon="Ã°Å¸Å’Âº",
    layout="wide"
)

@st.cache_data
def load_districts():
    districts = gpd.read_file(
        "data/boundaries/hawaii_house_districts.zip"
    )
    return districts.to_crs("EPSG:4326")

districts = load_districts()

@st.cache_data
def load_tracts():
    tracts = gpd.read_file(
        "data/boundaries/hawaii_census_tracts.zip"
    )
    return tracts.to_crs("EPSG:4326")

tracts = load_tracts()

@st.cache_data
def load_income():
    income = pd.read_csv(
        "data/demographics/hawaii_income_2024.csv",
        dtype=str
    )
    income["GEOID"] = (
        income["state"].str.zfill(2)
        + income["county"].str.zfill(3)
        + income["tract"].str.zfill(6)
    )
    return income.set_index("GEOID")

income_data = load_income()

@st.cache_data
def load_renter_housing():
    housing = pd.read_csv(
        "data/demographics/hawaii_housing_2024.csv",
        dtype=str
    )
    housing["GEOID"] = (
        housing["state"].str.zfill(2)
        + housing["county"].str.zfill(3)
        + housing["tract"].str.zfill(6)
    )
    return housing.set_index("GEOID")

renter_housing_data = load_renter_housing()

@st.cache_data
def load_internet():
    internet = pd.read_csv(
        "data/demographics/hawaii_internet_2024.csv",
        dtype=str
    )
    internet["GEOID"] = (
        internet["state"].str.zfill(2)
        + internet["county"].str.zfill(3)
        + internet["tract"].str.zfill(6)
    )
    return internet.set_index("GEOID")

internet_data = load_internet()




st.title("Project Deep Bet")
st.caption("Team Veritas | HAIC 2026")
st.subheader("Hawaiʻi Legislative District Explorer")

col1, col2, col3 = st.columns(3)
col1.metric("House Districts", len(districts))
col2.metric("Census Tracts", "461")
col3.metric("Data Categories", "3")

st.divider()


# District and income search controls.
st.subheader("District Search")

district_mode = st.radio(
    "Search Mode",
    ["All Districts", "Single District", "District Range"],
    horizontal=True,
    key="district_search_mode"
)

district_numbers = sorted(
    districts["SLDLST"].astype(str).unique().tolist()
)

selected_search_districts = set(district_numbers)

if district_mode == "Single District":
    search_district = st.selectbox(
        "House District",
        district_numbers,
        key="search_district_single"
    )
    selected_search_districts = {search_district}

elif district_mode == "District Range":
    range_col1, range_col2 = st.columns(2)

    with range_col1:
        first_district = st.selectbox(
            "From District",
            district_numbers,
            index=0,
            key="search_district_from"
        )

    with range_col2:
        last_district = st.selectbox(
            "Through District",
            district_numbers,
            index=len(district_numbers) - 1,
            key="search_district_to"
        )

    selected_search_districts = {
        number for number in district_numbers
        if first_district <= number <= last_district
    }

    search_district = "All Districts"

else:
    search_district = "All Districts"

income_col1, income_col2 = st.columns(2)

with income_col1:
    minimum_income = st.number_input(
        "Minimum Median Income ($)",
        min_value=0,
        max_value=500000,
        value=0,
        step=5000,
        key="minimum_income"
    )

with income_col2:
    maximum_income = st.number_input(
        "Maximum Median Income ($)",
        min_value=0,
        max_value=500000,
        value=250000,
        step=5000,
        key="maximum_income"
    )

search_income = pd.to_numeric(
    income_data["B19013_001E"],
    errors="coerce"
)

matching_income_tracts = set(
    search_income[
        (search_income >= minimum_income)
        & (search_income <= maximum_income)
    ].index
)

# Apply renter housing affordability filter to search results.
st.subheader("Housing Affordability Filter")

minimum_renter_burden = st.slider(
    "Minimum Percentage of Cost-Burdened Renters",
    min_value=0,
    max_value=100,
    value=0,
    step=5,
    key="minimum_renter_burden"
)

housing_numeric = renter_housing_data.copy()

housing_columns = [
    "B25070_001E",
    "B25070_007E",
    "B25070_008E",
    "B25070_009E",
    "B25070_010E",
    "B25070_011E"
]

for column in housing_columns:
    housing_numeric[column] = pd.to_numeric(
        housing_numeric[column],
        errors="coerce"
    )

eligible_renters = (
    housing_numeric["B25070_001E"]
    - housing_numeric["B25070_011E"]
)

burdened_renters = housing_numeric[
    [
        "B25070_007E",
        "B25070_008E",
        "B25070_009E",
        "B25070_010E"
    ]
].sum(axis=1, min_count=4)

renter_burden_percent = (
    burdened_renters / eligible_renters * 100
).where(eligible_renters > 0)

if minimum_renter_burden > 0:
    qualifying_housing_tracts = set(
        renter_burden_percent[
            renter_burden_percent >= minimum_renter_burden
        ].index
    )
    matching_income_tracts &= qualifying_housing_tracts

# Apply the internet access filter to search results.
st.subheader("Internet Access Filter")

minimum_no_internet = st.slider(
    "Minimum Households Without Internet Access (%)",
    min_value=0,
    max_value=100,
    value=0,
    step=5,
    key="minimum_no_internet"
)

internet_numeric = internet_data[
    ["B28002_001E", "B28002_013E"]
].apply(pd.to_numeric, errors="coerce")

internet_total = internet_numeric["B28002_001E"]
internet_without = internet_numeric["B28002_013E"]

internet_without_pct = (
    internet_without / internet_total * 100
).where(
    (internet_total > 0)
    & (internet_without >= 0)
    & (internet_without <= internet_total)
)

if minimum_no_internet > 0:
    qualifying_internet_tracts = set(
        internet_without_pct[
            internet_without_pct >= minimum_no_internet
        ].index
    )
    matching_income_tracts &= qualifying_internet_tracts

if district_mode != "All Districts":
    search_crosswalk = pd.read_csv(
        "data/boundaries/tract_house_crosswalk.csv",
        dtype={"tract_geoid": str, "house_district": str}
    )

    district_tract_ids = set(
        search_crosswalk.loc[
            search_crosswalk["house_district"].isin(
                selected_search_districts
            ),
            "tract_geoid"
        ]
    )

    matching_income_tracts &= district_tract_ids

if district_mode == "District Range" and first_district > last_district:
    matching_income_tracts = set()
    st.warning("Starting district must not exceed ending district.")

if minimum_income > maximum_income:
    matching_income_tracts = set()
    st.warning("Minimum income cannot exceed maximum income.")
else:
    st.caption(
        f"Matching Census Tracts: {len(matching_income_tracts)}"
    )

st.divider()

hawaii_map = folium.Map(
    location=[20.75, -157.5],
    zoom_start=7,
    tiles="OpenStreetMap",
    control_scale=True
)

# Remove focus outlines from map polygons.
hawaii_map.get_root().header.add_child(Element("""
<style>
.leaflet-container .leaflet-interactive:focus,
.leaflet-container path:focus,
.leaflet-container svg:focus {
    outline: none !important;
}
</style>
"""))

folium.GeoJson(
    districts,
    name="House Districts",
    style_function=lambda feature: {
        "fillColor": "#2878B5",
        "color": "#163F66",
        "weight": 2,
        "fillOpacity": 0.25
    },
    highlight_function=lambda feature: {
        "fillColor": "#FFD166",
        "color": "#FF9F1C",
        "weight": 3,
        "fillOpacity": 0.5
    },
    tooltip=folium.GeoJsonTooltip(
        fields=["SLDLST"],
        aliases=["House District:"],
        sticky=True
    )
).add_to(hawaii_map)

# Show census tracts overlapping the selected House district.
if st.session_state.get("selected_district"):
    selected_shape = districts[
        districts["SLDLST"] == st.session_state.selected_district
    ]

    if not selected_shape.empty:
        selected_geometry = selected_shape.geometry.union_all()
        matching_tracts = tracts[
            tracts.geometry.intersects(selected_geometry)
        ]

        if not matching_tracts.empty:
            folium.GeoJson(
                matching_tracts,
                name="Census Tracts",
                style_function=lambda feature: {
                    "fillColor": "#FFFFFF",
                    "color": "#E85D04",
                    "weight": 1.5,
                    "fillOpacity": 0.05
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=["GEOID", "NAME"],
                    aliases=["Tract GEOID:", "Census Tract:"]
                )
            ).add_to(hawaii_map)


# Highlight census tracts matching the district and income filters.
# Keep this layer below the LayerControl so it can be toggled.
if minimum_income <= maximum_income and matching_income_tracts:
    highlighted_tracts = tracts[
        tracts["GEOID"].astype(str).isin(matching_income_tracts)
    ]

    if not highlighted_tracts.empty:
        folium.GeoJson(
            highlighted_tracts,
            name="Income Search Matches",
            style_function=lambda feature: {
                "fillColor": "#22C55E",
                "color": "#15803D",
                "weight": 2,
                "fillOpacity": 0.45
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["GEOID", "NAME"],
                aliases=["Tract GEOID:", "Census Tract:"]
            )
        ).add_to(hawaii_map)

folium.LayerControl().add_to(hawaii_map)

# Automatically navigate to districts selected in Search.
if district_mode != "All Districts":
    search_zoom_shapes = districts[
        districts["SLDLST"].isin(selected_search_districts)
    ]

    if not search_zoom_shapes.empty:
        if (
            district_mode == "Single District"
            and search_district == "051"
            and st.session_state.get("zoom_051_oahu", False)
        ):
            hawaii_map.fit_bounds([
                [21.28, -157.85],
                [21.48, -157.65]
            ])
        elif not (
            district_mode == "District Range"
            and first_district > last_district
        ):
            minx, miny, maxx, maxy = search_zoom_shapes.total_bounds
            hawaii_map.fit_bounds([
                [miny, minx],
                [maxy, maxx]
            ])

# Remember the district selected by the user.
if "selected_district" not in st.session_state:
    st.session_state.selected_district = None

if (
    st.session_state.selected_district
    and district_mode == "All Districts"
):
    district_shape = districts[
        districts["SLDLST"] == st.session_state.selected_district
    ]

    if not district_shape.empty:
        if (
            st.session_state.selected_district == "051"
            and st.session_state.get("zoom_051_oahu", False)
        ):
            hawaii_map.fit_bounds([
                [21.28, -157.85],
                [21.48, -157.65]
            ])
        else:
            minx, miny, maxx, maxy = district_shape.total_bounds
            hawaii_map.fit_bounds([[miny, minx], [maxy, maxx]])

# Display the map beside the district information panel.
# Full-width interactive map.
map_data = st_folium(
    hawaii_map,
    width=None,
    height=550,
    returned_objects=["last_active_drawing", "last_clicked"]
)

# Four information panels below the map.
selected_tract = st.session_state.get("selected_tract")
panel_columns = st.columns(4, gap="small")

with panel_columns[0]:
    st.subheader("District Information")

    if st.session_state.get("selected_district"):
        st.write(
            "House District:",
            st.session_state.selected_district
        )
    else:
        st.write("Select a House district on the map.")

    if st.session_state.get("selected_tract"):
        st.write(
            "Census Tract:",
            st.session_state.selected_tract
        )
    else:
        st.write("Select a census tract to see its details.")

with panel_columns[1]:
    st.subheader("Median Household Income")

    selected_tract = st.session_state.get("selected_tract")

    if selected_tract and selected_tract in income_data.index:
        value = pd.to_numeric(
            income_data.loc[selected_tract, "B19013_001E"],
            errors="coerce"
        )

        if pd.notna(value) and value >= 0:
            st.metric("Annual Median Income", f"${value:,.0f}")
        else:
            st.write("Income estimate unavailable.")
    else:
        st.write("Select a census tract to view income.")

    st.caption("Source: U.S. Census ACS 2024, 5-year estimates.")

with panel_columns[2]:
    st.subheader("Renter Housing Affordability")

    if selected_tract and selected_tract in renter_housing_data.index:
        row = renter_housing_data.loc[selected_tract]

        def census_number(column):
            return pd.to_numeric(row[column], errors="coerce")

        total = census_number("B25070_001E")
        not_computed = census_number("B25070_011E")
        burden_values = [
            census_number(f"B25070_{i:03d}E")
            for i in range(7, 11)
        ]

        if (
            pd.notna(total)
            and pd.notna(not_computed)
            and all(pd.notna(v) and v >= 0 for v in burden_values)
            and total >= 0
            and not_computed >= 0
            and total > not_computed
        ):
            burdened = sum(burden_values)
            eligible = total - not_computed
            percentage = burdened / eligible * 100

            st.metric("Renters Cost-Burdened", f"{percentage:.1f}%")
            st.caption(
                "Share of renter households spending at least "
                "30% of income on rent and utilities."
            )
        else:
            st.write("Housing affordability estimate unavailable.")
    else:
        st.write("Select a census tract to view housing affordability.")

with panel_columns[3]:
    st.subheader("Internet Access")

    if selected_tract and selected_tract in internet_data.index:
        internet_row = internet_data.loc[selected_tract]

        total_households = pd.to_numeric(
            internet_row["B28002_001E"], errors="coerce"
        )
        no_internet = pd.to_numeric(
            internet_row["B28002_013E"], errors="coerce"
        )

        if (
            pd.notna(total_households)
            and pd.notna(no_internet)
            and total_households > 0
            and 0 <= no_internet <= total_households
        ):
            no_internet_pct = no_internet / total_households * 100

            st.metric(
                "Households Without Internet Access",
                f"{no_internet_pct:.1f}%"
            )
            st.caption(
                "Source: U.S. Census ACS 2024, 5-year estimates."
            )
        else:
            st.write("Internet access estimate unavailable.")
    else:
        st.write("Select a census tract to view internet access.")




st.caption(
    "2025 U.S. Census TIGER/Line boundaries | "
    "Hover over a district to see its number."
)


# Search results table.
st.divider()
st.subheader("Matching Census Tracts")

results_ids = sorted(matching_income_tracts)

if results_ids:
    results = pd.DataFrame(index=pd.Index(results_ids, name="GEOID"))

    results["Census Tract"] = results.index

    # Map each census tract to every overlapping House district.
    crosswalk = pd.read_csv(
        "data/boundaries/tract_house_crosswalk.csv",
        dtype={
            "tract_geoid": str,
            "house_district": str
        }
    )

    tract_districts = (
        crosswalk.groupby("tract_geoid")["house_district"]
        .apply(lambda values: ", ".join(sorted(set(values))))
    )

    results["House District(s)"] = (
        results.index.map(tract_districts).fillna("Unknown")
    )

    results["Median Household Income"] = pd.to_numeric(
        income_data["B19013_001E"], errors="coerce"
    ).reindex(results.index)

    results["Renters Cost-Burdened (%)"] = (
        renter_burden_percent.reindex(results.index)
    )

    results["Without Internet Access (%)"] = (
        internet_without_pct.reindex(results.index)
    )

    results = results.reset_index(drop=True)

    # Download only the census tracts matching the current filters.
    export_results = results.copy()

    for column in [
        "Renters Cost-Burdened (%)",
        "Without Internet Access (%)"
    ]:
        export_results[column] = export_results[column].round(1)

    export_csv = export_results.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        label="Download Filtered Results (CSV)",
        data=export_csv,
        file_name="deep_bet_filtered_tracts.csv",
        mime="text/csv",
        key="download_filtered_tracts"
    )


    st.caption(f"{len(results)} census tracts match your search.")

    st.dataframe(
        results,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Median Household Income": st.column_config.NumberColumn(
                "Median Household Income",
                format="$%d"
            ),
            "Renters Cost-Burdened (%)": st.column_config.NumberColumn(
                "Renters Cost-Burdened (%)",
                format="%.1f%%"
            ),
            "Without Internet Access (%)": st.column_config.NumberColumn(
                "Without Internet Access (%)",
                format="%.1f%%"
            )
        }
    )


    # District-level summary of matching census tracts.
    st.divider()
    st.subheader("House District Summary")

    summary_rows = results.merge(
        crosswalk[["tract_geoid", "house_district"]].drop_duplicates(),
        left_on="Census Tract",
        right_on="tract_geoid",
        how="inner"
    )

    # Keep the summary focused on the districts selected in Search.
    if district_mode != "All Districts":
        summary_rows = summary_rows[
            summary_rows["house_district"].isin(selected_search_districts)
        ]

    if not summary_rows.empty:
        district_summary = (
            summary_rows.groupby("house_district")
            .agg(
                Matching_Tracts=("Census Tract", "nunique"),
                Median_Tract_Income=("Median Household Income", "median"),
                Median_Tract_Renter_Burden=("Renters Cost-Burdened (%)", "median"),
                Median_Tract_No_Internet=("Without Internet Access (%)", "median")
            )
            .reset_index()
            .rename(columns={
                "house_district": "House District",
                "Matching_Tracts": "Matching Tracts",
                "Median_Tract_Income": "Median Tract Income",
                "Median_Tract_Renter_Burden": "Median Tract Renter Burden (%)",
                "Median_Tract_No_Internet": "Median Tract Without Internet (%)"
            })
            .sort_values("House District")
        )

        st.caption(
            "Summaries reflect matching census tracts overlapping each House "
            "district. Median values are calculated across tracts, not residents. "
            "A tract may appear in multiple districts."
        )

        st.dataframe(
            district_summary,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Median Tract Income": st.column_config.NumberColumn(
                    "Median Tract Income", format="$%d"
                ),
                "Median Tract Renter Burden (%)": st.column_config.NumberColumn(
                    "Median Tract Renter Burden (%)", format="%.1f%%"
                ),
                "Median Tract Without Internet (%)": st.column_config.NumberColumn(
                    "Median Tract Without Internet (%)", format="%.1f%%"
                )
            }
        )


else:
    st.info("No census tracts match the current search filters.")

# Identify the legislative district selected on the map.
if map_data and map_data.get("last_active_drawing"):
    selected = map_data["last_active_drawing"]
    district_id = selected.get("properties", {}).get("SLDLST")

    if district_id:
        if district_id != st.session_state.selected_district:
            st.session_state.selected_district = district_id
            st.rerun()

# Identify a clicked census tract without changing the House district.
if map_data:
    clicked_feature = map_data.get("last_active_drawing")

    if clicked_feature:
        properties = clicked_feature.get("properties", {})
        tract_geoid = properties.get("GEOID")

        if tract_geoid:
            if tract_geoid != st.session_state.get("selected_tract"):
                st.session_state.selected_tract = tract_geoid
                st.rerun()

if st.session_state.get("selected_tract"):
    st.info(
        f"Selected Census Tract: {st.session_state.selected_tract}"
    )

# Always display the currently selected district.
if st.session_state.selected_district:
    st.success(
        f"Selected House District: {st.session_state.selected_district}"
    )

    if st.session_state.selected_district == "051":
        if st.button("Zoom to Oahu"):
            st.session_state.zoom_051_oahu = True
            st.rerun()

        if st.button("Show Entire District 051"):
            st.session_state.zoom_051_oahu = False
            st.rerun()

# Temporary diagnostic: show what the map returns.
# st.subheader("Map Click Diagnostic")
# st.write("Map response:", map_data)


# Phase 5: Independent district intelligence report.
st.divider()
st.header("District Intelligence Report")

intelligence_crosswalk = pd.read_csv(
    "data/boundaries/tract_house_crosswalk.csv",
    dtype={
        "tract_geoid": str,
        "house_district": str
    }
)

intelligence_indicators = build_tract_indicators(
    income_data,
    renter_housing_data,
    internet_data
)

intelligence_profiles, intelligence_tracts = build_district_profiles(
    intelligence_indicators,
    intelligence_crosswalk
)

intelligence_benchmarks = statewide_benchmarks(
    intelligence_indicators
)

intelligence_priorities = prioritize_needs(
    intelligence_profiles,
    intelligence_benchmarks
)

intelligence_programs = match_assistance_programs(
    intelligence_priorities
)

report_district = st.selectbox(
    "Select House District for Intelligence Report",
    sorted(intelligence_profiles["house_district"].unique()),
    key="intelligence_district"
)

report_profile = intelligence_profiles[
    intelligence_profiles["house_district"] == report_district
].iloc[0]

st.subheader(f"House District {report_district}")

metric1, metric2, metric3, metric4 = st.columns(4)

metric1.metric(
    "Overlapping Census Tracts",
    int(report_profile["tract_count"])
)

metric2.metric(
    "Median Tract Income",
    f'${report_profile["median_income"]:,.0f}'
)

metric3.metric(
    "Median Tract Renter Burden",
    f'{report_profile["renter_burden_pct"]:.1f}%'
)

metric4.metric(
    "Median Tract Without Internet",
    f'{report_profile["no_internet_pct"]:.1f}%'
)

st.caption(
    "District values are unweighted medians across overlapping census "
    "tracts. They are not population-weighted district estimates."
)

st.subheader("Community Needs Assessment")

report_priorities = intelligence_priorities[
    intelligence_priorities["House District"] == report_district
].copy()

st.dataframe(
    report_priorities[
        [
            "Community Need",
            "District Value",
            "Statewide Benchmark",
            "Difference (%)",
            "Priority"
        ]
    ],
    use_container_width=True,
    hide_index=True
)

st.caption(
    "Priority classifications are prototype comparisons against "
    "statewide tract medians, not official government standards."
)

st.subheader("Potential Assistance Programs")

report_programs = intelligence_programs[
    intelligence_programs["House District"] == report_district
].copy()

if not report_programs.empty:
    st.dataframe(
        report_programs[
            [
                "Community Need",
                "Priority",
                "Program",
                "Agency",
                "Official Website",
                "Eligibility"
            ]
        ],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Official Website": st.column_config.LinkColumn(
                "Official Website"
            )
        }
    )
else:
    st.info(
        "No elevated or moderate community needs were identified "
        "using the current prototype thresholds."
    )

st.caption(
    "Program matches indicate potential relevance only. "
    "Individual eligibility, current availability, and program "
    "requirements must be verified with the responsible agency."
)


# Phase 9: District question interface.
from district_questions import answer_district_question

st.divider()
st.header("District Question Assistant")
st.caption(
    "Ask about the selected House district. Answers use existing "
    "Census-based prototype profiles, not a generative AI model."
)

st.info(
    f"Currently analyzing House District {report_district}. "
    "Change the district in the Intelligence Report selector above."
)

st.caption(
    "Try: What is the median tract income? | "
    "How severe is housing cost burden? | "
    "How many households lack internet access? | "
    "What assistance programs are relevant?"
)

district_question = st.text_input(
    "Ask a district question",
    placeholder="What assistance programs are relevant?",
    key="district_question_input"
)

if st.button("Get District Answer", key="district_question_submit"):
    try:
        district_answer = answer_district_question(
            district_question,
            report_district,
            intelligence_profiles,
            intelligence_programs
        )
        st.session_state["district_question_result"] = {
            "district": report_district,
            "question": district_question,
            "answer": district_answer
        }
    except Exception as exc:
        st.error(
            "The question could not be processed. "
            "Please review the district data and try again."
        )

question_result = st.session_state.get("district_question_result")

if question_result:
    if question_result["district"] == report_district:
        st.subheader("District Answer")
        st.write(question_result["answer"])
    else:
        st.info("Select Get District Answer to analyze the new district.")

# Phase 6: External CSV inspection interface.
st.divider()
st.header("External Data Importer")

st.caption(
    "Upload a CSV dataset for inspection. Imported information "
    "will not modify the existing census data or intelligence reports."
)

uploaded_csv = st.file_uploader(
    "Choose an external CSV dataset",
    type=["csv"],
    key="external_csv_upload"
)

if uploaded_csv is not None:
    from external_data import inspect_csv

    try:
        imported_frame, import_report = inspect_csv(
            uploaded_csv.getvalue()
        )

        st.success("CSV loaded successfully.")

        import_col1, import_col2, import_col3 = st.columns(3)

        import_col1.metric("Rows", import_report["Rows"])
        import_col2.metric("Columns", import_report["Columns"])
        import_col3.metric(
            "Duplicate Rows",
            import_report["Duplicate Rows"]
        )

        st.write(
            "Missing Cells:",
            import_report["Missing Cells"]
        )

        st.write(
            "Possible Geographic Columns:",
            import_report["Possible Geographic Columns"]
        )

        st.subheader("Imported Data Preview")

        st.dataframe(
            imported_frame.head(20),
            use_container_width=True,
            hide_index=True
        )


        st.subheader("Geographic Validation Results")

        from geographic_validation import validate_geography
        import pandas as pd

        reference_crosswalk = pd.read_csv(
            "data/boundaries/tract_house_crosswalk.csv",
            dtype=str
        )

        reference_tracts = (
            reference_crosswalk["tract_geoid"]
            .dropna()
            .unique()
        )

        reference_districts = (
            reference_crosswalk["house_district"]
            .dropna()
            .unique()
        )

        try:
            geographic_results, geographic_summary = (
                validate_geography(
                    imported_frame,
                    reference_tracts,
                    reference_districts,
                    reference_crosswalk
                )
            )

            geo_col1, geo_col2, geo_col3 = st.columns(3)

            geo_col1.metric(
                "Valid Records",
                geographic_summary["Valid"]
            )

            geo_col2.metric(
                "Review Required",
                geographic_summary["Review"]
            )

            geo_col3.metric(
                "Invalid Records",
                geographic_summary["Invalid"]
            )

            st.dataframe(
                geographic_results,
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                "Download Geographic Validation Report",
                data=geographic_results.to_csv(
                    index=False
                ).encode("utf-8"),
                file_name="deep_bet_geographic_validation.csv",
                mime="text/csv",
                key="download_geographic_validation"
            )

            st.caption(
                "Geographic validation confirms location "
                "relationships only. It does not verify the "
                "accuracy or credibility of external statistics."
            )

        except ValueError as geo_error:
            st.warning(
                "Geographic validation unavailable: "
                + str(geo_error)
            )


        # Phase 6.3: Data quality and declared-source screening.
        st.subheader("Data Quality and Source Screening")

        from data_screening import screen_external_data

        try:
            quality_report, quality_summary = (
                screen_external_data(imported_frame)
            )

            quality_col1, quality_col2, quality_col3 = (
                st.columns(3)
            )

            quality_col1.metric(
                "Passed Checks",
                quality_summary["Passed Checks"]
            )

            quality_col2.metric(
                "Review Checks",
                quality_summary["Review Checks"]
            )

            quality_col3.metric(
                "Failed Checks",
                quality_summary["Failed Checks"]
            )

            st.dataframe(
                quality_report[
                    ["Status", "Category", "Finding"]
                ],
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                "Download Data Quality Report",
                data=quality_report.to_csv(
                    index=False
                ).encode("utf-8"),
                file_name="deep_bet_data_quality_report.csv",
                mime="text/csv",
                key="download_data_quality_report"
            )

            st.warning(
                "Source authenticity is NOT independently verified. "
                "A declared agency name or reporting year does not "
                "establish that the dataset is authoritative."
            )

        except ValueError as quality_error:
            st.error(
                "Data quality screening failed: "
                + str(quality_error)
            )

        st.info(
            "Inspection complete. This dataset has not been "
            "approved or merged into the district analysis."
        )

    except ValueError as error:
        st.error(f"Import rejected: {error}")

# DEEP_BET_LIVE_CENSUS_RETRIEVAL_V1
st.divider()
st.subheader("Live Census Data Retrieval")

st.caption(
    "Retrieve official Census API data for review. "
    "Retrieved records are not automatically merged into district reports."
)

from external_retrieval import retrieve_census_data

CENSUS_DATASETS = {
    "2024 ACS ? Hawaii County Median Household Income": (
        "https://api.census.gov/data/2024/acs/acs5"
        "?get=NAME,B19013_001E&for=county:*&in=state:15"
    ),
    "2024 ACS ? Hawaii Tract Median Household Income": (
        "https://api.census.gov/data/2024/acs/acs5"
        "?get=NAME,B19013_001E&for=tract:*&in=state:15"
    )
}

selected_dataset = st.selectbox(
    "Approved Census dataset",
    options=list(CENSUS_DATASETS.keys()),
    key="deep_bet_census_dataset"
)

selected_url = CENSUS_DATASETS[selected_dataset]

st.caption("Source: U.S. Census Bureau, 2024 ACS 5-Year API")

if "deep_bet_census_result" not in st.session_state:
    st.session_state["deep_bet_census_result"] = None

if st.button(
    "Retrieve Census Data",
    key="deep_bet_retrieve_census"
):
    with st.spinner("Contacting the Census API..."):
        try:
            frame, metadata = retrieve_census_data(selected_url)

            st.session_state["deep_bet_census_result"] = {
                "dataset": selected_dataset,
                "frame": frame,
                "metadata": metadata
            }

            st.success("Census data retrieved successfully.")

        except Exception as error:
            st.session_state["deep_bet_census_result"] = None

            message = str(error)

            if "Redirects are not permitted" in message:
                st.warning(
                    "The Census API redirected the request. "
                    "Earlier diagnostics indicated a missing API key. "
                    "No data was imported."
                )
            else:
                st.error(
                    "Retrieval failed. No data was imported. "
                    f"Details: {message}"
                )

result = st.session_state["deep_bet_census_result"]

if result is not None:
    st.markdown("#### Retrieved Dataset")

    st.write("Dataset:", result["dataset"])

    metadata = result["metadata"]

    st.write("Source URL:", metadata["Source URL"])
    st.write("Retrieved UTC:", metadata["Retrieved UTC"])
    st.write("Records:", metadata["Records"])
    st.write("Columns:", metadata["Columns"])

    st.info(
        "The source endpoint is approved, but individual "
        "data values have not been independently verified."
    )

    retrieved_frame = result["frame"]

    st.dataframe(
        retrieved_frame.head(100),
        use_container_width=True
    )

    st.download_button(
        "Download Retrieved Census CSV",
        data=retrieved_frame.to_csv(index=False).encode("utf-8"),
        file_name="deep_bet_retrieved_census.csv",
        mime="text/csv",
        key="deep_bet_download_census"
    )

    st.caption(
        "Review only. No changes have been made to "
        "the existing district intelligence datasets."
    )

# === SOURCE INTELLIGENCE PANEL: PHASE 8.3 ===
st.divider()
st.header("Source Intelligence")
st.caption(
    "Import public-source text, extract numerical claims, "
    "inspect evidence, and visualize comparable values. "
    "Extracted claims are not independently verified."
)

from source_intelligence import extract_source_facts
from public_source_retrieval import retrieve_public_text

source_mode = st.radio(
    "Choose source type",
    ["Paste text", "Public website URL"],
    horizontal=True,
    key="source_intelligence_mode"
)

source_name = st.text_input(
    "Source title",
    value="External public source",
    key="source_intelligence_title"
)

source_url = ""
source_text = ""

if source_mode == "Paste text":
    source_text = st.text_area(
        "Paste the report, article, or source excerpt",
        height=180,
        key="source_intelligence_text"
    )
else:
    source_url = st.text_input(
        "Public HTTPS URL",
        placeholder="https://www.census.gov/",
        key="source_intelligence_url"
    )
    st.caption(
        "Initial supported domains: census.gov, hawaii.gov, congress.gov. "
        "Some pages may block automated retrieval."
    )

if st.button("Analyze Source", key="source_intelligence_analyze"):
    st.session_state.pop("si_results", None)
    st.session_state.pop("si_source_text", None)
    st.session_state.pop("si_retrieval", None)
    try:
        if source_mode == "Public website URL":
            if not source_url.strip():
                raise ValueError("Enter a website URL.")

            with st.spinner("Retrieving public-source text..."):
                retrieved = retrieve_public_text(source_url)

            source_text = retrieved["text"]
            source_url = retrieved["url"]
            st.session_state["si_retrieval"] = retrieved
        else:
            st.session_state["si_retrieval"] = None

        results = extract_source_facts(
            source_text,
            source_name=source_name,
            source_url=source_url
        )

        st.session_state["si_results"] = results
        st.session_state["si_source_text"] = source_text

    except Exception as exc:
        st.error(f"Source analysis failed: {exc}")

results = st.session_state.get("si_results")

if results is not None:
    st.subheader("Extracted Numerical Claims")
    st.metric("Claims extracted", len(results))

    if results.empty:
        st.info("No numerical claims found in the supplied text.")
    else:
        st.dataframe(
            results,
            use_container_width=True,
            hide_index=True
        )

        csv_data = results.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download extracted claims CSV",
            data=csv_data,
            file_name="deepbet_source_claims.csv",
            mime="text/csv",
            key="source_intelligence_download"
        )

        unit = st.selectbox(
            "Chart values with the same unit",
            sorted(results["Unit"].unique().tolist()),
            key="source_intelligence_unit"
        )

        chart_data = results[results["Unit"] == unit].copy()
        chart_data = chart_data.head(20)
        chart_data["Claim"] = [
            f"Claim {i + 1}" for i in range(len(chart_data))
        ]

        if not chart_data.empty:
            st.bar_chart(
                chart_data.set_index("Claim")["Value"]
            )
            st.caption(
                "Claims are charted for exploration only. "
                "Shared units do not establish comparable populations, "
                "time periods, or definitions."
            )

    with st.expander("View retrieved or pasted source text"):
        st.text(
            st.session_state.get("si_source_text", "")[:15000]
        )

# === END SOURCE INTELLIGENCE PANEL ===

