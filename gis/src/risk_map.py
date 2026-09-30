"""Build and save the interactive ClimateSense AI risk map."""

from html import escape
from pathlib import Path

import folium
import geopandas as gpd

from data_loader import DEFAULT_DATA_PATH, load_predictions
from geo_processor import to_geodataframe
from regional_processor import (
    DEFAULT_BOUNDARY_PATH,
    aggregate_predictions_by_region,
    load_admin_regions,
)


DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent.parent / "output" / "climate_risk_map.html"
RISK_LEVEL_COLORS = {
    "LOW": "#547A57",
    "MEDIUM": "#C79538",
    "HIGH": "#C45D3D",
}
RISK_LEVELS = ("LOW", "MEDIUM", "HIGH")
RISK_TYPE_LABELS = {
    "flood": "Flood",
    "drought": "Drought",
    "heatwave": "Heatwave",
    "air_quality": "Air Quality",
}


def create_risk_map(
    geodataframe: gpd.GeoDataFrame,
    boundary_path: str | Path = DEFAULT_BOUNDARY_PATH,
    regional_data: gpd.GeoDataFrame | None = None,
) -> folium.Map:
    """Create an interactive risk map from geocoded prediction records."""
    required_fields = {"location", "risk_type", "risk_score", "risk_level", "geometry"}
    missing_fields = required_fields - set(geodataframe.columns)
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(f"Geospatial predictions are missing required fields: {missing}.")
    if geodataframe.empty:
        raise ValueError("Cannot create a risk map without prediction locations.")

    min_longitude, min_latitude, max_longitude, max_latitude = geodataframe.total_bounds
    center = [(min_latitude + max_latitude) / 2, (min_longitude + max_longitude) / 2]
    risk_map = folium.Map(
        location=center,
        zoom_start=5,
        tiles="OpenStreetMap",
        control_scale=True,
    )
    risk_map.fit_bounds(
        [[min_latitude, min_longitude], [max_latitude, max_longitude]],
        padding=(48, 48),
        max_zoom=7,
    )

    if regional_data is None:
        regional_data = aggregate_predictions_by_region(
            geodataframe,
            load_admin_regions(boundary_path),
        )
    _add_regional_layer(risk_map, regional_data)

    risk_layers = {
        risk_type: folium.FeatureGroup(name=label, show=True).add_to(risk_map)
        for risk_type, label in RISK_TYPE_LABELS.items()
    }

    for _, prediction in geodataframe.iterrows():
        location = escape(str(prediction["location"]))
        risk_type_key = str(prediction["risk_type"]).lower()
        if risk_type_key not in risk_layers:
            raise ValueError(f"Unsupported risk_type {prediction['risk_type']!r}.")
        risk_type = RISK_TYPE_LABELS[risk_type_key]
        risk_level = str(prediction["risk_level"])
        color = RISK_LEVEL_COLORS[risk_level]
        risk_score = float(prediction["risk_score"])
        popup_html = f"""
        <div class="risk-popup">
          <div class="risk-popup__location">{location}</div>
          <div class="risk-popup__type">{escape(risk_type)}</div>
          <div class="risk-popup__details">
            <div class="risk-popup__row"><span>Risk score</span><strong>{risk_score:.2f}</strong></div>
            <div class="risk-popup__row"><span>Risk level</span>
              <strong class="risk-popup__badge" style="color:{color};">{escape(risk_level)}</strong>
            </div>
          </div>
        </div>
        """
        folium.CircleMarker(
            location=[prediction.geometry.y, prediction.geometry.x],
            radius=8,
            color="#fffdf8",
            weight=2,
            fill=True,
            fill_color=color,
            fill_opacity=0.92,
            tooltip=f"{location} · {escape(risk_level)}",
            popup=folium.Popup(popup_html, max_width=280),
        ).add_to(risk_layers[risk_type_key])

    _add_map_styles(risk_map)
    _add_title(risk_map)
    _add_summary(risk_map, geodataframe)
    _add_risk_type_filter(risk_map, risk_layers)
    _add_legend(risk_map)
    return risk_map


