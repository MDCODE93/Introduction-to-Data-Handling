"""
Rogel-Salazar (RS-1): Data Science and Analytics with Python
Chapters 1-3 — companion script.

Ch 1  Trade Winds Set in Motion: ML & Data Analysis  (conceptual; brief notes)
Ch 2  Python: For Something Completely Different      (language + NumPy/pandas/matplotlib)
Ch 3  The Machine Learning Landscape                  (supervised vs unsupervised,
                                                       train/test split, bias-variance,
                                                       regression + classification demos)

How to run
----------
- Open in VS Code, ensure interpreter is the 'sds' conda env.
- Use the "Run Cell" link above each `# %%` block, or run the whole file with ▶.
- Or from terminal:   conda activate sds && python rs1_ch1_3.py
"""

# %% [markdown]
# # Chapter 1 — Trade Winds Set in Motion
# Conceptual only. Key take-aways to keep in mind while coding:
#
# 1. **Data science** ≈ statistics + computer science + domain expertise.
# 2. **ML taxonomy**: supervised (labels) vs unsupervised (no labels) vs reinforcement.
# 3. **Goal split**: prediction (data science) vs causal explanation (econometrics).
# 4. **Workflow**: question → data → clean → explore → model → evaluate → communicate.

# %%
print("Chapter 1: conceptual — no code to run. Moving on.")

# %% [markdown]
# # Chapter 2 — Python language refresher

# %% Basic types and control flow
x = 42
pi = 3.14159
name = "Martin"
flags = [True, False, True]

for i, f in enumerate(flags):
    label = "on" if f else "off"
    print(f"flag[{i}] = {label}")

# %% Functions, comprehensions, lambdas
def standardise(values):
    """Return (x - mean) / sd for a list of numbers."""
    m = sum(values) / len(values)
    var = sum((v - m) ** 2 for v in values) / len(values)
    sd = var ** 0.5
    return [(v - m) / sd for v in values]

z = standardise([10, 12, 9, 11, 13, 8])
print("z-scores:", [round(v, 3) for v in z])

square = lambda n: n * n
squares = [square(n) for n in range(6)]
print("squares 0..5:", squares)

# %% A minimal class
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age
    def greet(self):
        return f"Hi, I'm {self.name} ({self.age})."

print(Person("Ada", 36).greet())

# %% NumPy essentials
import numpy as np

rng = np.random.default_rng(seed=42)
a = rng.normal(loc=0, scale=1, size=1000)
print("array shape :", a.shape)
print("mean / sd   :", round(a.mean(), 3), round(a.std(), 3))

A = np.arange(12).reshape(3, 4)
print("A =\n", A)
print("A.T =\n", A.T)
print("A @ A.T =\n", A @ A.T)

# %% pandas essentials
import pandas as pd

df = pd.DataFrame({
    "country": ["DK", "DK", "SE", "SE", "DE", "DE"],
    "year":    [2020, 2021, 2020, 2021, 2020, 2021],
    "gdp_pc":  [60000, 62000, 55000, 56000, 47000, 48000],
    "unemp":   [4.6, 4.2, 8.3, 7.9, 3.8, 3.5],
})
print(df)

print("\nGroup means by country:")
print(df.groupby("country")[["gdp_pc", "unemp"]].mean())

print("\nWide → long:")
long = df.melt(id_vars=["country", "year"], var_name="indicator", value_name="value")
print(long.head())

# %% Matplotlib essentials
import matplotlib.pyplot as plt

fig, ax = plt.subplots(1, 2, figsize=(9, 3.2))
ax[0].hist(a, bins=40, edgecolor="white")
ax[0].set_title("Standard-normal sample (n=1000)")
ax[0].set_xlabel("value"); ax[0].set_ylabel("count")

for c, sub in df.groupby("country"):
    ax[1].plot(sub["year"], sub["gdp_pc"], marker="o", label=c)
ax[1].set_title("GDP per capita")
ax[1].set_xlabel("year"); ax[1].set_ylabel("GDP pc"); ax[1].legend()

