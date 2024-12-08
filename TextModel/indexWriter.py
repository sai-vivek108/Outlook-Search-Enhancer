import os
# import Classes.Path as Path
from whoosh import index
from whoosh.fields import Schema, TEXT, KEYWORD, ID, STORED, NUMERIC
from whoosh.analysis import RegexTokenizer


# Efficiency and memory cost should be paid with extra attention.
class MyIndexWriter:
    def __init__(self):
        path_dir = "D:\MSIS\SEM_III\ISR\project\Whooshindex"
        if not os.path.exists(path_dir):
            os.mkdir(path_dir)
        schema = Schema(docNo=NUMERIC(stored=True),
            ID=ID(stored=True),  # Store id
            subject=TEXT(stored=True),  # Store the subject
            body=TEXT(analyzer=RegexTokenizer(), stored=True))  # Tokenize and store body

        # Create index if it doesn't exist
        if not index.exists_in(path_dir):
            self.indexing = index.create_in(path_dir, schema)
        else:
            self.indexing = index.open_dir(path_dir)
        self.writer = self.indexing.writer()
        return

    # This method build index for each document.
    def index(self,docNo, ID, subject, body):
        self.writer.add_document(docNo=docNo, ID=ID, subject=subject, body=body)

    # Close the index writer
    def close(self):
        self.writer.commit()
        return
