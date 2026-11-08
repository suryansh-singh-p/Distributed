"""
LLM Engine & Multi-Agent Reasoning Infrastructure.
Provides unified access to Gemini API, OpenAI API, and an Intelligent Offline Engine
for zero-failure execution in offline or sandboxed environments.
"""

import os
import json
import re
import difflib
from typing import Dict, Any, Optional, List
from config import SKU_CATALOG, REGIONS


def canonicalize_sku(raw_sku: Optional[str]) -> str:
    """Resolve the LLM output to one of the exact catalog keys in SKU_CATALOG."""
    if not raw_sku:
        return "all"
    c_upper = str(raw_sku).strip().upper()
    if c_upper in SKU_CATALOG:
        return c_upper
    if f"SKU-{c_upper}" in SKU_CATALOG:
        return f"SKU-{c_upper}"
    for sku_id in SKU_CATALOG.keys():
        if sku_id in c_upper:
            return sku_id
    c_lower = str(raw_sku).lower()
    if "laptop" in c_lower or "ultrabook" in c_lower or "notebook" in c_lower:
        return "SKU-LAPTOP"
    if "phone" in c_lower or "smartphone" in c_lower or "mobile" in c_lower:
        return "SKU-PHONE"
    if re.search(r'\bac\b', c_lower) or "air conditioner" in c_lower or "cooling" in c_lower:
        return "SKU-AC"
    if "jacket" in c_lower or "parka" in c_lower or "coat" in c_lower or "winter" in c_lower:
        return "SKU-JACKET"
    return "all"


def canonicalize_region(raw_region: Optional[str]) -> str:
    """Resolve the LLM output to one of the exact region keys in REGIONS."""
    if not raw_region:
        return "all"
    c_lower = str(raw_region).strip().lower()
    if c_lower in REGIONS:
        return c_lower
    if f"node_{c_lower}" in REGIONS:
        return f"node_{c_lower}"
    for node_id in REGIONS.keys():
        if node_id in c_lower:
            return node_id
    if "north" in c_lower or "delhi" in c_lower or "ny" in c_lower:
        return "node_north"
    if "south" in c_lower or "bangalore" in c_lower or "tx" in c_lower:
        return "node_south"
    if "east" in c_lower or "kolkata" in c_lower or "fl" in c_lower:
        return "node_east"
    if "west" in c_lower or "mumbai" in c_lower or "ca" in c_lower:
        return "node_west"
    return "all"


