import ast
import os
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from openai import AzureOpenAI
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient
from azure.storage.blob import ContentSettings

client = AzureOpenAI(
  api_key = 
  api_version = 
  azure_endpoint = "https://openai-production001.openai.azure.com/openai/deployments/text-embedding-3-small-km/embeddings?api-version=2023-05-15"
)


def extract_array_of_embedding_from_file(file_name):
    print("extract_array_of_embedding_from_file")
    df = pd.read_csv(file_name)
    embedding_list_final = []
    embedding_list = df.embedding.apply(ast.literal_eval)
    for temp_element in embedding_list:
        embedding_list_final.append(temp_element)
    embedding_array = np.array(embedding_list_final)
    return embedding_array, df


def query_array(query, model="text-embedding-3-small-km"):
    print("query_array",query)
    print(type(query))

    # If query is a dictionary, extract the required string value
    if isinstance(query, dict):
        query = query['Output_query']  # Adjust this key based on your data structure

    # Ensure query is a string
    if not isinstance(query, str):
        raise ValueError(f"Invalid query: expected a string, but got {type(query).__name__}")

    # Send the request to the API
    try:
        # Ensure the input is a string or a list of strings
        data = client.embeddings.create(input=[query], model=model).data[0].embedding

        # Convert response to numpy array
        query_array = np.array(data)
        query_array = query_array.reshape(1, -1)
        print("Query array created successfully")
        return query_array

    except Exception as e:
        print(f"Error occurred in query_array: {str(e)}")
        raise e




