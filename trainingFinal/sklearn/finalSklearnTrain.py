import pandas as pd
import pickle
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

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

df_medical = pd.read_csv('../data/mtsamples.csv')
df_medical['medical_specialty'] = df_medical['medical_specialty'].str.strip()
df_medical = df_medical.dropna(subset=['transcription'])
df_medical['access_level'] = df_medical['medical_specialty'].apply(map_sensitivity)

df_public = pd.read_csv('../data/generated_public_data.csv')
df_internal = pd.read_csv('../data/generated_internal_data.csv')
df_restricted_pii = pd.read_csv('../data/generated_restricted_pii_data.csv')

df = pd.concat([
    df_medical[['transcription', 'access_level']],
    df_public[['transcription', 'access_level']],
    df_internal[['transcription', 'access_level']],
    df_restricted_pii[['transcription', 'access_level']]
], ignore_index=True)

print(f"Total samples: {len(df)}")
print("Class distribution:")
print(df['access_level'].value_counts())

X_train, X_test, y_train, y_test = train_test_split(
    df['transcription'].values, df['access_level'].values,
    test_size=0.2, random_state=42, stratify=df['access_level'].values
)

print(f"\nTraining samples: {len(X_train)}")
print(f"Testing samples: {len(X_test)}")

print("\nTraining Logistic Regression...")
pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(
        max_features=10000,
        ngram_range=(1, 2),
        stop_words='english',
        min_df=2
    )),
    ('clf', LogisticRegression(
        random_state=42,
        max_iter=1000,
        class_weight='balanced'
    ))
])

pipeline.fit(X_train, y_train)
y_pred = pipeline.predict(X_test)

print(f"\nAccuracy: {accuracy_score(y_test, y_pred):.4f}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred))

with open('../data/model_final.pkl', 'wb') as f:
    pickle.dump(pipeline, f)

print("\nModel saved as model_final.pkl!")