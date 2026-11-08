"""
Central Supplier Hub & Global Coordinator.
Aggregates telemetry from all distributed nodes, tracks global supply reserves,
and dispatches macro replenishment or resolves allocation conflicts.
"""

from typing import Dict, List, Any, Optional
from config import CENTRAL_SUPPLIER, SKU_CATALOG
from core.models import NodeStatus, BrokerMessage
from core.broker import DistributedMessageBroker


class CentralSupplierHub:
    """
    Acts as the global manufacturer / central supplier node.
    Monitors aggregate telemetry, holds master buffer reserves,
    and resolves allocation conflicts when regional demand exceeds supply.
    """
    def __init__(self, broker: DistributedMessageBroker):
        self.broker = broker
        self.supplier_id = CENTRAL_SUPPLIER["id"]
        self.name = CENTRAL_SUPPLIER["name"]
        
        # Central factory buffer reserves
        self.stock_reserves: Dict[str, int] = dict(CENTRAL_SUPPLIER["stock_reserves"])
        
        # Track global stats
        self.total_dispatched_units: int = 0
        self.arbitration_count: int = 0

    def get_global_inventory_snapshot(self) -> Dict[str, Any]:
        """Aggregate telemetry from all nodes to compute global stock metrics."""
        summary = {
            "total_network_stock": 0,
            "regional_stocks": {},
            "critical_nodes": [],
            "deficits_by_sku": {sku: 0 for sku in SKU_CATALOG.keys()},
        }

        for node_id, telemetry in self.broker.latest_telemetry.items():
            node_total = sum(item.current_stock for item in telemetry.inventory.values())
            summary["total_network_stock"] += node_total
            summary["regional_stocks"][node_id] = {
                "name": telemetry.node_name,
                "status": telemetry.overall_status.value,
                "total_stock": node_total,
                "skus": {sku: item.current_stock for sku, item in telemetry.inventory.items()}
            }
            if telemetry.overall_status in [NodeStatus.CRITICAL_STOCKOUT, NodeStatus.DEFICIT]:
                summary["critical_nodes"].append(node_id)
                for sku, item in telemetry.inventory.items():
                    if item.effective_stock < item.safety_stock:
                        shortage = item.safety_stock - item.effective_stock
                        summary["deficits_by_sku"][sku] += shortage

        return summary

    def dispatch_emergency_replenishment(
        self,
        allocations: Dict[str, Any],
        rationale: str,
        current_tick: int,
        default_sku: Optional[str] = None
    ) -> BrokerMessage:
        """
        Dispatches central stock to designated regional nodes and broadcasts
        the allocation decision and explanation to the distributed network.
        Defensively normalizes variable LLM allocation schemas.
        """
        # Defensive normalization of LLM output
        normalized_allocations: Dict[str, Dict[str, int]] = {}
        for node_id, sku_data in allocations.items():
            if isinstance(sku_data, dict):
                normalized_allocations[node_id] = {}
                for s_id, q in sku_data.items():
                    try:
                        normalized_allocations[node_id][s_id] = int(q)
                    except (ValueError, TypeError):
                        pass
            elif isinstance(sku_data, (int, float, str)):
                # LLM returned flat {node_id: quantity}
                target_sku = default_sku or list(SKU_CATALOG.keys())[0]
                try:
                    normalized_allocations[node_id] = {target_sku: int(sku_data)}
                except (ValueError, TypeError):
                    pass

        # Deduct dispatched units from central reserve
        for node_id, sku_map in normalized_allocations.items():
            for sku_id, qty in sku_map.items():
                available = self.stock_reserves.get(sku_id, 0)
                dispatched = min(qty, available)
                self.stock_reserves[sku_id] = available - dispatched
                sku_map[sku_id] = dispatched
                self.total_dispatched_units += dispatched

        self.arbitration_count += 1

        # Broadcast allocation across central_allocations channel
        msg = self.broker.publish(
            channel="central_allocations",
            sender_id=self.supplier_id,
            payload={
                "action": "CENTRAL_ALLOCATION",
                "allocations": normalized_allocations,
                "rationale": rationale,
                "remaining_reserves": dict(self.stock_reserves),
            },
            tick=current_tick
        )
        return msg

