
# -*- coding: utf-8 -*-
"""Assignment 2 tfidf and LDA.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1983MLMRqMRjEQu4LQxFNE-UCBJR64oVB
"""

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import nltk
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer
import string
import re
import scipy
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.naive_bayes import GaussianNB, MultinomialNB
from sklearn.metrics import accuracy_score, confusion_matrix

import warnings
warnings.filterwarnings("ignore")

"""We read the csv's to makes a dataframe to work on"""

df = pd.read_csv("data/processed_twitter_data_with_index.csv", encoding = "ISO-8859-1")
df.head()

"""description column has some missing columns, fill them with empyt space strings ('')."""

df['description'] = df['description'].apply(lambda x: '' if pd.isnull(x) else x)

"""check if is_bot has empty columns, unknown values

-> get assumed to be human?

-> get dropped?
"""

print(df.isnull().sum())
print(len(df))
#df['is_bot'] = df['is_bot'].apply(lambda x: 0 if pd.isnull(x) else x)
df = df.dropna(axis=0, subset=["is_bot"])
print(df.isnull().sum())
print(len(df))

print()
print(df['is_bot'].value_counts())

"""We extract the text columns also add, Unnamed index, is_bot and _golden for separating data later"""

text_df = df[['Unnamed: 0', 'description', 'name', 'text', 'is_bot', "_golden"]]
text_df.head(10)

"""mark any text+description that has hyperlinks and then delete hyperlinks from text"""

text_df["text_has_hyperlink"] = text_df["text"].apply(lambda x: 1 if ('http' in x) else 0)
text_df["text"]= text_df["text"].apply(lambda x: re.sub(r"\S*http\S+", "", x))

text_df["desc_has_hyperlink"] = text_df["description"].apply(lambda x: 1 if ('http' in x) else 0)
text_df["description"]= text_df["description"].apply(lambda x: re.sub(r"\S*http\S+", "", x))

"""emojis and other things leads to lots of encoding issues
take out all not basic latin encode
"""

basic_latin = [chr(i) for i in range(32, 126+1)]
def is_basic_latin_only(string):
  basic_latin_only = 1
  for i in range(len(string)):
    if not (string[i] in basic_latin):
      basic_latin_only = 0
  return basic_latin_only

text_df["text_basic_latin_only"] = text_df["text"].apply(lambda x: is_basic_latin_only(x))

def filter_basic_latin(string):
  filter_char_list = []
  for i in range(len(string)):
    if not (string[i] in basic_latin):
      filter_char_list.append(string[i])
  for char in filter_char_list:
    string = re.sub(r"\S*"+char+r"\S*", "", string)
  return string

text_df["text"] = text_df["text"].apply(lambda x: filter_basic_latin(x))

text_df["desc_basic_latin_only"] = text_df["description"].apply(lambda x: is_basic_latin_only(x))
text_df["description"] = text_df["description"].apply(lambda x: filter_basic_latin(x))

"""Tokenize description and text
We try two kinds of tokenizations:
 One is the recommended tokenization in general (destructive)
 One is good for tweets apparently (casual)
"""

nltk.download('punkt')

def token_column(func_df, column, token_func):
  tokens_list = []
  for i in func_df.index:
    column_i = func_df.loc[i, column]
    #convert all to lower case/Capital Case/UPPER case(?) for easier comparison later
    column_i = column_i.lower()
    column_tokens_i = token_func(column_i)
    tokens_list.append(column_tokens_i)
  return tokens_list

#text_df['text_token_destructive'] = token_column(text_df, 'text', nltk.word_tokenize)
#text_df['description_token_destructive'] = token_column(text_df, 'description', nltk.word_tokenize)

from nltk.tokenize import TweetTokenizer

text_df['text_token_casual'] = token_column(text_df, 'text', TweetTokenizer().tokenize)
text_df['description_token_casual'] = token_column(text_df, 'description', TweetTokenizer().tokenize)

#print(text_df.head())

