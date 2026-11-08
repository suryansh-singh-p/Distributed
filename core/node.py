"""
Regional Warehouse Node Implementation.
Represents an autonomous, distributed fulfillment center with partitioned local state,
local demand simulation, burn rate monitoring, and peer-to-peer rebalancing logic.
"""

import random
import uuid
from typing import Dict, List, Optional, Any
from config import SKU_CATALOG, TRANSIT_MATRIX, SIMULATION_CONFIG
from core.models import (
    InventoryItem,
    NodeStatus,
    ProposalStatus,
    TransferProposal,
    ShockEvent,
    NodeTelemetry,
    BrokerMessage
)
from core.broker import DistributedMessageBroker


class RegionalWarehouseNode:
    """
    An independent regional warehouse node operating on its own partitioned inventory data.
    Does not have direct shared memory access to other nodes; communicates exclusively via the message broker.
    """
    def __init__(self, node_id: str, name: str, broker: DistributedMessageBroker):
        self.node_id = node_id
        self.name = name
        self.broker = broker
        
        # Partitioned local inventory state: sku_id -> InventoryItem
        self.inventory: Dict[str, InventoryItem] = {}
        self._init_inventory()

        # Local active shock events impacting this node
        self.active_shocks: List[ShockEvent] = []

        # Local transfer tracking
        self.inbound_transfers: List[TransferProposal] = []
        self.outbound_transfers: List[TransferProposal] = []

        # Performance analytics
        self.total_lost_sales_units: int = 0
        self.total_revenue: float = 0.0
        self.total_freight_paid: float = 0.0

        # Subscribe to broker channels
        self.broker.subscribe("shocks", self.handle_shock_broadcast)
        self.broker.subscribe("p2p_negotiation", self.handle_p2p_message)
        self.broker.subscribe("central_allocations", self.handle_central_allocation)

    def _init_inventory(self) -> None:
        """Initialize local inventory state based on SKU catalog baseline configuration."""
        for sku_id, config in SKU_CATALOG.items():
            self.inventory[sku_id] = InventoryItem(
                sku_id=sku_id,
                name=config["name"],
                current_stock=config["default_initial_stock"],
                safety_stock=config["safety_stock"],
                reorder_point=config["reorder_point"],
                daily_burn_rate=float(config["base_daily_demand"]),
            )

    @property
    def overall_status(self) -> NodeStatus:
        """Compute the aggregate health of the regional warehouse."""
        statuses = [item.status for item in self.inventory.values()]
        if NodeStatus.CRITICAL_STOCKOUT in statuses:
            return NodeStatus.CRITICAL_STOCKOUT
        elif NodeStatus.DEFICIT in statuses:
            return NodeStatus.DEFICIT
        elif NodeStatus.WARNING in statuses:
            return NodeStatus.WARNING
        return NodeStatus.OPTIMAL

    def step_tick(self, current_tick: int) -> Dict[str, int]:
        """
        Execute one operational cycle (tick / business day) for this node:
        1. Receive delivered inbound transfers.
        2. Clean up expired shocks.
        3. Simulate local customer sales demand with active shocks.
        4. Update local burn rates.
        5. Publish telemetry snapshot.
        """
        # Step 1: Process arriving inbound shipments
        self._receive_inbound_shipments(current_tick)

        # Step 2: Decay shock durations
        self._decay_shocks()

        # Step 3: Consume daily customer orders
        demands_fulfilled = self._consume_daily_demand()

        # Step 4: Broadcast telemetry to broker
        self.publish_telemetry(current_tick)

        return demands_fulfilled

    def _receive_inbound_shipments(self, current_tick: int) -> None:
        """Check for and ingest arriving inbound stock transfers."""
        remaining_inbound = []
        for transfer in self.inbound_transfers:
            if transfer.delivered_at_tick is not None and current_tick >= transfer.delivered_at_tick:
                item = self.inventory[transfer.sku_id]
                item.current_stock += transfer.quantity
                item.pending_inbound = max(0, item.pending_inbound - transfer.quantity)
                transfer.status = ProposalStatus.DELIVERED
                self.broker.register_proposal(transfer)
            else:
                remaining_inbound.append(transfer)
        self.inbound_transfers = remaining_inbound

    def _decay_shocks(self) -> None:
        """Decrease remaining duration for active shock events."""
        active = []
        for shock in self.active_shocks:
            shock.remaining_ticks -= 1
            if shock.remaining_ticks > 0:
                active.append(shock)
        self.active_shocks = active

    def _consume_daily_demand(self) -> Dict[str, int]:
        """Simulate realistic customer orders, applying noise and active shock multipliers."""
        fulfilled_sales = {}
        for sku_id, item in self.inventory.items():
            catalog_cfg = SKU_CATALOG[sku_id]
            base_demand = catalog_cfg["base_daily_demand"]
            
            # Apply normal variance (+/- 15%)
            variance = random.uniform(-SIMULATION_CONFIG["random_demand_variance"], SIMULATION_CONFIG["random_demand_variance"])
            daily_demand = max(1, int(round(base_demand * (1.0 + variance))))

            # Apply active shock multipliers
            for shock in self.active_shocks:
                if shock.target_sku in [sku_id, "all"]:
                    daily_demand = int(round(daily_demand * shock.demand_multiplier))

            # Fulfill demand against available stock
            if item.current_stock >= daily_demand:
                item.current_stock -= daily_demand
                item.units_sold_cumulative += daily_demand
                self.total_revenue += daily_demand * catalog_cfg["unit_price"]
                fulfilled_sales[sku_id] = daily_demand
            else:
                # Stockout condition
                unmet = daily_demand - item.current_stock
                fulfilled_sales[sku_id] = item.current_stock
                self.total_revenue += item.current_stock * catalog_cfg["unit_price"]
                item.units_sold_cumulative += item.current_stock
                item.current_stock = 0
                item.stockout_count += 1
                self.total_lost_sales_units += unmet

            # Update moving average burn rate (EMA alpha = 0.3)
            item.daily_burn_rate = round(0.3 * daily_demand + 0.7 * item.daily_burn_rate, 1)

        return fulfilled_sales

    def evaluate_deficits(self, current_tick: int) -> List[Dict[str, Any]]:
        """
        Identify SKUs requiring replenishment and broadcast RFQ (Request For Quote)
        to peer regional nodes over the p2p_negotiation channel.
        """
        deficits = []
        for sku_id, item in self.inventory.items():
            if item.effective_stock < item.reorder_point:
                target_reorder_qty = (item.safety_stock * 2) - item.effective_stock
                deficits.append({
                    "sku_id": sku_id,
                    "sku_name": item.name,
                    "effective_stock": item.effective_stock,
                    "target_qty": target_reorder_qty,
                    "burn_rate": item.daily_burn_rate
                })
                
                # Broadcast RFQ to peers
                self.broker.publish(
                    channel="p2p_negotiation",
                    sender_id=self.node_id,
                    payload={
                        "action": "RFQ",
                        "requesting_node": self.node_id,
                        "sku_id": sku_id,
                        "needed_qty": target_reorder_qty,
                        "current_effective_stock": item.effective_stock,
                        "safety_stock": item.safety_stock,
                    },
                    tick=current_tick
                )
        return deficits

    def calculate_surplus(self, sku_id: str) -> int:
        """Calculate how many units this node can safely export without endangering local operations."""
        if sku_id not in self.inventory:
            return 0
        item = self.inventory[sku_id]
        # Keep 120% of safety stock reserved for local stability
        reserved = int(item.safety_stock * 1.2)
        surplus = item.effective_stock - reserved
        return max(0, surplus)

    def handle_p2p_message(self, msg: BrokerMessage) -> None:
        """Handle incoming peer-to-peer negotiation messages."""
        payload = msg.payload
        action = payload.get("action")

        # Ignore messages sent by self
        if msg.sender_id == self.node_id:
            return

        if action == "RFQ":
            # Peer is requesting stock. Evaluate if we have excess to share
            sku_id = payload.get("sku_id")
            needed_qty = payload.get("needed_qty", 0)
            requesting_node = payload.get("requesting_node")

            surplus = self.calculate_surplus(sku_id)
            if surplus > 0:
                offered_qty = min(needed_qty, surplus)
                transit_info = TRANSIT_MATRIX.get((self.node_id, requesting_node), {"transit_ticks": 2, "freight_cost_per_unit": 15.0})
                total_freight = offered_qty * transit_info["freight_cost_per_unit"]

                # Publish proposal offer back to the network
                proposal_id = f"prop_{uuid.uuid4().hex[:6]}"
                proposal = TransferProposal(
                    proposal_id=proposal_id,
                    from_node=self.node_id,
                    to_node=requesting_node,
                    sku_id=sku_id,
                    quantity=offered_qty,
                    freight_cost=total_freight,
                    eta_ticks=transit_info["transit_ticks"],
                    status=ProposalStatus.PROPOSED,
                    agent_rationale=f"Node {self.name} offers {offered_qty} units of {sku_id} (surplus available: {surplus}).",
                    created_at_tick=msg.tick
                )
                self.broker.register_proposal(proposal)

                self.broker.publish(
                    channel="p2p_negotiation",
                    sender_id=self.node_id,
                    payload={
                        "action": "QUOTE_OFFER",
                        "proposal": proposal.model_dump(),
                    },
                    tick=msg.tick
                )

        elif action == "QUOTE_OFFER":
            # Another node responded to our RFQ with an offer
            prop_data = payload.get("proposal", {})
            if prop_data.get("to_node") == self.node_id:
                self._evaluate_and_accept_proposal(prop_data, msg.tick)

        elif action == "PROPOSAL_ACCEPTED":
            # Another node accepted our quote offer. Commit outbound stock!
            prop_data = payload.get("proposal", {})
            if prop_data.get("from_node") == self.node_id:
                self._commit_outbound_transfer(prop_data)

    def _evaluate_and_accept_proposal(self, prop_data: Dict[str, Any], current_tick: int) -> None:
        """Evaluate peer quote offer and execute acceptance."""
        sku_id = prop_data.get("sku_id")
        qty = prop_data.get("quantity", 0)
        item = self.inventory[sku_id]

        # If we still need inventory, accept the offer
        if item.effective_stock < item.reorder_point:
            proposal = TransferProposal(**prop_data)
            proposal.status = ProposalStatus.IN_TRANSIT
            proposal.delivered_at_tick = current_tick + proposal.eta_ticks
            
            # Commit inbound
            item.pending_inbound += qty
            self.inbound_transfers.append(proposal)
            self.total_freight_paid += proposal.freight_cost
            self.broker.register_proposal(proposal)

            # Broadcast acceptance to sender node
            self.broker.publish(
                channel="p2p_negotiation",
                sender_id=self.node_id,
                payload={
                    "action": "PROPOSAL_ACCEPTED",
                    "proposal": proposal.model_dump(),
                },
                tick=current_tick
            )

    def _commit_outbound_transfer(self, prop_data: Dict[str, Any]) -> None:
        """Deduct stock from current inventory to dispatch peer transfer."""
        sku_id = prop_data.get("sku_id")
        qty = prop_data.get("quantity", 0)
        item = self.inventory[sku_id]
        
        # Deduct physical stock
        item.current_stock = max(0, item.current_stock - qty)
        
        proposal = TransferProposal(**prop_data)
        proposal.status = ProposalStatus.IN_TRANSIT
        self.outbound_transfers.append(proposal)
        self.broker.register_proposal(proposal)

    def handle_central_allocation(self, msg: BrokerMessage) -> None:
        """Receive replenishment stock dispatched by the Central Supplier."""
        allocations = msg.payload.get("allocations", {})
        if self.node_id in allocations:
            for sku_id, qty in allocations[self.node_id].items():
                if sku_id in self.inventory and qty > 0:
                    transit_info = TRANSIT_MATRIX.get(("central_supplier", self.node_id), {"transit_ticks": 2, "freight_cost_per_unit": 15.0})
                    proposal = TransferProposal(
                        proposal_id=f"central_{uuid.uuid4().hex[:6]}",
                        from_node="central_supplier",
                        to_node=self.node_id,
                        sku_id=sku_id,
                        quantity=qty,
                        freight_cost=qty * transit_info["freight_cost_per_unit"],
                        eta_ticks=transit_info["transit_ticks"],
                        status=ProposalStatus.IN_TRANSIT,
                        agent_rationale=msg.payload.get("rationale", "Central replenishment"),
                        created_at_tick=msg.tick,
                        delivered_at_tick=msg.tick + transit_info["transit_ticks"]
                    )
                    self.inventory[sku_id].pending_inbound += qty
                    self.inbound_transfers.append(proposal)
                    self.broker.register_proposal(proposal)

    def handle_shock_broadcast(self, msg: BrokerMessage) -> None:
        """Receive demand/supply shock notification broadcast by the broker."""
        shock_data = msg.payload.get("shock")
        if shock_data:
            shock = ShockEvent(**shock_data)
            if shock.target_region in [self.node_id, "all"]:
                # Check if not already added
                if not any(s.shock_id == shock.shock_id for s in self.active_shocks):
                    self.active_shocks.append(shock)

    def publish_telemetry(self, current_tick: int) -> None:
        """Publish real-time telemetry snapshot to the broker."""
        telemetry = NodeTelemetry(
            node_id=self.node_id,
            node_name=self.name,
            tick=current_tick,
            overall_status=self.overall_status,
            inventory={k: v.model_copy() for k, v in self.inventory.items()},
            active_shocks=[s.shock_id for s in self.active_shocks],
            incoming_transfers_count=len(self.inbound_transfers),
            outgoing_transfers_count=len(self.outbound_transfers)
        )
        self.broker.publish(
            channel="telemetry",
            sender_id=self.node_id,
            payload={"telemetry": telemetry},
            tick=current_tick
        )
