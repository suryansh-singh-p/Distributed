"""
Streamlit Interactive Dashboard for DistriDemand-LLM.
Multi-Agent Distributed E-Commerce Demand-Supply Analytics & Autonomous Rebalancing.
"""

import streamlit as st
import pandas as pd
import time
from config import REGIONS, SKU_CATALOG, CENTRAL_SUPPLIER
from simulation.engine import SimulationEngine
from simulation.scenarios import SCENARIO_CATALOG
from core.models import NodeStatus, ProposalStatus

# Page configuration
st.set_page_config(
    page_title="DistriDemand-LLM | Distributed Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.1rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.2rem;
    }
    .metric-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 12px 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .node-card {
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 14px;
        border: 1px solid #CBD5E1;
        background: #FFFFFF;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    .badge-optimal { background-color: #DEF7EC; color: #03543F; padding: 3px 8px; border-radius: 12px; font-weight: 600; font-size: 0.8rem; }
    .badge-warning { background-color: #FEF08A; color: #854D0E; padding: 3px 8px; border-radius: 12px; font-weight: 600; font-size: 0.8rem; }
    .badge-deficit { background-color: #FED7AA; color: #9A3412; padding: 3px 8px; border-radius: 12px; font-weight: 600; font-size: 0.8rem; }
    .badge-critical { background-color: #FEE2E2; color: #991B1B; padding: 3px 8px; border-radius: 12px; font-weight: 600; font-size: 0.8rem; }
    .agent-bubble {
        background-color: #F8FAFC;
        border-left: 5px solid #2563EB;
        padding: 14px 18px;
        border-radius: 6px;
        margin-bottom: 14px;
        word-break: break-word;
        overflow-wrap: anywhere;
        white-space: pre-wrap;
        line-height: 1.6;
        font-size: 0.95rem;
    }
    .ledger-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 5px solid #3B82F6;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        word-break: break-word;
        overflow-wrap: anywhere;
        white-space: pre-wrap;
        line-height: 1.6;
    }
    /* Ensure Streamlit table cells wrap text */
    [data-testid="stDataFrame"] td {
        white-space: normal !important;
        word-break: break-word !important;
    }
</style>
""", unsafe_allow_html=True)


# Initialize Session State
if "sim" not in st.session_state:
    st.session_state.sim = SimulationEngine(provider="auto")
if "last_shock" not in st.session_state:
    st.session_state.last_shock = None

sim: SimulationEngine = st.session_state.sim


# Sidebar: Control Panel & Configuration
with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/network.png", width=60)
    st.title("Control Center")
    st.caption("Distributed Analytics Orchestrator")

    st.divider()

    # Step Advance Controls
    st.subheader("⏱️ Simulation Clock")
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        if st.button("▶️ +1 Day", use_container_width=True):
            sim.step()
            st.rerun()
    with col_btn2:
        if st.button("⏩ +3 Days", use_container_width=True):
            for _ in range(3):
                sim.step()
            st.rerun()
    with col_btn3:
        if st.button("🔄 Reset", use_container_width=True):
            sim.reset()
            st.session_state.last_shock = None
            st.rerun()

    st.caption(f"Current Clock: **Day {sim.current_tick}**")

    st.divider()

    # Pre-packaged Scenarios
    st.subheader("⚡ Demand-Supply Shocks")
    scenario_keys = list(SCENARIO_CATALOG.keys())
    scenario_titles = [SCENARIO_CATALOG[k]["title"] for k in scenario_keys]
    selected_title = st.selectbox("Select Scenario Preset", scenario_titles)
    selected_scenario = next(s for s in SCENARIO_CATALOG.values() if s["title"] == selected_title)

    st.info(f"**{selected_scenario['headline']}**\n\n{selected_scenario['description']}")

    if st.button("🚨 Inject Selected Shock", use_container_width=True):
        shock = sim.inject_shock(raw_text=selected_scenario["raw_text"], title=selected_scenario["title"])
        st.session_state.last_shock = shock
        st.success(f"Injected: {shock.title}!")
        st.rerun()

    st.divider()

    # Custom Unstructured Signal Injector
    st.subheader("🧠 Custom Text Signal (LLM)")
    custom_text = st.text_area(
        "Enter Raw Market News / Tweets / Alerts:",
        placeholder="e.g. Blizzard in North causes 4x spike in Winter Jacket orders...",
        height=85
    )
    if st.button("Extract & Inject via LLM", use_container_width=True) and custom_text.strip():
        shock = sim.inject_shock(raw_text=custom_text.strip(), title="Custom Market Signal")
        st.session_state.last_shock = shock
        st.success(f"LLM extracted shock: {shock.target_sku} @ {shock.target_region} ({shock.demand_multiplier}x)")
        st.rerun()

    st.divider()

    # Optional API Settings
    with st.expander("🤖 LLM Engine Settings", expanded=True):
        provider_choice = st.selectbox(
            "Provider",
            ["ollama", "auto", "gemini", "openai", "offline"],
            index=0,
            help="Select Local Ollama, Cloud API, or Offline Fallback."
        )
        ollama_model_name = sim.llm_engine.ollama_model
        if provider_choice in ["ollama", "auto"]:
            ollama_model_name = st.text_input("Local Ollama Model", value=sim.llm_engine.ollama_model)
            st.caption("🟢 Local Ollama connected at `http://127.0.0.1:11434`")

        api_key_input = None
        if provider_choice in ["gemini", "openai"]:
            api_key_input = st.text_input("Cloud API Key", type="password")

        if st.button("Apply LLM Config", use_container_width=True):
            sim.set_api_key(
                api_key=api_key_input if api_key_input else None,
                provider=provider_choice,
                ollama_model=ollama_model_name
            )
            st.success(f"Configured: {sim.llm_engine.provider.upper()}")
            st.rerun()


# Top Main Header
model_display = sim.llm_engine.ollama_model.split(":")[0] if sim.llm_engine.provider == "ollama" else sim.llm_engine.provider.upper()
st.markdown('<div class="main-header">⚡ DistriDemand-LLM: Distributed E-Commerce Analytics</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="sub-header">Multi-Agent Regional Inventory Rebalancing, Asynchronous Pub/Sub & Autonomous LLM Demand Sensing &bull; <span style="background-color:#E0E7FF; color:#3730A3; padding:2px 8px; border-radius:10px; font-weight:600; font-size:0.85rem;">🧠 LLM: {sim.llm_engine.provider.upper()} ({model_display})</span></div>',
    unsafe_allow_html=True
)

# KPI Summary Row
kpis = sim.get_kpis()
col_kpi1, col_kpi2, col_kpi3, col_kpi4, col_kpi5 = st.columns(5)

with col_kpi1:
    fill_rate = kpis.get("fill_rate", 100.0)
    st.metric("Global Fill Rate", f"{fill_rate:.1f}%", delta=f"{fill_rate - 100.0:.1f}%" if fill_rate < 100 else "Optimal")

with col_kpi2:
    st.metric("Units Delivered / In-Transit", f"{kpis.get('total_rebalanced_units', 0):,} units", delta=f"{kpis.get('active_transfers', 0)} active routes")

with col_kpi3:
    st.metric("Cumulative Sales", f"{kpis.get('total_sold', 0):,} units")

with col_kpi4:
    st.metric("Lost Sales (Stockouts)", f"{kpis.get('total_lost', 0):,} units", delta_color="inverse", delta=f"-{kpis.get('total_lost', 0)}")

with col_kpi5:
    st.metric("Est. Revenue Preserved", f"${kpis.get('estimated_saved_rev', 0):,.0f}", delta=f"Freight: -${kpis.get('total_freight_cost', 0):,.0f}")

st.write("")

# Main Content Tabs
tab_map, tab_agents, tab_analytics, tab_ledger = st.tabs([
    "🗺️ Regional Warehouses & Topology",
    "🤖 Multi-Agent Dialogue & LLM Rationale",
    "📈 Distributed Analytics & Trends",
    "📜 Broker Audit Ledger (Pub/Sub)"
])


def generate_topology_dot(sim_instance: SimulationEngine) -> str:
    """Generate Graphviz DOT string for live network topology and in-transit transfers."""
    status_colors = {
        NodeStatus.OPTIMAL: "#DEF7EC",
        NodeStatus.WARNING: "#FEF08A",
        NodeStatus.DEFICIT: "#FED7AA",
        NodeStatus.CRITICAL_STOCKOUT: "#FEE2E2",
    }
    status_borders = {
        NodeStatus.OPTIMAL: "#10B981",
        NodeStatus.WARNING: "#F59E0B",
        NodeStatus.DEFICIT: "#EA580C",
        NodeStatus.CRITICAL_STOCKOUT: "#DC2626",
    }

    dot_lines = [
        "digraph NetworkTopology {",
        '  rankdir="TB";',
        '  node [shape="box", style="filled,rounded", fontname="sans-serif", fontsize=10];',
        '  edge [fontname="sans-serif", fontsize=9];',
        '  bgcolor="transparent";',
        '  central_supplier [label="🏢 Central Factory Supplier\\n(Global Buffer Reserves)", fillcolor="#EFF6FF", color="#2563EB", penwidth=2.2];'
    ]

    for node_id, node in sim_instance.nodes.items():
        st_val = node.overall_status
        bg = status_colors.get(st_val, "#FFFFFF")
        border = status_borders.get(st_val, "#64748B")
        total_stk = sum(i.current_stock for i in node.inventory.values())
        lbl = f"🏭 {node.name.split(' (')[0]}\\n[{st_val.value}]\\nTotal: {total_stk} units"
        dot_lines.append(f'  {node_id} [label="{lbl}", fillcolor="{bg}", color="{border}", penwidth=2];')

    # Baseline connections
    for node_id in sim_instance.nodes.keys():
        dot_lines.append(f'  central_supplier -> {node_id} [style="dotted", color="#CBD5E1", arrowhead="none", weight=1];')

    # Active Transfers
    active = [p for p in sim_instance.broker.active_proposals.values() if p.status == ProposalStatus.IN_TRANSIT]
    if active:
        for tr in active:
            lbl = f"🚚 {tr.sku_id}: {tr.quantity}u\\n(ETA: {tr.eta_ticks}d)"
            dot_lines.append(f'  {tr.from_node} -> {tr.to_node} [label="{lbl}", color="#2563EB", penwidth=2.5, fontcolor="#1E40AF", weight=3];')

    dot_lines.append("}")
    return "\n".join(dot_lines)


# ==========================================
# TAB 1: REGIONAL WAREHOUSE GRID & TOPOLOGY
# ==========================================
with tab_map:
    st.markdown("#### 🌐 Live Distributed Network Topology & In-Transit Flows")
    st.caption("Visualizes partitioned regional nodes, health status, and active inter-node transfer pipelines.")
    st.graphviz_chart(generate_topology_dot(sim))

    st.divider()

    st.markdown("#### 🏭 Partitioned Regional Fulfillment Nodes")
    st.caption("Each node maintains an independent local state. No shared memory; all coordination occurs via the broker.")

    cols_nodes = st.columns(4)

    for idx, (node_id, node) in enumerate(sim.nodes.items()):
        cfg = REGIONS[node_id]
        status = node.overall_status

        badge_class = {
            NodeStatus.OPTIMAL: "badge-optimal",
            NodeStatus.WARNING: "badge-warning",
            NodeStatus.DEFICIT: "badge-deficit",
            NodeStatus.CRITICAL_STOCKOUT: "badge-critical",
        }.get(status, "badge-optimal")

        with cols_nodes[idx]:
            st.markdown(f"""
            <div class="node-card" style="border-top: 5px solid {cfg['color']};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <b style="font-size: 1rem;">{node.name.split(' (')[0]}</b>
                    <span class="{badge_class}">{status.value}</span>
                </div>
                <div style="font-size: 0.8rem; color: #64748B; margin-bottom: 12px;">📍 {node.name.split(' (')[1].replace(')', '')}</div>
            """, unsafe_allow_html=True)

            # Display stock for each SKU
            for sku_id, item in node.inventory.items():
                cat = SKU_CATALOG[sku_id]
                pct = min(100, int((item.effective_stock / (cat["default_initial_stock"] * 1.5)) * 100))
                
                # Inbound tag if stock on the way
                inbound_tag = f" (+{item.pending_inbound} 🚚)" if item.pending_inbound > 0 else ""
                
                st.write(f"**{cat['name']}**: {item.current_stock}{inbound_tag}")
                st.progress(pct / 100.0)
                st.caption(f"Burn: {item.daily_burn_rate:.1f}/day | Safety: {item.safety_stock}")

            # Active Transfers info
            st.markdown(f"""
                <hr style="margin: 8px 0;"/>
                <div style="font-size: 0.75rem; color: #475569;">
                    🚚 Inbound: <b>{len(node.inbound_transfers)}</b> | Outbound: <b>{len(node.outbound_transfers)}</b>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Central Supplier Hub Status
    st.markdown("#### 🏢 Central Factory Supplier Reserves (Global Buffer)")
    res_cols = st.columns(4)
    for idx, (sku_id, qty) in enumerate(sim.central_hub.stock_reserves.items()):
        with res_cols[idx]:
            st.metric(f"Reserve {SKU_CATALOG[sku_id]['name']}", f"{qty:,} units", delta="Factory Buffer")


# ==========================================
# TAB 2: AGENT DIALOGUE & EXPLAINABILITY
# ==========================================
with tab_agents:
    st.markdown("#### 🤖 Autonomous Agent Dialogue & Explainable AI Audit")
    st.caption("Inspect live negotiations, unstructured demand-sensing telemetry, and Central Arbiter trade-offs.")

    if not sim.agent_dialogues:
        st.info("No agent dialogues recorded yet. Advance a day or inject a demand shock to trigger autonomous agent reasoning.")
    else:
        for entry in reversed(sim.agent_dialogues[-12:]):
            icon = "📡" if entry["type"] == "DEMAND_SENSING" else "⚖️"
            st.markdown(f"""
            <div class="agent-bubble">
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <b style="color: #1E40AF;">{icon} {entry['speaker']} (Day {entry['tick']})</b>
                    <span style="font-size: 0.8rem; color: #64748B;">{entry['title']}</span>
                </div>
                <div style="font-size: 0.9rem; white-space: pre-line; color: #1F2937;">{entry['content']}</div>
            </div>
            """, unsafe_allow_html=True)


# ==========================================
# TAB 3: DISTRIBUTED ANALYTICS & TRENDS
# ==========================================
with tab_analytics:
    st.markdown("#### 📈 Multi-Node Time-Series Telemetry")
    
    if len(sim.history) > 1:
        # Build dataframe for inventory trajectory
        records = []
        for snap in sim.history:
            tick = snap["tick"]
            for node_id, data in snap["regional_stocks"].items():
                for sku, qty in data["skus"].items():
                    records.append({
                        "Day": tick,
                        "Region": REGIONS[node_id]["name"].split(" (")[0],
                        "SKU": SKU_CATALOG[sku]["name"],
                        "Stock": qty
                    })
        df_trends = pd.DataFrame(records)

        # SKU Selector
        sku_to_plot = st.selectbox("Select SKU to Visualize", [s["name"] for s in SKU_CATALOG.values()])
        df_filtered = df_trends[df_trends["SKU"] == sku_to_plot]

        # Line chart across regions
        chart_data = df_filtered.pivot(index="Day", columns="Region", values="Stock")
        st.line_chart(chart_data)

        # Fill rate & Sales Chart
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown("##### Global Fill Rate %")
            df_perf = pd.DataFrame([{"Day": s["tick"], "Fill Rate (%)": s["fill_rate"]} for s in sim.history]).set_index("Day")
            st.line_chart(df_perf)
        with col_c2:
            st.markdown("##### Cumulative Sales vs. Lost Units")
            df_sales = pd.DataFrame([{"Day": s["tick"], "Units Sold": s["total_sold"], "Lost Sales": s["total_lost"]} for s in sim.history]).set_index("Day")
            st.bar_chart(df_sales)

        # Cross-Regional Transfer Volume Matrix
        st.divider()
        st.markdown("##### 🔄 Inter-Node P2P Transfer Matrix (Volume in Units)")
        st.caption("Quantifies peer-to-peer inventory rebalanced bilaterally across distributed regional nodes.")
        
        transfer_matrix = {n1: {n2: 0 for n2 in sim.nodes.keys()} for n1 in sim.nodes.keys()}
        for p in sim.broker.active_proposals.values():
            if p.from_node in transfer_matrix and p.to_node in transfer_matrix[p.from_node]:
                transfer_matrix[p.from_node][p.to_node] += p.quantity

        df_matrix = pd.DataFrame(transfer_matrix).T
        df_matrix.columns = [REGIONS[c]["name"].split(" (")[0] for c in df_matrix.columns]
        df_matrix.index = [REGIONS[r]["name"].split(" (")[0] for r in df_matrix.index]
        st.dataframe(df_matrix, use_container_width=True)

    else:
        st.info("Advance the simulation at least 2 days to generate time-series trend lines.")


def format_payload_summary(msg) -> str:
    """Produce clean, complete, un-truncated descriptions of broker message payloads."""
    p = msg.payload
    ch = msg.channel

    if ch == "telemetry":
        tel = p.get("telemetry")
        if tel:
            status = getattr(tel, "overall_status", None)
            st_val = getattr(status, "value", str(status)) if status else "OPTIMAL"
            inv = getattr(tel, "inventory", {})
            sku_summaries = []
            if isinstance(inv, dict):
                for s_id, item in inv.items():
                    c_stk = getattr(item, "current_stock", 0)
                    burn = getattr(item, "daily_burn_rate", 0.0)
                    inb = getattr(item, "pending_inbound", 0)
                    inb_str = f" (+{inb}🚚)" if inb > 0 else ""
                    sku_summaries.append(f"{s_id}: {c_stk}u{inb_str} (burn {burn:.1f}/d)")
            inbound = getattr(tel, "incoming_transfers_count", 0)
            return f"Overall Status: {st_val} | Inventory: [{', '.join(sku_summaries)}] | Inbound Routes: {inbound}"
        return "Regional Node Telemetry Heartbeat"

    elif ch == "shocks":
        shock = p.get("shock", {})
        if hasattr(shock, "model_dump"):
            shock = shock.model_dump()
        sku = shock.get("target_sku", "All")
        reg = shock.get("target_region", "All")
        mult = shock.get("demand_multiplier", 1.0)
        dur = shock.get("duration_ticks", 3)
        reason = shock.get("ai_reasoning", "")
        return f"⚡ Demand Shock Injected: {mult}x multiplier for {sku} in {reg} (Duration: {dur} days). Rationale: {reason}"

    elif ch == "p2p_negotiation":
        action = p.get("action")
        if action == "RFQ":
            return f"📢 RFQ Broadcast: Node '{p.get('requesting_node')}' has deficit of {p.get('needed_qty')} units for {p.get('sku_id')} (Effective Stock: {p.get('current_effective_stock')}, Safety: {p.get('safety_stock')})"
        elif action == "QUOTE_OFFER":
            prop = p.get("proposal", {})
            return f"🤝 Bilateral Quote Offer: Node '{prop.get('from_node')}' offers {prop.get('quantity')} units of {prop.get('sku_id')} to '{prop.get('to_node')}' (Freight: ${prop.get('freight_cost', 0):.2f}, ETA: {prop.get('eta_ticks')} day(s)). Agent Rationale: {prop.get('agent_rationale', '')}"
        elif action == "PROPOSAL_ACCEPTED":
            prop = p.get("proposal", {})
            return f"✅ Agreement Finalized: Node '{prop.get('to_node')}' accepted transfer of {prop.get('quantity')} units of {prop.get('sku_id')} from '{prop.get('from_node')}'. Stock committed to transit."
        return f"P2P Action: {action}"

    elif ch == "central_allocations":
        alloc = p.get("allocations", {})
        parts = []
        if isinstance(alloc, dict):
            for n, skus in alloc.items():
                if isinstance(skus, dict):
                    for s, q in skus.items():
                        parts.append(f"{n} -> +{q} {s}")
                else:
                    parts.append(f"{n} -> +{skus}")
        rat = p.get("rationale", "")
        return f"🏢 Central Factory Buffer Dispatched: [{', '.join(parts)}] | Executive Rationale: {rat}"

    return str(p)


def serialize_payload(val):
    """Recursively convert Pydantic objects and models to JSON serializable dicts."""
    if hasattr(val, "model_dump"):
        return val.model_dump()
    if isinstance(val, dict):
        return {k: serialize_payload(v) for k, v in val.items()}
    if isinstance(val, list):
        return [serialize_payload(item) for item in val]
    if hasattr(val, "value"):
        return val.value
    return val


# ==========================================
# TAB 4: BROKER AUDIT LEDGER
# ==========================================
with tab_ledger:
    st.markdown("#### 📜 Distributed Event Ledger (Append-Only Event Store)")
    st.caption("Complete, verifiable trace of all pub/sub messages passed between regional nodes.")

    # Filter and display mode controls
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        channel_filter = st.selectbox(
            "Filter Channel",
            ["All Channels", "telemetry", "p2p_negotiation", "shocks", "central_allocations"]
        )
    with col_f2:
        view_mode = st.radio(
            "View Mode",
            ["📋 Full Detail Event Feed (Word-Wrapped, Zero Truncation)", "📊 Data Table View"],
            horizontal=True
        )

    all_msgs = sim.broker.ledger
    if channel_filter != "All Channels":
        all_msgs = [m for m in all_msgs if m.channel == channel_filter]

    recent_msgs = list(reversed(all_msgs[-40:]))

    if not recent_msgs:
        st.info("No messages recorded for this channel.")
    elif "Full Detail" in view_mode:
        # Full Detail Expandable Cards (Zero truncation, word-wrapped)
        for msg in recent_msgs:
            summary = format_payload_summary(msg)
            channel_icons = {
                "telemetry": "📊",
                "p2p_negotiation": "🤝",
                "shocks": "⚡",
                "central_allocations": "🏢"
            }
            icon = channel_icons.get(msg.channel, "✉️")
            with st.expander(f"{icon} Day {msg.tick} | [{msg.channel.upper()}] from {msg.sender_id} ({msg.simulated_latency_ms} ms)", expanded=(msg.channel != "telemetry")):
                st.markdown(f"**Event Summary:**\n\n{summary}")
                st.caption(f"Message ID: `{msg.message_id}` | Timestamp: `{time.strftime('%H:%M:%S', time.localtime(msg.timestamp))}`")
                with st.expander("🔍 View Raw JSON Payload"):
                    st.json(serialize_payload(msg.payload))
    else:
        # Compact Table View with full column widths
        ledger_records = []
        for msg in recent_msgs:
            ledger_records.append({
                "Msg ID": msg.message_id,
                "Day": msg.tick,
                "Channel": msg.channel,
                "Sender": msg.sender_id,
                "Payload Summary": format_payload_summary(msg),
                "Latency": f"{msg.simulated_latency_ms} ms"
            })
        df_ledger = pd.DataFrame(ledger_records)
        st.dataframe(
            df_ledger,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Payload Summary": st.column_config.TextColumn("Payload Summary", width="large")
            }
        )

    # Export Audit Report Button
    st.divider()
    st.markdown("##### 📥 Export Formal Audit Report")
    st.caption("Generate a signed markdown report detailing all simulation transactions and LLM decisions.")
    
    report_text = f"""# DistriDemand-LLM: Simulation Audit Report
**Simulation Day:** {sim.current_tick}  
**Active LLM Engine:** {sim.llm_engine.provider.upper()} ({sim.llm_engine.ollama_model})  
**Generated Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S')}

---

## 1. Executive Performance Metrics
- **Global Network Fill Rate:** {kpis.get('fill_rate', 100.0):.1f}%
- **Cumulative Units Sold:** {kpis.get('total_sold', 0):,} units
- **Total Lost Sales (Stockouts):** {kpis.get('total_lost', 0):,} units
- **Total Autonomous Rebalanced Units:** {kpis.get('total_rebalanced_units', 0):,} units
- **Estimated Stockout Revenue Preserved:** ${kpis.get('estimated_saved_rev', 0):,.2f}
- **Total Freight Logistics Cost Paid:** ${kpis.get('total_freight_cost', 0):,.2f}

---

## 2. Distributed Node Status Summary
"""
    for node_id, node in sim.nodes.items():
        report_text += f"\n### Node: {node.name}\n- Status: {node.overall_status.value}\n- Inbound Transfers: {len(node.inbound_transfers)}\n- Outbound Transfers: {len(node.outbound_transfers)}\n"
        for sku_id, it in node.inventory.items():
            report_text += f"  * {it.name}: Current Stock={it.current_stock}, Burn Rate={it.daily_burn_rate:.1f}/day\n"

    report_text += f"""
---

## 3. Distributed Broker Telemetry
- **Total Message Ledger Events:** {len(sim.broker.ledger)}
- **Total P2P Proposals Tracked:** {len(sim.broker.active_proposals)}
"""

    st.download_button(
        label="📄 Download Audit Report (Markdown)",
        data=report_text,
        file_name=f"distridemand_audit_day_{sim.current_tick}.md",
        mime="text/markdown",
        use_container_width=True
    )