#print(text_df[['text_token_destructive', 'description_token_destructive']].head(10))

print(text_df[['text_token_casual', 'description_token_casual']].head(10))

"""Change words based off lemmatisation."""

nltk.download('wordnet')
def lemmatization_filter_column(func_df, token_column):
  filtered_token_list_list = []
  for i in func_df.index:
    filtered_token_list = []
    token_list_i = func_df.loc[i, token_column]
    for word in token_list_i:
      pos_list = [wordnet.NOUN, wordnet.VERB, wordnet.ADJ, wordnet.ADV]
      lemma_word = word
      j = 0
      while (lemma_word == word) and j<len(pos_list):
        if (word in ['was', 'has']):
          break
        lemma_word = WordNetLemmatizer().lemmatize(word, pos=pos_list[j])
        j += 1
      filtered_token_list.append(lemma_word)
    filtered_token_list_list.append(filtered_token_list)
  return filtered_token_list_list

#text_df['text_token_destructive_filtered'] = lemmatization_filter_column(text_df, 'text_token_destructive_filtered')
#text_df['description_token_destructive_filtered'] = lemmatization_filter_column(text_df, 'description_token_destructive_filtered')

text_df['text_token_casual_filtered'] = lemmatization_filter_column(text_df, 'text_token_casual')
text_df['description_token_casual_filtered'] = lemmatization_filter_column(text_df, 'description_token_casual')

#print(text_df[['text_token_destructive_filtered', 'description_token_destructive_filtered']].head(10))

print(text_df[['text_token_casual_filtered', 'description_token_casual_filtered']].head(10))

"""list of stopwords to consider filtering"""

nltk.download('stopwords')
my_stopwords = stopwords.words('english')
#add anymore you think are legitimate and missing
my_stopwords.extend(["i'd", "i'm", "i've", "n't"])
#remove really common words/topics not already in stopwords
generic_words = ["get", "make", "like", "look",
                     "come", "love", "weather",
                     "see", "follow", "go",
                     "one", "new", "best", "good"]
my_stopwords.extend(generic_words)
my_stopwords.extend(["time", "year", "month", "week", "day"]) #time periods
  #due to bad grammar of Tweets, add in contractions that leave out the apostrophe
  #in the destructive tokenization, the end of a contraction is prepended with an apostrophe -- reflect this
L = len(my_stopwords)
for i in range(L):
  if "'" in my_stopwords[i]:
    temp_word = my_stopwords[i].replace("'", "")
    my_stopwords.append(temp_word)

    temp_word = my_stopwords[i][my_stopwords[i].index("'"):]
    my_stopwords.append(temp_word)
my_stopwords = list(set(my_stopwords))
print(my_stopwords)

"""Create a filtered version via the stopwords"""

def stopwords_filter_column(func_df, token_column):
  filtered_token_list_list = []
  for i in func_df.index:
    filtered_token_list = []
    token_list_i = func_df.loc[i, token_column]
    for word in token_list_i:
      if not (word in my_stopwords):
        filtered_token_list.append(word)
    filtered_token_list_list.append(filtered_token_list)
  return filtered_token_list_list

#text_df['text_token_destructive_filtered'] = stopwords_filter_column(text_df, 'text_token_destructive')
#text_df['description_token_destructive_filtered'] = stopwords_filter_column(text_df, 'description_token_destructive')

text_df['text_token_casual_filtered'] = stopwords_filter_column(text_df, 'text_token_casual_filtered')
text_df['description_token_casual_filtered'] = stopwords_filter_column(text_df, 'description_token_casual_filtered')

#print(text_df[['text_token_destructive_filtered', 'description_token_destructive_filtered']].head(10))

print(text_df[['text_token_casual_filtered', 'description_token_casual_filtered']].head(10))

"""Have a look at the TFIDF"""

