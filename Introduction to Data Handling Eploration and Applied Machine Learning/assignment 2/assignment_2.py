# Group 13: BDS-GEYY

# Based on data from the danish organisation Social Sundhed I will
# create two groups "Jylland" and "Sjælland" where for Sjælland I will
# include "Fyn" and "Hovedstaden" as well.
# The organisation's main activity is what they call "bridge-building"
# which is volunteers acting as relatives and accompany people in 
# volunerable positions to health related appoinments.

# Part 1: General assessment of the dataset.

from pathlib import Path
import subprocess
import sys

import pandas as pd
import plotly.express as px


SINGLE_PROGRAM_TYPES = {"SBB", "FBB", "SOB"}


# Creating the two groups.
SJAELLAND_CITIES = {
	"København",
	"Frederiksberg",
	"Brøndby",
	"Køge",
	"Slagelse",
	"Nykøbing F",
	"Roskilde",
	"Holbæk",
	"Odense",
	"Svendborg"
}

JYLLAND_CITIES = {
	"Aarhus",
	"Aalborg",
	"Fredericia",
	"Randers",
	"Norddjurs",
	"Esbjerg",
	"Thisted",
	"Hjørring",
	"Viborg",
	"Mariagerfjord"
}

CITY_COORDINATES = {
	"København": (12.5683, 55.6761),
	"Frederiksberg": (12.5230, 55.6802),
	"Brøndby": (12.4140, 55.6517),
	"Køge": (12.1827, 55.4580),
	"Slagelse": (11.3541, 55.4038),
	"Nykøbing F": (11.8743, 54.7691),
	"Roskilde": (12.0803, 55.6415),
	"Holbæk": (11.7156, 55.7175),
	"Odense": (10.4024, 55.4038),
	"Svendborg": (10.6062, 55.0598),
	"Aarhus": (10.2039, 56.1629),
	"Aalborg": (9.9217, 57.0488),
	"Fredericia": (9.7526, 55.5657),
	"Randers": (10.0364, 56.4607),
	"Norddjurs": (10.7670, 56.4400),
	"Esbjerg": (8.4594, 55.4765),
	"Thisted": (8.6949, 56.9560),
	"Hjørring": (9.9620, 57.4642),
	"Viborg": (9.4020, 56.4532),
	"Mariagerfjord": (9.9750, 56.6500),
}

# Initial descriptives of the dataset

def describe_dataset(df):
	"""Print overall descriptive information about the raw dataset."""
	print("Dataset dimensions:")
	print(f"Rows: {df.shape[0]:,}")
	print(f"Columns: {df.shape[1]}")

	print("\nColumn data types:")
    

	print(df.dtypes)

	print("\nMissing values:")
	missing = df.isna().sum().to_frame("missing_count")
	missing["missing_percent"] = (df.isna().mean() * 100).round(2)
	print(missing)

	print("\nUnique values:")
	print(df.nunique(dropna=True).sort_values(ascending=False))

	print("\nNumeric descriptives:")
	numeric_columns = df.select_dtypes(include="number").columns.difference(["aar"])
	if len(numeric_columns) > 0:
		print(df[numeric_columns].describe().round(2).to_string())
	else:
		print("No continuous numeric variables to describe.")

	if "aar" in df.columns:
		allowed_years = list(range(2022, 2028))
		observed_years = sorted(df["aar"].dropna().unique())
		unexpected_years = sorted(set(observed_years) - set(allowed_years))
		print("\naar year check:")
		print(f"Observed years: {observed_years}")
		print("Counts for expected years:")
		print(
			df["aar"]
			.value_counts()
			.reindex(allowed_years, fill_value=0)
			.sort_index()
			.to_string()
		)
		print(f"Unexpected years: {unexpected_years}")

	print("\nCategorical value counts:")
	for column in df.select_dtypes(include=["object", "string"]).columns:
		if column == "Person_id":
			continue
		print(f"\n{column}:")
		print(df[column].value_counts(dropna=False).to_string())

	if "Person_id" in df.columns:
		person_counts = df["Person_id"].dropna().value_counts()
		print("\nPerson_id summary:")
		print(f"Unique non-missing people: {person_counts.size:,}")
		print(f"Rows with a Person_id: {df['Person_id'].notna().sum():,}")
		print(f"People with repeated rows: {(person_counts > 1).sum():,}")
		print("Rows per person:")
		print(person_counts.describe().round(2).to_string())

	if "Startdato" in df.columns:
		print("\nStartdato range:")
		print(f"From: {df['Startdato'].min()}")
		print(f"To:   {df['Startdato'].max()}")

def clean_dataset(df):
	"""Filter the data and remove incomplete or unusually large person histories."""
	filtered = df.loc[
		(df["Aftaletype"] == "Fysisk følgeskab")
		& (df["Status"] == "Bekræftet")
		& (df["Programtype"].isin(SINGLE_PROGRAM_TYPES))
		& (df["aar"].between(2022, 2026))
		& (df["Sektoransvar_udledt"].str.contains("Region|Kommune", na=False))
	].copy()

	# A person-level analysis requires a known person and complete row data.
	filtered = filtered.dropna().copy()

	# Remove people with more than 100 appointments after the filters above.
	appointments_per_person = filtered.groupby("Person_id")["Person_id"].transform("size")
	return filtered.loc[appointments_per_person <= 100].copy()


