# Imports Path so file locations can be built in a platform-independent way.
from pathlib import Path
# Imports json for embedding the generated map data in the interactive HTML file.
import json
# Imports math for deterministic year-to-year fire variation.
import math

# Imports pandas for reading, filtering, sorting, and writing spreadsheet data.
import pandas as pd
# Imports matplotlib for creating and saving the two comparison graphs.
import matplotlib.pyplot as plt
# Imports seaborn for a polished chart theme and color palette.
import seaborn as sns
# Imports GeoPandas for plotting country boundaries and emissions by country.
import geopandas as gpd
# Imports PowerPoint tools for creating the presentation.
from pptx import Presentation
from pptx.util import Inches, Pt


# Stores the names of the 27 current European Union member states.
EU_MEMBER_STATES = {
    # Adds Austria to the set of EU member states.
    "Austria",
    # Adds Belgium to the set of EU member states.
    "Belgium",
    # Adds Bulgaria to the set of EU member states.
    "Bulgaria",
    # Adds Croatia to the set of EU member states.
    "Croatia",
    # Adds Cyprus to the set of EU member states.
    "Cyprus",
    # Adds Czechia to the set of EU member states.
    "Czechia",
    # Adds Denmark to the set of EU member states.
    "Denmark",
    # Adds Estonia to the set of EU member states.
    "Estonia",
    # Adds Finland to the set of EU member states.
    "Finland",
    # Adds France to the set of EU member states.
    "France",
    # Adds Germany to the set of EU member states.
    "Germany",
    # Adds Greece to the set of EU member states.
    "Greece",
    # Adds Hungary to the set of EU member states.
    "Hungary",
    # Adds Ireland to the set of EU member states.
    "Ireland",
    # Adds Italy to the set of EU member states.
    "Italy",
    # Adds Latvia to the set of EU member states.
    "Latvia",
    # Adds Lithuania to the set of EU member states.
    "Lithuania",
    # Adds Luxembourg to the set of EU member states.
    "Luxembourg",
    # Adds Malta to the set of EU member states.
    "Malta",
    # Adds the Netherlands to the set of EU member states.
    "Netherlands",
    # Adds Poland to the set of EU member states.
    "Poland",
    # Adds Portugal to the set of EU member states.
    "Portugal",
    # Adds Romania to the set of EU member states.
    "Romania",
    # Adds Slovakia to the set of EU member states.
    "Slovakia",
    # Adds Slovenia to the set of EU member states.
    "Slovenia",
    # Adds Spain to the set of EU member states.
    "Spain",
    # Adds Sweden to the set of EU member states.
    "Sweden",
}


# Defines the first year included in the analysis.
START_YEAR = 2000
# Defines the last year included in the analysis.
END_YEAR = 2024


# Defines a function that creates the filtered workbook from source to target.
def create_subset(source: Path, target: Path) -> None:
    # Combines the 27 EU countries with China to define the requested subset.
    selected_countries = EU_MEMBER_STATES | {"China"}
    # Reads the main dataset from the data sheet of the source workbook.
    data = pd.read_excel(source, sheet_name="data")
    # Reads the variable descriptions from the metadata sheet of the source workbook.
    metadata = pd.read_excel(source, sheet_name="metadata")

    # Keeps only rows whose country is one of the requested countries.
    subset = data[data["country"].isin(selected_countries)].copy()
    # Sorts the retained rows first by country and then by year.
    subset = subset.sort_values(["country", "year"], kind="stable")
    # Replaces the old row labels with a clean sequence starting at zero.
    subset = subset.reset_index(drop=True)

    # Opens the destination workbook for writing and selects the openpyxl format.
    with pd.ExcelWriter(target, engine="openpyxl") as writer:
        # Writes the filtered observations to a sheet named data.
        subset.to_excel(writer, sheet_name="data", index=False)
        # Writes the original variable descriptions to a sheet named metadata.
        metadata.to_excel(writer, sheet_name="metadata", index=False)

    # Collects the distinct country names that were actually found in the subset.
    found_countries = set(subset["country"].dropna().unique())
    # Identifies requested countries that were absent from the source data.
    missing_countries = sorted(selected_countries - found_countries)
    # Checks whether any requested country was missing.
    if missing_countries:
        # Stops the script and reports the missing country names if the check fails.
        raise ValueError(f"Missing requested countries: {missing_countries}")

    # Reports the path of the workbook that was created.
    print(f"Created: {target}")
    # Reports the number of data rows in the filtered workbook.
    print(f"Rows: {len(subset)}")
    # Reports the number of distinct countries in the filtered workbook.
    print(f"Countries: {len(found_countries)}")


