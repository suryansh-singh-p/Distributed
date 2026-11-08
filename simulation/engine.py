"""
Simulation Engine for DistriDemand-LLM.
Orchestrates discrete-time simulation ticks, ties together distributed nodes,
broker event bus, LLM agents, and time-series telemetry recording.
"""

import uuid
from typing import Dict, List, Any, Optional
from config import REGIONS, SKU_CATALOG
from core.broker import DistributedMessageBroker
from core.node import RegionalWarehouseNode
from core.central_hub import CentralSupplierHub
from core.models import ShockEvent, NodeStatus, ProposalStatus
from core.llm_engine import LLMEngine, EdgeDemandSensingAgent, P2PNegotiationAgent, CentralArbiterAgent


class SimulationEngine:
    """
    Clock-driven orchestrator managing the distributed multi-agent simulation.
    Coordinates tick execution, customer demand ingestion, LLM demand sensing,
    and distributed rebalancing.
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: str = "auto",
        ollama_model: Optional[str] = None
    ):
        self.current_tick: int = 0
        self.broker = DistributedMessageBroker()
        
        # Instantiate 4 autonomous regional nodes
        self.nodes: Dict[str, RegionalWarehouseNode] = {}
        for node_id, cfg in REGIONS.items():
            self.nodes[node_id] = RegionalWarehouseNode(
                node_id=node_id,
                name=cfg["name"],
                broker=self.broker
            )

        # Central factory buffer
        self.central_hub = CentralSupplierHub(broker=self.broker)

        # LLM Intelligence Layer
        self.llm_engine = LLMEngine(api_key=api_key, provider=provider, ollama_model=ollama_model)
        self.sensing_agent = EdgeDemandSensingAgent(llm_engine=self.llm_engine)
        self.p2p_agent = P2PNegotiationAgent(llm_engine=self.llm_engine)
        self.arbiter_agent = CentralArbiterAgent(llm_engine=self.llm_engine)

        # Time-series history for dashboard charts
        self.history: List[Dict[str, Any]] = []
        self.agent_dialogues: List[Dict[str, Any]] = []

        # Record initial baseline state
        self._record_snapshot()

    def set_api_key(self, api_key: Optional[str] = None, provider: str = "auto", ollama_model: Optional[str] = None) -> None:
        """Update API credentials dynamically from dashboard UI."""
        self.llm_engine = LLMEngine(api_key=api_key, provider=provider, ollama_model=ollama_model)
        self.sensing_agent = EdgeDemandSensingAgent(llm_engine=self.llm_engine)
        self.p2p_agent = P2PNegotiationAgent(llm_engine=self.llm_engine)
        self.arbiter_agent = CentralArbiterAgent(llm_engine=self.llm_engine)

    def inject_shock(self, raw_text: str, title: Optional[str] = None) -> ShockEvent:
        """
        Ingests unstructured text, utilizes LLM Edge Demand Sensing to parse parameters,
        and broadcasts the structured shock onto the distributed message broker.
        """
        # Call LLM Agent
        parsed = self.sensing_agent.analyze_signal(raw_text)

        target_region = parsed.get("target_region", "all")
        target_sku = parsed.get("target_sku", "SKU-PHONE")
        multiplier = float(parsed.get("demand_multiplier", 2.5))
        reasoning = parsed.get("reasoning", "Parsed unstructured market signal")

        shock = ShockEvent(
            shock_id=f"shock_{uuid.uuid4().hex[:6]}",
            title=title or f"Market Shock: {target_sku} in {target_region}",
            raw_text=raw_text,
            target_region=target_region,
            target_sku=target_sku,
            demand_multiplier=multiplier,
            duration_ticks=3,
            remaining_ticks=3,
            created_at_tick=self.current_tick,
            ai_reasoning=reasoning
        )

        # Broadcast over distributed broker channel
        self.broker.publish(
            channel="shocks",
            sender_id="edge_sensor_agent",
            payload={"shock": shock.model_dump()},
            tick=self.current_tick
        )

        # Log agent dialogue
        self.agent_dialogues.append({
            "tick": self.current_tick,
            "type": "DEMAND_SENSING",
            "title": shock.title,
            "speaker": "Edge Demand Sensing Agent",
            "content": f"Parsed signal -> Target: {target_sku} @ {target_region} | Multiplier: {multiplier}x | Confidence: {parsed.get('confidence', 0.9):.2f}\nRationale: {reasoning}"
        })

        return shock

    def step(self) -> Dict[str, Any]:
        """
        Advance the simulation clock by 1 tick (1 operational day).
        Executes distributed customer consumption, P2P peer rebalancing, and central arbitration.
        """
        self.current_tick += 1
        daily_sales_by_node = {}

        # 1. Step all regional nodes (process inbound arrivals, consumer demand, burn rates)
        for node_id, node in self.nodes.items():
            sales = node.step_tick(current_tick=self.current_tick)
            daily_sales_by_node[node_id] = sales

        # 2. Nodes evaluate deficits & broadcast RFQs over p2p_negotiation channel
        all_deficits = {}
        for node_id, node in self.nodes.items():
            deficits = node.evaluate_deficits(current_tick=self.current_tick)
            if deficits:
                all_deficits[node_id] = deficits

        # 3. Check for remaining unaddressed shortages requiring Central Factory Arbitration
        critical_unfulfilled = {}
        for node_id, node in self.nodes.items():
            for sku_id, item in node.inventory.items():
                if item.effective_stock < item.safety_stock and item.pending_inbound == 0:
                    shortage = (item.safety_stock * 2) - item.effective_stock
                    if sku_id not in critical_unfulfilled:
                        critical_unfulfilled[sku_id] = {}
                    critical_unfulfilled[sku_id][node_id] = {
                        "requested_qty": shortage,
                        "burn_rate": item.daily_burn_rate,
                        "current_stock": item.current_stock
                    }

        # 4. Trigger Central Arbiter Agent if multiple nodes contend for scarce factory buffer
        for sku_id, competing_demands in critical_unfulfilled.items():
            if len(competing_demands) > 0:
                available_stock = self.central_hub.stock_reserves.get(sku_id, 0)
                if available_stock > 0:
                    arb_decision = self.arbiter_agent.arbitrate_shortage(
                        sku_id=sku_id,
                        available_central_stock=available_stock,
                        competing_requests=competing_demands
                    )
                    allocations = arb_decision.get("allocations", {})
                    rationale = arb_decision.get("rationale", "Central buffer allocation")
                    
                    self.central_hub.dispatch_emergency_replenishment(
                        allocations=allocations,
                        rationale=rationale,
                        current_tick=self.current_tick,
                        default_sku=sku_id
                    )

                    self.agent_dialogues.append({
                        "tick": self.current_tick,
                        "type": "CENTRAL_ARBITRATION",
                        "title": f"Central Supply Arbitration for {sku_id}",
                        "speaker": "Central Arbiter LLM Agent",
                        "content": f"Resolved contention for {sku_id}: {allocations}\nExecutive Rationale: {rationale}"
                    })

        # 5. Capture snapshot for charting
        snapshot = self._record_snapshot()
        return snapshot

    def _record_snapshot(self) -> Dict[str, Any]:
        """Record time-series metrics for Streamlit charts."""
        total_stock = 0
        total_sold = 0
        total_lost = 0
        total_freight = 0
        regional_stocks = {}

        for node_id, node in self.nodes.items():
            node_total = sum(i.current_stock for i in node.inventory.values())
            total_stock += node_total
            total_sold += sum(i.units_sold_cumulative for i in node.inventory.values())
            total_lost += node.total_lost_sales_units
            total_freight += node.total_freight_paid

            regional_stocks[node_id] = {
                "name": node.name,
                "status": node.overall_status.value,
                "skus": {sku: item.current_stock for sku, item in node.inventory.items()}
            }

        fill_rate = 100.0
        if (total_sold + total_lost) > 0:
            fill_rate = round((total_sold / (total_sold + total_lost)) * 100.0, 1)

        snapshot = {
            "tick": self.current_tick,
            "total_network_stock": total_stock,
            "total_sold": total_sold,
            "total_lost": total_lost,
            "fill_rate": fill_rate,
            "total_freight": total_freight,
            "active_transfers": len([p for p in self.broker.active_proposals.values() if p.status == ProposalStatus.IN_TRANSIT]),
            "delivered_transfers": len([p for p in self.broker.active_proposals.values() if p.status == ProposalStatus.DELIVERED]),
            "regional_stocks": regional_stocks,
            "central_reserves": dict(self.central_hub.stock_reserves),
        }
        self.history.append(snapshot)
        return snapshot

    def get_kpis(self) -> Dict[str, Any]:
        """Compute aggregate platform KPIs."""
        if not self.history:
            return {}
        latest = self.history[-1]
        
        # Estimate stockout revenue saved by rebalancing
        delivered_units = sum(
            p.quantity for p in self.broker.active_proposals.values()
            if p.status in [ProposalStatus.IN_TRANSIT, ProposalStatus.DELIVERED]
        )
        avg_price = 500.0
        estimated_saved_rev = delivered_units * avg_price

        return {
            "current_tick": self.current_tick,
            "fill_rate": latest["fill_rate"],
            "total_sold": latest["total_sold"],
            "total_lost": latest["total_lost"],
            "active_transfers": latest["active_transfers"],
            "delivered_transfers": latest["delivered_transfers"],
            "total_rebalanced_units": delivered_units,
            "estimated_saved_rev": estimated_saved_rev,
            "total_freight_cost": latest["total_freight"]
        }

    def reset(self) -> None:
        """Reset simulation to initial baseline."""
        self.__init__(api_key=self.llm_engine.api_key, provider=self.llm_engine.provider)