#text_df['text_destructive_filtered'] = text_df['text_token_destructive_filtered'].apply(lambda x: ' '.join(x))
#text_df['description_destructive_filtered'] = text_df['description_token_destructive_filtered'].apply(lambda x: ' '.join(x))
text_df['text_casual_filtered'] = text_df['text_token_casual_filtered'].apply(lambda x: ' '.join(x))
text_df['description_casual_filtered'] = text_df['description_token_casual_filtered'].apply(lambda x: ' '.join(x))

def tfidf_df(func_df, column):
  vectorizer = TfidfVectorizer()
  vectors = vectorizer.fit_transform(func_df[column])
  feature_names = vectorizer.get_feature_names_out()
  #dense = vectors.todense()
  #dense_list = dense.tolist()
  """this method wasnt scaling well enough,
  the sparse matrix (crs in scipy) method toarray worked very well"""
  dense_list = vectors.toarray()
  df = pd.DataFrame(dense_list, columns=feature_names)
  return df

#text_destructive_tfidf_df = tfidf_df(text_df, 'text_destructive_filtered')
#description_destructive_tfidf_df = tfidf_df(text_df, 'description_destructive_filtered')
text_casual_tfidf_df = tfidf_df(text_df, 'text_casual_filtered')
text_casual_tfidf_df.index = text_df.index

description_casual_tfidf_df = tfidf_df(text_df, 'description_casual_filtered')
description_casual_tfidf_df.index = text_df.index

"""
print(len(text_destructive_tfidf_df))
print(text_destructive_tfidf_df.head(10))
for i in text_destructive_tfidf_df.index[:10]:
  series = pd.Series(text_destructive_tfidf_df.iloc[i])
  result = series.to_numpy().nonzero()
  ''''''
  features = []
  for r in result:
    features.append(text_destructive_tfidf_df.columns[r])
  ''''''
  values = []
  for r in result:
    values.append(text_destructive_tfidf_df.iloc[i,r])
  print(result)
  #print(features)
  print(values)
"""
display = True
if display:
    #!pip install wordcloud
    from wordcloud import WordCloud
    import matplotlib.pyplot as plt

    Cloud = WordCloud(background_color="white", max_words=50).generate_from_frequencies(text_casual_tfidf_df.T.sum(axis=1))
    plt.figure()
    plt.imshow(Cloud, interpolation="bilinear")
    plt.axis("off")
    plt.show()

    print(text_casual_tfidf_df.T.sum(axis=1).sort_values(ascending=False).head(50))

    temp_df = text_casual_tfidf_df[text_df['is_bot']==1]
    Cloud = WordCloud(background_color="white", max_words=50).generate_from_frequencies(temp_df.T.sum(axis=1))
    plt.figure()
    plt.imshow(Cloud, interpolation="bilinear")
    plt.axis("off")
    plt.show()

    print(temp_df.T.sum(axis=1).sort_values(ascending=False).head(50))

    temp_df = text_casual_tfidf_df[text_df['is_bot']==0]
    Cloud = WordCloud(background_color="white", max_words=50).generate_from_frequencies(temp_df.T.sum(axis=1))
    plt.figure()
    plt.imshow(Cloud, interpolation="bilinear")
    plt.axis("off")
    plt.show()

    print(print(temp_df.T.sum(axis=1).sort_values(ascending=False).head(50)))

    Cloud = WordCloud(background_color="white", max_words=50).generate_from_frequencies(description_casual_tfidf_df.T.sum(axis=1))
    plt.figure()
    plt.imshow(Cloud, interpolation="bilinear")
    plt.axis("off")
    plt.show()

    print(print(description_casual_tfidf_df.T.sum(axis=1).sort_values(ascending=False).head(50)))

    temp_df = description_casual_tfidf_df[text_df['is_bot']==1]
    Cloud = WordCloud(background_color="white", max_words=50).generate_from_frequencies(temp_df.T.sum(axis=1))
    plt.figure()
    plt.imshow(Cloud, interpolation="bilinear")
    plt.axis("off")
    plt.show()

    print(temp_df.T.sum(axis=1).sort_values(ascending=False).head(50))

    temp_df = description_casual_tfidf_df[text_df['is_bot']==0]
    Cloud = WordCloud(background_color="white", max_words=50).generate_from_frequencies(temp_df.T.sum(axis=1))
    plt.figure()
    plt.imshow(Cloud, interpolation="bilinear")
    plt.axis("off")
    plt.show()

    print(temp_df.T.sum(axis=1).sort_values(ascending=False).head(50))

