import os
from whoosh.index import open_dir
from whoosh.qparser import QueryParser
from whoosh import scoring
from indexReader import MyIndexReader
from indexWriter import MyIndexWriter
from nltk.stem import PorterStemmer
from nltk.corpus import stopwords
import json

def preProcessText(text):
    content = ''
    split_text = text.split()
    stemmer = PorterStemmer()
    stopwords_list = stopwords.words('english')
    for i in  split_text:
        if i in stopwords_list:
            continue
        else:
            word = stemmer.stem(i)
            content+=word+' '
    return content.strip()

def writeIndex():
    docNo=0
    indexWriter = MyIndexWriter()
    with open("cleaned_data.jsonl", 'r', encoding='utf-8') as docs:
        for doc in docs:
            doc_data = json.loads(doc)
            # print(doc)
            if doc_data is None:
                indexWriter.close()
                return ''
            else:
                docNo+=1
                subject = preProcessText(doc_data['subject'])
                body = preProcessText(doc_data['body'])
                indexWriter.index(docNo, doc_data['id'], subject , body)
    indexWriter.close()


def queryRetrieval(query):
    prep_query = preProcessText(query)
    index = open_dir(os.path.join(os.getcwd(), 'WhooshIndex'))
    query_obj = QueryParser("body", index.schema)
    parsed_query = query_obj.parse(prep_query)
    print(parsed_query)
    with index.searcher(weighting=scoring.BM25F()) as searcher:
        results = searcher.search(parsed_query, limit = 15)
        if results:
            for result in results:
                print(result['docNo'], '\t', result['subject'])
        else:
            print('no results found')

# writeIndex()
queryRetrieval('potential research opportunity')#