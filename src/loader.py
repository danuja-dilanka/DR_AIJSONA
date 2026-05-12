import json
import os
from typing import Dict, List, Optional, Tuple

from langchain_core.documents import Document

class PBACLoader:
    """
    Policy-Based Access Control document loader with relation resolution.

    Loads JSON data files and filters fields per role using a policy file
    and per-attribute schemas. Supports cross-schema joins via a ``relations``
    block in the schema, merging related visible fields inline at index time
    for richer RAG context.

    Schema format
    -------------
    {
      "schema_name": "Invoices Records",
      "relations": {
        "customer_id": { "references": "customers.json", "foreign_key": "customer_id" },
        "product_id":  { "references": "products.json",  "foreign_key": "product_id"  }
      },
      "attributes": {
        "invoice_number": { "type": "string", "policy": "sales_access", "visibility": true },
        ...
      }
    }
    """

    def __init__(self, data_path: str, schema_path: str, policy_file: str) -> None:
        self.data_path   = data_path
        self.schema_path = schema_path
        self.policy_file = policy_file
        self._role_policies: Dict[str, List[str]] = self._load_role_policies()

        self._data_cache:   Dict[str, List[Dict]] = {}
        self._schema_cache: Dict[str, Dict]       = {}

    # ------------------------------------------------------------------
    # Policy helpers
    # ------------------------------------------------------------------

    def _load_role_policies(self) -> Dict[str, List[str]]:
        """Return {policy_name: [allowed_role, ...]} or {} on failure."""
        if not os.path.exists(self.policy_file):
            print(f"[loader] Policy file not found: {self.policy_file}")
            return {}
        try:
            with open(self.policy_file, "r") as f:
                return json.load(f).get("policies", {})
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[loader] Failed to load policy file: {exc}")
            return {}

    def _get_user_policies(self, user_role: str) -> List[str]:
        """Return the list of policy names the given role is permitted to use."""
        return [
            policy_name
            for policy_name, allowed_roles in self._role_policies.items()
            if user_role in allowed_roles
        ]

    # ------------------------------------------------------------------
    # File helpers (with caching)
    # ------------------------------------------------------------------

    def _load_data_file(self, filename: str) -> List[Dict]:
        """Load and cache a JSON data file. Returns [] on failure."""
        if filename in self._data_cache:
            return self._data_cache[filename]

        filepath = os.path.join(self.data_path, filename)
        if not os.path.exists(filepath):
            print(f"[loader] Data file not found: {filename}")
            self._data_cache[filename] = []
            return []

        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            if not isinstance(data, list):
                data = [data]
            self._data_cache[filename] = [r for r in data if isinstance(r, dict)]
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[loader] Failed to load data file '{filename}': {exc}")
            self._data_cache[filename] = []

        return self._data_cache[filename]

    def _load_schema_file(self, filename: str) -> Dict:
        """Load and cache a JSON schema file. Returns {} on failure."""
        if filename in self._schema_cache:
            return self._schema_cache[filename]

        filepath = os.path.join(self.schema_path, filename)
        if not os.path.exists(filepath):
            print(f"[loader] Schema file not found: {filename}")
            self._schema_cache[filename] = {}
            return {}

        try:
            with open(filepath, "r") as f:
                raw = json.load(f)
            self._schema_cache[filename] = raw
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[loader] Failed to load schema file '{filename}': {exc}")
            self._schema_cache[filename] = {}

        return self._schema_cache[filename]

    # ------------------------------------------------------------------
    # PBAC filter
    # ------------------------------------------------------------------

    def _apply_pbac_filter(
        self,
        item: Dict,
        schema: Dict,
        user_policies: List[str],
    ) -> Tuple[Dict, Dict]:
        """
        Split *item* fields into two dicts:

        * ``visible`` — fields that belong in the RAG context string.
        * ``hidden``  — accessible but excluded from context (visibility=False);
                        stored as Document metadata.

        Fields absent from the schema are skipped entirely.
        Fields with no ``policy`` key are universally accessible.
        """
        visible: Dict = {}
        hidden:  Dict = {}

        for attribute, value in item.items():
            attr_config = schema.get(attribute)
            if not attr_config:
                continue

            required_policy = attr_config.get("policy")
            if required_policy is not None and required_policy not in user_policies:
                continue

            if attr_config.get("visibility", True):
                visible[attribute] = value
            else:
                hidden[f"internal_{attribute}"] = value

        return visible, hidden

    # ------------------------------------------------------------------
    # Relation resolver
    # ------------------------------------------------------------------

    def _resolve_relations(
        self,
        item: Dict,
        relations: Dict,
        user_policies: List[str],
        _visiting: Optional[set] = None,
    ) -> Dict:
        """
        For each relation declared in the schema, look up the related record
        and merge its visible fields (prefixed with the relation key) into a
        flat dict.

        Only fields the current role can see (per the related schema) are
        included. Circular references are guarded via ``_visiting``.

        Example output for an invoice row
        ----------------------------------
        {
          "customer_id__name": "Kasun",
          "customer_id__city": "Colombo",
          "product_id__name": "Laptop",
          "product_id__category": "Electronics",
        }
        """
        _visiting = _visiting or set()
        merged: Dict = {}

        for local_key, relation in relations.items():
            ref_file   = relation.get("references")
            foreign_key = relation.get("foreign_key")

            if not ref_file or not foreign_key:
                continue

            # Guard against circular reference loops
            if ref_file in _visiting:
                print(f"[loader] Circular relation detected: {ref_file}. Skipping.")
                continue

            local_value = item.get(local_key)
            if local_value is None:
                continue

            # Load related data + schema
            related_records = self._load_data_file(ref_file)
            related_schema_raw = self._load_schema_file(ref_file)
            related_attributes = related_schema_raw.get("attributes", {})
            related_relations  = related_schema_raw.get("relations", {})

            # Find the matching record
            matched = next(
                (r for r in related_records if r.get(foreign_key) == local_value),
                None,
            )
            if matched is None:
                continue

            # Apply PBAC to the related record
            visible, _ = self._apply_pbac_filter(matched, related_attributes, user_policies)

            prefix = local_key
            for field, value in visible.items():
                if field != foreign_key:
                    merged[f"{prefix}__{field}"] = value

            if related_relations:
                nested = self._resolve_relations(
                    matched,
                    related_relations,
                    user_policies,
                    _visiting | {ref_file},
                )
                for field, value in nested.items():
                    merged[f"{prefix}__{field}"] = value

        return merged

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def load_documents(self, user_role: str) -> List[Document]:
        """
        Return a list of :class:`~langchain_core.documents.Document` objects
        accessible to *user_role*, with related fields merged inline.

        * Each JSON data file is matched with a same-named schema file.
        * Relations declared in the schema are resolved and merged into the
          context text so the LLM has full denormalized context per chunk.
        * Malformed or missing files are skipped with a warning.
        * Non-dict array elements are skipped gracefully.
        """
        user_policies = self._get_user_policies(user_role)
        documents: List[Document] = []

        if not os.path.isdir(self.data_path):
            print(f"[loader] Data path does not exist: {self.data_path}")
            return documents

        for filename in sorted(os.listdir(self.data_path)):
            if not filename.endswith(".json"):
                continue

            schema_file = os.path.join(self.schema_path, filename)
            if not os.path.exists(schema_file):
                print(f"[loader] Skipping '{filename}': no matching schema.")
                continue

            schema_raw = self._load_schema_file(filename)
            if not schema_raw:
                continue

            attributes = schema_raw.get("attributes", {})
            relations  = schema_raw.get("relations", {})
            data       = self._load_data_file(filename)

            for item in data:
                # Apply PBAC to the primary record
                visible, hidden = self._apply_pbac_filter(item, attributes, user_policies)
                if not visible:
                    continue

                # Resolve and merge related fields
                if relations:
                    related_fields = self._resolve_relations(item, relations, user_policies)
                    visible.update(related_fields)

                # Build a rich, labelled context string
                context_text = " | ".join(f"{k}: {v}" for k, v in visible.items())

                documents.append(
                    Document(
                        page_content=context_text,
                        metadata={
                            "source": filename,
                            "role":   user_role,
                            **hidden,
                        },
                    )
                )

        return documents