import requests
import json
import csv
import time

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"  

#Document types to generate
PUBLIC_DOCUMENT_TYPES = [
    "hospital cafeteria weekly menu",
    "ward cleaning schedule and rota",
    "staff car park maintenance notice",
    "hospital visiting hours notice",
    "staff meeting minutes",
    "fire safety notice",
    "hospital gym and wellness facilities notice",
    "staff canteen price list",
    "building maintenance schedule",
    "hospital recycling and waste disposal notice",
    "staff social club newsletter",
    "general health and safety notice",
    "hospital map and directions notice",
    "staff training schedule",
    "hospital events and activities notice"
]

def generate_document(doc_type, index):
    prompt = f"""Generate a realistic hospital administrative document of type: {doc_type}

Requirements:
- Must contain absolutely NO patient names, patient data, diagnoses, medications or any medical information
- Must contain NO personally identifiable information (PII) such as staff names, phone numbers, emails or ID numbers
- Should be realistic and professional in tone
- Should be between 100-300 words
- Do not include any headers like "Document:" just write the document content directly

Generate the document now:"""

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        if response.status_code == 200:
            result = response.json()
            return result.get('response', '').strip()
        else:
            print(f"Error {response.status_code} for {doc_type}")
            return None
    except Exception as e:
        print(f"Error generating {doc_type}: {str(e)}")
        return None

def main():
    documents = []
    total = len(PUBLIC_DOCUMENT_TYPES) * 40  #40 documents per type = 600 total
    count = 0

    print(f"Generating {total} PUBLIC class documents...")
    print("Make sure Ollama is running: ollama serve")
    print()

    for doc_type in PUBLIC_DOCUMENT_TYPES:
        print(f"Generating documents for: {doc_type}")
        
        for i in range(40):  # 40 per type
            count += 1
            print(f"Progress: {count}/{total}", end='\r')
            
            text = generate_document(doc_type, i)
            
            if text:
                documents.append({
                    'transcription': text,
                    'medical_specialty': 'Public Administrative',
                    'access_level': 'PUBLIC',
                    'source': 'generated',
                    'doc_type': doc_type
                })
            
            time.sleep(0.5)  #Small delay to not overwhelm Ollama

    print(f"\nGenerated {len(documents)} documents successfully!")

    # Save to CSV
    output_file = 'nonSensData/generated_public_data.csv'
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['transcription', 'medical_specialty', 'access_level', 'source', 'doc_type'])
        writer.writeheader()
        writer.writerows(documents)

    print(f"Saved to {output_file}")
    print(f"Total documents: {len(documents)}")

if __name__ == "__main__":
    main()