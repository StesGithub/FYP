import pandas as pd

df = pd.read_csv('ModelTraining/dataset/mtsamples.csv')
print(df['medical_specialty'].value_counts())
