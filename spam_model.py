import pandas as pd, pickle
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

data = pd.read_csv("spam.csv", encoding="latin-1")
if "v1" in data.columns:
    data = data[["v1","v2"]].rename(columns={"v1":"label","v2":"message"})
else:
    data = data[["label","message"]]

X, y = data["message"], data["label"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

vec   = CountVectorizer()
model = MultinomialNB()
model.fit(vec.fit_transform(X_train), y_train)
pred  = model.predict(vec.transform(X_test))

metrics = {
    "accuracy":         accuracy_score(y_test, pred),
    "precision":        precision_score(y_test, pred, pos_label="spam"),
    "recall":           recall_score(y_test, pred, pos_label="spam"),
    "f1":               f1_score(y_test, pred, pos_label="spam"),
    "confusion_matrix": confusion_matrix(y_test, pred).tolist(),
}

pickle.dump(model,   open("model.pkl","wb"))
pickle.dump(vec,     open("vectorizer.pkl","wb"))
pickle.dump(metrics, open("metrics.pkl","wb"))

print("Model trained!")
for k,v in metrics.items():
    if k != "confusion_matrix": print(f"  {k}: {round(v*100,2)}%")