def _add_regional_layer(
    risk_map: folium.Map,
    regions: gpd.GeoDataFrame,
) -> None:
    tooltip_fields = [
        "region_name",
        "location_count",
        "average_risk_score",
        "regional_risk_level",
        "low_count",
        "medium_count",
        "high_count",
    ]
    tooltip_aliases = [
        "State / union territory",
        "Prediction locations",
        "Mean risk score",
        "Regional risk",
        "Low",
        "Medium",
        "High",
    ]

    def style_region(feature: dict) -> dict:
        risk_level = feature["properties"]["regional_risk_level"]
        return {
            "color": "#788978",
            "weight": 0.8,
            "fillColor": RISK_LEVEL_COLORS.get(risk_level, "#b8b9a8"),
            "fillOpacity": 0.22 if risk_level != "NO DATA" else 0.06,
        }

    folium.GeoJson(
        regions.to_json(),
        name="India state and union territory risk",
        smooth_factor=0.8,
        style_function=style_region,
        highlight_function=lambda _: {"weight": 1.8, "fillOpacity": 0.32},
        tooltip=folium.GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=tooltip_aliases,
            localize=True,
            sticky=False,
        ),
    ).add_to(risk_map)


def _add_map_styles(risk_map: folium.Map) -> None:
        styles = """
        <style>
            .risk-panel {
                position: fixed; z-index: 9999; box-sizing: border-box;
                background: rgba(250, 248, 240, .97); color: #34463a;
                border: 1px solid #d9dfd3; border-radius: 5px;
                box-shadow: 0 2px 10px rgba(38, 55, 45, .12);
                font: 12px/1.45 Arial, sans-serif;
            }
            .risk-panel__heading {
                color: #294b37; font-size: 12px; font-weight: 700;
                margin: 0 0 9px;
            }
            .risk-title {
                top: 18px; left: 58px; padding: 13px 18px;
                border-left: 4px solid #315640;
            }
            .risk-title__name { color: #294b37; font: 600 16px/1.35 Georgia, serif; }
            .risk-title__subtitle { color: #68766b; font-size: 11px; margin-top: 3px; }
            .risk-summary { top: 18px; right: 18px; width: 248px; padding: 13px 15px; }
            .risk-summary__total, .risk-summary__row {
                display: flex; align-items: center; justify-content: space-between; gap: 10px;
            }
            .risk-summary__total {
                padding-bottom: 9px; margin-bottom: 9px;
                border-bottom: 1px solid #e1e5dc; color: #68766b;
            }
            .risk-summary__total strong { color: #294b37; font-size: 18px; }
            .risk-summary__section { color: #68766b; font-size: 10px; margin: 7px 0 4px; }
            .risk-summary__row { min-height: 20px; }
            .risk-summary__label { display: flex; align-items: center; gap: 7px; }
            .risk-summary__swatch, .risk-legend__swatch {
                display: inline-block; width: 9px; height: 9px; border-radius: 50%;
            }
            .risk-summary__count { color: #294b37; font-weight: 700; }
            .risk-filter { left: 18px; bottom: 22px; padding: 10px 12px; }
            .risk-filter label { color: #294b37; font-size: 11px; font-weight: 700; margin-right: 8px; }
            .risk-filter select {
                min-width: 132px; padding: 5px 24px 5px 8px; border: 1px solid #cfd8cc;
                border-radius: 3px; background: #fffdf8; color: #34463a; font: 12px Arial, sans-serif;
            }
            .risk-legend { right: 18px; bottom: 22px; padding: 11px 14px; }
            .risk-legend__row { display: flex; align-items: center; gap: 8px; margin-top: 6px; }
            .risk-popup { min-width: 185px; padding: 2px; color: #34463a; font: 12px/1.45 Arial, sans-serif; }
            .risk-popup__location { color: #294b37; font: 600 15px/1.3 Georgia, serif; }
            .risk-popup__type { color: #758176; font-size: 11px; margin: 3px 0 10px; }
            .risk-popup__details { border-top: 1px solid #e1e5dc; padding-top: 7px; }
            .risk-popup__row { display: flex; justify-content: space-between; gap: 20px; margin: 4px 0; }
            .risk-popup__row span { color: #68766b; }
            .risk-popup__row strong { color: #294b37; }
            .risk-popup__row .risk-popup__badge { font-size: 10px; letter-spacing: .04em; }
            @media (max-width: 680px) {
                .risk-title { top: 10px; left: 54px; right: 10px; padding: 9px 11px; }
                .risk-title__name { font-size: 14px; }
                .risk-summary { top: 67px; left: 10px; right: 10px; width: auto; padding: 9px 11px; }
                .risk-summary__section { display: inline-block; width: 58px; }
                .risk-summary__total { padding-bottom: 5px; margin-bottom: 5px; }
                .risk-summary__total strong { font-size: 15px; }
                .risk-summary__row { display: inline-flex; width: calc(50% - 5px); min-height: 18px; }
                .risk-filter { left: 10px; right: 10px; bottom: 126px; padding: 8px 10px; }
                .risk-filter select { width: calc(100% - 88px); }
                .risk-legend { left: 10px; right: 10px; bottom: 10px; padding: 8px 10px; }
                .risk-legend__row { display: inline-flex; margin: 5px 12px 0 0; }
            }
        </style>
        """
        risk_map.get_root().header.add_child(folium.Element(styles))


