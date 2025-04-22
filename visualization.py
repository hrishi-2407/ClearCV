# ------------------ Visualization Functions ------------------
import plotly.graph_objects as go

def create_resume_health_gauge(overall_score):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = overall_score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        gauge = {
            'axis': {
                'range': [0, 100],
                'tickmode': 'array',
                'tickvals': list(range(0, 101, 10)),  # [0, 10, ..., 100]
                'ticktext': [str(i) for i in range(0, 101, 10)],
                'tickwidth': 1,
                'tickcolor': "darkblue"
            },
            'bar': {'color': "darkblue"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 40], 'color': 'red'},
                {'range': [40, 70], 'color': 'yellow'},
                {'range': [70, 100], 'color': 'green'}],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': overall_score}
        }
    ))
    
    # Fixed scale to always be 0-100
    fig.update_layout(
        title={
            'text': "<b>Resume Health Score</b>",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20}
        },
        height=250,
        margin=dict(l=20, r=30, t=50, b=20)
    )
    return fig

def create_category_radar_chart(category_scores):
    categories = list(category_scores.keys())
    values = list(category_scores.values())

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],  # close the loop
        theta=categories + [categories[0]],
        fill='toself',
        name='Resume Performance'
    ))

    fig.update_layout(
        title={
            'text': "Category Radar Chart",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16, 'family': 'Arial', 'color': '#333'}
        },
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],  # ensures full scale
                tickvals=[0, 20, 40, 60, 80, 100],
                tickfont=dict(size=10)  # smaller ticks
            ),
            angularaxis=dict(
                tickfont=dict(size=10),  # smaller angle labels
                rotation=0,  # start from top
                direction="clockwise"
            )
        ),
        showlegend=False,
        height=230,
        margin=dict(l=40, r=40, t=60, b=40)
    )
    return fig

def create_severity_breakdown(results):
    # Group anomalies by severity level
    severity_levels = {
        "Critical": 0,
        "Moderate": 0, 
        "Minor": 0,
        "No Issues": 0
    }
    
    for check in results:
        if not check['passed']:
            if check['severity'] >= 8:
                severity_levels["Critical"] += 1
            elif check['severity'] >= 4:
                severity_levels["Moderate"] += 1
            elif check['severity'] >= 1:
                severity_levels["Minor"] += 1
        else:
            severity_levels["No Issues"] += 1
    
    # Create custom labels with counts
    custom_labels = []
    for level, count in severity_levels.items():
        if count > 0 or level == "No Issues":  # Always show "No Issues" even if zero
            custom_labels.append(f"{level} - {count}")
        else:
            custom_labels.append("")
    
    # Create horizontal bar chart
    fig = go.Figure()
    colors = ['red', 'orange', 'yellow', 'green']
    
    for i, (level, count) in enumerate(severity_levels.items()):
        fig.add_trace(go.Bar(
            y=[custom_labels[i] if count > 0 or level == "No Issues" else ""],
            x=[count],
            orientation='h',
            marker=dict(color=colors[i]),
            showlegend=False,
            name=level
        ))
    
    fig.update_layout(
        title="Anomaly Severity Breakdown",
        xaxis_title="Number of Checks",
        height=250,
        margin=dict(l=20, r=20, t=50, b=20),
        barmode='stack'
    )
    
    return fig