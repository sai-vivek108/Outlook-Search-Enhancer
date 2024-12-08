import json
import regex as re

def clean_text(text):
    # Remove image URLs using regex
    text = text.replace('\n',' ')
    # text = re.sub(r'http[^\s]+(?:\.jpg|\.png|\.gif|\.jpeg)', '', text, flags=re.IGNORECASE)
    
    # Remove HTML tags (such as <img>, <a>, etc.)
    text = re.sub(r'<.*?>', '', text)

    # Remove links (URLs), keeping only meaningful text
    text = re.sub(r'http[s]?://[^\s]+', '', text)
    text = re.sub(r'\b\w{15,}\b', '', text)
    # text = re.sub(r'\b\w{1,3}\b', '', text)
    # print(text)
    # Remove email headers, footers, and any other irrelevant sections
    text = re.sub(r'(?i)unsubscribe|preferences|submit a story|event|.*pitt.edu.*', '', text, flags=re.IGNORECASE)
    
    # Remove any non-text elements (like special characters, unnecessary spaces)
    text = re.sub(r'[^\w\s]', ' ', text)  # Remove non-alphanumeric characters except spaces
    text = re.sub(r'\s+', ' ', text)     # Replace multiple spaces with a single space
    text = text.strip().lower()                  # Remove leading/trailing whitespaces
    # print(text)
    return text

with open('cleaned_data.jsonl', 'a', encoding= 'utf-8') as content:
    with open('deleted_items.jsonl', 'r', encoding='utf-8') as file:
        for line in file:
            data = json.loads(line)
            cleaned_data = clean_text(data['body'])
            cleaned_subject = clean_text(data['subject'])
            # json_obj.append(data)
            # print(data)
            record = {
                "id": data['id'],
                "from": data['from'],
                "to": data['to'],
                "isRead": data['isRead'],
                "subject": cleaned_subject,
                "body": cleaned_data,
                "receivedDateTime": data['receivedDateTime']
                }
            content.write(json.dumps(record, ensure_ascii=False)+'\n')



# filtered=''
# word_pattern = re.compile(r'\b\w+\b')
# for match in word_pattern.finditer(text_obj['body']):
#     filtered+=''.join(match.group(0)+' ')

# print(text_obj['body'])