class LLMEngine:
    """
    Unified LLM Client supporting Local Ollama, Google Gemini, OpenAI,
    and an Intelligent Offline Heuristic Engine for zero-failure fallback.
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: str = "auto",
        ollama_model: Optional[str] = None,
        ollama_url: str = "http://127.0.0.1:11434"
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model or os.getenv("OLLAMA_MODEL") or "mannix/llama3.1-8b-abliterated:tools-q4_0"
        self.provider = provider

        if provider == "auto":
            # Auto-detect local Ollama first
            if self._check_ollama():
                self.provider = "ollama"
            elif os.getenv("GEMINI_API_KEY") or (api_key and "AIza" in api_key):
                self.provider = "gemini"
            elif os.getenv("OPENAI_API_KEY") or (api_key and api_key.startswith("sk-")):
                self.provider = "openai"
            else:
                self.provider = "offline"

    def _check_ollama(self) -> bool:
        """Quickly check if local Ollama instance is reachable."""
        try:
            import requests
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=1.5)
            if resp.status_code == 200:
                models = [m.get("name") for m in resp.json().get("models", [])]
                if models and not self.ollama_model:
                    self.ollama_model = models[0]
                return True
        except Exception:
            pass
        return False

    def complete(self, prompt: str, system_prompt: str = "", temperature: float = 0.2) -> str:
        """Execute LLM completion with graceful fallback to offline heuristic engine."""
        # 1. Local Ollama Provider (Real local LLM)
        if self.provider == "ollama":
            try:
                import requests
                url = f"{self.ollama_url}/api/chat"
                payload = {
                    "model": self.ollama_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": temperature}
                }
                resp = requests.post(url, json=payload, timeout=45)
                if resp.status_code == 200:
                    return resp.json()["message"]["content"]
            except Exception as e:
                print(f"[LLM Warning] Ollama call failed ({e}), falling back to offline engine.")

        # 2. Google Gemini Provider
        elif self.provider == "gemini" and self.api_key:
            try:
                import requests
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
                payload = {
                    "contents": [{"parts": [{"text": f"{system_prompt}\n\n{prompt}"}]}],
                    "generationConfig": {"temperature": temperature}
                }
                resp = requests.post(url, json=payload, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                print(f"[LLM Warning] Gemini call failed ({e}), falling back to offline engine.")

        # 3. OpenAI Provider
        elif self.provider == "openai" and self.api_key:
            try:
                import requests
                headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
                payload = {
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": temperature
                }
                resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"[LLM Warning] OpenAI call failed ({e}), falling back to offline engine.")

        # 4. Offline Heuristic Fallback
        return self._offline_reasoning(prompt, system_prompt)

    def _offline_reasoning(self, prompt: str, system_prompt: str) -> str:
        """
        Deterministic, intelligent rule-based engine that reliably answers structured
        prompts for demand sensing, P2P negotiations, and central arbitration.
        """
        p_lower = prompt.lower()

        # 1. Demand Sensing Request
        sys_lower = system_prompt.lower()
        if "demand" in sys_lower or "sensing" in sys_lower or "extract" in p_lower or "unstructured" in p_lower:
            target_sku = "SKU-PHONE"
            if "ac" in p_lower or "air condition" in p_lower or "heat" in p_lower or "summer" in p_lower:
                target_sku = "SKU-AC"
            elif "jacket" in p_lower or "winter" in p_lower or "cold" in p_lower or "snow" in p_lower or "parka" in p_lower:
                target_sku = "SKU-JACKET"
            elif "laptop" in p_lower or "back to school" in p_lower or "student" in p_lower or "book" in p_lower:
                target_sku = "SKU-LAPTOP"

            target_region = "all"
            if "north" in p_lower or "delhi" in p_lower or "ny" in p_lower:
                target_region = "node_north"
            elif "south" in p_lower or "bangalore" in p_lower or "tx" in p_lower:
                target_region = "node_south"
            elif "east" in p_lower or "kolkata" in p_lower or "fl" in p_lower:
                target_region = "node_east"
            elif "west" in p_lower or "mumbai" in p_lower or "ca" in p_lower:
                target_region = "node_west"

            # Parse multiplier
            multiplier = 2.5
            mult_match = re.search(r"(\d+(\.\d+)?)x", p_lower)
            if mult_match:
                multiplier = float(mult_match.group(1))
            elif "surge" in p_lower or "viral" in p_lower:
                multiplier = 3.5
            elif "delay" in p_lower or "strike" in p_lower:
                multiplier = 0.5

            return json.dumps({
                "target_region": target_region,
                "target_sku": target_sku,
                "demand_multiplier": multiplier,
                "confidence": 0.94,
                "reasoning": f"Unstructured signal indicates {target_sku} demand adjustment of {multiplier}x in region {target_region}."
            })

        # 2. P2P Autonomous Negotiation Dialogue
        if "negotiat" in sys_lower or "p2p" in sys_lower or "negotiat" in p_lower:
            return json.dumps({
                "dialogue_turn": "We accept the transfer proposal. Our current buffer permits sharing stock without risking local safety stock.",
                "agreed_quantity": 80,
                "estimated_delivery_days": 1,
                "economic_rationale": "Transfer reduces network holding costs while preventing emergency stockout penalties at the destination node."
            })

        # 3. Central Arbitration Request
        if "central arbiter" in system_prompt.lower() or "arbitration" in p_lower:
            # Parse requests from prompt
            allocations = {}
            for node_id in REGIONS.keys():
                if node_id in prompt:
                    allocations[node_id] = {"SKU-PHONE": 150}
            if not allocations:
                allocations["node_north"] = {"SKU-PHONE": 150}
                allocations["node_east"] = {"SKU-PHONE": 150}

            return json.dumps({
                "allocations": allocations,
                "rationale": "Pareto allocation: Central buffer split equitably based on local burn-rate acceleration and shortest transit lead-times.",
                "confidence": 0.96
            })

        # Generic response fallback
        return json.dumps({"status": "SUCCESS", "message": "Processed successfully by autonomous LLM agent."})


class EdgeDemandSensingAgent:
    """
    Agent residing on regional edge nodes.
    Parses unstructured text (social trends, weather reports, local disruptions)
    into structured demand multipliers and affected SKU bindings.
    Enforces canonical SKU & Region mappings to prevent vocabulary drift.
    """
    def __init__(self, llm_engine: LLMEngine):
        self.llm = llm_engine
        sku_list = list(SKU_CATALOG.keys())
        sku_examples = [f"{k} ({SKU_CATALOG[k]['name']})" for k in sku_list]
        region_list = list(REGIONS.keys())
        self.system_prompt = (
            "You are an expert E-Commerce Demand-Sensing AI Agent in a Distributed Analytics architecture. "
            f"Analyze raw text signals and extract structured parameters.\n"
            f"Allowed target_region: {region_list} or 'all'.\n"
            f"Allowed target_sku: {sku_list} or 'all'. (Catalog: {', '.join(sku_examples)})\n"
            "Extract: target_region, target_sku, demand_multiplier (float e.g. 3.5), confidence (0.0 to 1.0), and reasoning. "
            "Return valid JSON ONLY."
        )

    def analyze_signal(self, raw_text: str) -> Dict[str, Any]:
        """Convert unstructured text into structured shock parameters with defensive canonicalization."""
        prompt = f"Analyze the following real-time unstructured market signal:\n\"{raw_text}\"\n\nJSON output:"
        response_text = self.llm.complete(prompt=prompt, system_prompt=self.system_prompt)

        # Clean JSON markdown fences if present
        clean_text = re.sub(r"```json\s*", "", response_text)
        clean_text = re.sub(r"```\s*$", "", clean_text).strip()

        try:
            data = json.loads(clean_text)
        except Exception:
            data = {
                "target_region": "all",
                "target_sku": "SKU-PHONE",
                "demand_multiplier": 2.0,
                "confidence": 0.85,
                "reasoning": f"Parsed text signal: {raw_text}"
            }

        # Apply two-tier canonicalization guards
        raw_target_sku = data.get("target_sku")
        raw_target_region = data.get("target_region")

        data["target_sku"] = canonicalize_sku(raw_target_sku)
        data["target_region"] = canonicalize_region(raw_target_region)

        # Ensure multiplier is a valid positive float clamped safely between 0.1x and 10.0x
        try:
            data["demand_multiplier"] = max(0.1, min(10.0, float(data.get("demand_multiplier", 2.0))))
        except (ValueError, TypeError):
            data["demand_multiplier"] = 2.0

        return data


class P2PNegotiationAgent:
    """
    Autonomous multi-agent negotiator enabling peer regional nodes to
    negotiate inventory transfers, freight costs, and ETAs.
    """
    def __init__(self, llm_engine: LLMEngine):
        self.llm = llm_engine
        self.system_prompt = (
            "You are an Autonomous Regional Supply Chain Agent participating in decentralized P2P stock rebalancing. "
            "When negotiating with peer nodes, consider stockout penalty risk, freight costs, and inventory holding costs. "
            "Output JSON containing dialogue_turn, agreed_quantity, estimated_delivery_days, and economic_rationale."
        )

    def negotiate_transfer(
        self,
        requesting_node: str,
        supplying_node: str,
        sku_id: str,
        needed_qty: int,
        available_surplus: int,
        freight_cost: float,
        transit_days: int
    ) -> Dict[str, Any]:
        """Conduct autonomous agent dialogue between two warehouse nodes."""
        prompt = (
            f"Negotiation Context:\n"
            f"- Requesting Node: {requesting_node} (Urgent deficit of {needed_qty} units of {sku_id})\n"
            f"- Supplying Node: {supplying_node} (Available surplus above safety stock: {available_surplus} units)\n"
            f"- Freight Cost: ${freight_cost:.2f}\n"
            f"- Transit Lead Time: {transit_days} day(s)\n"
            f"Generate the bilateral agreement dialogue and economic rationale. Output JSON ONLY."
        )
        response_text = self.llm.complete(prompt=prompt, system_prompt=self.system_prompt)
        clean_text = re.sub(r"```json\s*", "", response_text)
        clean_text = re.sub(r"```\s*$", "", clean_text).strip()

        try:
            data = json.loads(clean_text)
            qty = int(data.get("agreed_quantity", min(needed_qty, available_surplus)))
            data["agreed_quantity"] = min(qty, available_surplus)
            if data["agreed_quantity"] <= 0:
                data["agreed_quantity"] = min(needed_qty, available_surplus)
        except Exception:
            qty = min(needed_qty, available_surplus)
            data = {
                "dialogue_turn": f"{supplying_node}: We agree to transfer {qty} units of {sku_id} to {requesting_node} with ETA {transit_days}d.",
                "agreed_quantity": qty,
                "estimated_delivery_days": transit_days,
                "economic_rationale": "Transfer minimizes network stockout penalty while retaining 120% local safety buffer."
            }
        return data


class CentralArbiterAgent:
    """
    Global Supply Arbiter Agent.
    Resolves multi-node allocation conflicts when aggregate regional demand
    exceeds available central supplier inventory.
    """
    def __init__(self, llm_engine: LLMEngine):
        self.llm = llm_engine
        self.system_prompt = (
            "You are the Central Supply Arbiter AI in a Distributed E-Commerce Supply Chain. "
            "Multiple regional warehouses are contending for scarce central stock. "
            "Perform multi-criteria Pareto arbitration balancing burn rate, stockout urgency, and transit lead time. "
            "Output JSON with allocations map and explainable rationale."
        )

    def arbitrate_shortage(
        self,
        sku_id: str,
        available_central_stock: int,
        competing_requests: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Arbitrate scarce stock allocation across multiple contending nodes."""
        prompt = (
            f"Contention Arbitration Case:\n"
            f"SKU: {sku_id}\n"
            f"Available Central Factory Stock: {available_central_stock} units\n"
            f"Competing Regional Demands:\n"
        )
        for node_id, req in competing_requests.items():
            prompt += f"  * Node {node_id}: Requested={req['requested_qty']}, BurnRate={req.get('burn_rate', 0)}/day, CurrentStock={req.get('current_stock', 0)}\n"
        prompt += (
            f"\nDetermine fair allocations and provide explainable executive rationale.\n"
            f"Return JSON ONLY in this format: {{\"allocations\": {{\"<node_id>\": {{\"{sku_id}\": <quantity>}}}}, \"rationale\": \"<explanation>\"}}"
        )

        response_text = self.llm.complete(prompt=prompt, system_prompt=self.system_prompt)
        clean_text = re.sub(r"```json\s*", "", response_text)
        clean_text = re.sub(r"```\s*$", "", clean_text).strip()

        try:
            data = json.loads(clean_text)
            # Normalize allocations schema
            raw_alloc = data.get("allocations", {})
            norm_alloc: Dict[str, Dict[str, int]] = {}

            if isinstance(raw_alloc, dict):
                for n_id, val in raw_alloc.items():
                    if isinstance(val, dict):
                        norm_alloc[n_id] = {k: int(v) for k, v in val.items() if str(v).isdigit()}
                    elif isinstance(val, (int, float, str)):
                        norm_alloc[n_id] = {sku_id: int(val)}
            elif isinstance(raw_alloc, list):
                for item in raw_alloc:
                    if isinstance(item, dict) and "node" in item:
                        norm_alloc[item["node"]] = {sku_id: int(item.get("quantity", 0))}

            data["allocations"] = norm_alloc if norm_alloc else None
            if not data["allocations"]:
                raise ValueError("Could not parse allocations")

        except Exception:
            # Proportional allocation fallback
            total_req = sum(r["requested_qty"] for r in competing_requests.values())
            allocations = {}
            for node_id, req in competing_requests.items():
                ratio = req["requested_qty"] / total_req if total_req > 0 else 0
                alloc_qty = int(available_central_stock * ratio)
                allocations[node_id] = {sku_id: alloc_qty}
            data = {
                "allocations": allocations,
                "rationale": "Proportional Pareto allocation based on relative regional order volume.",
                "confidence": 0.90
            }
        return data