fig.tight_layout()
fig.savefig("rs1_ch2_plots.png", dpi=120)
print("Saved rs1_ch2_plots.png")

# %% [markdown]
# # Chapter 3 — The Machine Learning Landscape
# We illustrate the core ideas with two small, classical scikit-learn datasets:
#
# - **Regression** on the diabetes dataset (predict disease progression).
# - **Classification** on the iris dataset (3-class flower species).
#
# Concepts demonstrated:
# 1. Train/test split
# 2. Pipelines + standardisation
# 3. A simple model and a slightly more flexible model
# 4. Evaluation metrics
# 5. Bias-variance illustration via cross-validated learning curves

# %% Regression demo
from sklearn.datasets import load_diabetes
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score

X, y = load_diabetes(return_X_y=True)
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, random_state=0)

pipe_ols = Pipeline([("sc", StandardScaler()), ("ols", LinearRegression())])
pipe_rdg = Pipeline([("sc", StandardScaler()), ("rdg", Ridge(alpha=1.0))])

for name, model in [("OLS", pipe_ols), ("Ridge", pipe_rdg)]:
    model.fit(X_tr, y_tr)
    pred = model.predict(X_te)
    print(f"{name:5s}  RMSE={mean_squared_error(y_te, pred, squared=False):6.2f}  "
          f"R²={r2_score(y_te, pred):.3f}")

# %% Classification demo
from sklearn.datasets import load_iris
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

X, y = load_iris(return_X_y=True)
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.30, random_state=0,
                                          stratify=y)

logit = Pipeline([("sc", StandardScaler()),
                  ("clf", LogisticRegression(max_iter=500))])
rf    = RandomForestClassifier(n_estimators=300, random_state=0)

for name, model in [("Logistic", logit), ("RandomForest", rf)]:
    model.fit(X_tr, y_tr)
    pred = model.predict(X_te)
    print(f"\n{name} — accuracy = {accuracy_score(y_te, pred):.3f}")
    print("confusion matrix:\n", confusion_matrix(y_te, pred))

print("\nClassification report (RF):")
print(classification_report(y_te, rf.predict(X_te),
                            target_names=load_iris().target_names))

# %% Bias-variance via learning curve
from sklearn.model_selection import learning_curve

X, y = load_diabetes(return_X_y=True)
model = Pipeline([("sc", StandardScaler()), ("rdg", Ridge(alpha=1.0))])

sizes, train_scores, test_scores = learning_curve(
    model, X, y,
    train_sizes=np.linspace(0.1, 1.0, 8),
    cv=5, scoring="r2", random_state=0)

train_mean = train_scores.mean(axis=1)
test_mean  = test_scores.mean(axis=1)

fig, ax = plt.subplots(figsize=(6, 4))
ax.plot(sizes, train_mean, "o-", label="train R²")
ax.plot(sizes, test_mean,  "s-", label="CV R²")
ax.set_xlabel("training set size"); ax.set_ylabel("R²")
ax.set_title("Learning curve — Ridge on diabetes")
ax.legend(); ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig("rs1_ch3_learning_curve.png", dpi=120)
print("Saved rs1_ch3_learning_curve.png")

# %% Cross-validation summary
cv_r2 = cross_val_score(model, X, y, cv=10, scoring="r2")
print(f"\n10-fold CV R²:  mean = {cv_r2.mean():.3f}   sd = {cv_r2.std():.3f}")

# %% [markdown]
# ## Exercises (try on your own)
# 1. Replace `Ridge` with `Lasso` and inspect which coefficients are zeroed.
# 2. On iris, add a `KNeighborsClassifier` and compare CV accuracy across k = 1, 3, 5, 15.
# 3. Load `easySHARE` (your thesis subset), pick a binary outcome (e.g. unmet_any),
#    and run the same logistic-regression pipeline on a few covariates.
# 4. Reproduce the learning curve for `RandomForestRegressor(n_estimators=200)`
#    — does the gap between train and CV R² shrink or grow?

print("\n--- end of RS-1 Ch. 1-3 script ---")
