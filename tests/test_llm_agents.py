"""
Checkpoint 2 Test Script: LLM Analytical Engine & Autonomous Multi-Agent Reasoning.
Validates unstructured text parsing, autonomous P2P negotiation dialogue, and central shortage arbitration.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.llm_engine import (
    LLMEngine,
    EdgeDemandSensingAgent,
    P2PNegotiationAgent,
    CentralArbiterAgent,
    canonicalize_sku,
    canonicalize_region
)


def run_checkpoint_2():
    print("=" * 70)
    print("🚀 RUNNING CHECKPOINT 2: LLM ANALYTICAL ENGINE & MULTI-AGENT REASONING")
    print("=" * 70)

    # 1. Initialize LLM Engine
    llm = LLMEngine(provider="auto")
    print(f"✓ LLM Engine initialized (Active Provider: {llm.provider.upper()})")

    # 2. Test Edge Demand Sensing Agent with Unstructured Text
    print("\n--- Testing Agent 1: Edge Demand Sensing (Unstructured Text -> Elasticity) ---")
    sensing_agent = EdgeDemandSensingAgent(llm_engine=llm)

    signals = [
        "Massive tech influencer unboxing video goes viral! Demand for Flagship Smartphones in North Hub surging 4x over the weekend.",
        "Unprecedented 44°C heatwave alert issued across West Hub (Mumbai/CA); residential AC inquiries up 3.5x.",
        "Early winter snowfall reported across North Hub; severe chill driving 2.8x increase in Thermal Winter Parka purchases."
    ]

    for idx, signal in enumerate(signals, 1):
        parsed = sensing_agent.analyze_signal(signal)
        print(f"\n  [Signal {idx}]: \"{signal[:65]}...\"")
        print(f"   -> Target Region: {parsed.get('target_region')}")
        print(f"   -> Target SKU:    {parsed.get('target_sku')}")
        print(f"   -> Multiplier:    {parsed.get('demand_multiplier')}x")
        print(f"   -> Confidence:    {parsed.get('confidence')}")
        print(f"   -> AI Rationale:  {parsed.get('reasoning')}")

        assert parsed.get("demand_multiplier") > 1.0, "Multiplier should reflect demand surge!"
        assert parsed.get("target_sku") is not None, "Target SKU must be identified!"

    print("\n✓ Edge Demand Sensing Agent successfully converted raw text signals into quantitative shock vectors.")

    # 2b. Test Two-Tier Canonicalization against Vocabulary Drift
    print("\n--- Testing Vocabulary Drift Canonicalizer (SKU & Region Guards) ---")
    assert canonicalize_sku("laptop") == "SKU-LAPTOP"
    assert canonicalize_sku("UltraBook Pro 15") == "SKU-LAPTOP"
    assert canonicalize_sku("SKU-LAPTOPS") == "SKU-LAPTOP"
    assert canonicalize_sku("phone") == "SKU-PHONE"
    assert canonicalize_sku("air conditioner") == "SKU-AC"
    assert canonicalize_sku("winter jacket") == "SKU-JACKET"
    assert canonicalize_region("Delhi") == "node_north"
    assert canonicalize_region("Mumbai") == "node_west"
    assert canonicalize_region("Bangalore") == "node_south"
    assert canonicalize_region("Kolkata") == "node_east"
    print("✓ Canonicalizer successfully mapped fuzzy synonyms, product titles, and cities to strict catalog keys!")

    # 3. Test P2P Autonomous Agent Negotiation
    print("\n--- Testing Agent 2: Decentralized P2P Inventory Negotiation ---")
    p2p_agent = P2PNegotiationAgent(llm_engine=llm)

    negotiation_res = p2p_agent.negotiate_transfer(
        requesting_node="node_north",
        supplying_node="node_west",
        sku_id="SKU-PHONE",
        needed_qty=120,
        available_surplus=180,
        freight_cost=1680.0,
        transit_days=1
    )

    print(f"  [Bilateral Dialogue]: \"{negotiation_res.get('dialogue_turn')}\"")
    print(f"  [Agreed Quantity]:    {negotiation_res.get('agreed_quantity')} units")
    print(f"  [Estimated Delivery]: {negotiation_res.get('estimated_delivery_days')} day(s)")
    print(f"  [Economic Rationale]: {negotiation_res.get('economic_rationale')}")

    assert negotiation_res.get("agreed_quantity") > 0, "Negotiated transfer quantity must be > 0"
    print("✓ Autonomous P2P Agent completed negotiation with transparent economic rationale.")

    # 4. Test Central Arbiter Agent under Contention
    print("\n--- Testing Agent 3: Central Shortage Arbitration (Contention Management) ---")
    arbiter_agent = CentralArbiterAgent(llm_engine=llm)

    competing_demands = {
        "node_north": {"requested_qty": 300, "burn_rate": 85.0, "current_stock": 15},
        "node_east":  {"requested_qty": 250, "burn_rate": 60.0, "current_stock": 20}
    }
    available_factory_stock = 400  # Contention: Total demand = 550, Available = 400

    arb_decision = arbiter_agent.arbitrate_shortage(
        sku_id="SKU-PHONE",
        available_central_stock=available_factory_stock,
        competing_requests=competing_demands
    )

    print(f"  [Available Factory Supply]: {available_factory_stock} units")
    print(f"  [Total Competing Demand]:   {sum(r['requested_qty'] for r in competing_demands.values())} units")
    print(f"  [Arbitrated Allocations]:   {arb_decision.get('allocations')}")
    print(f"  [Executive AI Rationale]:   \"{arb_decision.get('rationale')}\"")

    assert arb_decision.get("allocations") is not None, "Allocations map must be returned"
    print("✓ Central Arbiter Agent successfully resolved multi-node contention.")

    print("\n" + "=" * 70)
    print("🎉 CHECKPOINT 2 PASSED: ALL LLM MULTI-AGENT TESTS SUCCESSFUL!")
    print("=" * 70)


if __name__ == "__main__":
    run_checkpoint_2()

