from langchain.memory import ConversationBufferMemory
# Initialize conversation memory (global for demo)
memory = ConversationBufferMemory(return_messages=True)
from flask import Flask, jsonify, request
from flask_compress import Compress
from functools import lru_cache
from flask_cors import CORS
from flask_compress import Compress
from src.helper import download_hugging_face_embeddings
from langchain_pinecone import PineconeVectorStore
#from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from src.prompt import *
import os


app = Flask(__name__)
CORS(app)
Compress(app)

load_dotenv()

PINECONE_API_KEY=os.environ.get('PINECONE_API_KEY')
GOOGLE_API_KEY=os.environ.get('GOOGLE_API_KEY')

os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY


embeddings = download_hugging_face_embeddings()

index_name = "medical-chatbot" 
# Embed each chunk and upsert the embeddings into your Pinecone index.
docsearch = PineconeVectorStore.from_existing_index(
    index_name=index_name,
    embedding=embeddings
)

retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k":5})

chatModel = ChatGoogleGenerativeAI(model='gemini-2.0-flash')
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{input}"),
    ]
)

question_answer_chain = create_stuff_documents_chain(chatModel, prompt)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)




@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.get_json()
    prompt = data.get('prompt', '')
    # Add user input to memory (output is empty string for now)
    memory.save_context({"input": prompt}, {"output": ""})
    # Use memory in chain invocation
    response = rag_chain.invoke({"input": prompt, "history": memory.chat_memory.messages})
    # Add model response to memory (input is empty string for now)
    memory.save_context({"input": ""}, {"output": response["answer"]})
    return jsonify({'answer': response["answer"]})

# Simple in-memory cache for repeated queries
@lru_cache(maxsize=128)
def get_cached_response(prompt):
    response = rag_chain.invoke({"input": prompt})
    return response["answer"]

#if __name__ == '__main__':
#    app.run(host="0.0.0.0", port= 8080, debug= True)

if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)

