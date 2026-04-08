import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from torch.optim import AdamW
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import pickle

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

MODEL_NAME = 'dmis-lab/biobert-base-cased-v1.2'
MAX_LENGTH = 512
BATCH_SIZE = 16
EPOCHS = 3
LEARNING_RATE = 2e-5

LABEL_MAP = {'PUBLIC': 0, 'INTERNAL': 1, 'RESTRICTED': 2}
ID_TO_LABEL = {v: k for k, v in LABEL_MAP.items()}

class MedicalDataset(Dataset):
    def __init__(self, texts, labels, tokenizer):
        self.encodings = tokenizer(
            list(texts), truncation=True, padding=True,
            max_length=MAX_LENGTH, return_tensors='pt'
        )
        self.labels = torch.tensor(labels, dtype=torch.long)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return {
            'input_ids': self.encodings['input_ids'][idx],
            'attention_mask': self.encodings['attention_mask'][idx],
            'labels': self.labels[idx]
        }

def map_sensitivity(specialty):
    restricted = [
        'Surgery', 'Cardiovascular / Pulmonary', 'Neurology',
        'Neurosurgery', 'Hematology - Oncology', 'Nephrology',
        'Psychiatry / Psychology', 'Obstetrics / Gynecology',
        'Pediatrics - Neonatal', 'Emergency Room Reports',
        'Discharge Summary', 'Radiology', 'Orthopedic',
        'General Medicine', 'Urology', 'ENT - Otolaryngology',
        'Ophthalmology', 'Gastroenterology', 'Dermatology',
        'Allergy / Immunology', 'Endocrinology', 'Rheumatology',
        'Pain Management', 'Podiatry', 'Autopsy',
        'Lab Medicine - Pathology', 'Hospice - Palliative Care',
        'Cosmetic / Plastic Surgery', 'Bariatrics', 'Dentistry',
        'Chiropractic', 'Sleep Medicine'
    ]
    internal = [
        'Consult - History and Phy.', 'SOAP / Chart / Progress Notes',
        'Office Notes', 'Letters', 'IME-QME-Work Comp etc.',
        'Physical Medicine - Rehab', 'Speech - Language',
        'Diets and Nutritions'
    ]
    if specialty in restricted:
        return 'RESTRICTED'
    elif specialty in internal:
        return 'INTERNAL'
    else:
        return 'PUBLIC'

print("Loading datasets...")

# MTSamples
df_medical = pd.read_csv('../data/mtsamples.csv')
df_medical['medical_specialty'] = df_medical['medical_specialty'].str.strip()
df_medical = df_medical.dropna(subset=['transcription'])
df_medical['access_level'] = df_medical['medical_specialty'].apply(map_sensitivity)

# Generated PUBLIC
df_public = pd.read_csv('../data/generated_public_data.csv')

# Generated INTERNAL
df_internal = pd.read_csv('../data/generated_internal_data.csv')

# Generated RESTRICTED PII
df_restricted_pii = pd.read_csv('../data/generated_restricted_pii_data.csv')

# Combine all
df = pd.concat([
    df_medical[['transcription', 'access_level']],
    df_public[['transcription', 'access_level']],
    df_internal[['transcription', 'access_level']],
    df_restricted_pii[['transcription', 'access_level']]
], ignore_index=True)

print(f"Total samples: {len(df)}")
print("Class distribution:")
print(df['access_level'].value_counts())

df['label'] = df['access_level'].map(LABEL_MAP)

X_train, X_test, y_train, y_test = train_test_split(
    df['transcription'].values, df['label'].values,
    test_size=0.2, random_state=42, stratify=df['label'].values
)

print(f"\nTraining samples: {len(X_train)}")
print(f"Testing samples: {len(X_test)}")

print(f"\nLoading {MODEL_NAME}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=3)
model.to(device)
print("Model loaded!")

print("\nTokenizing datasets...")
train_dataset = MedicalDataset(X_train, y_train, tokenizer)
test_dataset = MedicalDataset(X_test, y_test, tokenizer)

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE)

optimizer = AdamW(model.parameters(), lr=LEARNING_RATE)

print(f"\nTraining for {EPOCHS} epochs...")
for epoch in range(EPOCHS):
    model.train()
    total_loss = 0
    correct = 0
    total = 0

    for batch_idx, batch in enumerate(train_loader):
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        labels = batch['labels'].to(device)

        optimizer.zero_grad()
        outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
        loss = outputs.loss
        loss.backward()
        optimizer.step()

        total_loss += loss.item()
        preds = torch.argmax(outputs.logits, dim=1)
        correct += (preds == labels).sum().item()
        total += labels.size(0)

        if batch_idx % 50 == 0:
            print(f"Epoch {epoch+1}/{EPOCHS} | Batch {batch_idx}/{len(train_loader)} | Loss: {loss.item():.4f}")

    print(f"\nEpoch {epoch+1} complete — Avg Loss: {total_loss/len(train_loader):.4f} | Train Accuracy: {correct/total:.4f}\n")

print("Evaluating...")
model.eval()
all_preds = []
all_labels = []

with torch.no_grad():
    for batch in test_loader:
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        labels = batch['labels'].to(device)

        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
        preds = torch.argmax(outputs.logits, dim=1)
        all_preds.extend(preds.cpu().numpy())
        all_labels.extend(labels.cpu().numpy())

pred_labels = [ID_TO_LABEL[p] for p in all_preds]
true_labels = [ID_TO_LABEL[l] for l in all_labels]

print(f"\nAccuracy: {accuracy_score(true_labels, pred_labels):.4f}")
print("\nClassification Report:")
print(classification_report(true_labels, pred_labels))

print("\nSaving model...")
model.save_pretrained('biobert_model_final')
tokenizer.save_pretrained('biobert_model_final')
print("Model saved to biobert_model_final/")