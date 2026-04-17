import os
import json
from typing import List, Dict
from langchain_core.documents import Document

class PBACLoader:
    def __init__(self, data_path: str, schema_path: str, policy_file: str):
        self.data_path = data_path
        self.schema_path = schema_path
        self.policy_file = policy_file
        self.role_policies = self._load_role_policies()

    def _load_role_policies(self) -> Dict:
        if os.path.exists(self.policy_file):
            with open(self.policy_file, 'r') as f:
                return json.load(f).get("policies", {})
        return {}

    def _get_user_policies(self, user_role: str) -> List[str]:
        active_policies = []
        for policy_name, allowed_roles in self.role_policies.items():
            if user_role in allowed_roles:
                active_policies.append(policy_name)
        return active_policies

    def _apply_pbac_filter(self, item: Dict, schema: Dict, user_policies: List[str]) -> Dict:
        clean_item = {}
        clean_entry = {}
        for attribute, value in item.items():
            attr_config = schema.get(attribute)
            if not attr_config: continue

            required_policy = attr_config.get("policy")
            visibility = attr_config.get("visibility", True)

            if required_policy in user_policies:
                if visibility:
                    clean_item[attribute] = value
                else:
                    clean_entry[f"internal_{attribute}"] = value
        return clean_item

    def load_documents(self, user_role: str) -> List[Document]:
        user_policies = self._get_user_policies(user_role)
        all_documents = []

        for filename in os.listdir(self.data_path):
            if filename.endswith('.json'):
                data_file = os.path.join(self.data_path, filename)
                schema_file = os.path.join(self.schema_path, filename)

                if not os.path.exists(schema_file):
                    print(f"Skipping {filename}: No schema found.")
                    continue

                with open(schema_file, 'r') as sf:
                    schema = json.load(sf).get("attributes", {})

                with open(data_file, 'r') as df:
                    data = json.load(df)
                    if not isinstance(data, list): data = [data]

                    for item in data:
                        filtered = self._apply_pbac_filter(item, schema, user_policies)
                        if filtered:
                            text_content = " | ".join([f"{k}: {v}" for k, v in filtered.items()])
                            all_documents.append(Document(
                                page_content=text_content,
                                metadata={"source": filename, "role": user_role}
                            ))
        return all_documents