import geopandas as gpd

tracts = gpd.read_file("data/boundaries/hawaii_census_tracts.zip")
districts = gpd.read_file("data/boundaries/hawaii_house_districts.zip")

# Use a projected coordinate system for area calculations.
tracts = tracts.to_crs("EPSG:26904")
districts = districts.to_crs("EPSG:26904")

tracts = tracts[["GEOID", "geometry"]].rename(
    columns={"GEOID": "tract_geoid"}
)
districts = districts[["SLDLST", "geometry"]].rename(
    columns={"SLDLST": "house_district"}
)

tracts["tract_area"] = tracts.geometry.area

overlaps = gpd.overlay(
    tracts, districts, how="intersection", keep_geom_type=False
)

overlaps["overlap_area"] = overlaps.geometry.area
overlaps["tract_fraction"] = (
    overlaps["overlap_area"] / overlaps["tract_area"]
)

overlaps = overlaps[overlaps["overlap_area"] > 0].copy()

overlaps[[
    "tract_geoid",
    "house_district",
    "tract_fraction"
]].to_csv(
    "data/boundaries/tract_house_crosswalk.csv",
    index=False
)

print("House districts:", districts.house_district.nunique())
print("Census tracts:", tracts.tract_geoid.nunique())
print("Tract-district overlaps:", len(overlaps))
print("Districts with overlaps:", overlaps.house_district.nunique())
print("Tracts with overlaps:", overlaps.tract_geoid.nunique())
print("Crosswalk saved successfully.")
