import numpy as np
import pymongo
import re
from pprint import pprint
from sklearn.cross_validation import KFold
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.grid_search import GridSearchCV
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline


def find_pull_requests(db, owner, repo, is_merged=True):
    query = {
        '$and': [
            {'owner': owner},
            {'repo': repo},
            {'closed_at': {'$ne': None}}
        ]
    }

    if is_merged:
        query['$and'].append({'merged_at': {'$ne': None}})
    else:
        query['$and'].append({'merged_at': None})

    return db.pull_requests.find(query)
    # return list(db.pull_requests.find(query))


# prepare database connection
client = pymongo.MongoClient('localhost', 27017)
db = client.msr14


# split full name into owner and repo
full_name = 'rails/rails'
owner, repo = full_name.split('/')


# extract merged or unmerged pull requests
m_pulls = find_pull_requests(db, owner, repo, is_merged=True)
u_pulls = find_pull_requests(db, owner, repo, is_merged=False)


# extract titles of pull requests
m_titles = [p['title'] for p in m_pulls]
u_titles = [p['title'] for p in u_pulls]


# remove square bracket tags
tag = re.compile('(^\[(.*?)\]|\[(.*?)\]$)', re.MULTILINE | re.DOTALL)
m_titles = [tag.sub('', t) for t in m_titles]
u_titles = [tag.sub('', t) for t in u_titles]


# prepare numpy arrays
X_orig = m_titles + u_titles
y_orig = ['merge' for _ in range(len(m_titles))] + ['unmerge' for _ in range(len(u_titles))]

X = np.asarray(X_orig)
y = np.asarray(y_orig)


# transform documents to tfidf vectors
vect = TfidfVectorizer(stop_words='english')
X_trans = vect.fit_transform(X)


# train naive bayes model with K-Fold
kf = KFold(n=len(X), n_folds=5, shuffle=True)

scores = []

for train_index, test_index in kf:
    X_train, X_test = X_trans[train_index], X_trans[test_index]
    y_train, y_test = y[train_index], y[test_index]

    clf = MultinomialNB()
    clf.fit(X_train, y_train)

    train_score = clf.score(X_train, y_train)
    test_score = clf.score(X_test, y_test)
    print('train:', train_score, 'test:', test_score)

    scores.append(test_score)

print('MEAN:', np.mean(scores), 'STDDEV:', np.std(scores))


'''
# train naive bayes model
pipeline = Pipeline([
    ('vect', TfidfVectorizer(stop_words='english')),
    ('clf', MultinomialNB())
])

parameters = {
    # 'vect__ngram_range': ((1, 1), (1, 2), (1, 3)),
    # 'vect__norm': ('l1', 'l2'),
    # 'vect__use_idf': (True, False),
    'vect__binary': (True, False),
    # 'vect__smooth_idf': (True, False),
}


grid_search = GridSearchCV(pipeline, parameters, n_jobs=-1, verbose=1)
grid_search.fit(X, y)
for grid_score in grid_search.grid_scores_:
    print(grid_score)
'''