def _add_title(risk_map: folium.Map) -> None:
        title_html = """
        <div class="risk-panel risk-title">
            <div class="risk-title__name">ClimateSense AI — Climate Risk Map</div>
            <div class="risk-title__subtitle">Climate risk by location</div>
        </div>
        """
        risk_map.get_root().html.add_child(folium.Element(title_html))


def _add_summary(risk_map: folium.Map, geodataframe: gpd.GeoDataFrame) -> None:
        level_counts = geodataframe["risk_level"].value_counts().to_dict()
        type_counts = geodataframe["risk_type"].value_counts().to_dict()
        level_rows = "".join(
                f"<div class='risk-summary__row' data-risk-level='{level}'>"
                f"<span class='risk-summary__label'><span class='risk-summary__swatch' style='background:{RISK_LEVEL_COLORS[level]};'></span>{level.title()}</span>"
                f"<span class='risk-summary__count'>{level_counts.get(level, 0)}</span></div>"
                for level in RISK_LEVELS
        )
        type_rows = "".join(
                f"<div class='risk-summary__row' data-risk-type='{risk_type}'>"
                f"<span>{escape(label)}</span><span class='risk-summary__count'>{type_counts.get(risk_type, 0)}</span></div>"
                for risk_type, label in RISK_TYPE_LABELS.items()
        )
        summary_html = f"""
        <section class="risk-panel risk-summary" aria-label="Climate risk summary">
            <div class="risk-panel__heading">Risk summary</div>
            <div class="risk-summary__total"><span>Total locations</span><strong>{len(geodataframe)}</strong></div>
            <div class="risk-summary__section">Risk level</div>
            {level_rows}
            <div class="risk-summary__section">Risk type</div>
            {type_rows}
        </section>
        """
        risk_map.get_root().html.add_child(folium.Element(summary_html))


def _add_risk_type_filter(
        risk_map: folium.Map,
        risk_layers: dict[str, folium.FeatureGroup],
) -> None:
        filter_id = f"risk-type-filter-{risk_map.get_name()}"
        options = "".join(
                f"<option value='{risk_type}'>{escape(label)}</option>"
                for risk_type, label in RISK_TYPE_LABELS.items()
        )
        filter_html = f"""
        <div class="risk-panel risk-filter">
            <label for="{filter_id}">Risk type</label>
            <select id="{filter_id}" aria-label="Filter map by risk type">
                <option value="all">All risks</option>
                {options}
            </select>
        </div>
        """
        risk_map.get_root().html.add_child(folium.Element(filter_html))

        layer_names = ",".join(
                f"'{risk_type}':{layer.get_name()}" for risk_type, layer in risk_layers.items()
        )
        filter_script = f"""
            (function() {{
                const map = {risk_map.get_name()};
                const layers = {{{layer_names}}};
                const selector = document.getElementById('{filter_id}');
                selector.addEventListener('change', function() {{
                    Object.values(layers).forEach(function(layer) {{ map.removeLayer(layer); }});
                    Object.entries(layers).forEach(function(entry) {{
                        if (selector.value === 'all' || selector.value === entry[0]) {{
                            entry[1].addTo(map);
                        }}
                    }});
                }});
            }})();
        """
        risk_map.get_root().script.add_child(folium.Element(filter_script))


def _add_legend(risk_map: folium.Map) -> None:
    legend_rows = "".join(
        f"<div class='risk-legend__row'><span class='risk-legend__swatch' style='background:{color};'></span>"
        f"<span>{level.title()}</span></div>"
        for level, color in RISK_LEVEL_COLORS.items()
    )
    legend_html = f"""
    <div class="risk-panel risk-legend">
      <div class="risk-panel__heading">Risk level</div>
      {legend_rows}
    </div>
    """
    risk_map.get_root().html.add_child(folium.Element(legend_html))


def generate_risk_map(
    data_path: str | Path = DEFAULT_DATA_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    """Load predictions, build the map, and save a browser-ready HTML file."""
    predictions = load_predictions(data_path)
    geodataframe = to_geodataframe(predictions)
    risk_map = create_risk_map(geodataframe)

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    risk_map.save(str(path))
    return path


if __name__ == "__main__":
    print(f"Created climate risk map: {generate_risk_map()}")
