import requests
import json
import csv
import time
import os

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"

INTERNAL_DOCUMENT_TYPES = [
    "internal staff memo regarding patient care procedures",
    "interdepartmental referral letter between hospital departments",
    "staff performance review document",
    "internal incident report non patient related",
    "hospital policy update memo to clinical staff",
    "internal meeting minutes from department heads",
    "staff training completion record",
    "internal audit report on hospital procedures",
    "employee absence and leave request documentation",
    "internal budget allocation memo",
    "staff roster and shift scheduling document",
    "internal complaint handling procedure document",
    "hospital department handover notes",
    "internal equipment maintenance request",
    "staff onboarding documentation"
]

def generate_document(doc_type, index):
    prompt = f"""Generate a realistic hospital internal administrative document of type: {doc_type}

Requirements:
- Must contain NO patient names, patient data, diagnoses, medications or direct patient medical information
- May reference general patient care procedures or policies but NOT specific patient cases
- Should contain realistic staff roles such as Doctor, Nurse, Administrator, Department Head
- Should be realistic and professional in tone
- Should be between 100-300 words
- May contain general medical department names like Cardiology, Oncology, Emergency etc
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
    total = len(INTERNAL_DOCUMENT_TYPES) * 55  # 55 per type = ~825 total
    count = 0

    os.makedirs('internalData', exist_ok=True)

    print(f"Generating {total} INTERNAL class documents...")
    print("Make sure Ollama is running: ollama serve")
    print()

    for doc_type in INTERNAL_DOCUMENT_TYPES:
        print(f"Generating documents for: {doc_type}")

        for i in range(55):
            count += 1
            print(f"Progress: {count}/{total}", end='\r')

            text = generate_document(doc_type, i)

            if text:
                documents.append({
                    'transcription': text,
                    'medical_specialty': 'Internal Administrative',
                    'access_level': 'INTERNAL',
                    'source': 'generated',
                    'doc_type': doc_type
                })

            time.sleep(0.5)

    print(f"\nGenerated {len(documents)} documents successfully!")

    output_file = 'internalData/generated_internal_data.csv'
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['transcription', 'medical_specialty', 'access_level', 'source', 'doc_type'])
        writer.writeheader()
        writer.writerows(documents)

    print(f"Saved to {output_file}")
    print(f"Total documents: {len(documents)}")

if __name__ == "__main__":
    main()