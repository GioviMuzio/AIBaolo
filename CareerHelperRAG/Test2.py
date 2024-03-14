from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from pinecone import Pinecone
import time

# Initialize Pinecone and OpenAI clients
pc = Pinecone(api_key="42304d01-e229-41b6-a281-498ef5e8a39f")
index = pc.Index("merlin")
client = OpenAI(api_key="")
ns = "Identity"

# Initialize Flask app
app = Flask(__name__)

def text_to_embedding_openai(text):
    try:
        response = client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return response.data[0].embedding
    except Exception as e:
        print("Error:", e)
        return None

def embed_chunks_and_save(input_file, output_file):
    # Embed and save data
    with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'w', encoding='utf-8') as outfile:
        for line in infile:
            line = line.strip()  # Remove leading/trailing whitespace
            if line:  # Skip empty lines
                # Check if the delimiter is present in the line
                if '/nome_metadato' in line:
                    # Split the line into text and metadata
                    text, metadata = line.split('/nome_metadato', 1)
                    text = text.strip()  # Remove leading/trailing whitespace from text
                    metadata = metadata.strip()  # Remove leading/trailing whitespace from metadata
                else:
                    # If the delimiter is not present, use the entire line as text and set an empty metadata
                    text = line.strip()
                    metadata = {}

                # Remove or replace non-ASCII characters from the text
                sanitized_text = ''.join(char for char in text if ord(char) < 128)

                # Embed the sanitized text using OpenAI API
                embedding = text_to_embedding_openai(sanitized_text)
                if embedding:
                    # Write original line and embedding to the output file
                    outfile.write(f"{text}\t{embedding}\t{metadata}\n")

    print("Processing complete. Output saved to", output_file)





def create_vectors_for_index(input_file):
    vectors = []
    with open(input_file, 'r', encoding='utf-8') as infile:
        for line in infile:
            line = line.strip()
            if line:
                parts = line.split('\t')
                text = parts[0][:512]  # Truncate 'id' to 512 characters
                embedding = parts[1]
                metadata_str = parts[2].strip() if len(parts) > 2 and parts[2].strip() != 'None' else "{}"

                try:
                    # Attempt to convert the metadata string to a dictionary
                    metadata = eval(metadata_str)
                    if not isinstance(metadata, dict):
                        raise ValueError("Metadata is not a dictionary")
                except (SyntaxError, ValueError):
                    # If conversion fails, set metadata to an empty dictionary
                    metadata = {}

                vector = {
                    "id": text.encode('ascii', 'ignore').decode(),  # Remove non-ASCII characters
                    "values": [float(value.strip("[]")) for value in embedding.split(",")],
                    "metadata": metadata,
                }
                vectors.append(vector)
    return vectors




def complete_prompt(prompt):
    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are Ai Vtuber Merlin talk in first person"},
                {"role": "user", "content": prompt}
            ]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print("Error completing prompt:", e)
        return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_input = request.json['user_input']
    except KeyError:
        return jsonify({'response': 'Invalid request. Missing user_input parameter.'}), 400
    
    input_vector = text_to_embedding_openai(user_input)
    contexts = []
    time_waited = 0
    while (len(contexts) < 3 and time_waited < 10):
        query_result = index.query(
            namespace=ns,
            vector=input_vector,
            top_k=3,
            include_values=True,
            include_metadata=True,
            #distance_threshold=0.8
        )
        contexts = contexts + [
            x['id'] for x in query_result['matches']
        ]
        time.sleep(1)
        time_waited += 1
    
    if not contexts:  # If no similar vectors found in Pinecone
        prompt_start = ""  # No context from Pinecone
        prompt_end = (
            f"\n\nQuestion: {user_input}\n"
        )
        prompt = prompt_start + prompt_end
        openai_response = complete_prompt(prompt)
        if openai_response:
            return jsonify({'response': openai_response})
        else:
            return jsonify({'response': 'Failed to generate OpenAI response.'})
    else:
        prompt_start = (
            "You are Merlin answer the question based on the information received.\n\n"+
            "information:\n" +
            "\n---\n".join(contexts)
        )
        prompt_end = (
            f"\n\nQuestion: {user_input}\n"
        )
        prompt = prompt_start + prompt_end
        openai_response = complete_prompt(prompt)
        if openai_response:
            return jsonify({'response': openai_response})
        else:
            return jsonify({'response': 'Failed to generate OpenAI response.'})





if __name__ == '__main__':
    input_file = "Document.txt"
    output_file = "output.txt"
    if(input("Insert new data? ") == "YES"):
        embed_chunks_and_save(input_file, output_file)
        vectors = create_vectors_for_index(output_file)
        index.upsert(vectors=vectors, namespace=ns)
        print("Vectors inserted into index.")
    else:
        print("Running on previous data")
    app.run(debug=True)