# Defines a function that combines the EU countries and compares them with China.
def create_graphs(data: pd.DataFrame, output_folder: Path) -> None:
    # Applies a clean Seaborn theme to both charts.
    sns.set_theme(style="whitegrid", context="talk")
    # Defines consistent colors for the EU and China across both charts.
    colors = {"European Union": "#0072B2", "China": "#D55E00"}
    # Keeps only observations from 1980 through 2024, inclusive.
    period = data[data["year"].between(START_YEAR, END_YEAR)].copy()
    # Keeps only China and the 27 EU member states in the graph data.
    period = period[period["country"].isin(EU_MEMBER_STATES | {"China"})]

    # Creates a table containing China's annual total CO2 and population.
    china = period[period["country"] == "China"].set_index("year")
    # Creates a table containing the annual observations for EU member states.
    eu = period[period["country"].isin(EU_MEMBER_STATES)]
    # Adds the EU countries' total CO2 emissions for each year.
    eu_total_co2 = eu.groupby("year")["co2"].sum(min_count=1)
    # Adds the EU countries' populations for each year.
    eu_population = eu.groupby("year")["population"].sum(min_count=1)
    # Calculates EU total CO2 divided by total EU population.
    eu_per_capita = eu_total_co2 * 1_000_000 / eu_population

    # Creates a graph showing total CO2 emissions over time.
    figure, axis = plt.subplots(figsize=(11, 6))
    # Draws the EU total emissions line.
    axis.plot(eu_total_co2.index, eu_total_co2, label="European Union", linewidth=2.8, color=colors["European Union"])
    # Draws the China total emissions line.
    axis.plot(china.index, china["co2"], label="China", linewidth=2.8, color=colors["China"])
    # Adds the graph title and axis labels.
    axis.set_title("Total Fossil CO2 Emissions: EU vs China, 2000-2024")
    axis.set_xlabel("Year")
    axis.set_ylabel("CO2 emissions (million tonnes)")
    # Adds a legend and light grid to make the two lines easier to compare.
    axis.legend()
    axis.grid(True, alpha=0.3)
    # Prevents labels from being clipped at the edges of the figure.
    figure.tight_layout()
    # Saves the total-emissions graph as a PNG file.
    figure.savefig(output_folder / "co2_eu_vs_china_2000_2024.png", dpi=300)
    # Closes the figure so it does not remain open in memory.
    plt.close(figure)

    # Creates a graph showing population-adjusted CO2 emissions over time.
    figure, axis = plt.subplots(figsize=(11, 6))
    # Draws the EU per-capita emissions line.
    axis.plot(eu_per_capita.index, eu_per_capita, label="European Union", linewidth=2.8, color=colors["European Union"])
    # Draws China's per-capita emissions line.
    axis.plot(china.index, china["co2_per_capita"], label="China", linewidth=2.8, color=colors["China"])
    # Adds the graph title and axis labels.
    axis.set_title("Fossil CO2 Emissions per Capita: EU vs China, 2000-2024")
    axis.set_xlabel("Year")
    axis.set_ylabel("CO2 emissions per person (tonnes)")
    # Adds a legend and light grid to make the two lines easier to compare.
    axis.legend()
    axis.grid(True, alpha=0.3)
    # Prevents labels from being clipped at the edges of the figure.
    figure.tight_layout()
    # Saves the per-capita graph as a PNG file.
    figure.savefig(output_folder / "co2_per_capita_eu_vs_china_2000_2024.png", dpi=300)
    # Closes the figure so it does not remain open in memory.
    plt.close(figure)

    # Creates the 2000 and 2024 per-capita emissions map.
    map_chart = create_map(data, output_folder)
    # Creates the interactive illustrative forest-fire map with a time slider.
    create_synthetic_fire_map(output_folder)
    # Reports the locations of both graph files.
    print("Created: co2_eu_vs_china_2000_2024.png")
    print("Created: co2_per_capita_eu_vs_china_2000_2024.png")

    # Creates the PowerPoint presentation after both charts are available.
    presentation_path = output_folder / "china_eu_co2_comparison_2000_2024.pptx"
    create_presentation(
        total_chart=output_folder / "co2_eu_vs_china_2000_2024.png",
        per_capita_chart=output_folder / "co2_per_capita_eu_vs_china_2000_2024.png",
        map_chart=map_chart,
        target=presentation_path,
    )
    # Reports the location of the PowerPoint presentation.
    print(f"Created: {presentation_path.name}")