"""Some insights:
brands use more numbers in their tweets.
brands top three tweet words: "weather", "channel" and "update".
non-brands top three tweet words: "get", "make" and "go" (doesnt really have much information in it).
brand top three description words: "news", "follow", "update"
non-brands top three description words: "love", "like", "life"

Insights after filtering more stopwords:
brands top three tweet words: "channel", "update", "15"
non-brands top three tweet words: "one", "time", "know"
brand top three description words: "news", "update", "tweet"
non-brand top three description words: "live", "life", "fan"

choice of tokenizer doesn't seem to matter --> should I just use casual since that is supposedly used specifically for Twitter/tweets? (probs)

how many top words to use?
uses numbers in tweets as a discriminator?

take numbers out of tokenisation and try again?
"""

text_df = df[['description', 'name', 'text', 'is_bot', '_golden']]

text_df["text_has_hyperlink"] = text_df["text"].apply(lambda x: ('http' in x))
text_df["text"]= text_df["text"].apply(lambda x: re.sub(r"\S*http\S+", "", x))

text_df["desc_has_hyperlink"] = text_df["description"].apply(lambda x: ('http' in x))
text_df["description"]= text_df["description"].apply(lambda x: re.sub(r"\S*http\S+", "", x))

text_df["text_basic_latin_only"] = text_df["text"].apply(lambda x: is_basic_latin_only(x))
text_df["text"] = text_df["text"].apply(lambda x: filter_basic_latin(x))

text_df["desc_basic_latin_only"] = text_df["description"].apply(lambda x: is_basic_latin_only(x))
text_df["description"] = text_df["description"].apply(lambda x: filter_basic_latin(x))

#filter out number words

def has_number(string):
  without_number = True
  for i in range(len(string)):
    if (string[i] in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]):
      without_number = False
  if without_number:
    return 0
  else:
    return 1


text_df["text_has_number"] = text_df["text"].apply(lambda x: has_number(x))

def filter_number(string):
  filter_char_list = []
  for i in range(len(string)):
    if (string[i] in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]):
      filter_char_list.append(string[i])
  for char in filter_char_list:
    string = re.sub(r"\S*"+char+r"\S*", "", string)
  return string

text_df["text"] = text_df["text"].apply(lambda x: filter_number(x))

text_df["desc_has_number"] = text_df["description"].apply(lambda x: has_number(x))
text_df["description"] = text_df["description"].apply(lambda x: filter_number(x))

print(text_df[['text_has_number', 'desc_has_number']].head(10))

text_df['text_token_casual'] = token_column(text_df, 'text', TweetTokenizer().tokenize)
text_df['description_token_casual'] = token_column(text_df, 'description', TweetTokenizer().tokenize)

#token filters

text_df['text_token_casual_filtered'] = lemmatization_filter_column(text_df, 'text_token_casual')
text_df['description_token_casual_filtered'] = lemmatization_filter_column(text_df, 'description_token_casual')

text_df['text_token_casual_filtered'] = stopwords_filter_column(text_df, 'text_token_casual_filtered')
text_df['description_token_casual_filtered'] = stopwords_filter_column(text_df, 'description_token_casual_filtered')

print(text_df[['text_token_casual_filtered', 'description_token_casual_filtered']].head(70))

text_df['text_casual_filtered'] = text_df['text_token_casual_filtered'].apply(lambda x: ' '.join(x))
text_df['description_casual_filtered'] = text_df['description_token_casual_filtered'].apply(lambda x: ' '.join(x))

