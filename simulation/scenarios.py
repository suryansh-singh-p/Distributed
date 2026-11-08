"""
Pre-packaged Scenarios for DistriDemand-LLM.
Provides realistic market shocks, weather disruptions, viral trends, and supplier delays.
"""

from typing import Dict, Any, List

SCENARIO_CATALOG: Dict[str, Dict[str, Any]] = {
    "viral_phone_north": {
        "id": "viral_phone_north",
        "title": "📱 Viral Smartphone Trend (North)",
        "headline": "Tech Influencer Video Breaks Internet",
        "raw_text": "A viral teardown video on YouTube praising the Flagship Smartphone X1's camera has sparked massive buyer frenzy! Retail orders in the North Hub (Delhi/NY) have surged 3.8x overnight.",
        "target_region": "node_north",
        "target_sku": "SKU-PHONE",
        "expected_multiplier": 3.8,
        "duration_ticks": 3,
        "description": "Tests autonomous P2P stock rebalancing where North requests urgent transfers from surplus nodes (West/South)."
    },
    "heatwave_ac_west": {
        "id": "heatwave_ac_west",
        "title": "☀️ Extreme Heatwave Alert (West)",
        "headline": "44°C Heatwave Grips Coastal Cities",
        "raw_text": "A severe heatwave alert has been declared across the West Coast! Residential demand for Smart Inverter 1.5T AC units has spiked 3.5x as retail stores report empty shelves.",
        "target_region": "node_west",
        "target_sku": "SKU-AC",
        "expected_multiplier": 3.5,
        "duration_ticks": 4,
        "description": "Tests edge demand-sensing and cross-regional cooling appliance rebalancing."
    },
    "blizzard_jackets_north": {
        "id": "blizzard_jackets_north",
        "title": "❄️ Sub-Zero Blizzard Warning (North)",
        "headline": "Polar Vortex Brings Heavy Snowfall",
        "raw_text": "An arctic blast and early blizzard warning has struck the Northern territory. Online orders for Thermal Winter Parkas have skyrocketed 3.2x as temperatures plummet.",
        "target_region": "node_north",
        "target_sku": "SKU-JACKET",
        "expected_multiplier": 3.2,
        "duration_ticks": 3,
        "description": "Tests seasonal anomaly detection and rapid inter-node apparel transfers."
    },
    "campus_rush_laptops_south": {
        "id": "campus_rush_laptops_south",
        "title": "💻 Back-to-School Tech Rush (South)",
        "headline": "University Semester Admissions Open",
        "raw_text": "Major tech universities in the South Hub have commenced orientations. Student purchases of UltraBook Pro 15 laptops have surged 2.7x across campus postal codes.",
        "target_region": "node_south",
        "target_sku": "SKU-LAPTOP",
        "expected_multiplier": 2.7,
        "duration_ticks": 3,
        "description": "Tests localized student electronics spike balancing against non-college regions."
    },
    "concurrent_contention": {
        "id": "concurrent_contention",
        "title": "⚡ Dual-Region Shortage Contention",
        "headline": "Simultaneous Smartphone Demand Shocks",
        "raw_text": "Concurrent flash promotions in both North and East hubs trigger massive simultaneous demand spikes for Flagship Smartphones! Both regions face imminent stockouts and compete for scarce Central factory reserves.",
        "target_region": "all",
        "target_sku": "SKU-PHONE",
        "expected_multiplier": 3.0,
        "duration_ticks": 3,
        "description": "Stress-tests the Central Arbiter LLM Agent to perform Pareto-optimal allocation under strict supply scarcity."
    }
}


def get_scenario_list() -> List[Dict[str, Any]]:
    return list(SCENARIO_CATALOG.values())

