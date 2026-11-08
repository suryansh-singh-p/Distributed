"""
Checkpoint 3 Test Script: Simulation Engine & Scenario Ingestion.
Runs a multi-day discrete-event simulation, injects a demand shock, and verifies autonomous rebalancing.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation.engine import SimulationEngine
from simulation.scenarios import SCENARIO_CATALOG


def run_checkpoint_3():
    print("=" * 70)
    print("🚀 RUNNING CHECKPOINT 3: SIMULATION ENGINE & AUTONOMOUS BALANCING")
    print("=" * 70)

    # 1. Initialize Simulation Engine
    sim = SimulationEngine(provider="auto")
    print("✓ Simulation Engine initialized at Day 0.")

    # 2. Step Day 1 (Baseline operations)
    print("\n--- Day 1: Baseline Market Operations ---")
    snap_1 = sim.step()
    print(f"  Day 1 Total Stock: {snap_1['total_network_stock']} | Units Sold: {snap_1['total_sold']} | Fill Rate: {snap_1['fill_rate']}%")

    # 3. Inject Viral Demand Shock at Day 2
    print("\n--- Day 2: Injecting Viral Smartphone Shock in North Hub ---")
    scenario = SCENARIO_CATALOG["viral_phone_north"]
    shock = sim.inject_shock(raw_text=scenario["raw_text"], title=scenario["title"])
    print(f"  [Shock Injected]: \"{shock.title}\"")
    print(f"   -> AI Detected Target: {shock.target_region} | SKU: {shock.target_sku} | Multiplier: {shock.demand_multiplier}x")
    print(f"   -> Rationale: {shock.ai_reasoning}")

    # 4. Advance Simulation (Days 2 to 5)
    for day in range(2, 6):
        print(f"\n--- Simulating Day {day} ---")
        snap = sim.step()
        north_phone_stock = sim.nodes["node_north"].inventory["SKU-PHONE"].current_stock
        north_phone_eff = sim.nodes["node_north"].inventory["SKU-PHONE"].effective_stock
        inbound = sim.nodes["node_north"].inventory["SKU-PHONE"].pending_inbound
        
        print(f"  [North Hub] Physical Phone Stock: {north_phone_stock} | Inbound: {inbound} | Effective: {north_phone_eff}")
        print(f"  [Network] Fill Rate: {snap['fill_rate']}% | Active Transfers: {snap['active_transfers']} | Delivered: {snap['delivered_transfers']}")

    # 5. Review Broker Audit Ledger & Rebalancing Metrics
    print("\n--- Reviewing Final Platform KPIs ---")
    kpis = sim.get_kpis()
    for k, v in kpis.items():
        print(f"  * {k}: {v}")

    # Assertions
    assert kpis["fill_rate"] >= 85.0, "Fill rate should remain high due to autonomous rebalancing!"
    assert kpis["total_rebalanced_units"] > 0, "Autonomous rebalancing should have transferred units!"
    print(f"\n✓ Successfully transferred {kpis['total_rebalanced_units']} units across nodes to cushion demand shock.")

    # 6. Check LLM Dialogue Log
    print(f"\n--- Multi-Agent Dialogue Log ({len(sim.agent_dialogues)} entries logged) ---")
    for d in sim.agent_dialogues[:4]:
        print(f"  [{d['speaker']} @ Day {d['tick']}]: {d['title']}")
        print(f"    {d['content'][:110]}...")

    print("\n" + "=" * 70)
    print("🎉 CHECKPOINT 3 PASSED: SIMULATION & REBALANCING FULLY VERIFIED!")
    print("=" * 70)


if __name__ == "__main__":
    run_checkpoint_3()

