import pandas as pd
import plotly.express as px

# Load the dataset
url = "https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv"
data = pd.read_csv(url)

# Data Cleaning
columns_of_interest = ["country", "year", "co2", "co2_per_capita", "population"]
data = data[columns_of_interest]
data = data.dropna()

# Filter for specific countries and years
filtered_data = data[(data["year"] >= 1990) & (data["year"] <= 2022)]

# Top Emitters in 2022
latest_year = 2022
top_emitters = (
    filtered_data[filtered_data["year"] == latest_year]
    .sort_values("co2", ascending=False)
    .head(10)
)

# Create Visualizations
# 1. Line chart: CO2 emissions over time for selected countries
selected_countries = ["United States", "China", "India", "Germany", "Brazil"]
country_data = filtered_data[filtered_data["country"].isin(selected_countries)]
line_chart = px.line(
    country_data,
    x="year",
    y="co2",
    color="country",
    title="CO2 Emissions Over Time",
    labels={"co2": "CO2 Emissions (Mt)", "year": "Year"}
)
line_chart.write_html("line_chart.html")

# 2. Bar chart: Top 10 emitters in 2022
bar_chart = px.bar(
    top_emitters,
    x="country",
    y="co2",
    title="Top 10 CO2 Emitters in 2022",
    labels={"co2": "CO2 Emissions (Mt)", "country": "Country"},
    text="co2"
)
bar_chart.update_traces(texttemplate='%{text:.2s}', textposition='outside')
bar_chart.write_html("bar_chart.html")

# 3. World map: CO2 emissions per capita in 2022
world_data = filtered_data[filtered_data["year"] == latest_year]
map_chart = px.choropleth(
    world_data,
    locations="country",
    locationmode="country names",
    color="co2_per_capita",
    title="CO2 Emissions Per Capita (2022)",
    color_continuous_scale="Viridis",
    labels={"co2_per_capita": "CO2 Per Capita (t)"}
)
map_chart.write_html("map_chart.html")

print("Visualizations saved as HTML files.")