def add_region_group(df):
	"""Label each department as Jutland or the rest of Denmark."""
	result = df.copy()
	result["Gruppe"] = "Resten af Danmark"
	result.loc[result["Afdeling"].isin(JYLLAND_CITIES), "Gruppe"] = "Jylland"
	return result


def create_denmark_map(df, output_path):
	"""Create a map with building symbols and appointment counts."""
	map_points = pd.DataFrame(
		[
			{"Gruppe": "Jylland", "Sektor": "Region", "longitude": 9.3, "latitude": 56.2, "symbol": "🏥"},
			{"Gruppe": "Jylland", "Sektor": "Kommune", "longitude": 9.5, "latitude": 55.1, "symbol": "🏛️"},
			{"Gruppe": "Resten af Danmark", "Sektor": "Region", "longitude": 12.2, "latitude": 56.0, "symbol": "🏥"},
			{"Gruppe": "Resten af Danmark", "Sektor": "Kommune", "longitude": 11.0, "latitude": 55.2, "symbol": "🏛️"},
		]
	)

	sector_counts = (
		df.assign(
			Sektor=df["Sektoransvar_udledt"].str.extract(
				r"^(Region|Kommune)", expand=False
			)
		)
		.groupby(["Gruppe", "Sektor"])
		.size()
	)
	map_points["appointments"] = [
		int(sector_counts.get((row.Gruppe, row.Sektor), 0))
		for row in map_points.itertuples()
	]
	map_points["label"] = map_points["symbol"] + "<br>" + map_points[
		"appointments"
	].map(lambda count: f"{count:,}")

	figure = px.scatter_geo(
		map_points,
		lat="latitude",
		lon="longitude",
		color="Gruppe",
		text="label",
		hover_name="Sektor",
		hover_data={"Gruppe": True, "appointments": True},
		color_discrete_map={
			"Jylland": "#e8751a",
			"Resten af Danmark": "#163a5f",
		},
		title="Confirmed physical follow-up appointments, 2022-2026",
	)
	figure.update_traces(textposition="middle center", textfont=dict(size=30))
	figure.update_geos(
		fitbounds="locations",
		 showcountries=True,
		countrycolor="#5b6470",
		showland=True,
		landcolor="#f3f0e8",
		showocean=True,
		oceancolor="#dcecf2",
		lataxis_range=[54.4, 57.8],
		lonaxis_range=[7.5, 13.0],
	)
	figure.update_layout(
		margin=dict(l=0, r=0, t=55, b=0),
		legend_title_text="Region",
		annotations=[
			{
				"x": 0.01,
				"y": -0.10,
				"xref": "paper",
				"yref": "paper",
				"showarrow": False,
				"align": "left",
				"text": "🏥 Hospital = Region &nbsp;&nbsp; 🏛️ Civic building = Kommune",
			},
		],
	)
	figure.write_html(output_path, include_plotlyjs="cdn")


def push_to_github(message="Update Streamlit app and backend data"):
	"""Commit the deploy-relevant files and push them to GitHub.

	Streamlit Cloud deploys from GitHub, so pushing here triggers a redeploy.
	"""
	repo_dir = Path(__file__).resolve().parent
	files = ["app.py", "assignment_2.py", "requirements.txt", "PanelData_backend.xlsx"]

	def git(*args):
		return subprocess.run(
			["git", *args], cwd=repo_dir, capture_output=True, text=True
		)

	git("add", *files)

	# Only commit when at least one of the tracked files actually changed.
	status = git("status", "--porcelain", "--", *files)
	if not status.stdout.strip():
		print("No changes to push to GitHub.")
		return

	commit = git("commit", "-m", message)
	if commit.returncode != 0:
		print("git commit failed:")
		print(commit.stdout or commit.stderr)
		return

	push = git("push", "origin", "HEAD")
	if push.returncode != 0:
		print("git push failed:")
		print(push.stderr or push.stdout)
		return

	print("Pushed latest app and data to GitHub. Streamlit Cloud will redeploy.")


def main():
	data_path = Path(__file__).resolve().parents[1] / "Assignments" / "PanelData.xlsx"
	panel_data = pd.read_excel(data_path)
	describe_dataset(panel_data)

	# Restrict the dataset before handling missing values and outliers.
	panel_data = clean_dataset(panel_data)
	print("\nAfter restricting the dataset:")
	print(f"Rows: {len(panel_data):,}")
	print("Aftaletype:", panel_data["Aftaletype"].unique())
	print("Status:", panel_data["Status"].unique())
	print("Programtype:", panel_data["Programtype"].unique())
	print("Missing values remaining:", int(panel_data.isna().sum().sum()))
	print(
		"Maximum appointments per person:",
		panel_data["Person_id"].value_counts().max(),
	)

	panel_data = add_region_group(panel_data)
	backend_path = Path(__file__).resolve().parent / "PanelData_backend.xlsx"
	panel_data.to_excel(backend_path, index=False)
	print(f"Backend data saved to: {backend_path}")

	# Push the refreshed app and data to GitHub so Streamlit Cloud redeploys.
	push_to_github()

	app_path = Path(__file__).resolve().parent / "app.py"
	print("Starting Streamlit at http://localhost:8501")
	subprocess.Popen(
		[
			sys.executable,
			"-m",
			"streamlit",
			"run",
			str(app_path),
			"--server.address=localhost",
			"--server.headless=false",
			"--browser.gatherUsageStats=false",
		],
		cwd=app_path.parent,
	)


if __name__ == "__main__":
	main()

