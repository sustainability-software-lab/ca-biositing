import json
import plotly.graph_objects as go

data = [{"x": {"dtype": "f8", "bdata": "FK5H4Xp0QEA="}, "y": {"dtype": "f8", "bdata": "N9BpA52WQkA="}, "type": "scatter"}]
try:
    fig = go.Figure(data=data)
    print("Success!")
except Exception as e:
    print("Error:", e)
