import os
from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from src.brain import initialize_brain, get_retriever

DATA_PATH = "./data"
BRAIN_PATH = "./brain_data"

def run_ai_analyzer():
    if not os.path.exists(BRAIN_PATH) or not os.listdir(BRAIN_PATH):
        initialize_brain(DATA_PATH, BRAIN_PATH)
    
    retriever = get_retriever(BRAIN_PATH).with_config(search_kwargs={'k': 10})
    llm = Ollama(model="qwen2.5-coder:1.5b")

    template = """You are a professional business assistant. 
    Use the following pieces of information to answer the user's question directly. 

    STRICT RULES:
    1. Do NOT mention 'JSON', 'files', 'context', or 'database'.
    2. Do NOT say 'Based on the provided data' or 'According to the documents'.
    3. Just provide the final answer in a natural, conversational way.
    4. If the answer is a price or a name, state it clearly.

    Information: {context}

    Question: {question}

    Answer:"""
    
    prompt = ChatPromptTemplate.from_template(template)

    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    print("\n--- AI Codebase Analyzer\n")
    
    while True:
        query = input(":")
        if query.lower() in ['exit', 'quit']:
            break
            
        try:
            response = chain.invoke(query)
            print(response)
        except Exception as e:
            print(f"{e}")

if __name__ == "__main__":
    run_ai_analyzer()