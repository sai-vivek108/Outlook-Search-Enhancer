# import os
# import json
# import datetime
# import re
# from whoosh import index
# from whoosh.fields import Schema, TEXT, ID, KEYWORD, NUMERIC, DATETIME
# from whoosh.analysis import RegexTokenizer
# from whoosh.index import create_in, open_dir
# from whoosh.qparser import MultifieldParser, OrGroup
# from whoosh.query import Term, Or, And, DateRange, FuzzyTerm
# from whoosh import scoring
# import spacy
# from nltk.corpus import wordnet
# from dateutil.parser import parse as dateutil_parse

# # Constants
# INDEX_DIR = "EmailIndex_new"
# MAIN_DATA_FILE = "cleaned_data.jsonl"

# # Load spaCy model
# nlp = spacy.load("en_core_web_trf")

# def create_schema():
#     return Schema(
#         docNo=NUMERIC(stored=True, unique=True),
#         docID=ID(stored=True),
#         sender=KEYWORD(stored=True, lowercase=True, commas=True),
#         recipient=KEYWORD(stored=True, lowercase=True, commas=True),
#         cc=KEYWORD(stored=True, lowercase=True, commas=True),
#         date=DATETIME(stored=True),
#         subject=TEXT(stored=True, analyzer=RegexTokenizer()),
#         body=TEXT(stored=True, analyzer=RegexTokenizer()),
#         thread_count=NUMERIC(stored=True),
#         people=KEYWORD(stored=True, lowercase=True, commas=True),
#         isRead=NUMERIC(stored=True),
#         receivedDateTime=DATETIME(stored=True)
#     )

# def preprocess_text(text):
#     doc = nlp(text)
#     return " ".join([token.lemma_ for token in doc if not token.is_stop])

# def parse_date(date_str):
#     return datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S%z')

# def extract_entities(subject, body):
#     doc = nlp(subject + " " + body)
#     return [ent.text for ent in doc.ents if ent.label_ in ["PERSON", "ORG"]]

# def build_index():
#     count = 0
#     if not os.path.exists(INDEX_DIR):
#         os.mkdir(INDEX_DIR)
#     idx = create_in(INDEX_DIR, create_schema()) if not index.exists_in(INDEX_DIR) else open_dir(INDEX_DIR)
#     writer = idx.writer()
#     with open(MAIN_DATA_FILE, 'r', encoding='utf-8') as f:
#         for line in f:
#             count += 1
#             data = json.loads(line)
#             people = extract_entities(data.get('subject', ''), data.get('body', ''))
#             writer.add_document(
#                 docNo=data['docNo'],
#                 docID=data['id'],
#                 sender=data.get('from', ''),
#                 recipient=",".join(data.get('to', [])),
#                 cc=",".join(data.get('cc', [])),
#                 date=parse_date(data.get('date', "2023-01-01 00:00:00+00:00")),
#                 subject=preprocess_text(data.get('subject', '')),
#                 body=preprocess_text(data.get('body', '')),
#                 thread_count=data.get('thread_count', 1),
#                 people=",".join(people),
#                 isRead=int(data.get('isRead', False)),
#                 receivedDateTime=parse_date(data.get('receivedDateTime', '2023-01-01 00:00:00+00:00'))
#             )
#             if count % 100 == 0:
#                 print("finished docs:   ", count, '\t', datetime.datetime.now())
#     writer.commit()

# def filtered_synonyms(token_text, token_pos):
#     synsets = wordnet.synsets(token_text)
#     synonyms = set()
#     original_token = nlp(token_text)[0]
#     for s in synsets:
#         for lemma in s.lemmas():
#             candidate = lemma.name().replace('_', ' ')
#             candidate_token = nlp(candidate)
#             if candidate_token and candidate_token[0].pos_ == original_token.pos_:
#                 if original_token.has_vector and candidate_token[0].has_vector:
#                     if original_token.similarity(candidate_token[0]) > 0.6:
#                         synonyms.add(candidate)
#     return synonyms

# def expand_text_with_synonyms(text):
#     doc = nlp(text)
#     expanded_tokens = []
#     for token in doc:
#         if not token.is_stop and not token.is_punct and token.has_vector:
#             expanded_tokens.append(token.lemma_)
#             if token.pos_ in ["NOUN", "PROPN", "ADJ", "VERB", "ADV"]:
#                 syns = filtered_synonyms(token.lemma_)
#                 expanded_tokens.extend(list(syns))
#     return " ".join(expanded_tokens)

# def interpret_query(query_str):
#     doc = nlp(query_str.lower())
#     person_entities = [ent.text for ent in doc.ents if ent.label_ in ["PERSON", "ORG", "GPE"]]

