import os
import json
from langchain_core.documents import Document

def load_json_files(data_path):
    all_documents = []
    for filename in os.listdir(data_path):
        if filename.endswith('.json'):
            file_path = os.path.join(data_path, filename)
            source_name = filename.replace('.json', '')
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    text_content = " | ".join([f"{k}: {v}" for k, v in item.items()])
                    doc = Document(
                        page_content=text_content, 
                        metadata={"source": source_name}
                    )
                    all_documents.append(doc)
    return all_documents