text_casual_tfidf_df = tfidf_df(text_df, 'text_casual_filtered')
text_casual_tfidf_df.index = text_df.index
description_casual_tfidf_df = tfidf_df(text_df, 'description_casual_filtered')
description_casual_tfidf_df.index = text_df.index

def combine_tfidf_df(func_df, column1, column2):
  vectorizer1 = TfidfVectorizer()
  vectors1 = vectorizer1.fit_transform(func_df[column1])
  feature_names1 = vectorizer1.get_feature_names_out()
  #dense = vectors.todense()
  #dense_list = dense.tolist()
  """this method wasnt scaling well enough,
  the sparse matrix (crs in scipy) method toarray worked very well"""

  vectorizer2 = TfidfVectorizer()
  vectors2 = vectorizer2.fit_transform(func_df[column2])
  feature_names2 = vectorizer2.get_feature_names_out()
  #dense = vectors.todense()
  #dense_list = dense.tolist()
  """this method wasnt scaling well enough,
  the sparse matrix (crs in scipy) method toarray worked very well"""

  feature_names = np.append(feature_names1, feature_names2)
  vectors = scipy.sparse.hstack((vectors1, vectors2))
  dense_list = vectors.toarray()
  dense_list = dense_list.astype(np.float32)
  df = pd.DataFrame(dense_list, columns=feature_names)
  return df

casual_tfidf_df = combine_tfidf_df(text_df, 'text_casual_filtered', 'description_casual_filtered')
casual_tfidf_df.index = text_df.index

if display:
    Cloud = WordCloud(background_color="white", max_words=50).generate_from_frequencies(text_casual_tfidf_df.T.sum(axis=1))
    plt.figure()
    plt.imshow(Cloud, interpolation="bilinear")
    plt.axis("off")
    plt.show()

    print(text_casual_tfidf_df.T.sum(axis=1).sort_values(ascending=False).head(50))

    temp_df = text_casual_tfidf_df[text_df['is_bot']==1]
    Cloud = WordCloud(background_color="white", max_words=50).generate_from_frequencies(temp_df.T.sum(axis=1))
    plt.figure()
    plt.imshow(Cloud, interpolation="bilinear")
    plt.axis("off")
    plt.show()

    print(temp_df.T.sum(axis=1).sort_values(ascending=False).head(50))

    temp_df = text_casual_tfidf_df[text_df['is_bot']==0]
    Cloud = WordCloud(background_color="white", max_words=50).generate_from_frequencies(temp_df.T.sum(axis=1))
    plt.figure()
    plt.imshow(Cloud, interpolation="bilinear")
    plt.axis("off")
    plt.show()

    print(print(temp_df.T.sum(axis=1).sort_values(ascending=False).head(50)))

    Cloud = WordCloud(background_color="white", max_words=50).generate_from_frequencies(description_casual_tfidf_df.T.sum(axis=1))
    plt.figure()
    plt.imshow(Cloud, interpolation="bilinear")
    plt.axis("off")
    plt.show()

    print(print(description_casual_tfidf_df.T.sum(axis=1).sort_values(ascending=False).head(50)))

    temp_df = description_casual_tfidf_df[text_df['is_bot']==1]
    Cloud = WordCloud(background_color="white", max_words=50).generate_from_frequencies(temp_df.T.sum(axis=1))
    plt.figure()
    plt.imshow(Cloud, interpolation="bilinear")
    plt.axis("off")
    plt.show()

    print(temp_df.T.sum(axis=1).sort_values(ascending=False).head(50))

    temp_df = description_casual_tfidf_df[text_df['is_bot']==0]
    Cloud = WordCloud(background_color="white", max_words=50).generate_from_frequencies(temp_df.T.sum(axis=1))
    plt.figure()
    plt.imshow(Cloud, interpolation="bilinear")
    plt.axis("off")
    plt.show()

    print(temp_df.T.sum(axis=1).sort_values(ascending=False).head(50))
    
    print()
    
    print("both")
    print(casual_tfidf_df.T.sum(axis=1).sort_values(ascending=False).head(50))
    print()
    print("both bot")
    print(casual_tfidf_df[text_df['is_bot']==1].T.sum(axis=1).sort_values(ascending=False).head(50))
    print()
    print("both not bot")
    print(casual_tfidf_df[text_df['is_bot']==0].T.sum(axis=1).sort_values(ascending=False).head(50))