#     keywords = []
#     for token in doc:
#         if not token.is_stop and not token.is_punct:
#             keywords.append(token.lemma_)

#     # Check if user wants to search sender or recipients
#     # This is a very naive approach: if query contains "from", assume sender; if "to" or "received by", assume recipient.
#     # You can tailor this logic further as needed.
#     search_sender = any(token.lemma_ in ["send", "sent", "from"] for token in doc)
#     search_recipients = any(token.lemma_ in ["receive", "recipient", "receiver", "to"] for token in doc)

#     # Extract and parse date entities
#     date_entities = [ent.text for ent in doc.ents if ent.label_ == "DATE"]
#     start_date, end_date = None, None
#     for d in date_entities:
#         try:
#             parsed_date = dateutil_parse(d, fuzzy=True)
#             # Assuming user gives one date meaning exact day
#             start_date = parsed_date
#             end_date = parsed_date + datetime.timedelta(days=1)
#         except ValueError:
#             continue

#     return person_entities, keywords, search_sender, search_recipients, (start_date, end_date)


# def extract_email_addresses(query_str):
#     # New function to extract emails directly from the query
#     EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
#     return EMAIL_REGEX.findall(query_str)

# def build_generic_query(idx, query_str):
#     # Extract explicit email addresses first
#     emails = extract_email_addresses(query_str)
#     person_entities, keywords, search_sender, search_recipients, date_range = interpret_query(query_str)
    
#     subqueries = []

#     # If emails are found, directly query sender/recipient fields
#     if emails:
#         email_subqueries = []
#         for email in emails:
#             # If user says "from", query sender field; if "to", query recipient field.
#             # If not specified, we can search both fields.
#             if search_sender and not search_recipients:
#                 # Only sender
#                 email_subqueries.append(Or([Term("sender", email), FuzzyTerm("sender", email, maxdist=2)]))
#             elif search_recipients and not search_sender:
#                 # Only recipient
#                 email_subqueries.append(Or([Term("recipient", email), FuzzyTerm("recipient", email, maxdist=2)]))
#             else:
#                 # Check both sender and recipient if no specific clue
#                 email_subqueries.append(Or([
#                     Term("sender", email), 
#                     FuzzyTerm("sender", email, maxdist=2),
#                     Term("recipient", email),
#                     FuzzyTerm("recipient", email, maxdist=2)
#                 ]))
#         if email_subqueries:
#             subqueries.append(Or(email_subqueries))

#     # Handle person entities only if we did not handle emails or if we want to combine
#     if person_entities:
#         person_subqueries = []
#         for p in person_entities:
#             if search_sender:
#                 person_subqueries.append(Or([Term("sender", p), FuzzyTerm("sender", p, maxdist=2)]))
#             if search_recipients:
#                 person_subqueries.append(Or([Term("recipient", p), FuzzyTerm("recipient", p, maxdist=2)]))
#         if person_subqueries:
#             subqueries.append(Or(person_subqueries))

#     # Add keyword queries
#     if keywords:
#         qp = MultifieldParser(["subject", "body"], schema=idx.schema, fieldboosts={"subject": 2.0, "body": 1.0}, group=OrGroup)
#         query_str_expanded = []
#         for kw in keywords:
#             query_str_expanded.append(f"({kw} OR {kw}~2)")
#         final_keyword_query = " OR ".join(query_str_expanded)
#         keyword_query = qp.parse(final_keyword_query)
#         subqueries.append(keyword_query)

#     # Add date range query if applicable
#     if date_range[0] is not None:
#         start, end = date_range
#         date_query = DateRange("date", start, end)
#         subqueries.append(date_query)

#     # Fallback to a simple full-text query if no subqueries
#     if not subqueries:
#         qp = MultifieldParser(["subject", "body"], schema=idx.schema, fieldboosts={"subject": 2.0, "body": 1.0}, group=OrGroup)
#         fallback_query = qp.parse(query_str)
#         return fallback_query

#     return And(subqueries)

# def query_emails(query_str, limit=20):
#     idx = open_dir(INDEX_DIR)
#     q = build_generic_query(idx, query_str)
#     print("Query:   ", q)
#     with idx.searcher(weighting=scoring.BM25F()) as searcher:
#         results = searcher.search(q, limit=limit)
#         return [(result['docNo'], result['sender'], result['subject']) for result in results]

# def main():
#     # Uncomment if you need to build the index
#     # build_index()
#     # Example query:
#     results = query_emails("fetch me emails from anc527")
#     print("Results:", results)

# if __name__ == "__main__":
#     main()