# Defines a function that creates maps showing how per-capita emissions change.
def create_map(data: pd.DataFrame, output_folder: Path) -> Path:
    # Locates the bundled Natural Earth country-boundary data.
    boundaries = output_folder / "naturalearth_admin_0_countries.zip"
    # Reads the country polygons directly from the bundled ZIP file.
    world = gpd.read_file(f"zip://{boundaries}")
    # Keeps only years and countries needed for the map comparison.
    selected = data[
        data["year"].isin([START_YEAR, END_YEAR])
        & data["country"].isin(EU_MEMBER_STATES | {"China"})
    ].copy()
    # Retains each country's ISO code and per-capita emissions for joining to polygons.
    emissions = selected[["country", "iso_code", "year", "co2_per_capita"]]
    # Limits the boundary layer to China and current EU member states.
    world = world[world["ISO_A3"].isin(emissions["iso_code"].dropna())]
    # Uses one shared color range so the change from 2000 to 2024 is meaningful.
    color_max = emissions["co2_per_capita"].max()
    # Creates two map panels, one for the start year and one for the end year.
    figure, axes = plt.subplots(1, 2, figsize=(14, 6), sharex=True, sharey=True)
    # Draws each year using the same warm color scale.
    for axis, year in zip(axes, [START_YEAR, END_YEAR]):
        # Selects the emissions values for the current map year.
        year_emissions = emissions[emissions["year"] == year]
        # Joins emissions values to their country polygons using ISO codes.
        map_data = world.merge(year_emissions, left_on="ISO_A3", right_on="iso_code", how="left")
        # Draws country boundaries as a subtle background.
        world.plot(ax=axis, color="#F1F1F1", edgecolor="white", linewidth=0.5)
        # Colors countries by per-capita emissions, from pale yellow to deep red.
        map_data.plot(
            ax=axis,
            column="co2_per_capita",
            cmap="YlOrRd",
            vmin=0,
            vmax=color_max,
            edgecolor="#6B1D1D",
            linewidth=0.6,
            missing_kwds={"color": "#F1F1F1"},
        )
        # Frames Europe and China together in the map view.
        axis.set_xlim(-15, 145)
        axis.set_ylim(10, 72)
        # Removes axes so the map reads as a geographic comparison.
        axis.set_axis_off()
        # Labels each panel with its year.
        axis.set_title(str(year), fontsize=18, fontweight="bold")
    # Adds a shared title explaining the color meaning.
    figure.suptitle("Per-Capita CO2 Emissions: Where Is the Burning?", fontsize=22, fontweight="bold")
    # Adds a note clarifying that the same scale is used in both panels.
    figure.text(0.5, 0.02, "Same scale in both panels: darker red means higher tonnes of CO2 per person.", ha="center", fontsize=11)
    # Leaves room for the title and explanatory note.
    figure.tight_layout(rect=[0, 0.06, 1, 0.92])
    # Saves the map image for use in the presentation.
    map_path = output_folder / "co2_per_capita_map_2000_2024.png"
    figure.savefig(map_path, dpi=300, bbox_inches="tight")
    # Closes the map figure after saving it.
    plt.close(figure)
    # Returns the saved map path to the presentation builder.
    return map_path


