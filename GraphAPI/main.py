import asyncio
import configparser
from msgraph.generated.models.o_data_errors.o_data_error import ODataError
from graph import Graph
from html2text import HTML2Text
import json

async def main():
    print('Python Graph Tutorial\n')

    # Load settings
    config = configparser.ConfigParser()
    config.read("D:\MSIS\SEM_III\ISR\project\GraphAPI\config.cfg")
    print(config.sections())
    azure_settings = config['azure']

    graph: Graph = Graph(azure_settings)

    await greet_user(graph)

    choice = -1

    while choice != 0:
        print('Please choose one of the following options:')
        print('0. Exit')
        print('1. Display access token')
        print('2. List my inbox')
        print('3. Send mail')
        print('4. Make a Graph call')
        print('5. List the items in deleted folder')

        try:
            choice = int(input())
        except ValueError:
            choice = -1

        try:
            if choice == 0:
                print('Goodbye...')
            elif choice == 1:
                await display_access_token(graph)
            elif choice == 2:
                await list_inbox(graph)
            elif choice == 3:
                await send_mail(graph)
            elif choice == 4:
                await make_graph_call(graph)
            elif choice == 5:
                await list_deleted_items(graph)
            else:
                print('Invalid choice!\n')
        except ODataError as odata_error:
            print('Error:')
            if odata_error.error:
                print(odata_error.error.code, odata_error.error.message)

async def greet_user(graph: Graph):
    user = await graph.get_user()
    if user:
        print('Hello,', user.display_name)
        # Personal accounts, email is in userPrincipalName
        print('Email:', user.mail or user.user_principal_name, '\n')

async def display_access_token(graph: Graph):
    token = await graph.get_user_token()
    print('User token:', token, '\n')

    
async def list_inbox(graph: Graph):
    message_page = await graph.get_inbox()
    if message_page:
        # Output each message's details
        for message in message_page:
            print('Message:', message.subject)
            if (message.from_ and
                message.from_.email_address):
                print('  From:', message.from_.email_address.name or 'NONE')
            else:
                print('  From: NONE')
            print('  Status:', 'Read' if message.is_read else 'Unread')
            print('  Received:', message.received_date_time)
            if message.body.content:
                print('Message body: ', html2text(message.body.content))

        # If @odata.nextLink is present
        more_available = message_page.odata_next_link is not None
        print('\nMore messages available?', more_available, '\n')

async def list_deleted_items(graph):
    h2t = HTML2Text()
    h2t.ignore_links = True
    message_page = await graph.get_deleted_items()
    if message_page:
        for message in message_page:
            with open('deleted_items.jsonl', 'a', encoding='utf-8') as f:
                # for message in message_page:
                # Extract fields.
                from_email = (message.from_.email_address.address 
                                if message.from_ and message.from_.email_address else None)
    
                # toRecipients is a list of Recipient objects, if any.
                to_emails = []
                if message.to_recipients:
                    to_emails = [r.email_address.address for r in message.to_recipients if r.email_address]
    
                # extracting text from HTML.
                body_content = h2t.handle(message.body.content) if message.body else None
    
                record = {
                    "id": message.id,
                    "from": from_email,
                    "to": to_emails,
                    "isRead": message.is_read,
                    "subject": message.subject,
                    "body": body_content,
                    "receivedDateTime": str(message.received_date_time) if message.received_date_time else None
                }
    
                # Write the record as a JSON line
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        print("Export completed.")
# async def send_mail(graph: Graph):
#     # TODO
#     return

# async def make_graph_call(graph: Graph):
#     # TODO
#     return

# Run main
asyncio.run(main())