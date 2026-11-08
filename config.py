"""
Configuration & Topology Settings for DistriDemand-LLM.
Defines regional nodes, SKU properties, transport matrix, and operational thresholds.
"""

from typing import Dict, Any

# Regional Nodes Topology
REGIONS = {
    "node_north": {
        "id": "node_north",
        "name": "North Hub (Delhi / NY)",
        "coordinates": {"lat": 28.6139, "lon": 77.2090},
        "color": "#3B82F6",  # Blue
    },
    "node_south": {
        "id": "node_south",
        "name": "South Hub (Bangalore / TX)",
        "coordinates": {"lat": 12.9716, "lon": 77.5946},
        "color": "#10B981",  # Green
    },
    "node_east": {
        "id": "node_east",
        "name": "East Hub (Kolkata / FL)",
        "coordinates": {"lat": 22.5726, "lon": 88.3639},
        "color": "#F59E0B",  # Amber
    },
    "node_west": {
        "id": "node_west",
        "name": "West Hub (Mumbai / CA)",
        "coordinates": {"lat": 19.0760, "lon": 72.8777},
        "color": "#8B5CF6",  # Purple
    },
}

# Central Supplier Hub (Global Factory / Reserve)
CENTRAL_SUPPLIER = {
    "id": "central_supplier",
    "name": "Central Manufacturing Hub",
    "stock_reserves": {
        "SKU-PHONE": 2000,
        "SKU-LAPTOP": 1000,
        "SKU-AC": 1200,
        "SKU-JACKET": 1500,
    },
    "replenishment_lead_time_ticks": 3,
}

# SKU Catalog Definitions
SKU_CATALOG: Dict[str, Dict[str, Any]] = {
    "SKU-PHONE": {
        "id": "SKU-PHONE",
        "name": "Flagship Smartphone X1",
        "category": "Electronics",
        "unit_price": 799.0,
        "unit_cost": 450.0,
        "base_daily_demand": 35,
        "default_initial_stock": 250,
        "safety_stock": 80,
        "reorder_point": 120,
    },
    "SKU-LAPTOP": {
        "id": "SKU-LAPTOP",
        "name": "UltraBook Pro 15",
        "category": "Electronics",
        "unit_price": 1299.0,
        "unit_cost": 850.0,
        "base_daily_demand": 20,
        "default_initial_stock": 160,
        "safety_stock": 50,
        "reorder_point": 80,
    },
    "SKU-AC": {
        "id": "SKU-AC",
        "name": "Smart Inverter AC 1.5T",
        "category": "Appliances",
        "unit_price": 599.0,
        "unit_cost": 340.0,
        "base_daily_demand": 15,
        "default_initial_stock": 140,
        "safety_stock": 40,
        "reorder_point": 70,
    },
    "SKU-JACKET": {
        "id": "SKU-JACKET",
        "name": "Thermal Winter Parka",
        "category": "Apparel",
        "unit_price": 149.0,
        "unit_cost": 60.0,
        "base_daily_demand": 25,
        "default_initial_stock": 180,
        "safety_stock": 60,
        "reorder_point": 90,
    },
}

# Inter-Node Transit Matrix (Transit ticks & Shipping cost per unit in $)
# Format: (from_node, to_node) -> {"transit_ticks": int, "unit_freight_cost": float}
TRANSIT_MATRIX = {
    ("node_north", "node_south"): {"transit_ticks": 2, "freight_cost_per_unit": 18.0},
    ("node_north", "node_east"):  {"transit_ticks": 1, "freight_cost_per_unit": 12.0},
    ("node_north", "node_west"):  {"transit_ticks": 1, "freight_cost_per_unit": 14.0},

    ("node_south", "node_north"): {"transit_ticks": 2, "freight_cost_per_unit": 18.0},
    ("node_south", "node_east"):  {"transit_ticks": 1, "freight_cost_per_unit": 13.0},
    ("node_south", "node_west"):  {"transit_ticks": 1, "freight_cost_per_unit": 10.0},

    ("node_east", "node_north"):  {"transit_ticks": 1, "freight_cost_per_unit": 12.0},
    ("node_east", "node_south"):  {"transit_ticks": 1, "freight_cost_per_unit": 13.0},
    ("node_east", "node_west"):   {"transit_ticks": 2, "freight_cost_per_unit": 19.0},

    ("node_west", "node_north"):  {"transit_ticks": 1, "freight_cost_per_unit": 14.0},
    ("node_west", "node_south"):  {"transit_ticks": 1, "freight_cost_per_unit": 10.0},
    ("node_west", "node_east"):   {"transit_ticks": 2, "freight_cost_per_unit": 19.0},

    # Central Supplier to Regional Nodes
    ("central_supplier", "node_north"): {"transit_ticks": 2, "freight_cost_per_unit": 15.0},
    ("central_supplier", "node_south"): {"transit_ticks": 2, "freight_cost_per_unit": 15.0},
    ("central_supplier", "node_east"):  {"transit_ticks": 2, "freight_cost_per_unit": 15.0},
    ("central_supplier", "node_west"):  {"transit_ticks": 2, "freight_cost_per_unit": 15.0},
}

# Simulation Default Parameters
SIMULATION_CONFIG = {
    "tick_duration_hours": 24,       # Each simulation step represents 1 business day
    "random_demand_variance": 0.20,  # 20% random variance in daily organic demand
    "holding_cost_rate": 0.01,       # 1% per tick holding cost of unit cost
    "stockout_penalty_multiplier": 1.5, # 1.5x lost revenue penalty for stockouts
}