# Defines a function that creates an illustrative, synthetic forest-fire dataset.
def create_synthetic_fire_map(output_folder: Path) -> Path:
        # Locates the bundled Natural Earth country-boundary data.
        boundaries = output_folder / "naturalearth_admin_0_countries.zip"
        # Reads country polygons for China and the 27 current EU member states.
        world = gpd.read_file(f"zip://{boundaries}")
        selected_iso_codes = {
                "AUT", "BEL", "BGR", "HRV", "CYP", "CZE", "DNK", "EST", "FIN",
                "FRA", "DEU", "GRC", "HUN", "IRL", "ITA", "LVA", "LTU", "LUX",
                "MLT", "NLD", "POL", "PRT", "ROU", "SVK", "SVN", "ESP", "SWE", "CHN",
        }
        # Corrects Natural Earth's placeholder code for France at this map scale.
        world["ISO_A3"] = world["ISO_A3"].replace({"-99": "FRA"})
        # Keeps only the countries shown in the fire map.
        world = world[world["ISO_A3"].isin(selected_iso_codes)].copy()
        # Defines higher illustrative fire-risk baselines for Mediterranean countries.
        risk_baselines = {
                "CHN": 72, "ESP": 78, "PRT": 84, "GRC": 76, "ITA": 63,
                "FRA": 48, "HRV": 58, "BGR": 52, "CYP": 60, "SVN": 42,
                "ROU": 38, "HUN": 35, "AUT": 31, "BEL": 26, "CZE": 30,
                "DEU": 34, "DNK": 22, "EST": 25, "FIN": 28, "IRL": 24,
                "LVA": 24, "LTU": 27, "LUX": 20, "MLT": 18, "NLD": 21,
                "POL": 37, "SVK": 32, "SWE": 29,
        }
        # Creates one deterministic fire record per country and year.
        records = []
        # Builds quick lookups for polygon names and representative map points.
        boundary_lookup = {row.ISO_A3: row for row in world[["ISO_A3", "NAME"]].itertuples(index=False)}
        boundary_centroids = world.to_crs("EPSG:3857").centroid.to_crs("EPSG:4326")
        centroid_lookup = dict(zip(world["ISO_A3"], boundary_centroids))
        # Generates records for all 28 requested countries, including tiny Malta.
        for country_index, iso_code in enumerate(sorted(selected_iso_codes)):
            country_name = boundary_lookup.get(iso_code, type("Country", (), {"NAME": "Malta"})).NAME
            for year in range(START_YEAR, END_YEAR + 1):
                # Models declining EU fire intensity and rising China fire intensity for illustration.
                progress = (year - START_YEAR) / (END_YEAR - START_YEAR)
                trend = 1 - 0.42 * progress if iso_code != "CHN" else 1 + 0.18 * progress
                variation = 1 + 0.14 * math.sin((year - START_YEAR) * 0.83 + country_index)
                intensity = max(1, min(100, risk_baselines[iso_code] * trend * variation))
                fire_count = round(intensity * (7.5 if iso_code == "CHN" else 2.5))
                burned_area = round(fire_count * (8 + 5 * variation), 1)
                records.append({
                    "year": year,
                    "iso_code": iso_code,
                    "country": country_name,
                    "fire_count": fire_count,
                    "burned_area_km2": burned_area,
                    "fire_intensity_index": round(intensity, 1),
                })
        # Converts the generated records into a table for export and mapping.
        fire_data = pd.DataFrame(records)
        # Saves the synthetic data separately so its illustrative nature is visible.
        fire_data_path = output_folder / "synthetic_forest_fire_data_2000_2024.csv"
        fire_data.to_csv(fire_data_path, index=False)

        # Converts the selected country polygons into browser-friendly GeoJSON.
        geojson = json.loads(world[["ISO_A3", "NAME", "geometry"]].to_json())
        # Calculates a representative point for each country to place flame markers.
        centroids = world.to_crs("EPSG:3857").centroid.to_crs("EPSG:4326")
        # Creates marker records with deterministic offsets for multiple fire locations.
        marker_records = []
        for country_index, iso_code in enumerate(sorted(selected_iso_codes)):
            country_name = boundary_lookup.get(iso_code, type("Country", (), {"NAME": "Malta"})).NAME
            centroid = centroid_lookup.get(iso_code)
            centroid_lat = centroid.y if centroid is not None else 35.9
            centroid_lon = centroid.x if centroid is not None else 14.4
            for year in range(START_YEAR, END_YEAR + 1):
                record = fire_data[(fire_data["iso_code"] == iso_code) & (fire_data["year"] == year)].iloc[0]
                marker_count = min(18, max(3, round(record["fire_count"] / 25)))
                for marker_index in range(marker_count):
                    angle = marker_index * 2.399 + country_index
                    spread = 0.25 + (marker_index % 4) * 0.16
                    marker_records.append({
                        "year": year,
                        "country": country_name,
                        "lat": centroid_lat + math.sin(angle) * spread,
                        "lon": centroid_lon + math.cos(angle) * spread,
                        "fire_count": int(record["fire_count"]),
                        "burned_area_km2": float(record["burned_area_km2"]),
                    })

        # Embeds all data in a standalone HTML file with a year slider and play button.
        html = f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Illustrative Forest Fires: China and EU</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
    <style>
        body {{ margin: 0; background: #17100d; color: #fff7ed; font-family: Georgia, serif; }}
        header {{ padding: 18px 26px 10px; }}
        h1 {{ margin: 0; font-size: 28px; }}
        p {{ margin: 6px 0; color: #f7c9a5; }}
        #map {{ height: calc(100vh - 150px); min-height: 520px; border-top: 3px solid #e85d04; }}
        .control {{ position: absolute; z-index: 1000; left: 28px; bottom: 28px; background: rgba(35, 15, 8, .93); padding: 14px 16px; border: 1px solid #e85d04; border-radius: 8px; width: min(370px, calc(100vw - 80px)); }}
        input[type=range] {{ width: 100%; accent-color: #ff6b00; }}
        button {{ background: #e85d04; color: white; border: 0; border-radius: 5px; padding: 7px 13px; cursor: pointer; font-weight: bold; }}
        #year {{ color: #ffb703; font-size: 25px; font-weight: bold; }}
        .legend {{ line-height: 18px; color: #fff7ed; }}
        .legend i {{ display: inline-block; width: 18px; height: 12px; margin-right: 5px; }}
    </style>
</head>
<body>
    <header>
        <h1>Forest fires over time: China and the European Union</h1>
        <p>Illustrative synthetic fire data for demonstration. Use the slider or play button to change the year.</p>
    </header>
    <div id="map"></div>
    <div class="control">
        <div><span id="year">2000</span> <button id="play">Play</button></div>
        <input id="slider" type="range" min="2000" max="2024" value="2000" step="1">
        <div class="legend"><i style="background:#fff3b0"></i>lower intensity &nbsp; <i style="background:#e85d04"></i>higher intensity &nbsp; 🔥 fire locations</div>
    </div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const boundaries = {json.dumps(geojson)};
        const fireData = {json.dumps(marker_records)};
        const annualData = {json.dumps(fire_data.to_dict(orient="records"))};
        const map = L.map('map').setView([45, 55], 3);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{ attribution: '&copy; OpenStreetMap contributors' }}).addTo(map);
        let polygonLayer, markerLayer;
        const palette = ['#fff3b0', '#ffd166', '#f8961e', '#e85d04', '#9d0208'];
        function colorFor(value) {{ return palette[Math.min(palette.length - 1, Math.floor(value / 20))]; }}
        function redraw(year) {{
            document.getElementById('year').textContent = year;
            const values = {{}};
            annualData.filter(row => row.year === year).forEach(row => values[row.iso_code] = row);
            if (polygonLayer) map.removeLayer(polygonLayer);
            polygonLayer = L.geoJSON(boundaries, {{ style: feature => {{ const value = values[feature.properties.ISO_A3]?.fire_intensity_index || 0; return {{ fillColor: colorFor(value), fillOpacity: .78, color: '#32130b', weight: 1 }}; }}, onEachFeature: (feature, layer) => {{ const row = values[feature.properties.ISO_A3]; layer.bindPopup(`<b>${{feature.properties.NAME}}</b><br>Fire intensity index: ${{row?.fire_intensity_index ?? 'n/a'}}<br>Fires: ${{row?.fire_count ?? 'n/a'}}<br>Burned area: ${{row?.burned_area_km2 ?? 'n/a'}} km²`); }} }}).addTo(map);
            if (markerLayer) map.removeLayer(markerLayer);
            markerLayer = L.layerGroup(fireData.filter(row => row.year === year).map(row => L.circleMarker([row.lat, row.lon], {{ radius: 5, color: '#ffb703', fillColor: '#ff4500', fillOpacity: .9, weight: 1 }}).bindPopup(`<b>${{row.country}}</b><br>${{row.fire_count}} illustrative fires<br>${{row.burned_area_km2}} km² burned area`))).addTo(map);
        }}
        const slider = document.getElementById('slider');
        slider.addEventListener('input', event => redraw(Number(event.target.value)));
        let playing = false, timer;
        document.getElementById('play').addEventListener('click', () => {{ playing = !playing; document.getElementById('play').textContent = playing ? 'Pause' : 'Play'; if (playing) timer = setInterval(() => {{ slider.value = Number(slider.value) >= 2024 ? 2000 : Number(slider.value) + 1; redraw(Number(slider.value)); }}, 650); else clearInterval(timer); }});
        redraw(2000);
    </script>
</body>
</html>"""
        # Writes the interactive fire map to the workspace.
        html_path = output_folder / "synthetic_forest_fire_map.html"
        html_path.write_text(html, encoding="utf-8")
        # Reports the generated data and interactive map paths.
        print(f"Created: {fire_data_path.name}")
        print(f"Created: {html_path.name}")
        return html_path


# Defines a function that places the two charts into a PowerPoint presentation.
def create_presentation(total_chart: Path, per_capita_chart: Path, map_chart: Path, target: Path) -> None:
    # Creates a widescreen PowerPoint presentation.
    presentation = Presentation()
    presentation.slide_width = Inches(13.333)
    presentation.slide_height = Inches(7.5)
    # Uses a blank layout so the chart placement is fully controlled.
    blank_layout = presentation.slide_layouts[6]

    # Adds one slide so the two chart pictures can appear next to each other.
    slide = presentation.slides.add_slide(blank_layout)
    # Adds an overall title above both charts.
    title = slide.shapes.add_textbox(Inches(0.45), Inches(0.2), Inches(12.4), Inches(0.55))
    title.text_frame.text = "China and EU Fossil CO2 Emissions, 2000-2024"
    title.text_frame.paragraphs[0].font.size = Pt(24)
    title.text_frame.paragraphs[0].font.bold = True
    # Adds the total-emissions picture on the left.
    slide.shapes.add_picture(str(total_chart), Inches(0.2), Inches(0.9), width=Inches(6.45))
    # Adds the per-capita picture on the right.
    slide.shapes.add_picture(str(per_capita_chart), Inches(6.68), Inches(0.9), width=Inches(6.45))
    # Adds a short note below the total-emissions picture.
    note = slide.shapes.add_textbox(Inches(0.35), Inches(4.45), Inches(6.1), Inches(0.55))
    note.text_frame.text = "Total: annual emissions; EU is the combined total of its 27 member states."
    note.text_frame.paragraphs[0].font.size = Pt(10)
    # Adds a short note below the per-capita picture.
    note = slide.shapes.add_textbox(Inches(6.83), Inches(4.45), Inches(6.1), Inches(0.55))
    note.text_frame.text = "Per capita: EU emissions divided by total EU population."
    note.text_frame.paragraphs[0].font.size = Pt(10)

    # Adds a second slide containing the 2000 and 2024 country maps.
    slide = presentation.slides.add_slide(blank_layout)
    # Adds a title above the map comparison.
    title = slide.shapes.add_textbox(Inches(0.45), Inches(0.2), Inches(12.4), Inches(0.55))
    title.text_frame.text = "Per-Capita CO2 Emissions by Country"
    title.text_frame.paragraphs[0].font.size = Pt(24)
    title.text_frame.paragraphs[0].font.bold = True
    # Adds the map image below the title.
    slide.shapes.add_picture(str(map_chart), Inches(0.2), Inches(0.85), width=Inches(12.9))
    # Adds the interpretation that the shared scale shows declining EU intensity.
    note = slide.shapes.add_textbox(Inches(0.55), Inches(6.95), Inches(12.1), Inches(0.3))
    note.text_frame.text = "With the same color scale, the EU's lighter 2024 map shows lower per-capita emissions than in 2000."
    note.text_frame.paragraphs[0].font.size = Pt(10)

    # Saves the one-slide presentation to the requested output path.
    presentation.save(target)


# Runs the following block only when this file is executed directly.
if __name__ == "__main__":
    # Finds the folder containing this Python script.
    workspace = Path(__file__).resolve().parent
    # Defines the source workbook path.
    source = workspace / "owid-co2-data.xlsx"
    # Creates the requested China and EU subset using files in the script folder.
    create_subset(
        # Specifies the original OWID workbook as the input file.
        source=source,
        # Specifies the filtered workbook as the output file.
        target=workspace / "owid-co2-china-eu-subset.xlsx",
    )
    # Reads the source data for the graph calculations.
    graph_data = pd.read_excel(source, sheet_name="data")
    # Creates the total and per-capita comparison graphs.
    create_graphs(graph_data, workspace)