import requests
import json
import csv
import time
import os

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"

RESTRICTED_PII_DOCUMENT_TYPES = [
    "patient admission form with personal details",
    "patient insurance and billing record",
    "patient next of kin and emergency contact form",
    "patient registration document with contact details",
    "staff personal employment record",
    "patient GP referral letter with personal details",
    "patient discharge summary with contact information",
    "patient consent form with personal details",
    "hospital invoice and payment record",
    "patient appointment confirmation letter"
]

def generate_document(doc_type, index):
    prompt = f"""You are generating FICTIONAL synthetic training data for a machine learning research project at a university. 
This data will NEVER be used in a real system and contains only made-up information.

Generate a fictional synthetic hospital document of type: {doc_type}

Requirements:
- All names, addresses, phone numbers, emails and any personal details must be COMPLETELY FICTIONAL
- Use obviously fake details like "John Smith", "123 Main Street", "555-0100" style placeholder data
- Include obviously fake bank details to ensure realism while remaining entirely ficticious
- This is synthetic training data for an NLP classifier — no real people are involved
- Should be realistic in structure and format
- Should be between 100-250 words
- Include fictional personal details such as fake names, fake addresses, fake phone numbers where appropriate for the document type
- Do not include any headers like "Document:" just write the document content directly

Generate the fictional synthetic document now:"""

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
    total = len(RESTRICTED_PII_DOCUMENT_TYPES) * 60  # 60 per type = 600 total
    count = 0

    os.makedirs('restrictedPIIData', exist_ok=True)

    print(f"Generating {total} RESTRICTED PII documents...")
    print()

    for doc_type in RESTRICTED_PII_DOCUMENT_TYPES:
        print(f"Generating: {doc_type}")

        for i in range(60):
            count += 1
            print(f"Progress: {count}/{total}", end='\r')

            text = generate_document(doc_type, i)

            if text:
                documents.append({
                    'transcription': text,
                    'medical_specialty': 'Patient Administrative',
                    'access_level': 'RESTRICTED',
                    'source': 'generated',
                    'doc_type': doc_type
                })

            time.sleep(0.5)

    print(f"\nGenerated {len(documents)} documents successfully!")

    output_file = 'restrictedPIIData/generated_restricted_pii_data.csv'
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['transcription', 'medical_specialty', 'access_level', 'source', 'doc_type'])
        writer.writeheader()
        writer.writerows(documents)

    print(f"Saved to {output_file}")
    print(f"Total documents: {len(documents)}")

if __name__ == "__main__":
    main()