"""compare length of tokens in one document and length of tokens in corpus
"""

print("Average length of tokens: "+ str(text_df['text_token_casual_filtered'].apply(len).mean()
                                        + text_df['description_token_casual_filtered'].apply(len).mean()))
print("Total number of tokens: " + str(len(casual_tfidf_df.columns)))

"""
Remove all the leftover columns to save.
"""

text_df = text_df.drop(['text_casual_filtered', 'description_casual_filtered',
                        'text_token_casual', 'description_token_casual',
                        'description', 'text', 'name'], axis=1)

print(text_df.head())

"""save to csv"""

text_df.to_csv('data/twitter_text_data_processed.csv')

"""
create a preprocessing function to be able to make a classifier on the dataset train_data and test_data
"""
def preprocess_df(target):
    df = pd.read_csv("data/processed_twitter_data_with_index.csv", encoding = "ISO-8859-1")
    target_df = target
    
    df = df.set_index("Unnamed: 0", verify_integrity=True)
    target_df = target_df.set_index("Unnamed: 0", verify_integrity=True)

    """description column has some missing columns, fill them with empyt space strings ('')."""

    df['description'] = df['description'].apply(lambda x: '' if pd.isnull(x) else x)

    basic_latin = [chr(i) for i in range(32, 126+1)]
    def is_basic_latin_only(string):
      basic_latin_only = 1
      for i in range(len(string)):
        if not (string[i] in basic_latin):
          basic_latin_only = 0
      return basic_latin_only
      
    def filter_basic_latin(string):
      filter_char_list = []
      for i in range(len(string)):
        if not (string[i] in basic_latin):
          filter_char_list.append(string[i])
      for char in filter_char_list:
        string = re.sub(r"\S*"+char+r"\S*", "", string)
      return string

    def token_column(func_df, column, token_func):
      tokens_list = []
      for i in func_df.index:
        column_i = func_df.loc[i, column]
        #convert all to lower case/Capital Case/UPPER case(?) for easier comparison later
        column_i = column_i.lower()
        column_tokens_i = token_func(column_i)
        tokens_list.append(column_tokens_i)
      return tokens_list


    from nltk.tokenize import TweetTokenizer

    """Change words based off lemmatisation."""
    def lemmatization_filter_column(func_df, token_column):
      filtered_token_list_list = []
      for i in func_df.index:
        filtered_token_list = []
        token_list_i = func_df.loc[i, token_column]
        for word in token_list_i:
          pos_list = [wordnet.NOUN, wordnet.VERB, wordnet.ADJ, wordnet.ADV]
          lemma_word = word
          j = 0
          while (lemma_word == word) and j<len(pos_list):
            if (word in ['was', 'has']):
              break
            lemma_word = WordNetLemmatizer().lemmatize(word, pos=pos_list[j])
            j += 1
          filtered_token_list.append(lemma_word)
        filtered_token_list_list.append(filtered_token_list)
      return filtered_token_list_list

    """list of stopwords to consider filtering"""

    my_stopwords = stopwords.words('english')
    #add anymore you think are legitimate and missing
    my_stopwords.extend(["i'd", "i'm", "i've", "n't"])
    #remove really common words/topics not already in stopwords
    generic_words = ["get", "make", "like", "look",
                         "come", "love", "weather",
                         "see", "follow", "go",
                         "one", "new", "best", "good"]
    my_stopwords.extend(generic_words)
    my_stopwords.extend(["time", "year", "month", "week", "day"]) #time periods
      #due to bad grammar of Tweets, add in contractions that leave out the apostrophe
      #in the destructive tokenization, the end of a contraction is prepended with an apostrophe -- reflect this
    L = len(my_stopwords)
    for i in range(L):
      if "'" in my_stopwords[i]:
        temp_word = my_stopwords[i].replace("'", "")
        my_stopwords.append(temp_word)

        temp_word = my_stopwords[i][my_stopwords[i].index("'"):]
        my_stopwords.append(temp_word)
    my_stopwords = list(set(my_stopwords))

    """Create a filtered version via the stopwords"""

    def stopwords_filter_column(func_df, token_column):
      filtered_token_list_list = []
      for i in func_df.index:
        filtered_token_list = []
        token_list_i = func_df.loc[i, token_column]
        for word in token_list_i:
          if not (word in my_stopwords):
            filtered_token_list.append(word)
        filtered_token_list_list.append(filtered_token_list)
      return filtered_token_list_list

    text_df = df[['description', 'name', 'text', 'is_bot', '_golden']]

    text_df["text_has_hyperlink"] = text_df["text"].apply(lambda x: ('http' in x))
    text_df["text"]= text_df["text"].apply(lambda x: re.sub(r"\S*http\S+", "", x))

    text_df["desc_has_hyperlink"] = text_df["description"].apply(lambda x: ('http' in x))
    text_df["description"]= text_df["description"].apply(lambda x: re.sub(r"\S*http\S+", "", x))

    text_df["text_basic_latin_only"] = text_df["text"].apply(lambda x: is_basic_latin_only(x))
    text_df["text"] = text_df["text"].apply(lambda x: filter_basic_latin(x))

    text_df["desc_basic_latin_only"] = text_df["description"].apply(lambda x: is_basic_latin_only(x))
    text_df["description"] = text_df["description"].apply(lambda x: filter_basic_latin(x))

    #filter out number words

    def has_number(string):
      without_number = True
      for i in range(len(string)):
        if (string[i] in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]):
          without_number = False
      if without_number:
        return 0
      else:
        return 1


    text_df["text_has_number"] = text_df["text"].apply(lambda x: has_number(x))

    def filter_number(string):
      filter_char_list = []
      for i in range(len(string)):
        if (string[i] in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]):
          filter_char_list.append(string[i])
      for char in filter_char_list:
        string = re.sub(r"\S*"+char+r"\S*", "", string)
      return string

    text_df["text"] = text_df["text"].apply(lambda x: filter_number(x))

    text_df["desc_has_number"] = text_df["description"].apply(lambda x: has_number(x))
    text_df["description"] = text_df["description"].apply(lambda x: filter_number(x))

    text_df['text_token_casual'] = token_column(text_df, 'text', TweetTokenizer().tokenize)
    text_df['description_token_casual'] = token_column(text_df, 'description', TweetTokenizer().tokenize)

    #token filters

    text_df['text_token_casual_filtered'] = lemmatization_filter_column(text_df, 'text_token_casual')
    text_df['description_token_casual_filtered'] = lemmatization_filter_column(text_df, 'description_token_casual')

    text_df['text_token_casual_filtered'] = stopwords_filter_column(text_df, 'text_token_casual_filtered')
    text_df['description_token_casual_filtered'] = stopwords_filter_column(text_df, 'description_token_casual_filtered')

    text_df['text_casual_filtered'] = text_df['text_token_casual_filtered'].apply(lambda x: ' '.join(x))
    text_df['description_casual_filtered'] = text_df['description_token_casual_filtered'].apply(lambda x: ' '.join(x))

    def combine_tfidf_df(func_df, column1, column2):
      vectorizer1 = TfidfVectorizer()
      vectors1 = vectorizer1.fit_transform(func_df[column1])
      feature_names1 = vectorizer1.get_feature_names_out()
      #dense = vectors.todense()
      #dense_list = dense.tolist()
      """this method wasnt scaling well enough,
      the sparse matrix (crs in scipy) method toarray worked very well"""

      vectorizer2 = TfidfVectorizer()
      vectors2 = vectorizer2.fit_transform(func_df[column2])
      feature_names2 = vectorizer2.get_feature_names_out()
      #dense = vectors.todense()
      #dense_list = dense.tolist()
      """this method wasnt scaling well enough,
      the sparse matrix (crs in scipy) method toarray worked very well"""

      feature_names = np.append(feature_names1, feature_names2)
      vectors = scipy.sparse.hstack((vectors1, vectors2))
      dense_list = vectors.toarray()
      dense_list = dense_list.astype(np.float32)
      df = pd.DataFrame(dense_list, columns=feature_names)
      return df

    casual_tfidf_df = combine_tfidf_df(text_df, 'text_casual_filtered', 'description_casual_filtered')
    casual_tfidf_df.index = text_df.index

    text_df = text_df.drop(['text_casual_filtered', 'description_casual_filtered',
                            'text_token_casual', 'description_token_casual',
                            'description', 'text', 'name'], axis=1)

    """Remove the non-numerical columns to prepare for classification."""
    """As well remove _golden because we're not using it directly"""

    class_text_df = text_df.drop(['_golden', 'text_token_casual_filtered', 'description_token_casual_filtered'],
                                 axis=1)
    class_text_df = casual_tfidf_df.join(class_text_df)
    class_text_df.index = text_df.index
    
    processed_df = class_text_df

    """reduce processed_df down to rows of just target_df"""

    processed_df = processed_df.reindex(target_df.index)
    
    return processed_df

