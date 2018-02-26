from __future__ import print_function
import httplib2
import os
import json

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

import logging
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

class Sheet:
    def __init__(self, id, secret):
        self.scopes = 'https://www.googleapis.com/auth/spreadsheets'
        self.application_name = 'Google Sheets API Python Quickstart'
        self.spreadsheetId = id
        self.credentials = self.get_credentials(secret)
        http = self.credentials.authorize(httplib2.Http())
        discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                        'version=v4')
        self.service = discovery.build('sheets', 'v4', http=http,
                              discoveryServiceUrl=discoveryUrl)


    def get_credentials(self, secret):
        """Gets valid user credentials from storage.

        If nothing has been stored, or if the stored credentials are invalid,
        the OAuth2 flow is completed to obtain the new credentials.
    
        Returns:
            Credentials, the obtained credential.
        """
        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir,
                                       'sheets.googleapis.com-python-quickstart.json')

        store = Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(secret, self.scopes)
            flow.user_agent = self.application_name
            if flags:
                credentials = tools.run_flow(flow, store, flags)
            else: # Needed only for compatibility with Python 2.6
                credentials = tools.run(flow, store)
            print('Storing credentials to ' + credential_path)
        return credentials

    def get_rows(self, rangeName):
        request = self.service.spreadsheets().get(spreadsheetId=self.spreadsheetId, ranges=rangeName, fields="sheets/data/rowData/values")
        response = request.execute()
        return response['sheets'][0]['data'][0]['rowData']

    def add_rows(self, range, data):
        result = self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheetId, range=range, valueInputOption="USER_ENTERED", body={'values': data}).execute()
        print(result)