import os
import json
import datetime
import re
from whoosh import index
from whoosh.fields import Schema, TEXT, ID, KEYWORD, NUMERIC, DATETIME
from whoosh.analysis import RegexTokenizer
from whoosh.index import create_in, open_dir
from whoosh.qparser import MultifieldParser, OrGroup
from whoosh.query import Term, Or, And, DateRange, FuzzyTerm, Prefix
from whoosh.query import Wildcard
from whoosh import scoring
import spacy
from nltk.corpus import wordnet
from dateutil.parser import parse as dateutil_parse

# Constants
INDEX_DIR = "EmailIndex_new"
MAIN_DATA_FILE = "cleaned_data.jsonl"

nlp = spacy.load("en_core_web_trf")

def create_schema():
    return Schema(
        docNo=NUMERIC(stored=True, unique=True),
        docID=ID(stored=True),
        sender=KEYWORD(stored=True, lowercase=True, commas=True),
        recipient=KEYWORD(stored=True, lowercase=True, commas=True),
        cc=KEYWORD(stored=True, lowercase=True, commas=True),
        date=DATETIME(stored=True),
        subject=TEXT(stored=True, analyzer=RegexTokenizer()),
        body=TEXT(stored=True, analyzer=RegexTokenizer()),
        thread_count=NUMERIC(stored=True),
        people=KEYWORD(stored=True, lowercase=True, commas=True),
        isRead=NUMERIC(stored=True),
        receivedDateTime=DATETIME(stored=True)
    )

def preprocess_text(text):
    doc = nlp(text)
    return " ".join([token.lemma_ for token in doc if not token.is_stop])

def parse_date(date_str):
    return datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S%z')

def extract_entities(subject, body):
    doc = nlp(subject + " " + body)
    return [ent.text for ent in doc.ents if ent.label_ in ["PERSON", "ORG"]]