train_df = pd.read_csv("data/train_data.csv")
test_df = pd.read_csv("data/test_data.csv")

train_df = preprocess_df(train_df)
test_df = preprocess_df(test_df)

X_train = train_df.drop(['is_bot'], axis=1)
y_train = train_df['is_bot']

X_test = test_df.drop(['is_bot'], axis=1)
y_test = test_df['is_bot']

"""Remove the non-numerical columns to prepare for classification in cross validation."""
"""As well remove _golden because we're not using it directly"""

class_text_df = text_df.drop(['_golden', 'text_token_casual_filtered', 'description_token_casual_filtered'],
                                 axis=1)
class_text_df = casual_tfidf_df.join(class_text_df)
class_text_df.index = text_df.index

X = class_text_df.drop(['is_bot'], axis = 1) 
y = class_text_df['is_bot']

"""Use the labels and the columns transformed into numerical data (mostly 0 and 1s but ah well) to train a classifier on the non-golden user data and validate on golden user.
"""

param_grid = {'alpha': [0, 1],
              'fit_prior': [False, True]}

analyse = True
if analyse:
    grid = GridSearchCV(MultinomialNB(), param_grid, refit = True, verbose = 3) 
    grid.fit(X_train, y_train)
    print(grid.best_params_)
    #{'alpha': 1, 'fit_prior': False}


    clf = MultinomialNB(alpha=1, fit_prior=False)
    scores_mnb_default = cross_val_score(clf, X, y, cv=10, scoring='accuracy', verbose=1)
    print('Accuracy range for Multinomial NB: [%.4f, %.4f]; mean: %.4f; std: %.4f\n'% (scores_mnb_default.min(), scores_mnb_default.max(), scores_mnb_default.mean(), scores_mnb_default.std()))

clf = MultinomialNB(alpha=1, fit_prior=False)
clf.fit(X_train, y_train)

y_pred = clf.predict(X_test)
accuracy = accuracy_score(y_pred, y_test)
print('Accuracy on test set is: %.4f\n' %accuracy)
matrix = confusion_matrix(y_test, y_pred)
print("     Human Bot (Predicted)")
print("Human " + str(matrix[0][0])+ "    " + str(matrix[0][1]))
print("Bot   " + str(matrix[1][0])+ "    " + str(matrix[1][1]))
print("(Actual)")
print('Estimated (log) probability of classess: \n', 
clf.class_log_prior_)
  #These are the same for fit_prior==False bc a uniform distribution was used
  #when fit_prior == True -> [-0.37789329 -1.15614699] == [log(0.68530362551) log(0.31469637622)]

