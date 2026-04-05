import os
import json
from langchain_core.documents import Document

def load_json_files(data_path):
    all_documents = []
    
    for filename in os.listdir(data_path):
        if filename.endswith('.json'):
            file_path = os.path.join(data_path, filename)
            source_name = filename.replace('.json', '')
            
            with open(file_path, 'r') as f:
                data = json.load(f)
                
                for item in data:
                    content = json.dumps(item)
                    doc = Document(page_content=content, metadata={"source": source_name})
                    all_documents.append(doc)
    
    return all_documents