def build_index():
    count = 0
    if not os.path.exists(INDEX_DIR):
        os.mkdir(INDEX_DIR)
    idx = create_in(INDEX_DIR, create_schema()) if not index.exists_in(INDEX_DIR) else open_dir(INDEX_DIR)
    writer = idx.writer()
    with open(MAIN_DATA_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            count += 1
            data = json.loads(line)
            people = extract_entities(data.get('subject', ''), data.get('body', ''))
            writer.add_document(
                docNo=data['docNo'],
                docID=data['id'],
                sender=data.get('from', ''),
                recipient=",".join(data.get('to', [])),
                cc=",".join(data.get('cc', [])),
                date=parse_date(data.get('date', "2023-01-01 00:00:00+00:00")),
                subject=preprocess_text(data.get('subject', '')),
                body=preprocess_text(data.get('body', '')),
                thread_count=data.get('thread_count', 1),
                people=",".join(people),
                isRead=int(data.get('isRead', False)),
                receivedDateTime=parse_date(data.get('receivedDateTime', '2023-01-01 00:00:00+00:00'))
            )
            if count % 100 == 0:
                print("finished docs:", count, datetime.datetime.now())
    writer.commit()

def filtered_synonyms(token_text, token_pos):
    synsets = wordnet.synsets(token_text)
    synonyms = set()
    original_token = nlp(token_text)[0]
    for s in synsets:
        for lemma in s.lemmas():
            candidate = lemma.name().replace('_', ' ')
            candidate_token = nlp(candidate)
            if candidate_token and candidate_token[0].pos_ == original_token.pos_:
                if original_token.has_vector and candidate_token[0].has_vector:
                    if original_token.similarity(candidate_token[0]) > 0.6:
                        synonyms.add(candidate)
    return synonyms

def expand_text_with_synonyms(text):
    doc = nlp(text)
    expanded_tokens = []
    for token in doc:
        if not token.is_stop and not token.is_punct and token.has_vector:
            expanded_tokens.append(token.lemma_)
            if token.pos_ in ["NOUN", "PROPN", "ADJ", "VERB", "ADV"]:
                syns = filtered_synonyms(token.lemma_)
                expanded_tokens.extend(list(syns))
    return " ".join(expanded_tokens)

def detect_sender_recipient_intent(query_str, doc):
    # Detect sender intent
    search_sender = any(
        phrase in query_str.lower()
        for phrase in ["received from", "sent by", "from", "authored by", "emailed by", "written by"]
    ) or any(
        token.lemma_ in ["send", "author", "email", "write"] and token.head.text.lower() in ["from", "by"]
        for token in doc
    )

    # Detect recipient intent
    search_recipients = any(
        phrase in query_str.lower()
        for phrase in ["sent to", "to", "delivered to", "addressed to", "copied to", "sent toward"]
    ) or any(
        token.lemma_ in ["receive", "send", "address", "deliver", "copy"] and token.head.text.lower() in ["to", "toward"]
        for token in doc
    )

    return search_sender, search_recipients


def interpret_query(query_str):
    doc = nlp(query_str.lower())
    person_entities = [ent.text for ent in doc.ents if ent.label_ in ["PERSON", "ORG", "GPE"]]

    keywords = []
    for token in doc:
        if not token.is_stop and not token.is_punct:
            keywords.append(token.lemma_)

    search_sender, search_recipients = detect_sender_recipient_intent(query_str, doc)

    date_entities = [ent.text for ent in doc.ents if ent.label_ == "DATE"]
    start_date, end_date = None, None
    for d in date_entities:
        try:
            parsed_date = dateutil_parse(d, fuzzy=True)
            start_date = parsed_date
            end_date = parsed_date + datetime.timedelta(days=1)
        except ValueError:
            continue

    return person_entities, keywords, search_sender, search_recipients, (start_date, end_date)

EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

def extract_email_addresses(query_str):
    return EMAIL_REGEX.findall(query_str)

def build_generic_query(idx, query_str):
    emails = extract_email_addresses(query_str)
    person_entities, keywords, search_sender, search_recipients, date_range = interpret_query(query_str)
    
    subqueries = []

    # If exact emails found, query them directly
    if emails:
        email_subqueries = []
        for email in emails:
            if search_sender and not search_recipients:
                email_subqueries.append(Or([Term("sender", email), Prefix("sender", email)]))
                email_subqueries.append(Or([Term("cc", email), Prefix("cc", email)]))

            elif search_recipients and not search_sender:
                email_subqueries.append(Or([Term("recipient", email), Prefix("recipient", email)]))
                email_subqueries.append(Or([Term("cc", email), Prefix("cc", email)]))
            else:
                email_subqueries.append(Or([
                    Term("sender", email), Prefix("sender", email),
                    Term("recipient", email), Prefix("recipient", email),
                    Term("cc", email), Prefix("cc", email)
                ]))
        if email_subqueries:
            subqueries.append(Or(email_subqueries))

    # If we have person entities and no direct emails
    if person_entities:
        print("Person Entities:   ", person_entities)
        person_subqueries = []
        for p in person_entities:
            print("Wild card:   ", Wildcard("sender", p))
            if search_sender:
                person_subqueries.append(Or([Term("sender", p), Prefix("sender", p)]))

            if search_recipients:
                person_subqueries.append(Or([Term("recipient", p), Prefix("recipient", p)]))
        if person_subqueries:
            subqueries.append(Or(person_subqueries))

    # Add keyword queries for subject/body
    if keywords:
        qp = MultifieldParser(["subject", "body"], schema=idx.schema, fieldboosts={"subject": 2.0, "body": 1.0}, group=OrGroup)
        query_str_expanded = []
        for kw in keywords:
            query_str_expanded.append(f"({kw} OR {kw}~2)")
        final_keyword_query = " OR ".join(query_str_expanded)
        keyword_query = qp.parse(final_keyword_query)
        subqueries.append(keyword_query)

    # Date range filter if needed
    if date_range[0] is not None:
        start, end = date_range
        date_query = DateRange("date", start, end)
        subqueries.append(date_query)

    # If no subqueries yet, try a fallback:
    # For example, if the query is "fetch me emails from anc123" and we didn't get an entity or email:
    # Try fuzzy/wildcard queries on sender/recipient directly.
    if not subqueries:
        # Attempt a fallback on sender/recipient with wildcard or fuzzy matches
        # We'll try each keyword as if it might be part of an email.
        fallback_subqueries = []
        for kw in keywords:
            # Try fuzzy match on sender and recipient
            fallback_subqueries.append(Or([
                Prefix("sender", kw),
                Wildcard("sender", kw + "*"),
                Prefic("recipient", kw),
                Wildcard("recipient", kw + "*")
            ]))
        if fallback_subqueries:
            subqueries.append(Or(fallback_subqueries))

    # If still no subqueries formed, fall back to a simple full-text search
    if not subqueries:
        qp = MultifieldParser(["subject", "body"], schema=idx.schema, fieldboosts={"subject":2.0, "body":1.0}, group=OrGroup)
        fallback_query = qp.parse(query_str)
        return fallback_query

    return And(subqueries)

def query_emails(query_str, limit=20):
    idx = open_dir(INDEX_DIR)
    q = build_generic_query(idx, query_str)
    print("Query:   ", q)
    with idx.searcher(weighting=scoring.BM25F()) as searcher:
        results = searcher.search(q, limit=limit)
        return [(result['docNo'], result['sender'], result['subject']) for result in results]

def main():
    # Uncomment if you need to build the index
    # build_index()
    # Test the fallback mechanism:
    results = query_emails("fetch me emails  sent to anc527")
    print("Results:", results)

if __name__ == "__main__":
    main()
