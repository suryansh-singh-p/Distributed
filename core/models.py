"""
Data contracts and Pydantic models for DistriDemand-LLM.
Defines inventory structures, broker messages, shock events, and agent negotiation proposals.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import time


class NodeStatus(str, Enum):
    OPTIMAL = "OPTIMAL"
    WARNING = "WARNING"
    DEFICIT = "DEFICIT"
    CRITICAL_STOCKOUT = "CRITICAL_STOCKOUT"


class ProposalStatus(str, Enum):
    PROPOSED = "PROPOSED"
    NEGOTIATING = "NEGOTIATING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"


class InventoryItem(BaseModel):
    sku_id: str
    name: str
    current_stock: int
    safety_stock: int
    reorder_point: int
    daily_burn_rate: float = 0.0
    pending_inbound: int = 0
    pending_outbound: int = 0
    stockout_count: int = 0
    units_sold_cumulative: int = 0

    @property
    def effective_stock(self) -> int:
        """Effective stock considering inbound and committed outbound transfers."""
        return self.current_stock + self.pending_inbound - self.pending_outbound

    @property
    def status(self) -> NodeStatus:
        eff = self.effective_stock
        if eff <= 0:
            return NodeStatus.CRITICAL_STOCKOUT
        elif eff <= self.safety_stock:
            return NodeStatus.DEFICIT
        elif eff <= self.reorder_point:
            return NodeStatus.WARNING
        return NodeStatus.OPTIMAL


class ShockEvent(BaseModel):
    shock_id: str
    title: str
    raw_text: str
    target_region: str  # e.g., 'node_north', 'node_west', or 'all'
    target_sku: str     # e.g., 'SKU-PHONE', or 'all'
    demand_multiplier: float = 1.0  # Multiplier applied to daily demand (e.g. 3.0 = 300% surge)
    duration_ticks: int = 3
    remaining_ticks: int = 3
    created_at_tick: int = 0
    ai_reasoning: Optional[str] = None


class TransferProposal(BaseModel):
    proposal_id: str
    from_node: str
    to_node: str
    sku_id: str
    quantity: int
    freight_cost: float
    eta_ticks: int
    status: ProposalStatus = ProposalStatus.PROPOSED
    agent_rationale: str = ""
    created_at_tick: int
    delivered_at_tick: Optional[int] = None


class BrokerMessage(BaseModel):
    message_id: str
    channel: str       # e.g., 'telemetry', 'shocks', 'p2p_negotiation', 'central_allocations'
    sender_id: str
    timestamp: float = Field(default_factory=time.time)
    tick: int = 0
    payload: Dict[str, Any]
    simulated_latency_ms: int = 0


class NodeTelemetry(BaseModel):
    node_id: str
    node_name: str
    tick: int
    overall_status: NodeStatus
    inventory: Dict[str, InventoryItem]
    active_shocks: List[str] = []
    incoming_transfers_count: int = 0
    outgoing_transfers_count: int = 0

