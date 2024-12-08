from configparser import SectionProxy
from azure.identity import DeviceCodeCredential
from msgraph import GraphServiceClient
from msgraph.generated.users.item.user_item_request_builder import UserItemRequestBuilder
from msgraph.generated.users.item.mail_folders.item.messages.messages_request_builder import (
    MessagesRequestBuilder)
from msgraph.generated.users.item.send_mail.send_mail_post_request_body import (
    SendMailPostRequestBody)
from msgraph.generated.models.message import Message
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.recipient import Recipient
from msgraph.generated.models.email_address import EmailAddress

class Graph:
    settings: SectionProxy
    device_code_credential: DeviceCodeCredential
    user_client: GraphServiceClient

    def __init__(self, config: SectionProxy):
        self.settings = config
        client_id = self.settings['clientId']
        tenant_id = self.settings['tenantId']
        graph_scopes = self.settings['graphUserScopes'].split(' ')

        self.device_code_credential = DeviceCodeCredential(client_id, tenant_id = tenant_id)
        self.user_client = GraphServiceClient(self.device_code_credential, graph_scopes)


    async def get_user_token(self):
        graph_scopes = self.settings['graphUserScopes']
        access_token = self.device_code_credential.get_token(graph_scopes)
        return access_token.token
 
    async def get_user(self):
        # Only request specific properties using $select
        query_params = UserItemRequestBuilder.UserItemRequestBuilderGetQueryParameters(
            select=['displayName', 'mail', 'userPrincipalName']
        )

        request_config = UserItemRequestBuilder.UserItemRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        user = await self.user_client.me.get(request_configuration=request_config)
        return user
    
    async def get_inbox(self):
        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            # Only request specific properties
            select=['from', 'isRead', 'receivedDateTime', 'subject', 'body'],
            # Get at most 25 results
            top=25,
            # Sort by received time, newest first
            orderby=['receivedDateTime DESC']
        )
        request_config = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
            query_parameters= query_params
        )

        messages = await self.user_client.me.mail_folders.by_mail_folder_id('inbox').messages.get(
                request_configuration=request_config)
        return messages

    async def get_deleted_items(self):
        # This method is similar to get_inbox, but fetches messages from deletedItems folder
        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            select=['from', 'isRead', 'receivedDateTime', 'subject', 'body'],
            top=25,
            orderby=['receivedDateTime DESC']
        )
        request_config = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )
        all_messages = []
        messages_page = await self.user_client.me.mail_folders.by_mail_folder_id('deleteditems').messages.get(
            request_configuration=request_config
        )

        if messages_page and messages_page.value:
            all_messages.extend(messages_page.value)

        while messages_page and messages_page.odata_next_link:
            # Create a new MessagesRequestBuilder from the next link
            next_page_builder = MessagesRequestBuilder(self.user_client.request_adapter, messages_page.odata_next_link)
            messages_page = await next_page_builder.get()
            
            # messages_page = await self.user_client.me.mail_folders.by_mail_folder_id('deleteditems').messages.get(
            #     next_link=messages_page.odata_next_link
            # )
            if messages_page and messages_page.value:
                all_messages.extend(messages_page.value)

        return all_messages

        # messages = await self.user_client.me.mail_folders.by_mail_folder_id('deleteditems').messages.get(
        #     request_configuration=request_config
        # )
        # return messages
