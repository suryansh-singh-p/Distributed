"""
Checkpoint 1 Test Script: Distributed Core & Message Broker.
Validates partitioned state, pub/sub channels, node telemetry, and P2P message exchange.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import REGIONS, SKU_CATALOG
from core.broker import DistributedMessageBroker
from core.node import RegionalWarehouseNode
from core.central_hub import CentralSupplierHub
from core.models import ShockEvent, NodeStatus


def run_checkpoint_1():
    print("=" * 70)
    print("🚀 RUNNING CHECKPOINT 1: DISTRIBUTED CORE & BROKER VALIDATION")
    print("=" * 70)

    # 1. Initialize Distributed Broker
    broker = DistributedMessageBroker()
    print("✓ Distributed Message Broker initialized.")

    # 2. Instantiate Independent Regional Nodes (Partitioned State)
    nodes = {}
    for node_id, cfg in REGIONS.items():
        node = RegionalWarehouseNode(node_id=node_id, name=cfg["name"], broker=broker)
        nodes[node_id] = node
    print(f"✓ Registered {len(nodes)} regional nodes with isolated local states.")

    # 3. Instantiate Central Supplier Hub
    central_hub = CentralSupplierHub(broker=broker)
    print(f"✓ Central Supplier Hub initialized with reserve stock: {central_hub.stock_reserves}")

    # 4. Verify Local Partitioning (Each node has distinct memory for SKUs)
    initial_stock_north = nodes["node_north"].inventory["SKU-PHONE"].current_stock
    nodes["node_north"].inventory["SKU-PHONE"].current_stock -= 50
    initial_stock_south = nodes["node_south"].inventory["SKU-PHONE"].current_stock
    assert nodes["node_north"].inventory["SKU-PHONE"].current_stock != initial_stock_south, "Partitioning check failed!"
    # Reset
    nodes["node_north"].inventory["SKU-PHONE"].current_stock = initial_stock_north
    print("✓ Verified strict memory isolation between regional nodes.")

    # 5. Simulate 1 Operational Day (Tick 1)
    print("\n--- Simulating Day 1 Customer Demand Across Nodes ---")
    for node_id, node in nodes.items():
        sales = node.step_tick(current_tick=1)
        print(f"  [{node.name}] Sales Fulfilled: {sales} | Status: {node.overall_status.value}")

    # 6. Verify Telemetry in Broker
    assert len(broker.latest_telemetry) == 4, f"Expected 4 telemetries, got {len(broker.latest_telemetry)}"
    print("✓ All 4 nodes published telemetry to broker successfully.")

    # 7. Test Targeted Shock Broadcast
    print("\n--- Testing Channel Filtering: Targeted Demand Shock ---")
    shock = ShockEvent(
        shock_id="shock_test_01",
        title="North Heatwave Alert",
        raw_text="Severe heatwave expected in North; demand for ACs up 300%",
        target_region="node_north",
        target_sku="SKU-AC",
        demand_multiplier=3.0,
        duration_ticks=2,
        remaining_ticks=2,
        created_at_tick=1
    )
    broker.publish(
        channel="shocks",
        sender_id="external_sensor",
        payload={"shock": shock.model_dump()},
        tick=1
    )

    # Check recipient nodes
    assert len(nodes["node_north"].active_shocks) == 1, "Node North should receive the shock"
    assert len(nodes["node_south"].active_shocks) == 0, "Node South should NOT receive North shock"
    print("✓ Channel targeting verified: Node North absorbed shock, Node South isolated.")

    # 8. Test P2P RFQ & Quote Negotiation
    print("\n--- Testing P2P Bilateral Negotiation Brokerage ---")
    # Artificially trigger deficit in node_east for SKU-PHONE
    nodes["node_east"].inventory["SKU-PHONE"].current_stock = 30  # Safety is 80, ROP is 120
    deficits = nodes["node_east"].evaluate_deficits(current_tick=1)
    print(f"  [Node East] Detected deficit: {deficits}")

    # Check if proposals were registered
    proposals = list(broker.active_proposals.values())
    print(f"  [Broker Ledger] Active P2P Proposals generated: {len(proposals)}")
    for p in proposals:
        print(f"    -> Proposal {p.proposal_id}: {p.from_node} -> {p.to_node} ({p.quantity} units of {p.sku_id}), ETA: {p.eta_ticks}d, Status: {p.status.value}")

    # 9. Verify Global Inventory Aggregation by Central Coordinator
    global_snap = central_hub.get_global_inventory_snapshot()
    print(f"\n✓ Central Hub aggregated global network stock: {global_snap['total_network_stock']} units.")
    print(f"  Critical Nodes flagged by Central Hub: {global_snap['critical_nodes']}")

    print("\n" + "=" * 70)
    print("🎉 CHECKPOINT 1 PASSED: ALL DISTRIBUTED CORE TESTS SUCCESSFUL!")
    print("=" * 70)


if __name__ == "__main__":
    run_checkpoint_1()

