from openai import OpenAI
from pinecone import Pinecone
import time
import unicodedata


# Initialize Pinecone and OpenAI clients
pc = Pinecone(api_key="42304d01-e229-41b6-a281-498ef5e8a39f")
index = pc.Index("merlin")
client = OpenAI(api_key="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")
ns = "orientamento"

def text_to_embedding_openai(text):
    try:
        # Call the OpenAI API to process the text
        response = client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return response.data[0].embedding
    except Exception as e:
        print("Error:", e)
        return None

def embed_and_save(input_file, output_file):
    # Embed and save data
    with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'w') as outfile:
        for line in infile:
            line = line.strip()  # Remove leading/trailing whitespace
            if line:  # Skip empty lines
                # Remove or replace non-ASCII characters from the text
                sanitized_text = ''.join(char for char in line if ord(char) < 128)
                # Embed the sanitized text using OpenAI API
                embedding = text_to_embedding_openai(sanitized_text)
                if embedding:
                    # Write original sanitized text and embedding to the output file
                    outfile.write(f"{sanitized_text}\t{embedding}\n")
    print("Processing complete. Output saved to", output_file)

def create_vectors_for_index(input_file):
    vectors = []
    # Read from the output file containing embedded lines
    with open(input_file, 'r', encoding='utf-8') as infile:
        for line in infile:
            line = line.strip()  # Remove leading/trailing whitespace
            if line:  # Skip empty lines
                # Split line to separate text and embedding
                text, embedding = line.split('\t')
                # Construct vector dictionary with ID and values
                vector = {
                    "id": text,  # Use text as ID
                    "values": [float(value.strip("[]")) for value in embedding.split(",")],  # Convert embedding to list of floats
                }
                vectors.append(vector)
    return vectors

# Define a function to complete the prompt using OpenAI
def complete_prompt(prompt):
    try:
        # Send the prompt to OpenAI for completion
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Choose the appropriate model
            messages=[
                {"role": "system", "content": "You are a helpful assistant that always answers questions."},
                {"role": "user", "content": prompt}
            ]
        )

        # Extract and return the completed response
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print("Error completing prompt:", e)
        return None

if __name__ == "__main__":
    input_file = "scuola_di_studi_superiori_ferdinando_rossi.txt"
    output_file = "output.txt"
    # Define the limit for the accumulated contexts
    limit = 10  # Set an appropriate limit value
    
    # Embed and save data
    embed_and_save(input_file, output_file)
    
    # Upsert vectors to the index
    vectors = create_vectors_for_index(output_file)
    index.upsert(vectors=vectors, namespace=ns)
    print("Vectors inserted into index.")

    # Receive input from the user
    user_input = input("Hello, Ask me anything!: ")
    
    # Embed user input and query the data
    input_vector = text_to_embedding_openai(user_input)
    
    # Get relevant contexts
    contexts = []
    time_waited = 0
    while (len(contexts) < 3 and time_waited < 10):
        query_result = index.query(
            namespace=ns,
            vector=input_vector,
            top_k=3,
            include_values=True,
            include_metadata=True,
        )
        contexts = contexts + [
            x['id'] for x in query_result['matches']
        ]
        print(f"Retrieved {len(contexts)} contexts, sleeping for 1 seconds...\n")
        time.sleep(1)
        time_waited += 1

    if time_waited >= 10:
        print("Timed out waiting for contexts to be retrieved.")
        contexts = ["No contexts retrieved. Try to answer the question yourself!"]
       
    # Build our prompt with the retrieved contexts included
    prompt_start = (
        "Answer the question based on the context below.\n\n"+
        "Context:\n" +
        "\n---\n".join(contexts)
    )
    prompt_end = (
        f"\n\nQuestion: {user_input}\n"
    )
    prompt = prompt_start + prompt_end
    print(prompt)
    
    # Complete the prompt using OpenAI
    openai_response = complete_prompt(prompt)
    
    # Print the response from OpenAI
    if openai_response:
        print("OpenAI response:", openai_response)
    else:
        print("Failed to generate OpenAI response.")
