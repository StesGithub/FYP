import pandas as pd
import numpy as np
import pickle
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from tqdm import tqdm 




#Read the csv 
df = pd.read_csv('dataset/mtsamples.csv')
#Strip the whitespace from each speciality - Didnt inititally work
df['medical_specialty'] = df['medical_specialty'].str.strip()


#Print the first 10 unique values
print(df.columns.tolist())
print(df['medical_specialty'].unique()[:10])



print(f"Dataset size before pruning:{len(df)}" )

#Prune for null values
df = df.dropna(subset=['transcription'])

print(f"Dataset size after pruning:{len(df)}" )

#TODO Refine sensitivity mapping 
# Map specialities to access levels
def map_sensitivity(speciality):
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
    
    if speciality in restricted:
        return 'RESTRICTED'
    elif speciality in internal:
        return 'INTERNAL'   
    else:  
        return 'PUBLIC'
    

df['access_level'] = df['medical_specialty'].apply(map_sensitivity)

#Check distribution
print("Class distribution:")
print(df['access_level'].value_counts())
print(f"\nTotal samples: {len(df)}")
print(f"Unmapped: {df['access_level'].isna().sum()}")

#Features and labels
X = df['transcription']
y = df['access_level']

#Train test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)


print(f"\nTraining samples: {len(X_train)}")
print(f"Testing samples: {len(X_test)}")

#TODO random forest for now - will need to look into other algorihtms and tuning
#TODO Full inquiry into different algorithms Naive Bayes, Logisitic regression, Linear SVM (Maybe)
pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(
        max_features=10000,
        ngram_range=(1, 2),
        stop_words='english',
        min_df=2
    )),
    ('clf', RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        n_jobs=-1,
        verbose=1  
    ))
])

# Train
print("\nTraining model...")
pipeline.fit(X_train, y_train)
print("Training complete!")

# Evaluate
y_pred = pipeline.predict(X_test)
print(f"\nAccuracy: {accuracy_score(y_test, y_pred):.4f}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred))

#Save model
with open('model.pkl', 'wb') as f:
    pickle.dump(pipeline, f)

print("\nModel saved as model.pkl")