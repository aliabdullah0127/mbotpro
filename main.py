import ast
import numpy as np
from openai import AzureOpenAI
import pandas as pd
import json
from typing import Any, Dict
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError
import os
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi import FastAPI, HTTPException, Depends, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app import query_chroma
from typing import List
import shutil
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import mysql.connector
from mysql.connector import Error
import base64
from qa import predefined_qa 
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
 




CONNECTION_STRING = 
CONTAINER_NAME = "aibot"

def clean_json_string(raw: str) -> str:
    """
    Remove markdown code fences (```json ... ```) if present
    so the string can be parsed by json.loads.
    """
    if not isinstance(raw, str):
        return raw
    return re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
# Database connection function
def create_connection(host_name, user_name, user_password, db_name):
    connection = None
    try:
        connection = mysql.connector.connect(
            host=host_name,
            user=user_name,
            passwd=user_password,
            database=db_name,
            ssl_ca='./DigiCertGlobalRootG2.crt.pem'
        )
        print("Connection to MySQL DB successful")
    except Error as e:
        print(f"The error '{e}' occurred")
    return connection
 
# Connection details
host_name = "mysqlai.mysql.database.azure.com"
user_name = "azureadmin"
user_password = "Meridian@123"
db_name = "chatbot"
 

def download_blobs_from_folder(container_name, folder_name, connection_string, local_download_path):
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)
    folder_path = os.path.join(local_download_path, folder_name)
   
    # Create local download path if it doesn't exist
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
   
    blob_list = container_client.list_blobs(name_starts_with=folder_name)
    csv_blobs = [blob for blob in blob_list if blob.name.endswith('.csv')]
   
    if not csv_blobs:
        #print("No .csv files found in the folder.")
        return False
 
    for blob in csv_blobs:
        blob_client = container_client.get_blob_client(blob.name)
        local_file_path = os.path.join(folder_path, os.path.relpath(blob.name, folder_name))
       
        # Create directories if they don't exist
        local_dir = os.path.dirname(local_file_path)
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)
       
        with open(local_file_path, "wb") as download_file:
            download_file.write(blob_client.download_blob().readall())
        #print(f"Downloaded {blob.name} to {local_file_path}")
   
    return True
 
 
# Function to store data in a JSON file
def store_data(file_path, data):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)
 
 
# Function to get data from a JSON file
def get_data(file_path):
    if not os.path.exists(file_path):
        return {"chat": []}  # Return an empty structure if the file does not exist
    with open(file_path, 'r') as file:
        return json.load(file)
 
 
# Function to append data to a JSON file
def append_data(file_path, new_data):
    # Load existing data
    data = get_data(file_path)
    print("a")
    # Append the new data
    data['chat'].append(new_data)
    print("ab")
    # Store the updated data
    store_data(file_path, data)
 


def respond_to_question(original_query_string, chat_history, language):
    try:
        print("Original:", original_query_string)
        print("History:", chat_history)

        # Get the last two queries and answers from chat history
        if len(chat_history) >= 2:
            last_user_queries = [chat_history[-2].get("user_query", ""), chat_history[-1].get("user_query", "")]
            last_bot_answers = [chat_history[-2].get("bot_response", ""), chat_history[-1].get("bot_response", "")]
        elif len(chat_history) == 1:
            last_user_queries = [chat_history[-1].get("user_query", "")]
            last_bot_answers = [chat_history[-1].get("bot_response", "")]
        else:
            last_user_queries = []
            last_bot_answers = []

        # ---------- Language correction (if any logic needed) ----------
        try:
            last_entry = chat_history[-1] if chat_history else {"user_query": ""}
            language_response = original_query_string
            if "error" in language_response:
                return language_response
        except Exception as e:
            print("Error occurred in language_correct_query:", str(e))
            return {"error": "Error occurred while correcting language"}

        # ---------- Direct query handling ----------
        query_string = original_query_string
        print("Query_string (direct):", query_string)

        # ---------- Content retrieval ----------
        try:
            content_list = query_chroma(query_string, n_results=10)
            
            content = "".join(content_list)
            print("skndjfdnjdfn")
            print("Full content retrieved from Chroma:\n", content)
        except Exception as e:
            print("Error occurred in query_chroma:", str(e))
            return {"error": "Error occurred while retrieving content from Chroma"}

        
        print("Language:", language)

        # ---------- Generate final response ----------
        try:
            bot_response = get_response_from_query(query_string, content, last_user_queries, language)
            print("bot_response:", bot_response)
            return {"user_query": original_query_string, "bot_response": bot_response["bot_response"]}
        
        except Exception as e:
            print("Error occurred while generating response from chat client:", str(e))
            return {"error": "Error occurred while generating response from chat client"}

    except Exception as e:
        print("Error occurred in respond_to_question:", str(e))
        return {"error": "An error occurred in respond_to_question"}



