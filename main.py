#!/usr/bin/env python

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime
from google.appengine.api import memcache, users
from google.appengine.ext import db, webapp
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import login_required
from oauth2client.appengine import CredentialsProperty, StorageByKeyName
from oauth2client.client import OAuth2WebServerFlow
import gdata.spreadsheet.service
import httplib2
import os
import pickle
import urllib
import db as mydb

FLOW = OAuth2WebServerFlow(
        # Visit https://code.google.com/apis/console to
        # generate your client_id, client_secret and to
        # register your redirect_uri.
        client_id='883052992731.apps.googleusercontent.com',
        client_secret='FnkhZgPvl8-rhmZpaIrhpbaC',
        scope='https://www.googleapis.com/auth/fusiontables',
        user_agent='gtags/1.0')

queryURL = "https://www.google.com/fusiontables/api/query?sql=%s"
insertSQL = "INSERT INTO <TABLEID> (timestamp, responseX, responseY) VALUES ('%s', %s, %s)"

memcacheClient = memcache.Client()

class Table(object):

    def __init__(self, db, table):
        self.db = db
        self.table = table.lower()

    def get(self, kvMap):
        return self.db.get(self.table, kvMap)

    def getOne(self, kvMap):
        return self.db.getOne(self.table, kvMap)

    def getAll(self):
        return self.db.getAll(self.table)

    def update(self, kvMap, vMap):
        return self.db.update(self.table, kvMap, vMap)

    def put(self, vMap):
        return self.db.put(self.table, vMap)

    def delete(self, kvMap):
        return self.db.delete(self.table, kvMap)

class Credentials(db.Model):
    credentials = CredentialsProperty()


class MainHandler(webapp.RequestHandler):

    @login_required
    def get(self):
        user = users.get_current_user()
        credentials = StorageByKeyName(
                Credentials, user.user_id(), 'credentials').get()

        if credentials is None or credentials.invalid == True:
            callback = self.request.relative_url('/oauth2callback')
            authorize_url = FLOW.step1_get_authorize_url(callback)
            memcacheClient.set("oauth-%s" % user.user_id(), pickle.dumps(FLOW))
            self.redirect(authorize_url)
        else:
            path = os.path.join(os.path.dirname(__file__), 'input.html')
            self.response.out.write(template.render(path, {}))

class OAuthHandler(webapp.RequestHandler):

    @login_required
    def get(self):
        user = users.get_current_user()
        flow = pickle.loads(memcacheClient.get("oauth-%s" % user.user_id()))
        if flow:
            credentials = flow.step2_exchange(self.request.params)
            StorageByKeyName(
                    Credentials, user.user_id(), 'credentials').put(credentials)
            self.redirect("/")
        else:
            pass

class ViewHandler(webapp.RequestHandler):
    
    def get(self):
        nick = 'wiki'
        email = 'wiki@gta.gs'
        password = 'w1k1w1k1'
        spreadsheetId = '0AntwXKY6rGRmdHAtdUlvMWR1NEpjWnNQamFYUHBzcFE'
        self.client = gdata.spreadsheet.service.SpreadsheetsService()
        self.client.email = email
        self.client.password = password
        self.client.source = nick
        self.spreadsheetId = spreadsheetId
        self.tableIdMap = {}
        self.tableMap = {}
        self.client.ProgrammaticLogin()
        feed = self.client.GetWorksheetsFeed(self.spreadsheetId)
        for entry in feed.entry:
            table = entry.title.text.lower()
            self.tableIdMap[table] = entry.id.text.rsplit('/', 1)[1]
            self.tableMap[table] = Table(self, table)
            worksheetId = self.tableIdMap[table]
            feed = self.client.GetListFeed(self.spreadsheetId, worksheetId)
            results = []
            for entry in feed.entry:
                results.append(([[(v.column, v.text)]] for v in entry.custom.values()))
            self.response.out.write(results)
            #path = os.path.join(os.path.dirname(__file__), 'view.html')
            #self.response.out.write(template.render(path, {results:feed.entry}))

class SubmitHandler(webapp.RequestHandler):

    def get(self):
        self.redirect("/")
    
    def post(self):
        user = users.get_current_user()
        credentials = StorageByKeyName(
                Credentials, user.user_id(), 'credentials').get()

        if credentials is None or credentials.invalid == True:
            self.redirect("/")
        else:
            http = httplib2.Http()
            http = credentials.authorize(http)
            x = self.request.get("x")
            y = self.request.get("y")
            url = insertSQL % (datetime.utcnow().isoformat(' ')[:19], x, y)
            (response, content) = http.request(queryURL % urllib.quote(url), "POST")
            self.response.set_status(response['status'])
            self.response.out.write(content)

def main():
    application = webapp.WSGIApplication(
            [
            ('/submit', SubmitHandler),
            ('/published', ViewHandler),
            ('/oauth2callback', OAuthHandler),
            ('/', MainHandler)
            ],
            debug=True)
    util.run_wsgi_app(application)

if __name__ == '__main__':
    main()
    
    

