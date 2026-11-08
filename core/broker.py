"""
Distributed Message Broker for DistriDemand-LLM.
Simulates an asynchronous pub/sub event bus with partitioned topics, network latency, and an append-only distributed ledger.
"""

import uuid
import time
from typing import Dict, List, Callable, Optional, Any
from core.models import BrokerMessage, NodeTelemetry, TransferProposal


class DistributedMessageBroker:
    """
    Simulates a distributed event broker (similar to Apache Kafka or RabbitMQ)
    with channels, subscriber callbacks, and an append-only audit ledger.
    """
    def __init__(self):
        # Channel subscribers: channel_name -> list of callback functions
        self._subscribers: Dict[str, List[Callable[[BrokerMessage], None]]] = {
            "telemetry": [],
            "shocks": [],
            "p2p_negotiation": [],
            "central_allocations": [],
            "general_broadcast": [],
        }
        
        # Append-only persistent distributed ledger
        self.ledger: List[BrokerMessage] = []
        
        # Latest telemetry snapshot from each node
        self.latest_telemetry: Dict[str, NodeTelemetry] = {}
        
        # Active transfer proposals currently in transit or being negotiated
        self.active_proposals: Dict[str, TransferProposal] = {}

    def subscribe(self, channel: str, callback: Callable[[BrokerMessage], None]) -> None:
        """Subscribe a regional node or orchestrator callback to a specific channel."""
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        self._subscribers[channel].append(callback)

    def publish(
        self,
        channel: str,
        sender_id: str,
        payload: Dict[str, Any],
        tick: int = 0,
        simulated_latency_ms: int = 20
    ) -> BrokerMessage:
        """
        Publish a message to a channel. Records to the immutable ledger
        and dispatches to all subscribed node listeners.
        """
        msg = BrokerMessage(
            message_id=f"msg_{uuid.uuid4().hex[:8]}",
            channel=channel,
            sender_id=sender_id,
            timestamp=time.time(),
            tick=tick,
            payload=payload,
            simulated_latency_ms=simulated_latency_ms
        )

        # Append to distributed ledger
        self.ledger.append(msg)

        # Update cache if this is telemetry
        if channel == "telemetry" and "telemetry" in payload:
            telemetry_data = payload["telemetry"]
            if isinstance(telemetry_data, NodeTelemetry):
                self.latest_telemetry[sender_id] = telemetry_data

        # Dispatch to subscribers
        if channel in self._subscribers:
            for callback in self._subscribers[channel]:
                try:
                    callback(msg)
                except Exception as e:
                    print(f"[Broker Error] Failed to dispatch message {msg.message_id} on channel {channel}: {e}")

        return msg

    def register_proposal(self, proposal: TransferProposal) -> None:
        """Register or update an active inter-node transfer proposal."""
        self.active_proposals[proposal.proposal_id] = proposal

    def get_ledger_history(self, limit: int = 50, channel: Optional[str] = None) -> List[BrokerMessage]:
        """Fetch the most recent events from the append-only ledger."""
        filtered = self.ledger
        if channel:
            filtered = [m for m in filtered if m.channel == channel]
        return filtered[-limit:]

    def clear(self) -> None:
        """Reset broker state (useful for fresh simulation runs)."""
        self.ledger.clear()
        self.latest_telemetry.clear()
        self.active_proposals.clear()

