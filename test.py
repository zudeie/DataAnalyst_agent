import plotly.io as pio

# Read the JSON from file
with open("monthly_sales_trend.json", "r") as f:
    chart_json = f.read()

fig = pio.from_json(chart_json)
fig.write_html("monthly_sales_trend.html")