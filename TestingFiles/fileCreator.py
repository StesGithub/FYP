import requests
import json
import os

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma4"

test_documents = [
    #RESTRICTED
    ("patient_discharge_cardiology_murphy.txt", "Generate a realistic hospital patient discharge summary for a cardiology patient. Include patient name, diagnosis, medications prescribed and follow up instructions. 150-200 words."),
    ("surgical_notes_appendectomy_2024.txt", "Generate realistic surgical operation notes for an appendectomy procedure. Include surgeon name, anaesthetist, procedure details and post op instructions. 150-200 words."),
    ("mri_referral_neurology_dept.txt", "Generate a realistic MRI referral letter from a GP to a neurology department for a patient with headaches. Include patient details, symptoms and urgency. 150-200 words."),
    ("psychiatric_assessment_inpatient.txt", "Generate a realistic psychiatric inpatient assessment note. Include presenting complaint, mental state examination and risk assessment. 150-200 words."),
    ("oncology_chemotherapy_protocol.txt", "Generate realistic oncology treatment notes for a chemotherapy patient. Include diagnosis, treatment protocol, dosage and monitoring plan. 150-200 words."),
    
    # INTERNAL
    ("staff_memo_infection_control.txt", "Generate a realistic hospital internal staff memo about updated infection control procedures. No patient data. Professional tone. 150 words."),
    ("department_handover_notes_icu.txt", "Generate realistic ICU department handover notes between nursing shifts. General ward status, staffing levels, no specific patient names. 150 words."),
    ("incident_report_equipment_failure.txt", "Generate a realistic hospital internal incident report about a non-patient equipment failure in a ward. Staff names and departments only. 150 words."),
    ("hr_memo_annual_leave_policy.txt", "Generate a realistic hospital HR memo to all staff about updated annual leave booking procedures. 150 words."),
    ("training_completion_record_fire_safety.txt", "Generate a realistic hospital internal training completion record for fire safety training across departments. 150 words."),
    
    # PUBLIC
    ("visiting_hours_policy_2024.txt", "Generate a realistic hospital public visiting hours policy document. General information suitable for public display. 150 words."),
    ("patient_rights_information_leaflet.txt", "Generate a realistic hospital patient rights information leaflet suitable for public distribution. 150 words."),
    ("cafeteria_menu_week_april.txt", "Generate a realistic hospital cafeteria weekly menu. No medical content. 100 words."),
    
    # AMBIGUOUS - to test failsafe
    ("invoice_medical_supplies_q1.txt", "Generate a realistic hospital invoice for medical supplies. Include supplier name, itemised costs, payment terms. Could contain some medical terminology. 150 words."),
    ("referral_letter_physiotherapy.txt", "Generate a realistic internal referral letter to physiotherapy. Minimal patient clinical detail, mostly administrative. 150 words."),
]

os.makedirs("test_documents", exist_ok=True)

for filename, prompt in test_documents:
    print(f"Generating {filename}...")
    
    response = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    })
    
    if response.status_code == 200:
        text = response.json().get('response', '').strip()
        with open(f"test_documents/{filename}", 'w') as f:
            f.write(text)
        print(f"✅ {filename}")
    else:
        print(f"❌ Failed: {filename}")

print("\nAll test documents generated!")