def get_response_from_query(query, content, history, language):
    # Ensure that there are at least two previous queries
    print("yohohoyohoho")
    print("History:", history)
        # Safely handle cases where history has fewer than 2 entries
    if len(history) == 0:
        previous_query1, previous_query2 = "", ""
    elif len(history) == 1:
        previous_query1, previous_query2 = "", history[0]
    else:
        previous_query1, previous_query2 = history[-2], history[-1]

    print("Pirate king...")

    prompt_template = f"""
    Your task is to follow the chain of thought method to first extract an accurate answer for the given user query, chat history, and provided input content. Then change the language of the response into {language}. Provide the response in JSON format only with 'bot_answer' and 'scope' as keys.
    All the content provided belongs to the Meridian Solutions Company.
    Input Content: {content}

    Previous User Query : {previous_query1}
    Last User Query : {previous_query2}
    Current User Query: {query}

    Important Points:
    1. The answer should be relevant to the input text.
    2. Answer complexity should match the input content.
    3. If input content is missing, direct the user to provide content.
    4. Answers should be safe and appropriate. If not, give instructions to the user.
    5. If the user query is out of scope, set the 'scope' key to False.
    6. Answer should be concise and to the point. Strictly avoid giving long answers.

    Extracted JSON response:
    """

    message = [
        {"role": "system", "content": f"You are an AI assistant that helps to answer the questions from the given content in {language} language."},
        {"role": "user", "content": prompt_template}
    ]

    try:
        response = chat_client_gpt4.chat.completions.create(
            model="gpt-4-cbt",
            messages=message,
            temperature=0.7,
            max_tokens=800,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None,
            response_format = {"type": "json_object"}
        )
        
        raw_response = response.choices[0].message.content
        
        # Debug: Check the type and content of raw_response
        print("Type of raw_response:", type(raw_response))
        print("Raw response from API:", raw_response)

        # Ensure the response is a string and parse it as JSON
        if isinstance(raw_response, str):
            try:
                json_response = json.loads(raw_response)
                print("Parsed JSON response:", json_response)
                return {"bot_response": json_response.get('bot_answer', "No answer provided")}
            except json.JSONDecodeError as e:
                print("Error occurred while decoding JSON response:", str(e))
                return {"error": "Error occurred while decoding JSON response"}
        else:
            print("Unexpected response type")
            return {"error": "Unexpected response type from chat client"}

    except Exception as e:
        print("Error occurred while generating response from chat client:", str(e))
        return {"error": "Error occurred while generating response from chat client"}


class QueryRequest(BaseModel):
    original_query_string: str
    chat_history: List[Dict[str, Any]]
    language: str


# Pydantic model for the request body
class Chat_User(BaseModel):
    name: str
    email: str
    company_name : str
    contact_number : str


# Initialize TF-IDF Vectorizer
vectorizer = TfidfVectorizer()

# Prepare predefined questions and their vectors
predefined_questions = list(predefined_qa.keys())
predefined_answers = list(predefined_qa.values())

# Fit the vectorizer on predefined questions
tfidf_matrix = vectorizer.fit_transform(predefined_questions)


def find_predefined_answer(user_query, language):
    # Transform the user query into a vector
    query_vector = vectorizer.transform([user_query])
    print("language", language)
    # Compute cosine similarity between the user query and predefined questions
    cosine_scores = cosine_similarity(query_vector, tfidf_matrix)
    
    # Find the highest score and its corresponding index
    best_score = np.max(cosine_scores)
    best_match_index = np.argmax(cosine_scores)
    
    if best_score > 0.8:  # Adjust threshold as needed
        return predefined_answers[best_match_index]
    else:
        return None

    
 
# Function to analyze the sentiment and determine intent
def detect_intent(user_input):
    prompt_template = f"""
    Please classify the following user input as either affirmative or negative:
    User Input: {user_input}
    Respond with 'true' for affirmative or 'false' for negative.
    """
    
    message = [
        {"role": "system", "content": "You are an AI assistant."},
        {"role": "user", "content": prompt_template}
    ]

    try:
        response = chat_client_gpt4o.chat.completions.create(
            model="gpt-4o-cbt",
            messages=message,
            temperature=0.7,
            max_tokens=10,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None,
        )
        
        raw_response = response.choices[0].message.content.strip().lower()
        
        if raw_response == 'true':
            return True
        elif raw_response == 'false':
            return False
        else:
            return {"error": "Unexpected response format from chat client"}

    except json.JSONDecodeError as json_error:
        return {"error": "Error parsing JSON response from chat client"}
    except Exception as e:
        return {"error": "Error occurred while generating response from chat client"}


class UserRequest(BaseModel):
    user_input: str




app = FastAPI()
 
 
 
origins = [
    "*"
]
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.post("/query")
def query_endpoint(query_data: QueryRequest):
    try:
        print("Starting...")
        original_query_string = query_data.original_query_string
        chat_history = query_data.chat_history
        language = query_data.language
        print("language....", language)
        print("Searching predefined QA")
        predefined_answer = find_predefined_answer(original_query_string, language)

        if predefined_answer:
            print("Got a predefined QA")
            return {
                "response": {
                    "user_query": original_query_string,
                    "bot_response": predefined_answer
                }
            }
        else:
            print("NO predefined QA found, trying LLM...")
            llm_answer = respond_to_question(original_query_string, chat_history, language)

            return {
                "response": {
                    "user_query": original_query_string,
                    "bot_response": llm_answer
                }
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/submit")
async def submit(data: UserRequest):
    # Detect intent based on sentiment
    intent = detect_intent(data.user_input)
    print("Intent:", intent)

    return {"intent": intent}

# Route to insert data
@app.post('/insert')
def insert_data(user: Chat_User):
    query = """
        INSERT INTO chatbot_form (name, email, company_name, contact_number)
        VALUES (%s, %s, %s, %s)
    """
    values = (user.name, user.email, user.company_name, user.contact_number)
 
    connection = create_connection(host_name, user_name, user_password, db_name)
    cursor = connection.cursor()
    try:
        cursor.execute(query, values)
        connection.commit()
        return {"message": "Data inserted successfully"}
    except Error as e:
        print(f"The error '{e}' occurred")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        connection.close()
 
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=4000)
